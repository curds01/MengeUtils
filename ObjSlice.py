from ObjReader import ObjFile
from math import sqrt, atan2
from primitives import Vector3, Vector2

class Plane:
    """The definition of a plane in R3 -- evaluating the plane returns distance"""
    def __init__( self, A, B, C, D ):
        self.norm = Vector3( A, B, C )
        mag = self.norm.length()
        self.norm.normalize_ip()
        self.D = D / mag

    def __repr__( self ):
        return "Plane: <%f %f %f %f>" % ( self.norm.x, self.norm.y, self.norm.z, self.D )

    def evaluate( self, p ):
        """Evaluates the given point p on the plane"""
        return self.norm.dot( p ) + self.D

    def segmentIntersect( self, a, b ):
        """Returns the point at which the line segment, ab, itnersects the plane.  None if no intersection"""
        aabb = AABB( [a, b] )
        if ( aabb.hitsPlane( self ) ):
            v = Vector3( b.x - a.x, b.y - a.y, b.z - a.z )
            dp = self.norm.dot( v )
            if ( dp != 0.0 ):
                t = - ( self.norm.dot( a ) + self.D ) / dp
                if ( t < 0 ):
                    raise ValueError, "Segment should intersect with t > 0 -- reported t = %f" % ( t )
                return Vector3( a.x + v.x * t, a.y + v.y * t, a.z + v.z * t )
        return None


class AABB:
    """Axis-aligned bounding box"""
    MIN = -100000000000.0
    MAX = 100000000000.0
    def __init__( self, vertices = [] ):
        self.min = Vector3( AABB.MAX, AABB.MAX, AABB.MAX )
        self.max = Vector3( AABB.MIN, AABB.MIN, AABB.MIN )
        if ( vertices ):
            self.expand( vertices )

    def flipY( self ):
        '''Flips the y-values of the bounding box'''
        temp = -self.min.y
        self.min.y = -self.max.y
        self.max.y = temp
        
    def __repr__( self ):
        return "BB: min %s, max %s" % ( self.min, self.max )
    
    def expand( self, vertices ):
        """Expands the bounding volume based on a list of vertices"""
        for v in vertices:
            if ( self.min.x > v.x ):
                self.min.x = v.x
            if ( self.min.y > v.y ):
                self.min.y = v.y
            if ( self.min.z > v.z ):
                self.min.z = v.z
            if ( self.max.x < v.x ):
                self.max.x = v.x
            if ( self.max.y < v.y ):
                self.max.y = v.y
            if ( self.max.z < v.z ):
                self.max.z = v.z

    def hitsAABB( self, aabb ):
        """Reports if this AABB overlaps with aabb"""
        if ( self.min.x > aabb.max.x or
             self.min.y > aabb.max.y or
             self.min.z > aabb.max.z or
             self.max.x < aabb.min.x or
             self.max.y < aabb.min.y or
             self.max.z < aabb.min.z ):
            return False
        return True

    
    def hitsPlane( self, plane ):
        sign = plane.evaluate( self.min )
        if ( sign == 0.0 ):
            return True
        if ( plane.evaluate( Vector3( self.max.x, self.min.y, self.min.z ) ) * sign < 0.0 ):
            return True
        if ( plane.evaluate( Vector3( self.max.x, self.min.y, self.max.z ) ) * sign < 0.0 ):
            return True
        if ( plane.evaluate( Vector3( self.min.x, self.min.y, self.max.z ) ) * sign < 0.0 ):
            return True
        if ( plane.evaluate( Vector3( self.min.x, self.max.y, self.min.z ) ) * sign < 0.0 ):
            return True
        if ( plane.evaluate( Vector3( self.max.x, self.max.y, self.min.z ) ) * sign < 0.0 ):
            return True
        if ( plane.evaluate( Vector3( self.max.x, self.max.y, self.max.z ) ) * sign < 0.0 ):
            return True
        if ( plane.evaluate( Vector3( self.min.x, self.max.y, self.max.z ) ) * sign < 0.0 ):
            return True
        return False
        
