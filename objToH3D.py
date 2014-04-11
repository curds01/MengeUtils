# Converts an obj file into a Horde3D scene/geometry/material file set.
#
#   1) Only supports static geometry.

# TODO:
#   1) Vertices
#       It is important that if I have normals and/or uvs that I
#       have total 1-to-1 correspondence between positions and normals
#       Essentially, I have to look at each referenced tuple and for
#       each unique tuple, I get a unique ID.

import ObjReader
import struct
import numpy as np

UVS = 6
POS = 0
NORM = 1

def writeVPos( file, data ):
    '''Writes the block of vertex position data to the h3d geometry file.

    @param;     file        An open file for writing.
    @param:     data        The array of data.
    '''
    file.write( struct.pack( 'I', POS ) )    # id for vertex positions
    file.write( struct.pack( 'I', 12 ) )    # number of floats * 4 bytes per float in the data type
    #write each vertex
    for x, y, z in data:
        file.write( struct.pack( 'fff', x, y, z ) )
    
def writeNorm( file, data ):
    '''Writes the block of vertex normal data to the h3d geometry file as shorts
    This assumes that all values in data lie in the range [0,1].

    @param;     file        An open file for writing.
    @param:     data        The array of data.
    '''
    data = np.array( data, dtype=np.float32 )
    shorts = np.array( data * (( 1 << 15 ) - 1 ), dtype=np.int16 )
    file.write( struct.pack( 'I', NORM ) )    # id for vertex positions
    file.write( struct.pack( 'I', 6 ) )     # number of shorts * 2 bytes in the data type
    #write each vertex
    for x, y, z in shorts:
        file.write( struct.pack( 'hhh', x, y, z ) )
    
def writeUV( file, data ):
    '''Writes the block of vertex UV data to the h3d geometry file.

    @param;     file        An open file for writing.
    @param:     data        The array of data.
    '''
    file.write( struct.pack( 'I', UVS ) )    # id for vertex positions
    file.write( struct.pack( 'I', 8 ) )     # number of floats * 4 bytes in the data type
    #write each vertex
    for x, y in data:
        file.write( struct.pack( 'ff', x, y ) )


def getPNUV( key, verts, norms, uvs, vertData ):
    '''Given a vertex key, populates the vertData with the position (P)
    normal (N), and uv coordinates (UV) referenced by the key from obj file.

    @param:     key         A 3-tuple of ints.  Indices into position, normal, and uvs, respectively.
    @param:     verts       List of vertices
    @param:     norms       List of normals
    @param:     uvs         List of uvs
    @param:     vertData    A dictionary to load the results into.
    '''
    v = verts[ key[0] - 1 ]
    vertData[ POS ].append( ( v.x, v.y, v.z ) )
    v = norms[ key[1] - 1 ]
    vertData[ NORM ].append( ( v.x, v.y, v.z ) )
    v = uvs[ key[2] - 1 ]
    vertData[ UVS ].append( ( v.x, v.y ) )
    
def getPN( key, verts, norms, uvs, vertData ):
    '''Given a vertex key, populates the vertData with the position (P)
    and normal (N) referenced by the key from obj file.

    @param:     key         A 2-tuple of ints.  Indices into position, normal, and uvs, respectively.
    @param:     verts       List of vertices
    @param:     norms       List of normals
    @param:     uvs         List of uvs
    @param:     vertData    A dictionary to load the results into.
    '''
    v = verts[ key[0] - 1 ]
    vertData[ POS ].append( ( v.x, v.y, v.z ) )
    v = norms[ key[1] - 1 ]
    vertData[ NORM ].append( ( v.x, v.y, v.z ) )
    
def getPUV( key, verts, norms, uvs, vertData ):
    '''Given a vertex key, populates the vertData with the position (P)
    and uv coordinates (UV) referenced by the key from obj file.

    @param:     key         A 2-tuple of ints.  Indices into position, normal, and uvs, respectively.
    @param:     verts       List of vertices
    @param:     norms       List of normals
    @param:     uvs         List of uvs
    @param:     vertData    A dictionary to load the results into.
    '''
    v = verts[ key[0] - 1 ]
    vertData[ POS ].append( ( v.x, v.y, v.z ) )
    v = uvs[ key[1] - 1 ]
    vertData[ UVS ].append( ( v.x, v.y ) )
    
