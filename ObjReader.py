# aspects of file format not supported
# doesn't read material libraries
# doesn't do smoothing groups (s)
# doesn't do any wacky parametric surfaces (vp, cstype, deg, bmat, step)
# poly line (l)
# curves (curve, curv2, surf)
# Free-form stuff ( parm, trim, hole, scrv, sp, end )
# connectivity (c)
# some grouping ( mg, o )
# Display/render attributes ( bevel, c_interp, d_interp, lod, shadow_obj, trace_obj, ctech, stech)
# see http://www.martinreddy.net/gfx/3d/OBJ.spec for details on above tags


import re
from primitives import *
from datetime import datetime
from copy import deepcopy
from struct import pack
#from Horde3D import Horde3DMesh

VERSION = '0.9'

FLOAT_EXP = '[-\+]?[0-9]+\.?[0-9]*e[-\+]?[0-9]+|[-\+]?[0-9]+\.?[0-9]*'
UINT_EXP = '[0-9]+'
# (?:_){0,2} - match 0 to 2 instances of previous expression
VERT_PAT = re.compile('\s*v\s+(%s)\s+(%s)\s(%s)' % (FLOAT_EXP, FLOAT_EXP, FLOAT_EXP) )
UV_PAT = re.compile('\s*vt\s+(%s)\s+(%s)' % (FLOAT_EXP, FLOAT_EXP) )
NORM_PAT = re.compile('\s*vn\s+(%s)\s+(%s)\s(%s)' % (FLOAT_EXP, FLOAT_EXP, FLOAT_EXP) )
FACE_PAT = re.compile('\s*f\s+(%s(?:\\%s){0,2})' % (UINT_EXP, UINT_EXP) )
MTLLIB_PAT = re.compile('\s*mtllib\s+([a-zA-Z_0-9\./]+\.[a-zA-Z0-9]{3})')
GRP_PAT = re.compile('\s*g\s+([a-zA-Z][a-zA-Z_0-9]*)')
USEMTL_PAT = re.compile('\s*usemtl\s+([a-zA-Z][a-zA-Z_0-9\(\)]*)')

##mtllib	wooddoll.mtl
##g Figure_4
##g Figure_4
##usemtl skin

# face format is f vert/uv/norm

def getFaceData( data ):
    """Extracts vertex, normal and uv indices for a face definition.
        data consists of strings: i, i/i, i//i, or i/i/i.
        All strings in the data should be of the same format. Format determines what
        indices are defined"""
    dataLists = [[], [], []]
    for s in data:
        indices = s.split('/')
        for i in range(len(indices)):
            try:
                index = int( indices[i] )
                if ( i == 0 and index in dataLists[i] ):
                    raise IOError
                dataLists[i].append( int( indices[i] ) )
            except ValueError:
                pass
    # validate the data -- i.e. lengths should equal all be equal, unless length = 0
    if ( ( len(dataLists[0]) != len(dataLists[1] ) and len(dataLists[1]) != 0 ) or
         ( len(dataLists[0] ) != len( dataLists[2] ) and len(dataLists[2]) != 0 ) ):
        raise IOError
    return dataLists

class Material:
    """Material class"""
    def __init__( self, name = 'default' ):
        self.isAssigned = False
        self.name = name
        self.diffuse = [0, 60, 128]        # ranges from 0-255

    def setDiffuse( self, r, g, b ):
        self.diffuse = [r, g, b]        

    def OBJFormat( self ):
        """Writes material definition to obj text format"""
        s = 'newmtl %s\n' % (self.name)
        r, g, b = self.diffuse
        s += 'Kd %d %d %d' % (r, g, b)
        return s
    
    def PLYBinaryFormat( self ):
        """Writes material definition in binary PLY format"""
        # for now it simply outputs the diffuse r, g, b vlaues
        r, g, b = self.diffuse
        return pack('>uuu', r, g, b )         