class Segment:
    """Line segment in R3"""
    def __init__( self, A, B ):
        """Line semgent spans from point A to point B"""
        self.A = A
        self.B = B

    def __str__( self ):
        return "%s - %s" % (self.A, self.B)

    def __repr__( self ):
        return str( self )

    def RVOString( self ):
        s = '<Obstacle p_x="0" p_y="0">\n'
        s += '\t<Vertex p_x="%f" p_y="%f" />\n' % (self.A.x, self.A.z)
        s += '\t<Vertex p_x="%f" p_y="%f" />\n' % (self.B.x, self.B.z)
        s += '</Obstacle>'
        return s

    def merge( self, seg ):
        """Reports if this segment can be merged with the other and gives the merged version"""
        # "merged" means they are colinear and share a common point
        if ( self.A == seg.A ):
            v1 = self.B - self.A
            v2 = seg.A - seg.B
            p1 = seg.B
            p2 = self.B
        elif ( self.B == seg.B ):
            v1 = self.A - self.B
            v2 = seg.B - seg.A
            p1 = seg.A
            p2 = self.A
        elif ( self.A == seg.B ):
            v1 = self.B - self.A
            v2 = seg.B - seg.A
            p1 = seg.A
            p2 = self.B
        elif ( self.B == seg.A ):
            v1 = self.A - self.B
            v2 = seg.A - seg.B
            p1 = seg.B
            p2 = self.A
        else:
            return None
        v1Len = v1.length()
        v2Len = v2.length()
        divider = 1.0 / (v1Len * v2Len)
        dotProd = v1.dot( v2 ) * divider
        if ( dotProd == 1.0 ):
            return p1, p2
        else:
            return None

    def shareVertex( self, seg, threshold = 0.001 ):
        """Determines if the given segment shares a vertex with this segment"""
        # reports shared as a numerical code
        #  0 - no share
        #     self = seg
        #  1 = A = A
        #  2 = B = A
        #  3 = A = B
        #  4 = B = B
        # A = A
        result = self.containsVertex( seg.A )
        if ( result ):
            return result
        result = self.containsVertex( seg.B )
        if ( result ):
            return result + 2
        return 0

    def containsVertex( self, vert, threshold = 0.001 ):
        """Determines if the given segment has the given vertex"""
        # reports shared as a numerical code
        #  0 - doesn't contain
        #     self = seg
        #  1 = A is the same
        #  2 = B is the same
        dist = ( self.A - vert ).lengthSquared()
        if ( dist <= threshold ):
            return 1
        dist = ( self.B - vert ).lengthSquared()
        if ( dist <= threshold ):
            return 2
        return 0
        
