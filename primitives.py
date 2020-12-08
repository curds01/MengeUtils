from copy import deepcopy
from math import sqrt
import warnings

# TODO: Vector2 and Vector3 do *not* have a common API (i.e., operator
#  overloads). Unify them and update the tests.

class Vector2(object):
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def set(self, v2):
        '''Sets this vector's components from a 2-tuple-like object v2'''
        self.x = v2[0]
        self.y = v2[1]

    def __getitem__( self, index ):
        if ( index == 0 ):
            return self.x
        elif (index == 1 ):
            return self.y
        else:
            raise IndexError("list index out of range")

    def __setitem__( self, index, value ):
        if ( index == 0 ):
            self.x = value
        elif (index == 1 ):
            self.y = value
        else:
            raise IndexError("list index out of range")

    def __str__(self):
        return "<%g, %g>" % (self.x, self.y )

    def __repr__( self ):
        return str(self)

    def __eq__( self, v ):
        assert(isinstance(v, Vector2))
        return self.x == v.x and self.y == v.y

    def __neq__( self, v ):
        assert(isinstance(v, Vector2))
        return self.x != v.x or self.y != v.y

    def __sub__( self, v ):
        assert(isinstance(v, Vector2))
        return Vector2( self.x - v.x, self.y - v.y )

    def __isub__( self, v ):
        assert(isinstance(v, Vector2))
        self.x -= v.x
        self.y -= v.y
        return self

    def __neg__( self ):
        return Vector2( -self.x, -self.y )

    def __add__( self, v ):
        assert(isinstance(v, Vector2))
        return Vector2( self.x + v.x, self.y + v.y )

    def __iadd__( self, v ):
        assert(isinstance(v, Vector2))
        self.x += v.x
        self.y += v.y
        return self

    def __truediv__(self, s):
        assert (isinstance(s, float) or isinstance(s, int))
        return Vector2(self.x / s, self.y / s)

    def __div__( self, s ):
        assert(isinstance(s, float) or isinstance(s, int))
        return Vector2( self.x / s, self.y / s )

    def __mul__( self, s ):
        assert (isinstance(s, float) or isinstance(s, int))
        return Vector2( self.x * s, self.y * s )

    def __rmul__( self, s ):
        assert (isinstance(s, float) or isinstance(s, int))
        return Vector2( self.x * s, self.y * s )

    def __imul__( self, s ):
        self.x *= s
        self.y *= s
        return self

    def normalize_ip( self ):
        mag = self.magnitude()
        if mag > 0.0:
            recip_length = 1.0 / mag
            self.x *= recip_length
            self.y *= recip_length

    def normalize( self ):
        """Returns a normalized version of the vector"""
        v = Vector2(self.x, self.y)
        v.normalize_ip()
        return v

    def dot( self, v ):
        return self.x * v.x + self.y * v.y

    def negate( self ):
        '''Negates the vector'''
        self.x = -self.x
        self.y = -self.y

    def magnitude( self ):
        return sqrt( self.x * self.x + self.y * self.y )

    def magSq( self ):
        return self.x * self.x + self.y * self.y

    def isZero( self ):
        '''Reports if the vector is zero'''
        return self.x == 0.0 and self.y == 0.0

    def asTuple( self ):
        return (self.x, self.y)

    def det( self, v ):
        """Computes the determinant of this vector with v"""
        return self.x * v.y - self.y * v.x