#ILLUM_RGB_PAT = re.compile('\s*[(?:K[asd])(?:Tf)]')
class MtlLib:
    """Class to handle material library"""
    def __init__( self, filename = None ):
        if ( filename != None ):
            self.materials = {'default':Material()}
            self.readFile( filename )

    def readFile( self, filename ):
        file = open( filename, 'r' )
        lineNum = 0
        currMat = None
        for line in file.xreadlines():
            lineNum +=1
            line = line.strip()
            if ( not line ):
                continue
            elif ( line.startswith( '#' ) ):
                continue
            elif ( line.startswith( 'newmtl' ) ):       # new material
                try:
                    name = line.split()[-1]
                    currMat = Material( name )
                    if ( self.materials.has_key( name ) ):
                        raise IOError, "Error on newmtl definition - library already has material with that name.  Line: %d: %s" % (lineNum, line)
                    else:
                        self.materials[name] = currMat
                except:
                    raise IOError, "Error on newmtl definition.  Line: %d: %s" % (lineNum, line)
            elif ( currMat == None ):
                raise IOError, "Reading line without having an active material.  Line: %d: %s" % ( lineNum, line )
            # following settings can use the format:
            #   1 Ka r g b
            #   2 Ka spectral name.rfl <factor>
            #   3 Ka xyz x y z}
            #   Only #1 is supported
            elif ( line.startswith( 'Ka' ) ):           # ambient color
                pass                                    # only supports Ka rgb
            elif ( line.startswith( 'Kd' ) ):           # diffuse color
                try:
                    r, g, b = line.split()[-3:]
                    currMat.setDiffuse( r, g, b )
                except:
                    raise IOError, "Error on Kd definition.  Line: %d: %s" % (lineNum, line) 
            elif ( line.startswith( 'Ks' ) ):           # specular color
                pass
            elif ( line.startswith( 'Tf' ) ):           # Transmission filter - determines which colors are permitted through
                pass
            # illumination model is illum #
            #   0 color on, ambient off
            #   1 Color on and Ambient on
            #   2 Highlight on
            #   3 Reflection on and Ray trace on
            #   4 Transparency: Glass on Reflection: Ray trace on
            #   5 Reflection: Fresnel on and Ray trace on
            #   6 Transparency: Refraction on Reflection: Fresnel off and Ray trace on
            #   7 Transparency: Refraction on Reflection: Fresnel on and Ray trace on
            #   8 Reflection on and Ray trace off
            #   9 Transparency: Glass on Reflection: Ray trace off
            #   10 Casts shadows onto invisible surfaces
            elif ( line.startswith( 'illum' ) ):        # illumination model
                pass
            elif ( line.startswith( 'd' ) ):            # dissolve (aka opacity) - optional -halo argument
                pass
            elif ( line.startswith( 'Ns' ) ):            # Specular exponent
                pass
            elif ( line.startswith( 'sharpness' ) ):            # sharpness of reflections
                pass
            elif ( line.startswith( 'Ni' ) ):            # index of refraction
                pass
            # map parameters have the format map_ -options args filename
            # possible options
            #   -blendu on | off    horizontal texture blending
            #   -blendv on | off    vertical texture blending
            #   -bm mult            bump mlutiplier                 bump maps only
            #   -cc on | off        color correction                only for color maps
            #   -imfchan r | g | b | m | l | z                      only for scalar maps
            #   -clamp on | off     clamping
            #   -mm base gain
            #   -o u v w            offset map origin
            #   -s u v w            scales image
            #   -t u v w            turbulence
            #   -texres value       resolution of texture created
            elif ( line.startswith( 'map_Ka' ) ):            # 
                pass
            elif ( line.startswith( 'map_Kd' ) ):            # ???
                pass
            elif ( line.startswith( 'map_Ks' ) ):            # ???
                pass
            elif ( line.startswith( 'map_Ns' ) ):            # ???
                pass
            elif ( line.startswith( 'map_d' ) ):            # ???
                pass
            elif ( line.startswith( 'map_aat' ) ):          # determiens if anti-aliasing is on for this one material
                pass
            elif ( line.startswith( 'disp' ) ):            # ???
                pass
            elif ( line.startswith( 'decal' ) ):            # ???
                pass
            elif ( line.startswith( 'bump' ) ):            # ???
                pass
            # material reflection map -- (environment reflection map)
            #   refl -type sphere -options -args filename
            #   -type: sphere, cube_side, cube_top, cube_bottom, cube_front, cube_back, cube_left, cube_right
            elif ( line.startswith( 'refl' ) ):            # ???
                pass
            elif ( line.startswith( 'map_Bump' ) ):            # funny U of U version of bump map????
                pass

    def OBJFormat( self ):
        """Writes material library to obj text format"""
        keys = self.materials.keys()
        keys.sort()
        s = ''
        for key in keys:
            mat = self.materials[ key ]
            if ( mat.isAssigned ):
                s += mat.OBJFormat()
        return s
        
                