def getP( key, verts, norms, uvs, vertData ):
    '''Given a vertex key, populates the vertData with the position (P)
    referenced by the key from obj file.

    @param:     key         An int.  Indices into position, normal, and uvs, respectively.
    @param:     obj         An instance of ObjFile.
    @param:     vertData    A dictionary to load the results into.
    '''
    v = verts[ key ]
    vertData[ POS ].append( ( v.x, v.y, v.z ) )
    
def getMatGroups( obj ):
    '''Given an ObjFile, returns a dictionary mapping unique materials to all
        triangles with that material.

    @param:     obj     An instance of ObjFile.
    @returns:   A dictionary: material name -> list of faces.
    '''
    matGroups = {}
    for grpName, grp in obj.groups.items():
        for mat, tris in grp.materials.items():
            if ( not matGroups.has_key( mat ) ):
                matGroups[ mat ] = []
            matGroups[ mat ] += tris
    return matGroups

class MeshGroup:
    '''Class for tracking a Horde3D mesh group -- a portion of a model.'''
    def __init__( self, matName, vStart, tStart ):
        '''Constructor

        @param:     matName         The name of the material.
        @param:     vStart          The index that marks the beginning of the contiguous
                                    block of vertices used by this group.
        @param:     tStart          The index that marks the beginning of the continguous
                                    block of vertex indices used by this group.
        '''
        self.matName = matName
        self.vertStart = vStart
        self.vertEnd = vStart   # this gets updated later
        self.triIdxStart = tStart
        self.tris = []
        
    def addTriangle( self, tri ):
        '''Adds a triangle to the MeshGroup.

        @param:     tri         A 3-tuple of ints (references to horde3d vertices.
        '''
        self.tris.append( tri )

    def __len__( self ):
        '''Report the number of triangles'''
        return len( self.tris )
    

def getVertices( matGroups, verts, norms=[], uvs=[] ):
    '''Given material triangle groups, vertices, norms, and uvs, creates a list of
    MeshGroups and a set of Horde3D vertices.  Horde3D vertices satisfy the following
    constraints:

    1) A vertex is fully defined with all available per-vertex attributes.  If a triangle
        uses vertex v, normal n, and uv t, then a vertex definition must exist such that
        the ith position, normal and uv coordinate combine those three.
    2) Triangles sharing a common material must appear in a contiguous block.
    3) The vertices used by a continguous block of triangles must themselves form
        a contiguous block in the vertex definitions.
    4) Vertices cannot be shared across contiguous blocks.

    @returns:       A 2-tuple: ( meshGroups, vertData ), such that:
                        meshGroups is simply an ordered list of MeshGroup instances.
                        vertData: a dictionary mapping the vertex attribute to the
                            list of vertex attribute values.  All attributes should be
                            of the same length.
    '''
    vertData = None
    # Determine the unique vertices used in the group
    tupleMap = {}       # mapping from key to index in vertData
    keyFunc = None      # generate key from triangle
    # Assuming that if normals and uvs are defined, they are referenced.
    vCount = len( verts )
    nCount = len( norms )
    uvCount = len( uvs )
    if ( nCount and uvCount ):
        keyFunc = lambda face, idx: ( face.verts[idx], face.norms[idx], face.uvs[idx] )
        dataFunc = getPNUV
        vertData = { POS:[], UVS:[], NORM:[] }
    elif ( nCount ):
        keyFunc = lambda face, idx: ( face.verts[idx], face.norms[idx] )
        dataFunc = getPN
        vertData = { POS:[], NORM:[] }
    elif ( uvCount ):
        dataFunc = getPUV
        keyFunc = lambda face, idx: ( face.verts[idx], face.uvs[idx] )
        vertData = { POS:[], UVS:[] }
    else:
        dataFunc = getP
        keyFunc = lambda face, idx: face.verts[idx]
        vertData = { POS:[] }

    groups = []
    triCount = 0
    # the function used to create a key from a face vertex
    for mat, tris in matGroups.items():
        tupleMap = {}
        vStart = len( vertData[ POS ] )
        meshGroup = MeshGroup( mat, vStart, triCount * 3 )
        for tri in tris:
            tIdx = [ 0, 0, 0 ]
            for i in xrange( 3 ):
                key = keyFunc( tri, i )
                if ( not tupleMap.has_key( key ) ):
                    idx = len( vertData[ POS ] )
                    tupleMap[ key ] = idx
                    dataFunc( key, verts, norms, uvs, vertData )
                else:
                    idx = tupleMap[ key ]
                tIdx[ i ] = idx
            meshGroup.addTriangle( tIdx )
        meshGroup.vertEnd = len( vertData[ POS ] ) - 1 # inclusive
        triCount += len( meshGroup )
        groups.append( meshGroup )
    return groups, vertData

