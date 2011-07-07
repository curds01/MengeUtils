'''A set of tools, classes and utilities for manipulating a vector field'''
from OpenGL.GL import *
import numpy as np
import vField as VF

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

def boundStroke( field, p0, p1, radius ):
    '''Given a center and radius, returns the indices of the cells in the field that bound the circle.

        @param field: a VectorField.  The field in which the circle is inscribed.
        @param p1: a 2-tuple of floats.  The beginning of the stroke.
        @param p2: a 2-tuple of floats.  The end of the stroke.
        @param radius: a float.  The radius of the circle to be bound.

        @return: a 2-tuple of arrays of two floats.  Returns indices of the cells which bound it: ( (i, j), (I, J) )
            such that the region that bounds the circle can be found with: field[ i:I, j:J ].  ** Note that
            it is NOT inclusive for I and J.
        '''
    # compute the x/y extents, determine the cells for each of them, and then extract the cell id extrema from
    #   those cells (plus 1 on the maximum side)
    extrema = np.array( ( ( p0[0] - radius, p0[1] - radius ),
                          ( p0[0] + radius, p0[1] - radius ),
                          ( p0[0] - radius, p0[1] + radius ),
                          ( p0[0] + radius, p0[1] + radius ),
                          ( p1[0] - radius, p1[1] - radius ),
                          ( p1[0] + radius, p1[1] - radius ),
                          ( p1[0] - radius, p1[1] + radius ),
                          ( p1[0] + radius, p1[1] + radius )
                        ) )
    cells = field.getCells( extrema )
    minima = cells.min( axis=0 )
    maxima = cells.max( axis=0 ) + 1
    return minima, maxima
    

def blendDirFromDistance( field, dir, minima, maxima, distances, radius ):
    '''Given a field, a region of that field defined by minima and maxima, and an arbitrary distance field,
    blends the given dir into the vector field using distance as weights.

    @param field: A VectorField.getCell
    @param dir: a 2-tuple-like value. The direction to be blended in.
    @param minima: a 2-tuple-like value.  The minimum indices in field over which the work is being done.
    @param maxima: a 2-tuple-like value.  The maximum indices in field over which the work is being done.
    @param distances: an M X N array of floats.  The distance field of size maxima - minima.
    @param radius: the radius used to compute weights.  The radius serves in a gaussian where sigma = radius / 3.0
    '''
    sigma = radius / 3.0
    sigma2 = 2.0 * sigma * sigma
    weights = np.exp( -(distances * distances) / sigma2 ) 
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

    field.fieldChanged() 
    
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

    blendDirFromDistance( field, dir, minima, maxima, distances, gaussRadius )

def blendDirectionStroke( field, dir, p1, p2, radius ):
    '''Given a field, a direction, and the definition stroke with width, update
    the direction of the field along the stroke, using the gauss as the influence weight.

    @param field: a VectorField object.  The field to be modified.
    @param dir: a 2-tuple of floats. The desired direction (not necessarily normalized).
    @param p1: a 2-tuple of floats.  The beginning of the stroke.
    @param p2: a 2-tuple of floats.  The end of the stroke.
    @param radius: a float.  The total radius of influence of the stroke.
        sigma = gaussRadius / 3.0
    '''
    # compute the weights
    minima, maxima = boundStroke( field, p1, p2, radius )
    distances = field.cellSegmentDistance( minima, maxima, p1, p2 )
    blendDirFromDistance( field, dir, minima, maxima, distances, radius )

def blendLengthStroke( field, length, p1, p2, radius ):
    '''Given a field, a scale factor, and the definition stroke with width, update
    the scale of the field along the stroke, using the gauss as the influence weight.

    @param field: a VectorField object.  The field to be modified.
    @param length: a float. The target length of the vector.
    @param p1: a 2-tuple of floats.  The beginning of the stroke.
    @param p2: a 2-tuple of floats.  The end of the stroke.
    @param radius: a float.  The total radius of influence of the stroke.
        sigma = gaussRadius / 3.0
    '''
    # compute the weights
    minima, maxima = boundStroke( field, p1, p2, radius )
    distances = field.cellSegmentDistance( minima, maxima, p1, p2 )
    blendLengthFromDistance( field, length, minima, maxima, distances, radius )

def blendLengthFromDistance( field, length, minima, maxima, distances, radius ):
    '''Given a field, a region of that field defined by minima and maxima, and an arbitrary distance field,
    blends the given vector length into the vector field using distance as weights.

    @param field: A VectorField.getCell
    @param length: a float. The target vector magnitude.
    @param minima: a 2-tuple-like value.  The minimum indices in field over which the work is being done.
    @param maxima: a 2-tuple-like value.  The maximum indices in field over which the work is being done.
    @param distances: an M X N array of floats.  The distance field of size maxima - minima.
    @param radius: the radius used to compute weights.  The radius serves in a gaussian where sigma = radius / 3.0
    '''
    sigma = radius / 3.0
    sigma2 = 2.0 * sigma * sigma
    weights = np.exp( -(distances * distances) / sigma2 )
    weights.shape = ( weights.shape[0], weights.shape[1], 1 )
    # get the region
    region = field.subRegion( minima, maxima )
    magnitude = np.sqrt( np.sum( region * region, axis=2 ) )
    magnitude.shape = ( magnitude.shape[0], -1, 1 )
    tgtLength = region * length / magnitude

    newVectors = weights * tgtLength + ( 1 - weights ) * region
    region[:,:,:] =  newVectors

    field.fieldChanged() 
    
def blendSmoothStroke( field, strength, kernelSize, p1, p2, radius ):
    '''Given a field, a scale factor, and the definition stroke with width, update
    the scale of the field along the stroke, using the gauss as the influence weight.

    @param field: a VectorField object.  The field to be modified.
    @param strength: a float. The strength of the smooth.
    @param p1: a 2-tuple of floats.  The beginning of the stroke.
    @param p2: a 2-tuple of floats.  The end of the stroke.
    @param radius: a float.  The total radius of influence of the stroke.
        sigma = gaussRadius / 3.0
    '''
    # compute the weights
    minima, maxima = boundStroke( field, p1, p2, radius )
    distances = field.cellSegmentDistance( minima, maxima, p1, p2 )
    blendLengthFromDistance( field, strength, minima, maxima, distances, radius )