class Group:
    """Group of faces in obj file"""
    def __init__(self, name):
        self.name = name
##        self.currMatName = matName
        # simply a list of faces
##        self.currMatGrp = []
        # a mapping from material name to list of faces
        self.materials = {}#{self.currMatName:[]}

    def __repr__( self ):
        return 'Group( %s ) with %d faces and %d materials' % ( self.name, len( self ), len( self.materials ) )

    def __str__( self ):
        return 'Group( %s ) with %d faces' % ( self.name, len( self ) )    

    def __len__(self):
        count = 0
        for matGrp in self.materials.values():
            count += len(matGrp)
        return count

##    def addMaterial( self, mat ):
##        self.currMatName = mat
##        if ( self.materials.has_key( mat ) ):
##            self.currMatGrp = self.materials[mat]
##        else:
##            self.currMatGrp = []
##            self.materials[ mat ] = self.currMatGrp

    def addFace( self, f, matName ):
        if ( self.materials.has_key( matName ) ):
            self.materials[ matName ].append( f )
        else:
            self.materials[ matName ] = [ f ]
##        self.currMatGrp.append( f )

    def OBJFormat( self ):
        """Outputs the group information into obj specific format"""
        #s = 'g %s' % self.name
        s = ''
        for mat, matGrp in self.materials.items():
            if ( matGrp ):
                s += '\nusemtl %s' % mat
                for f in matGrp:
                    s += '\n%s' % f.OBJFormat()
        if ( s ):
            return 'g %s' % self.name + s
        else:
            return ''

    def PLYAsciiFormat( self, useNorms, useUvs ):
        """Outputs the group information into ply ascii specific format"""
        #s = 'g %s' % self.name
        s = ''
        for mat, matGrp in self.materials.items():
            if ( matGrp ):
                for f in matGrp:
                    s += '\n%s' % f.PLYAsciiFormat( useNorms, useUvs )
        return s

    def PLYBinaryFormat( self, useNorms, useUvs ):
        """Outputs the group information into ply ascii specific format"""
        #s = 'g %s' % self.name
        s = ''
        for mat, matGrp in self.materials.items():
            if ( matGrp ):
                for f in matGrp:
                    s += '%s' % f.PLYBinaryFormat( useNorms, useUvs )
        return s    

    def triangulate( self ):
        """Returns a triangulated version of the group"""
        hasFaces = False
        newGrp = Group( self.name )
        for mat, matGrp in self.materials.items():
            if ( matGrp ):
                hasFaces = True
                newMatGrp = []
                newGrp.materials[ mat ] = newMatGrp
                for f in matGrp:
                    newMatGrp += f.triangulate()
        if (hasFaces):
            return newGrp
        else:
            return None
        