def writeIdentityMatrix( f ):
    '''Writes a 4x4 identity matrix to the binary file f.

    @param:     f       The file to write to.
    '''
    f.write( struct.pack( 'f', 1.0 ) )
    f.write( struct.pack( 'f', 0.0 ) )
    f.write( struct.pack( 'f', 0.0 ) )
    f.write( struct.pack( 'f', 0.0 ) )
    
    f.write( struct.pack( 'f', 0.0 ) )
    f.write( struct.pack( 'f', 1.0 ) )
    f.write( struct.pack( 'f', 0.0 ) )
    f.write( struct.pack( 'f', 0.0 ) )
    
    f.write( struct.pack( 'f', 0.0 ) )
    f.write( struct.pack( 'f', 0.0 ) )
    f.write( struct.pack( 'f', 1.0 ) )
    f.write( struct.pack( 'f', 0.0 ) )
    
    f.write( struct.pack( 'f', 0.0 ) )
    f.write( struct.pack( 'f', 0.0 ) )
    f.write( struct.pack( 'f', 0.0 ) )
    f.write( struct.pack( 'f', 1.0 ) )
    
def writeGeo( geoName, vertData, meshGroups ):
    '''Writes the geo for the H3D file.

    @param:     geoName     The name of the geo file.
    @param:     vertData    The vertData created by getVertices.
    @param:     meshGroups  The meshGroups created by getVertices.
    '''
    with open( geoName, 'wb' ) as f:
        # header
        f.write( 'H3DG' )
        # version 5
        f.write( struct.pack('i', 5 ) )
        # single default joint with identity
        f.write( struct.pack( 'i', 1 ) )
        writeIdentityMatrix( f )
        # channels of vertex data
        f.write( struct.pack( 'i', len( vertData ) ) )
        f.write( struct.pack( 'I', len( vertData[ POS ] ) ) ) # number of vertices
        # write out vertex block
        writeVPos( f, vertData[ POS ] )   # 0 --> vertex positions
        if ( vertData.has_key( NORM ) ):
            writeNorm( f, vertData[ NORM ] )
        if ( vertData.has_key( UVS ) ):
            writeUV( f, vertData[ UVS ] )
        # number of triangles * 3 - i.e. number of vertex indices in the mesh
        triCount = sum( map( lambda x: len( x ), meshGroups ) )
        f.write( struct.pack( 'I', triCount * 3 ) )
        for mGroup in meshGroups:
            for tri in mGroup.tris:
                f.write( struct.pack( 'iii', tri[0], tri[1], tri[2] ) )
        # no morph targets
        f.write( struct.pack( 'i', 0 ) )        