class Polygon:
    """A polygon -- i.e. shape made up of segments with common vertices"""
    def __init__( self ):
        self.vertices = []      # vertices in adjacent order -- no guarantee on clock-wise/counter-clockwise
        self.closed = False

    def __str__( self ):
        s = "Polygon"
        if ( self.closed ):
            s += "(closed)"
        else:
            s += "(open)"
        s += ": "
        for v in self.vertices:
            s += "%s " % v
        return s

    def flipY( self ):
        """Flips the y-values of the polygon (and reverses the order"""
        newVerts = []
        while ( self.vertices ):
            v = self.vertices.pop( -1 )
            v.y = -v.y
            newVerts.append( v )
        self.vertices = newVerts            
    
    def sjguy( self ):
        """Returns a string of this obstacle formatted to stephen guy's format"""
        s = ''
        for i in range( len( self.vertices ) - 1 ):
            v1 = self.vertices[i]
            v2 = self.vertices[ i + 1 ]
            s += '%f %f %f %f\n' % ( v1.x, v1.y, v2.x, v2.y )
        if ( self.closed ):
            v1 = self.vertices[0]
            v2 = self.vertices[-1]
            s += '%f %f %f %f\n' % ( v1.x, v1.y, v2.x, v2.y )
        return s
    
    def __len__( self ):
        return len( self.vertices )

    def isCCW( self, upDirection ):
        """Reports if this polygon is wound in a counter-clockwise direction (with respect to the up direction"""
        if ( len( self.vertices ) < 3 ):
            # winding doesn't matter for line segments
            return True
        turning = 0
        for i in range( -2, len( self.vertices ) - 2 ):
            v1 = self.vertices[ i + 1 ] - self.vertices[ i ]
            v2 = self.vertices[ i + 2 ] - self.vertices[i + 1]
            dot = v1.dot( v2 )
            c = v1.cross( v2 ).dot( upDirection )
            turning += atan2( c, dot )
        return turning < 0
        
    
    def fixWinding( self, upDirection ):
        """Forces the vertices to be ordered in counter-clockwise order"""
        if ( not self.isCCW( upDirection ) ):
            self.vertices = self.vertices[ ::-1 ]

    def merge( self ):
        """Removes co-linear vertices from polygon"""
        changed = True
        while changed:
            changed = False
            for i in range( 1, len( self.vertices ) - 1 ):
                # check if i is collinear with i - 1 and i + 1
                v1 = self.vertices[ i ] - self.vertices[ i - 1 ]
                v2 = self.vertices[ i + 1 ] - self.vertices[ i ]
                v1Len = v1.length()
                v2Len = v2.length()
                divider = 1.0 / (v1Len * v2Len)
                dotProd = abs( v1.dot( v2 ) * divider )
                if ( dotProd < 1.000001 and dotProd > 0.99999 ):
                    self.vertices = self.vertices[:i] + self.vertices[ i + 1: ]
                    changed = True
                    break
        if ( self.closed ):
            # test to see there exists co-linearity at the wrap around
            #   -- could merge either the first or last
            i = 0
            v1 = self.vertices[ i ] - self.vertices[ i - 1 ]
            v2 = self.vertices[ i + 1 ] - self.vertices[ i ]
            v1Len = v1.length()
            v2Len = v2.length()
            divider = 1.0 / (v1Len * v2Len)
            dotProd = abs( v1.dot( v2 ) * divider )
            if ( dotProd < 1.000001 and dotProd > 0.99999 ):
                self.vertices = self.vertices[ i: ]

            i = -1
            v1 = self.vertices[ i ] - self.vertices[ i - 1 ]
            v2 = self.vertices[ i + 1 ] - self.vertices[ i ]
            v1Len = v1.length()
            v2Len = v2.length()
            divider = 1.0 / (v1Len * v2Len)
            dotProd = abs( v1.dot( v2 ) * divider )
            if ( dotProd < 1.000001 and dotProd > 0.99999 ):
                self.vertices = self.vertices[:-1]
            

    def collectSegments( self, segments ):
        """Examines a set of segments and extracts a polygon from a contiguous set of polygons"""
        # returns a list of the unused segments
        #print "Polygon with %d vertices collecting segments from %d segments" % ( len( self.vertices ), len( segments ) )
        if ( len( self.vertices ) == 0 ):
            #print "\tAdding first segment's vertices"
            seg = segments.pop( 0 )
            self.vertices.append( seg.A )
            self.vertices.append( seg.B )

        changed = True
        while ( changed ):
            #print "\tLoop! %d segments" % ( len( segments ) )
            changed = False
            unusedSegments = []
            for seg in segments:
                # can only append on one end or the other
                #print "\t\tSegment!"
                if ( self.closed ):
                    unusedSegments.append( seg )
                    continue
                matchVertex = None
                insertIndex = 0
                match = seg.containsVertex( self.vertices[ 0 ] )                
                if ( match == 1 ):
                    matchVertex = seg.B
                elif ( match == 2 ):
                    matchVertex = seg.A
                else:
                    match = seg.containsVertex( self.vertices[ -1 ] )
                    if ( match ):
                        insertIndex = len( self.vertices )
                        if ( match == 1 ):
                            matchVertex = seg.B
                        else:
                            matchVertex = seg.A
                if ( matchVertex != None ):
                    #print "\t\t\tMatched vertex: %d" % ( insertIndex )
                    changed = True

                    self.vertices.insert( insertIndex, matchVertex )
                    if ( ( self.vertices[0] - self.vertices[-1] ).lengthSquared() < 0.0001 ):
                        # can't add any more
                        self.vertices.pop( 0 )
                        self.closed = True
                        changed = False
                else:
                    unusedSegments.append( seg )
            segments = unusedSegments
        return segments

    def RVOString( self, indent = 0 ):
        baseIndent = indent * '\t'
        vertIndent = baseIndent + '\t'
        s = baseIndent + '<Obstacle closed="%d" boundingbox="0">\n' % ( self.closed )
        for v in self.vertices:
            s += vertIndent + '<Vertex p_x="%f" p_y="%f" />\n' % ( v.x, v.z )
        s += baseIndent + '</Obstacle>'
        return s
    
    def vertCount( self ):
        return len( self.vertices )

    def edgeCount( self ):
        count = len( self.vertices )
        if ( not self.closed ):
            count -= 1
        return count

    def pointInside( self, point ):
        '''This assumes that the verticesa are Vector2 and the point is vector2'''
        assert( point.__class__ == Vector2 )
        assert( self.closed == True )
        # the algorithm is as follows
        #   for each segment
        #       If the segment lies completely above or below the point, 
        #           OR completely to the right
        #           don't count it
        #       else:
        #           intersect a horizontal line with the segment starting at point and
        #               moving to -infinity
        #           Compute the x value of the line segment at y = point.y
        #               If x < point.x, increment hit count
        #   If hit count is odd, it is inside.  If it is even, it is outside
        count = 0
        for i in range( len( self.vertices ) ):
            v1 = self.vertices[i-1]
            v2 = self.vertices[i]
            if ( ( v1.x > point.x and v2.x > point.x ) or
                 ( v1.y < point.y and v2.y < point.y ) or
                 ( v1.y > point.y and v2.y > point.y ) ):
                 continue
            dy = v2.y - v1.y
            t = ( point.y - v1.y ) / dy
            dx = t * ( v2.x - v1.x ) + v1.x
            if ( dx < point.x ):
                count += 1
        return count % 2 == 1
                                                  