class ObjFile:
    class FaceIterator:
        """An iterator through the objfile's faces

        It will iterate across all faces, returning the face data *and* the group to
        which the face belongs.
        """
        def __init__( self, objfile ):
            self.mesh = objfile
            self.groups = objfile.groups.values()
            self.grpIndex = 0
            self.matGrps = self.groups[0].materials.values()
            self.matGrpIndex = 0
            self.faces = self.matGrps[0]
            self.faceIndex = -1

        def __iter__( self ):
            return self

        def next( self ):
            self.faceIndex += 1
            if (self.faceIndex >= len( self.faces ) ):
                self.faceIndex = 0
                                    # TODO: Replace this test with an object clean up
                                    # that removes empty materials from a group
                tryAgain = True     # use this to skip empty groups
                while ( tryAgain ): 
                    self.matGrpIndex += 1
                    if ( self.matGrpIndex >= len( self.matGrps ) ):
                        self.matGrpIndex = 0
                        self.grpIndex += 1
                        if ( self.grpIndex >= len( self.groups) ):
                            raise StopIteration, "End of faces"
                        else:
                            self.matGrps = self.groups[ self.grpIndex ].materials.values()
                    if ( self.matGrps ):
                        self.faces = self.matGrps[ self.matGrpIndex ]
                        if ( self.faces ):
                            tryAgain = False
            try:
                return self.faces[ self.faceIndex ], self.groups[ self.grpIndex ].name
            except IndexError:
                print "Error getting face at index %d" % (self.faceIndex)
                raise StopIteration
            
        
    def __init__( self, filename = None ):
        self.vertSet = []
        self.normSet = []
        self.uvSet = []
        self.groups = {}#{'default':Group('default')}
        self.currGroup = None #self.groups['default']
        self.mtllib = None
        self.currMatName = 'default'
        # A map from each vertex, normal, uv and face read and which line it was found.
        self.object_line_numbers = {}
        if ( filename != None ):
            self.readFile( filename )

    def summary( self ):
        '''Creates a summary string of the obj file'''
        s = "OBJ file"
        s += '\n\t%d vertices' % ( len ( self.vertSet ) )
        s += '\n\t%d normals' % ( len ( self.normSet ) )
        s += '\n\t%d uvs' % ( len ( self.uvSet ) )
        grpCount, faceCount = self.faceStats()
        s += '\n\t%d faces in %d groups' % ( faceCount, grpCount )
        s += '\n\t%d materials' % ( self.materialCount() )
        return s
    
    def readFile( self, filename ):
        with open(filename, 'r') as file:
            self.readFileLike(file)

    def readFileLike(self, file):
        '''Reads the obj data from the given file-like object. Must have the xreadlines()
        method'''
        lineNum = 0
        for line in file.xreadlines():
            lineNum += 1
            line = line.strip()
            if ( not line ):
                continue
            elif ( line.startswith('vn') ):       # vertex normal
                match = NORM_PAT.match(line)
                if ( match ):
                    try:
                        self.normSet.append(Vector3( match.group(1), match.group(2), match.group(3) ) )
                        self.object_line_numbers[self.normSet[-1]] = lineNum
                    except:
                        raise IOError, "Expected vertex normal definition, line %d -- read: %s" % ( lineNum, line)
                else:
                    raise IOError, "Expected vertex normal definition, line %d -- read: %s" % ( lineNum, line)
            elif ( line.startswith('vt') ):     # texture vertex
                match = UV_PAT.match(line)
                if ( match ):
                    try:
                        self.uvSet.append(Vector2( match.group(1), match.group(2) ) )
                        self.object_line_numbers[self.uvSet[-1]] = lineNum
                    except:
                        raise IOError, "Expected texture vertex definition, line %d -- read: %s" % ( lineNum, line)
                else:
                    raise IOError, "Expected texture vertex definition, line %d -- read: %s" % ( lineNum, line)
            elif ( line.startswith('v') ):      # vertex
                match = VERT_PAT.match(line)
                if ( match ):
                    try:
                        v = Vector3( match.group(1), match.group(2), match.group(3) )
                        self.vertSet.append( v )
                        self.object_line_numbers[v] = lineNum
                    except:
                        raise IOError, "Expected vertex definition, line %d -- read: %s" % ( lineNum, line)
                else:
                    raise IOError, "Expected vertex definition, line %d -- read: %s" % ( lineNum, line)
            elif ( line.startswith('#') ):      # comment
                continue
            elif ( line.startswith('mtllib') ):   # material library
                match = MTLLIB_PAT.match(line)
                if ( match ):
                    try:
                        if ( self.mtllib ):
                            raise IOError, "Already have mtllib defined for file, line %d -- read: %s" % ( lineNum, line)
                        self.mtllib = match.group(1)
                    except:
                        raise IOError, "Expected mtllib definition, line %d -- read: %s" % ( lineNum, line)
                else:
                    raise IOError, "Expected mtllib definition, line %d -- read: %s" % ( lineNum, line)
            elif ( line.startswith('g') ):          # group definition
                match = GRP_PAT.match(line)
                if ( match ):
                    try:
                        groupName = match.group(1)
                    except:
                        raise IOError, "Expected group definition, line %d -- read: %s" % ( lineNum, line)
                    if ( self.groups.has_key( groupName ) ):
                         self.currGroup = self.groups[ groupName ]
                    else:
                        self.currGroup = Group( groupName )
                        self.groups[ groupName ] = self.currGroup
