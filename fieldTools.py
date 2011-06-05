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

def blendDirection( field, dir, gaussCenter, gaussRadius ):
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
    minima, maxima = field.boundCircle( gaussCenter, gaussRadius )
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

            
            