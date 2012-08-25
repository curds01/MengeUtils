# This file contain Abstract Grida and Grid which is used in computing density

import numpy as np
from primitives import Vector2
import copy

BUFFER_DIST = 0.46  # Based on Proxemics for Close Perosnal Distance
MAX_DIST = 10000

GRID_EPS = 0.00001
class RectDomain:
    '''A simple class to represent a rectangular domain'''
    def __init__( self, minCorner, size ):
        '''RectDomain constructor.
        @param  minCorner       A 2-tuple-like instace of floats.  The position, in world space,
                                of the "bottom-left" corner of the domain.  (Minimum x- and y-
                                values.
        @param  size            A 2-tuple-like instace of floats.  The span of the domain (in world
                                space.)  The maximum values of the domain are minCorner[0] + size[0]
                                and minCorner[1] + size[1], respectively.
        '''
        self.minCorner = minCorner
        self.size = size

    def copyDomain( self, domain ):
        '''Copies the domain settings from the given domain to this domain'''
        self.minCorner = copy.deepcopy( domain.minCorner )
        self.size = copy.deepcopy( domain.size )
        
class AbstractGrid( RectDomain ):
    '''A class to index into an abstract grid'''
    def __init__( self, minCorner=Vector2(0.0, 0.0), size=Vector2(1.0, 1.0), resolution=(1, 1) ):
        '''Grid constructor.

        @param  minCorner       A 2-tuple-like instace of floats.  The position, in world space,
                                of the "bottom-left" corner of the domain.  (Minimum x- and y-
                                values.
        @param  size            A 2-tuple-like instace of floats.  The span of the domain (in world
                                space.)  The maximum values of the domain are minCorner[0] + size[0]
                                and minCorner[1] + size[1], respectively.
        @param  resolution      A 2-tuple like instance of ints.  The number of cells in the domain in
                                both the x- and y-directions.  This will imply a cell size.
        '''
        RectDomain.__init__( self, minCorner, size )
        self.resolution = resolution        # tuple (x, y)  - int
        # size of each cell in the world grid
        self.cellSize = Vector2( size[0] / float( resolution[0] ), size[1] / float( resolution[1] ) )

    def copyDomain( self, grid ):
        '''Copies the grid domain parameters from the provided grid.minCorner
        
        @param  grid            An instance of an AbstractGrid.  If provided, the previous parameters
                                are ignored and the values are copied from the provided grid.
        '''
        RectDomain.copyDomain( self, grid )
        self.resolution = copy.deepcopy( grid.resolution )
        self.cellSize = copy.deepcopy( grid.cellSize )

    def getCenter( self, position ):
        """Returns the closest cell center to this position
        The result is in the discretized world grid
        @position: a Vector2 of position in the world"""
        # offset in euclidian space
        offset = position - self.minCorner
        # offset in cell sizes
        ofX = offset[0] / self.cellSize[0]
        ofY = offset[1] / self.cellSize[1]
        x = int( ofX )
        y = int( ofY )
        return x, y

    def distanceToNearestBoundary( self, position ):
        '''Returns the distance from the position to the nearest boundary.

        @param  position        A 2-tuple-like object of floats.  The x- and y-values
                                of the test point.
        @returns        A float.  The minimum distance to the nearest boundary.
        '''
        dx1 = abs( position[0] - self.minCorner[0] )
        dy1 = abs( position[1] - self.minCorner[1] )
        dx2 = abs( self.size[0] - dx1 )
        dy2 = abs( self.size[1] - dy1 )
        return min( dx1, dy1, dx2, dy2 )