##                    self.currGroup.addMaterial( self.currMatName )
                else:
                    pass # an empty group name will be skipped
                    #raise IOError, "Expected group definition, line %d -- read: %s" % ( lineNum, line )
            elif ( line.startswith('usemtl') ):     # material application
                match = USEMTL_PAT.match( line )
                if ( match ):
                    try:
##                        self.currGroup.addMaterial( match.group(1) )
                        self.currMatName = match.group(1)
                    except:
                        raise IOError, "Expected usemtl definition, line %d -- read: %s" % ( lineNum, line )
                else:
                    raise IOError, "Expected usemtl definition, line %d -- read: %s" % ( lineNum, line )
            elif ( line.startswith('f') and not line.startswith('fo') ):          # face definition
                tokens = line.split()[1:]           # extract f
                try:
                    verts, uvs, norms = getFaceData( tokens )
                except IOError:
                    continue
                    #raise IOError, "Poorly formatted face definition, line %d -- read: %s" % ( lineNum, line )
                f = Face( verts, norms, uvs )
                if ( self.currGroup == None ):
                    groupName = 'no_name'
                    self.currGroup = Group( groupName )
                    self.groups[ groupName ] = self.currGroup
                self.currGroup.addFace( f, self.currMatName )
                self.object_line_numbers[f] = lineNum
            

    def writeOBJ( self, outfile ):
        """Writes obj to the file object"""
        outfile.write("# OBJ written by python obj reader version %s -- %s\n" % (VERSION, datetime.today() ) )
        outfile.write("# %d vertices\n" % (len(self.vertSet ) ) )
        outfile.write("# %d texture vertices\n" % (len(self.uvSet) ) )
        outfile.write("# %d vertex normals\n" % (len(self.normSet) ) )
        gCount, fCount = self.faceStats()
        outfile.write("# %d groups\n" % (gCount))
        outfile.write("# %d faces\n" % (fCount))
        outfile.write("\n")
        outfile.write("# vertices\n")
        for v in self.vertSet:
            outfile.write("v %g %g %g\n" % (v.x, v.y, v.z ) )
        if ( self.normSet ):
            outfile.write("\n# vertex normals\n" )
            for v in self.normSet:
                outfile.write("vn %g %g %g\n" % (v.x, v.y, v.z) )
        if ( self.uvSet ):
            outfile.write("\n# texture vertices\n" )
            for v in self.uvSet:
                outfile.write("vt %g %g\n" % (v.x, v.y) )
        for gName, grp in self.groups.items():
            outfile.write( "%s\n" % grp.OBJFormat() )

    def writePLYAscii( self, outfile, useNorms = False, useUvs = False, useMat = False ):
        """Writes ascii ply to the file object"""
        useNorms = useNorms and self.normSet
        useUvs = useUvs and self.uvSet
        outfile.write("ply\n")
        outfile.write("format ascii 1.0\n")