def buildPolygons( segments, upDir ):
    """Builds a set of connected polygons from the list of segments"""
    polys = []

    poly = Polygon()
    while ( segments ):
        segments = poly.collectSegments( segments )
        poly.fixWinding( upDir )
        if ( len( poly ) > 0 ):
            poly.merge()
            polys.append( poly )
            poly = Polygon()
    return polys
            
            
def slice( obj, plane, findPolys, scale = 1.0, flip = 0 ):
    """Returns a list of line segments which are formed when itnersecting the obj with the plane"""
    segments = []

    for face in obj.getFaceIterator():
        vertices = [ obj.vertSet[ x - 1 ] for x in face.verts ]
        bb = AABB( vertices )
        if ( bb.hitsPlane( plane ) ):
            points = []
            vCount = len( vertices )
            for i in range( vCount ):
                p = plane.segmentIntersect( vertices[ i ], vertices[ (i + 1) % vCount ] )
                if ( p ):
                    if ( flip ):
                        points.append( Vector3( p.x, p.y, -p.z ) * scale )
                    else:
                        points.append( p * scale )
            if ( len( points ) < 2 ):
                print face,
                print "Only found one vertex"
                continue
            segments.append( Segment( points[0], points[1] ) )


##    print "Segments"
##    for seg in segments:
##        print seg
##    print
    
    polys = []
    if ( findPolys ):
        tempSegments = [ seg for seg in segments ]
        polys = buildPolygons( tempSegments, plane.norm )
    return segments, polys

def usage():
    print "ObjSlice -- slices a wavefront .obj file by a plane"
    print
    print "Usage: python ObjSlice -arg1 value1 -arg2 value2 ..."
    print "Options:"
    print "   -in file.obj  - the wavefront obj file to operate on"
    print "                   if argument not provided, program does nothing"
    print "   -A <float>    - "
    print "   -B <float>    - "
    print "   -C <float>    - "
    print "   -D <float>    - Defines the plane by the implicit equation"
    print "                   Ax + By + Cz + D = 0"
    print "                   Missing parameters are assumed to be zero."
    print "   -out file.txt - Outputs the results to this file, otherwise"
    print "                   to the console."
    print "   -flip [1|0]   - Determines if the vertices are flipped across the x-axis"
    print "                   (i.e. along the z-axis) -- defaults to 0"
    print "   -scale float  - scales the vertices around the origin"
    print "   -outData [seg|poly]"
    print "                 - determines the output data."
    print "                 - output data can be a list of individual line segments (seg)"
    print "                 - or a list of polygons made up of connected segments (poly)"
    print "                 - Default will output segments"

if __name__ == "__main__":
    import sys, os, getopt

    SEGMENT = 'seg'
    POLY = 'poly'
    
    from commandline import SimpleParamManager
    pMan = SimpleParamManager( sys.argv[1:], {'A':0.0, 'B':0.0, 'C':0.0, 'D':0.0, 'flip':0, 'scale':1.0 } )
    inputName = pMan[ 'in' ]
    if ( inputName == None ):
        usage()
        sys.exit(1)
    try:
        A = float( pMan['A'] )
        B = float( pMan['B'] )
        C = float( pMan['C'] )
        D = float( pMan['D'] )
        plane = Plane( A, B, C, D )
    except ValueError:
        print "Invalid argument for plane value"
        sys.exit(2)
    except ZeroDivisionError:
        print "Inavlid plane definition: %f, %f, %f, %f" % (A, B, C, D)
        sys.exit(3)
    outFile = pMan['out']
    flip = pMan['flip']
    scale = float( pMan['scale'] )
    outData = pMan['outData']
    if ( outData == None ):
        outData = SEGMENT
    print "outData:", outData
    if ( not( outData == SEGMENT or outData == POLY ) ):
        print 'Invalid value for outData argument: "%s".  Should be "seg" or "poly"' % outData
        sys.exit( 4 )
    out = sys.stdout

    if ( outFile ):
        try:
            out = open( outFile, 'w' )
        except IOError:
            print "Error opening file %s" % (outFile)
            print "Writing to console"

    print 'Opened %s with plane: %f, %f, %f, %f\n' % (inputName, A, B, C, D)  

    obj = ObjFile( inputName )

    gCount, fCount = obj.faceStats()
    print "File has %d faces" % (fCount)    

    findPolys = outData == POLY
    segments, polys = slice( obj, plane, findPolys, scale, flip )

    print "File has %d segments" % ( len(segments) )
    if ( findPolys ):
        print "File has %d polygons" % ( len( polys ) )
    print

    out.write("""<?xml version="1.0"?>

<Experiment time_step="0.25" num_samples="250" visualization="1" useProxies="1" neighbor_dist="5">
""")
    if ( findPolys ):
        for poly in polys:
            out.write( '%s\n' % ( poly.RVOString() ) )
    else:
        for seg in segments:
            out.write( '%s\n' % seg.RVOString() )
    out.write("""</Experiment>""")
    