class DataGrid( AbstractGrid) :
    """A Class to stroe information in grid based structure (i.e the one in Voronoi class ) """
    def __init__( self, minCorner=Vector2(0.0, 0.0), size=Vector2(1.0, 1.0), resolution=(1, 1), initVal=0.0, arrayType=np.float32 ):
        AbstractGrid.__init__( self, minCorner, size, resolution )
        self.initVal = initVal
        self.clear( arrayType )

    def copyDomain( self, grid ):
        '''Copies the grid domain parameters from the provided grid.minCorner
        
        @param  grid            An instance of an AbstractGrid.  If provided, the previous parameters
                                are ignored and the values are copied from the provided grid.
        '''
        AbstractGrid.copyDomain( self, grid )
        self.initVal = grid.initVal
        self.clear( grid.cells.dtype )

    def getCenters( self ):
        '''Return NxNx2 array of the world positions of each cell center'''
        firstCenter = self.minCorner + self.cellSize * 0.5
        resolution = self.resolution[1]
        if (self.resolution[0] > self.resolution[1]):
            resolution = self.resolution[0]
        x = np.arange( resolution ) * self.cellSize[0] + firstCenter[0]
        y = np.arange( resolution ) * self.cellSize[1] + firstCenter[1]
        X, Y = np.meshgrid( y,x ) 
        stack = np.dstack( (X,Y) )
        # Truncate the stack down
        stack = stack[0:self.resolution[0]:1,0:self.resolution[1]:1,:]
        return stack
    
    def __str__( self ):
        s = 'Grid'
        for row in range( self.resolution[1] - 1, -1, -1 ):
            s += '\n'
            for col in range( self.resolution[0] ):
                s += '%7.2f' % ( self.cells[ col ][ row ] )
        return s

    def binaryString( self ):
        """Produces a binary string for the data"""
        return self.cells.tostring()

    def setFromBinary( self, binary ):
        """Populates the grid values from a binary string"""
        self.cells = np.fromstring( binary, np.float32 )
        self.cells = self.cells.reshape( self.resolution )

    def __idiv__( self, scalar ):
        self.cells /= scalar
        return self

    def __imul__( self, scalar ):
        self.cells *= scalar
        return self

    def maxVal( self ):
        """Returns the maximum value of the grid"""
        return self.cells.max()

    def minVal( self ):
        """Returns the maximum value of the grid"""
        return self.cells.min()

    def clear( self, arrayType=np.float32 ):
        # Cells are a 2D array accessible with (x, y) values
        #   x = column, y = row
        if ( self.initVal == 0 ):
            self.cells = np.zeros( ( self.resolution[0], self.resolution[1] ), dtype=arrayType )
        else:
            self.cells = np.zeros( ( self.resolution[0], self.resolution[1] ), dtype=arrayType ) + self.initVal

    def surface( self, map, minVal, maxVal ):
        """Creates a pygame surface"""
        return map.colorOnSurface( (minVal, maxVal ), self.cells )

    


if __name__ == '__main__':
    def testIntersection():
        print "Testing grid intersection"
        g = AbstractGrid( Vector2( 0, 0 ), Vector2( 5, 5 ), (5, 5) )
        # test cases consist of pairs: an domain to intersect with d, and the expected result.
        testCases = [ ( AbstractGrid( Vector2( 0, 0 ),   Vector2( 5, 5 ), (6, 6) ),   None ),
                      ( AbstractGrid( Vector2( 6, 6 ),   Vector2( 1, 1 ), (5,5) ),   None ),
                      ( AbstractGrid( Vector2( 1, 1 ),   Vector2( 3, 3 ), (3,3) ),   ( (1,1), (4,4) ) ),
                      ( AbstractGrid( Vector2( -1, -1 ), Vector2( 2, 2 ), (2,2) ),   ( (0,0), (1,1) ) ),
                      ( AbstractGrid( Vector2( -1, 1 ),  Vector2( 2, 2 ), (2,2) ),   ( (0,1), (1,3) ) ),
                      ( AbstractGrid( Vector2( -1, 1 ),  Vector2( 8, 2 ), (8,2) ),   ( (0,1), (5,3) ) ),
                      ]
        for gTest, expInter in testCases:
            try:
                result = g.intersection( gTest )
            except AssertionError:
                result = None
            if ( result == expInter ):
                print "\tPASS!"
            else:
                print "\tFAIL!"
                print "\t\t%s n %s" % ( g, gTest )
                print "\t\tEXPECTED:\n\t\t", expInter
                print "\t\tGOT:    \n\t\t", result
                

    testIntersection()                