##        outfile.write("comment written by python objreader version %s\n" % VERSION )
##        outfile.write("comment date: %s\n" % datetime.today() )
        outfile.write("element vertex %d\n" % ( len(self.vertSet) ) )
        outfile.write("property float x\n")
        outfile.write("property float y\n")
        outfile.write("property float z\n")
        if ( useMat ):
            outfile.write("property uchar red\n")
            outfile.write("property uchar green\n")
            outfile.write('property uchar blue\n')
        if ( useNorms ):
            outfile.write("element normal %d\n" % ( len( self.normSet) ) )
            outfile.write('property float x\n')
            outfile.write('property float y\n')
            outfile.write('property float z\n')
        if ( useUvs ):
            outfile.write("element uv %d\n" % ( len( self.uvSet ) ) )
            outfile.write('property float u\n')
            outfile.write('property float v\n')
        gCount, fCount = self.faceStats()
        outfile.write("element face %d\n" % ( fCount ) )
        outfile.write("property list uchar int vertex_index\n")
        if ( useNorms ):
            outfile.write("property list uchar int norm_index\n")
        if ( useUvs ):
            outfile.write("property list uchar int uv_index\n")
        outfile.write("end_header")
        
        for v in self.vertSet:
            outfile.write("\n%g %g %g" % (v.x, v.y, v.z ) )
        if ( useNorms ):
            for n in self.normSet:
                outfile.write("\n%g %g %g" % (n.x, n.y, n.z ) )
        if ( useUvs ):
            for uv in self.uvSet:
                outfile.write("\n%g %g" % (uv.x, uv.y) )
##        if ( self.normSet ):
##            outfile.write("\n# vertex normals\n" )
##            for v in self.normSet:
##                outfile.write("vn %g %g %g\n" % (v.x, v.y, v.z) )
##        if ( self.uvSet ):
##            outfile.write("\n# texture vertices\n" )
##            for v in self.uvSet:
##                outfile.write("vt %g %g\n" % (v.x, v.y) )
        for gName, grp in self.groups.items():
            outfile.write( "%s" % grp.PLYAsciiFormat( useNorms, useUvs ) )
        outfile.write('\n')

    def writePLYBinary( self, outfile, useNorms = False, useUvs = False ):
        """Writes ascii ply to the file object"""
        outfile.write("ply\x0a")
        outfile.write("format binary_big_endian 1.0\x0a")
##        outfile.write("comment written by python objreader version %s\n" % VERSION )
##        outfile.write("comment date: %s\n" % datetime.today() )
        outfile.write("element vertex %d\x0a" % ( len(self.vertSet) ) )
        outfile.write("property float x\x0a")
        outfile.write("property float y\x0a")
        outfile.write("property float z\x0a")
        if ( useMat ):
            outfile.write("property uchar red\x0a")
            outfile.write("property uchar green\x0a")
            outfile.write('property uchar blue\x0a')
        gCount, fCount = self.faceStats()
        outfile.write("element face %d\x0a" % ( fCount ) )
        outfile.write("property list uchar int vertex_indices\x0a")
        outfile.write("end_header\x0a")
        
        for v in self.vertSet:
            outfile.write(pack('>fff', v.x, v.y, v.z))
##        if ( self.normSet ):
##            outfile.write("\n# vertex normals\n" )
##            for v in self.normSet:
##                outfile.write("vn %g %g %g\n" % (v.x, v.y, v.z) )
##        if ( self.uvSet ):
##            outfile.write("\n# texture vertices\n" )
##            for v in self.uvSet:
##                outfile.write("vt %g %g\n" % (v.x, v.y) )
        for gName, grp in self.groups.items():
            outfile.write( "%s" % grp.PLYBinaryFormat(useNorms, useUvs) )       

    # the geo format has several requirements
    #   1. There must be a one-to-one correspondence between vertices and normals
    #       i.e. I can't have four vertices all sharing the same normal,
    #       I would need four instances of the same normal
    #   2. I have to generate a tangent and binormal vector for each vertex
    #   3. All binary values are LITTLE Endian