class Vector3(object):
    def __init__( self, x, y, z ):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def set(self, v2):
        """Sets this vector's components from a 3-tuple-like object v2"""
        self.x = v2[0]
        self.y = v2[1]
        self.z = v2[2]

    def __getitem__( self, index ):
        if ( index == 0 ):
            return self.x
        elif (index == 1 ):
            return self.y
        elif ( index == 2 ):
            return self.z
        else:
            raise IndexError("list index out of range")

    def __setitem__( self, index, value ):
        if ( index == 0 ):
            self.x = value
        elif (index == 1 ):
            self.y = value
        elif (index == 2 ):
            self.z = value
        else:
            raise IndexError("list index out of range")

    def __str__(self):
        return "<%6.3f, %6.3f, %6.3f>" % (self.x, self.y, self.z )

    def __repr__( self ):
        return str(self)

    def __eq__( self, v ):
        return self.x == v.x and self.y == v.y and self.z == v.z

    def __neq__(self, v):
        assert(isinstance(v, Vector3))
        return self.x != v.x or self.y != v.y or self.z != v.z
    
    def __sub__( self, v ):
        if ( isinstance( v, Vector3 ) ):
            return Vector3( self.x - v.x, self.y - v.y, self.z - v.z )
        elif ( isinstance( v, Vector2 ) ):
            # TODO: Am I *really* using this??!?!? This is *horrible* API.
            warnings.warn("deprecated", DeprecationWarning)
            return Vector2( self.x - v.x, self.y - v.y )

    def __isub__(self, v):
        assert(isinstance(v, Vector3))
        self.x -= v.x
        self.y -= v.y
        self.z -= v.z
        return self

    def __neg__( self ):
        return Vector3(-self.x, -self.y, -self.z)

    def __add__( self, v ):
        return Vector3( self.x + v.x, self.y + v.y, self.z + v.z )

    def __iadd__( self, v ):
        self.x += v.x
        self.y += v.y
        self.z += v.z
        return self

    def __truediv__(self, s):
        return Vector3(self.x / s, self.y / s, self.z / s)

    def __div__( self, s ):
        return Vector3( self.x / s, self.y / s, self.z / s )

    def __mul__( self, s ):
        return Vector3( self.x * s, self.y * s, self.z * s )

    def __rmul__( self, s ):
        assert (isinstance(s, float) or isinstance(s, int))
        return Vector3(self.x * s, self.y * s, self.z * s)

    def __imul__( self, s ):
        self.x *= s
        self.y *= s
        self.z *= s
        return self

    def normalize_ip( self ):
        length = self.length()
        if length > 0:
            recip_length = 1.0 / self.length()
            self.x *= recip_length
            self.y *= recip_length
            self.z *= recip_length

    def normalize(self):
        v = Vector3(self.x, self.y, self.z)
        v.normalize_ip()
        return v

    def dot( self, v ):
        return self.x * v.x + self.y * v.y + self.z * v.z

    def negate( self ):
        '''Negates the vector'''
        self.x = -self.x
        self.y = -self.y
        self.z = -self.z

    def lengthSquared( self ):
        return self.x * self.x + self.y * self.y + self.z * self.z

    def length( self ):
        return sqrt( self.lengthSquared() )

    # TODO: magnitude() and magSq() serve as a common interface as Vector2.
    #  Remove the redundant API.
    def magnitude( self ):
        return self.length()

    def magSq( self ):
        return self.lengthSquared()

    def isZero( self ):
        '''Reports if the vector is zero'''
        return self.x == 0.0 and self.y == 0.0 and self.z == 0.0

    def asTuple( self ):
        return (self.x, self.y, self.z)

    def cross( self, v ):
        x = self.y * v.z - self.z * v.y
        y = self.z * v.x - self.x * v.z
        z = self.x * v.y - self.y * v.x
        return Vector3( x, y, z )

    def minAxis( self ):
        """Returns the axis with the minimum value"""
        dir = 0
        minVal = self.x
        if ( self.y < minVal ):
            minVal = self.y
            dir = 1
        if ( self.z < minVal ):
            dir = 2
        return dir

    def minAbsAxis( self ):
        """Returns the axis with the minimum absolute magnitude"""
        dir = 0
        minVal = abs(self.x)
        if ( abs(self.y) < minVal ):
            minVal = sab(self.y)
            dir = 1
        if ( abs(self.z) < minVal ):
            dir = 2
        return dir

class Face(object):
    """Specification of a polygonal face. The face is defined by three or more
    vertices. The face can also include per-vertex normals and texture
    coordinates. The lists provided will be copied.

    All indices are 1-indexed (a la Wavefront OBJ format).

        Args:
            v: a list containing indexes into an ordered set of vertex
              positions. If None, the face has zero vertices.
            vn: a list containing indexes into an ordered set of vertex
              normals. If None, the face has zero vertices. If not None it must
              be the same size as v.
            vt: a list containing indexes into an ordered set of texture
              coordinates. If None, the face has zero vertices. If not None it
              must be the same size as v."""
    def __init__( self, v = None, vn = None, vt = None ):
        if v is None:
            self.verts = []
        else:
            self.verts = deepcopy(v)
        if vn is None:
            self.norms = []
        else:
            self.norms = deepcopy(vn)
        if vt is None:
            self.uvs = []
        else:
            self.uvs = deepcopy(vt)
        assert len(self.verts) == 0 or len(self.verts) >= 3
        assert len(self.norms) == 0 or len(self.norms) == len(self.verts)
        assert len(self.uvs) == 0 or len(self.uvs) == len(self.verts)

    def triangulate( self ):
        """Triangulates the face - returns a list of independent faces"""
        if ( len(self.verts) == 3 ):
            return [deepcopy( self ), ]
        else:
            newFaces = []
            # Blindly create a fan triangulation (v1, v2, v3), (v1, v3, v4),
            # (v1, v4, v5), etc...
            for i in range(1, len(self.verts) - 1):
                verts = [self.verts[0], self.verts[i], self.verts[i+1]]
                norms = None
                if ( self.norms ):
                    norms = [self.norms[0], self.norms[i], self.norms[i+1]]
                uvs = None
                if ( self.uvs ):
                    uvs = [self.uvs[0], self.uvs[i], self.uvs[i+1]]
                newFaces.append( Face( verts, norms, uvs ) )
            return newFaces

    def OBJFormat( self ):
        """Writes face definition in OBJ format"""
        s = 'f'
        vIndex = 0
        for v in self.verts:
            s += ' %d' % v
            if ( self.uvs ):
                s += '/%d' % self.uvs[vIndex]
            if ( self.norms ):
                if (not self.uvs ):
                    s += '/'
                s += '/%d' % self.norms[vIndex]
            vIndex += 1
        return s