def writeScene( scenePath, modelName, geoName, meshGroups ):
    '''Writes the scene.xml file for the geometry.

    @param:     scenePath       Folder to put the scene file in.
    @param:     modelName       The name of the model - the scene will be called
                                modelName.scene.xml.
    @param:     geoName         The name of the geo file (without path).
    @param:     meshGroups      The mesh groups created by setVertices.
    '''
    sceneName = os.path.join( scenePath, "%s.scene.xml" % ( modelName ) )
    with open( sceneName, 'w' ) as f:
        f.write( '<Model name="%s" geometry="%s">\n' % ( modelName, geoName ) )
        for mGrp in meshGroups:
            grpName = mGrp.matName
            matName = mGrp.matName
            bStart = mGrp.triIdxStart  # The index of the vertex indices where this group starts
            bCount = len( mGrp ) * 3 # Number of triangles * 3
            vStart = mGrp.vertStart  # The index of the first vertex
            vEnd = mGrp.vertEnd   # the index of the last vertex in this group -- they need to be contiguous
            f.write( '    <Mesh name="%s" material="%s/%s.material.xml" batchStart="%d" batchCount="%d" vertRStart="%d" vertREnd="%d" />\n' % ( grpName,
                                                                                                                            modelName, matName,
                                                                                                                            bStart,
                                                                                                                            bCount,
                                                                                                                            vStart,
                                                                                                                            vEnd
                                                                                                                            )
                     )
        f.write( '</Model>' )

def writeMaterials( scenePath, modelName, meshGroups ):
    '''Writes material files for the geometry.

    @param:     scenePath       Folder to put the scene file in.
    @param:     modelName       The name of the model - the scene will be called
                                modelName.scene.xml.
    @param:     meshGroups      The mesh groups created by setVertices.
    '''
    matFldr = os.path.join( scenePath, 'materials', modelName )
    if ( not os.path.exists( matFldr ) ):
        os.makedirs( matFldr )
    for mGrp in meshGroups:
        matName = os.path.join( matFldr, '%s.material.xml' % mGrp.matName )
        with open( matName, 'w' ) as f:
            f.write( '<Material>' )
            f.write( '\n    <Shader name="material.shader.xml" />' )
            f.write( '\n    <Uniform name="myColor" a=".750" b="0.75" c="0.75" />' )
            f.write( '\n</Material>' )
         
        
def convertObjH3D( objFileName, outFileName ):
    '''Converts the indicated obj file into a Horde3D scene network.

    @param:     objFileName     The path to the obj file.
    @param:     outFileName     The base path for the Horde3D network.
    '''
    try:
        obj = ObjReader.ObjFile( objFileName )
    except IOError:
        print "!! Unable to open obj file:", objFileName
        return
    print "Original obj"
    print obj.summary()
    print "Triangulating the obj"
    obj = obj.triangulate()
    print obj.summary()
    materialGroups = getMatGroups( obj )
    meshGroups, vertData = getVertices( materialGroups, obj.vertSet, obj.normSet, obj.uvSet )
    print "Converted to %d unique vertices" % ( len( vertData[ POS ] ) )
    print "Writing geo file: %s.geo" % ( outFileName )
    geoName = '%s.geo' % outFileName
    writeGeo( geoName, vertData, meshGroups )
    modelPath, modelName = os.path.split( outFileName )
    writeScene( modelPath, modelName, os.path.split( geoName )[-1], meshGroups )
    writeMaterials( modelPath, modelName, meshGroups )
    
if __name__ == '__main__':
    import optparse, sys, os
    parser = optparse.OptionParser()

    parser.set_description( 'Convert obj files into Horde3D models' )
    parser.add_option( '-i', '--input', help='The input obj file',
                       action='store', dest='objFile', default=None )
    parser.add_option( '-o', '--output', help='The name of the output file.  If not specified, it will share the base name of the obj file',
                       action='store', dest='h3dFile', default=None )

    options, args = parser.parse_args()

    if ( options.objFile is None ):
        parser.print_help()
        print '\n!! You must specify an obj file'
        sys.exit(1)

    outFile = options.h3dFile
    if ( outFile is None ):
        outFile = os.path.splitext( options.objFile )[ 0 ]

    convertObjH3D( options.objFile, outFile )    

    