#    def writeGEO( self, outfile ):
#        """Writes two a binary, Horde3D geo file"""
#        geoMesh = Horde3DMesh()
#        geoMesh.makeFromObjFile( self )
#        geoMesh.writeToFile( outfile )                       
    
    def faceStats( self ):
        """Returns group and face count"""
        faceCount = 0
        groupCount = 0
        for grpName, grp in self.groups.items():
            if ( len(grp) ):
                faceCount += len(grp)
                groupCount += 1
        return groupCount, faceCount

    def materialCount( self ):
        '''Reports the number of materials found.'''
        matCount = 0
        for grpName, grp in self.groups.items():
            matCount += len( grp.materials )
        return matCount

    def triangulate( self ):
        """Returns a triangulated version of this obj"""
        newOBJ = ObjFile()
        newOBJ.vertSet = self.vertSet
        newOBJ.normSet = self.normSet
        newOBJ.uvSet = self.uvSet
        newOBJ.mtllib = self.mtllib
        for grpName, grp in self.groups.items():
            g = grp.triangulate()
            if ( g ):
                newOBJ.groups[ grpName ] = g
        return newOBJ 
    def getFaceIterator( self ):
        return ObjFile.FaceIterator( self )

    def getFaceNormal( self, face ):
        """Returns normal of the provided face"""
        # argument is an actual face object, not an index into it
        # assumes triangles
        v1 = self.vertSet[ face.verts[0] ]
        v2 = self.vertSet[ face.verts[1] ]
        v3 = self.vertSet[ face.verts[2] ]
        e1 = v2 - v1
        e2 = v3 - v1
        norm = e1.cross(e2)
        norm.normalize_ip()
        return norm
def usage():
    print "ObjReader -- reads wavefront .obj files and processes them"
    print ""
    print "Usage:  python ObjReader -arg1 value1, -arg2 value2..."
    print "Options:"
    print "   -in file.obj  - the wavefront obj file to operate on"
    print "                 - no input, no action"
    print "   -bp file.ply  - file to write binary ply data"
    print "                 - by default no binary ply file written"
    print "   -ap file.ply  - file to write ascii ply data"
    print "                 - by default no ascii ply file written"
    print "   -obj file.obj - file to write triangulated obj data"
    print "                 - defaults to file_t.obj"
    print "   -geo file.geo - file to write binary geo data"
    print "                 - by default, no geo file written"
    print "   -nt           - don't triangulate"
    print "                 - without this command line, the obj will be triangulated"
    print "   -mat          - Use materials, if available"
    print "   -uv           - output uvs"
    print "   -norm         - output normals"
    print ""
    print " If any output files are specified, that is exactly what will be written."
    print " If no output files are specified, an obj of the triangulated data will be"
    print " written to the name file_t.obj"

if __name__ == "__main__":
    import sys, os
    from commandline import ParamManager
    pMan = ParamManager(sys.argv[1:])
    inputName = pMan['in']
    if ( inputName == None ):
        usage()
        sys.exit(1)

    objTName = pMan['obj']
    asciiPlyName = pMan['ap']
    binaryPlyName = pMan['bp']
    geoName = pMan['geo']
    noTris = pMan['nt']
    useMat = pMan['mat']
    useUvs = pMan['uv']
    useNorms = pMan['norm']

    if (objTName == None and asciiPlyName == None and binaryPlyName == None ):
        tokens = os.path.splitext( inputName[0] )
        objTName = [tokens[0] + '_t.obj']
    
    obj = ObjFile( inputName[0] )
    if ( not noTris ):
        obj = obj.triangulate()

    if ( objTName ):
        outFile = open( objTName[0], 'w' )
        obj.writeOBJ( outFile )
        outFile.close()
    if ( asciiPlyName ):
        outFile = open( asciiPlyName[0], 'w' )
        obj.writePLYAscii( outFile, useNorms, useUvs )
        outFile.close()
    if ( binaryPlyName ):
        outFile = open( binaryPlyName[0], 'wb' )
        obj.writePLYBinary( outFile, useNorms, useUvs )
        outFile.close()
    if ( geoName ):
        outFile = open( geoName[0], 'wb' )
        obj.writeGEO( outFile )
        outFile.close()
