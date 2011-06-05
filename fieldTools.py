'''A set of tools, classes and utilities for manipulating a vector field'''
from OpenGL.GL import *
import numpy as np

class Path:
    '''A 2D sequence of points creating a path'''
    def __init__( self ):
        self.points = []    # a list of "points" as the path is built
                            # a point is simply a 2-tuple of floats
        self.path = None    # a Nx2 numpy array representing the path

    def beginPath( self, x, y ):
        self.points = []
        self.addPoint( x, y )

    def endPath( self, smoothWindow=0 ):
        self.path = np.array( self.points )
        self.points = []
        if ( smoothWindow > 0 ):
            pass
            # perform a gaussian smooth on this path with the size given

    def addPoint( self, x, y ):
        '''Adds a point to the path.

        @param x: a float. The x-position of the point to add.
        @param y: a float. They y-position of the point to add.
        '''
        self.points.append( (x,y) )

    def drawGL( self ):
        if ( self.path == None ):
            # draw from the temporary collection of data
            points = self.points
        else:
            points = self.path

        glBegin( GL_LINE_STRIP )
        for x, y in points:
            glVertex3f( x, y, 0 )
        glEnd()

def boundCircle( field, center, radius ):
    '''Given a center and radius, returns the indices of the cells in the field that bound the circle.

        @param field: a VectorField.  The field in which the circle is inscribed.
        @param center: a 2-tuple of floats.  The center of the circle in the same space as the field.
        @param radius: a float.  The radius of the circle to be bound.

        @return: a 2-tuple of arrays of two floats.  Returns indices of the cells which bound it: ( (i, j), (I, J) )
            such that the region that bounds the circle can be found with: field[ i:I, j:J ].  ** Note that
            it is NOT inclusive for I and J.
        '''
    # compute the x/y extents, determine the cells for each of them, and then extract the cell id extrema from
    #   those cells (plus 1 on the maximum side)
    extrema = np.array( ( ( center[0] - radius, center[1] - radius ),
                          ( center[0] + radius, center[1] - radius ),
                          ( center[0] - radius, center[1] + radius ),
                          ( center[0] + radius, center[1] + radius )
                        ) )
    cells = field.getCells( extrema )
    minima = cells.min( axis=0 )
    maxima = cells.max( axis=0 ) + 1
    return minima, maxima
    
def blendDirectionPoint( field, dir, gaussCenter, gaussRadius ):
    '''Given a field, a direction, and the definition of a gaussian region of influence, update
    the direction of the field at that gauss, using the gauss as the influence weight.

    @param field: a VectorField object.  The field to be modified.
    @param dir: a 2-tuple of floats. The desired direction (not necessarily normalized).
    @param gaussCenter: a 2-tuple of floats.  The center of the 2D-gaussian function (in the same
        space as the field.
    @param gaussRadius: a float.  The total radius of influence of the gaussian function.
        sigma = gaussRadius / 3.0
    '''
    # compute the weights
    minima, maxima = boundCircle( field, gaussCenter, gaussRadius )
    distances = field.cellDistances( minima, maxima, gaussCenter )
    sigma = gaussRadius / 3.0
    sigma2 = 2.0 * sigma * sigma
    weights = np.exp( -(distances * distances) / sigma2 ) #/ ( np.sqrt( np.pi * sigma2) )
    # get the region
    region = field.subRegion( minima, maxima )
    magnitude = np.sqrt( np.sum( region * region, axis=2 ) )

    # compute angles
    tgtAngle = np.arctan2( dir[1], dir[0] )
    angles = np.arctan2( region[:,:,1], region[:,:,0] )
    delta = tgtAngle - angles
    problems = abs( delta ) > np.pi
    change = 2.0 * np.pi
    if ( tgtAngle < 0 ):
        change = -2.0 * np.pi
    angles[ problems ] += change
    newAngles = weights * tgtAngle + ( 1 - weights ) * angles
    c = np.cos( newAngles ) * magnitude
    s = np.sin( newAngles ) * magnitude
    region[:,:,0] = c
    region[:, :, 1] = s
    confirmRegion = field.subRegion( minima, maxima )
    field.fieldChanged()

            
            