class Vertex:
    """Encoding of a vertex position in 3D space in an implied frame F."""

    def __init__( self, x, y, z ):
        self.pos = (x, y, z)

    def formatOBJ( self ):
        """Returns a string that represents this vertex"""
        return "v %f %f %f" % ( self.pos[0], self.pos[1], self.pos[2] )

        
class Segment:
    '''A line segment'''
    def __init__( self, p1, p2 ):
        """Constructs a line segment from two points (each a Vector2). The
        given points are aliased."""
        self.p1 = p1
        self.p2 = p2

    def __str__( self ):
        return "Segment (%s, %s)" % ( self.p1, self.p2 )

    def __repr__( self ):
        return str( self )

    def midPoint( self ):
        """Returns the mid-point of the line"""
        try:
            return ( self.p1 + self.p2 ) * 0.5
        except TypeError:
            print(type( self.p1 ), type( self.p2 ))

    def magnitude( self ):
        """Returns length of the line"""
        return ( self.p2 - self.p1 ).magnitude()

    def magSq(self):
        '''Returns the squared length of the segment'''
        return (self.p1 - self.p2).magSq()

    def normal( self ):
        '''Returns the normal of the line'''
        disp = self.p2 - self.p1
        segLen = disp.magnitude()
        if ( segLen ):
            norm = disp / segLen
            return Vector2( -norm.y, norm.x )
        else:
            return Vector2( 0, 0 )

    def unit_direction(self):
        """Reports a unit-length vector from p1 to p2 (unless the segment has
        zero length."""
        l = self.magnitude()
        if l > 0.0:
            return (self.p2 - self.p1) / l
        return Vector2(0, 0)
    
    def pointDistance( self, p ):
        """Computes the distance between this line segment and a point p"""
        disp = self.p2 - self.p1
        segLen = disp.magnitude()
        norm = disp / segLen
        dispP = p - self.p1
        dp = norm.dot( dispP )
        if ( dp < 0 ):      
            return (p - self.p1).magnitude()
        elif ( dp > segLen ):
            return ( p - self.p2).magnitude()
        else:
            A = -norm.y
            B = norm.x
            C = -( A * self.p1.x + B * self.p1.y )
            return abs( A * p.x + B * p.y + C )

    def implicitEquation( self ):
        '''Computes the implicit equation for the line on which this segment lies.

        The implicit equation is Ax + By + C = 0.  This function computes this equation and
        returns these coefficients.

        @returns    A 3-tuple of floats.  The floats (A, B, C ) in the implicit equation.
        '''
        disp = self.p2 - self.p1
        segLen = disp.magnitude()
        assert( segLen > 0 )
        dir = disp / segLen
        A = -dir.y
        B = dir.x
        C = -( A * self.p1.x + B * self.p1.y )
        return A, B, C

    def originDirLen( self ):
        '''Returns an alternative representation of the segment: origin, direction and length.

        @returns    A 3-tuple of various values: (Vector2, Vector2, float).  The first value is
                    the origin of the segment.  The second is a unit normal, the direction of
                    the segment.  The final float is the length of the segment.
        '''
        disp = self.p2 - self.p1
        segLen = disp.magnitude()
        assert( segLen > 0 )
        dir = disp / segLen
        return self.p1, dir, segLen

    def flip( self ):
        '''Reverses the direction of the line'''
        t = self.p1
        self.p1 = self.p2
        self.p2 = t

def segmentsFromString( s, SegmentClass ):
    '''Given a string of floats, constructs a list of segments.  For N segments there
    must be 4N floats.'''
    lines = []
    tokens = s.split()
    assert( len( tokens ) % 4 == 0 )  # four floats per line
    while tokens:
        x1, y1, x2, y2 = tokens[:4]
        tokens = tokens[ 4: ]
        lines.append( SegmentClass( Vector2( float(x1), float(y1) ), Vector2( float(x2), float(y2) ) ) )
    return lines
