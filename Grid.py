# This file contain Abstract Grida and Grid which is used in computing density

import numpy as np
from domains import RectDomain
from primitives import Vector2
import copy

BUFFER_DIST = 0.46  # Based on Proxemics for Close Perosnal Distance
MAX_DIST = 10000

GRID_EPS = 0.00001

class AbstractGrid( RectDomain ):
    '''A class to index into an abstract grid'''
    def __init__( self, minCorner=Vector2(0.0, 0.0), size=Vector2(1.0, 1.0), resolution=(1, 1), cellSize=None ):
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
        if ( cellSize is None ):
            self.cellSize = Vector2( size[0] / float( resolution[0] ), size[1] / float( resolution[1] ) )
        else:
            self.cellSize = cellSize
            assert( np.abs( self.cellSize[0] * self.resolution[0] - self.size[0] ) < 0.0001 and
                    np.abs( self.cellSize[1] * self.resolution[1] - self.size[1] ) < 0.0001 )

    def copy( self ):
        '''Creates a copy of itself'''
        return AbstractGrid( self.minCorner, self.size, self.resolution, self.cellSize )
            
    def isAligned( self, grid ):
        '''Reports if this grid is aligned with the given grid.cellSize

        To be aligned, two grids need to have the same cell size and their minimum
        corners must be an integer number of cells removed from each other.

        @param      grid        An instance of AbstractGrid.  The grid to test alignment
                                with.
        @returns    A boolean.  True if aligned, False otherwise.
        '''
        if ( abs( self.cellSize[0] - grid.cellSize[0] ) > GRID_EPS or
              abs( self.cellSize[1] - grid.cellSize[1] ) > GRID_EPS ):
            return False
        dx = abs( self.minCorner[0] - grid.minCorner[0] ) / self.cellSize[0]
        dy = abs( self.minCorner[1] - grid.minCorner[1] ) / self.cellSize[1]
        DX = int( np.round( dx ) )
        DY = int( np.round( dy ) )
        return ( abs( dx - DX ) < GRID_EPS and abs( dy - DY ) < GRID_EPS )

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
        x = int( np.floor( ofX ) )
        y = int( np.floor( ofY ) )
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

    def intersection( self, grid ):
        '''Computes the intersection of this Grid with another Grid or domain.

        If there is no intersection between the two domains, None is returned, regardless
        of input type.
        
        The nature of the intersection depends on the type of domain provided.  If the
        input is an abstract RectDomain, then the intersection returned is, in turn,
        a RectDomain in continuous space.

        If the input is a derivative of an AbstractGrid, the grids must be aligned because
        the intersection is defined in terms of overlapping cells and the return type
        is a pair of 2-tuples, the minCorner and maxCorner (in grid coordinates) in THIS
        grid of the intersection.  To determine the coordinates in the provided grid's
        coordinates, use a GridTransform.        

        @param      grid        The grid/domain against which the intersection is performed.
        @returns    It depends on the input.  See the notes above.
        '''
        if ( isinstance( grid, AbstractGrid ) ):
            assert( self.isAligned( grid ) )
            if ( not self.intersects( grid ) ):
                return None
            xform = GridTransform( grid, self ) # grid cell coords in this grid's coords
            gmc = xform( (0, 0) )
            gMC = xform( grid.resolution )
            X = [ gmc[0], gMC[0], 0, self.resolution[0] ]
            X.sort()
            Y = [ gmc[1], gMC[1], 0, self.resolution[1] ]
            Y.sort()
            minCorner = ( X[1], Y[1] )
            maxCorner = ( X[2], Y[2] )
            return minCorner, maxCorner
        elif ( isinstance( grid, RectDomain ) ):
            return RectDomain.intersection( self, grid )
        else:
            raise ValueError, 'Grids can only be intersected with RectDomain and its subclasses'

    def getCenters( self ):
        '''Return MxNx2 array of the world positions of each cell center'''
        firstCenter = self.minCorner + self.cellSize * 0.5
        x = np.arange( self.resolution[0] ) * self.cellSize[0] + firstCenter[0]
        y = np.arange( self.resolution[1] ) * self.cellSize[1] + firstCenter[1]
        X, Y = np.meshgrid( y, x ) 
        stack = np.dstack( (X, Y) )
        return stack
    
    def getDataGrid( self, initVal=0.0, arrayType=np.float32, leaveEmpty=False ):
        '''Creates an instance of a DataGrid from this abstract data grid.cellSize
        
        @param          initVal         The initial value for the data grid to contain.
        @param          arrayType       The type of values in the array.
        @param          leaveEmpty      A boolean.  Determines if the DataGrid is initialized or not.
                                        If True, the data will NOT be initialized, if False, it will be
                                        initialize to initVal.
        @returns        An instance of DataGrid with this grid's position, extent, resolution
                        and cellsize.
        '''
        return DataGrid( self.minCorner, self.size, self.resolution, self.cellSize, initVal, arrayType, leaveEmpty )

    def cellArea( self ):
        '''Reports the area of the cell in the grid.cellSize

        @returns    A float.  The area of the square.
        '''
        return self.cellSize[0] * self.cellSize[1]

class GridTransform:
    '''A class for transforming from the coordinates of one AbstractGrid to the coordinates of
    another.'''
    def __init__( self, srcGrid, dstGrid ):
        '''Constructor.

        Creates a transform to map from grid coordinates in srcGrid to dstGrid.
        It assumes that the two grids have the same cell size and have corners that
        are naturally aligned (i.e. the cell centers of the two grids match up.

        @param  srcGrid     An instance of AbstractGrid.  Inputs to the transform are in
                            this Grid's space.
        @param  dstGrid     An instance of AbstractGrid.  Outputs of the transform are in
                            this Grid's space.
        '''
        assert( srcGrid.isAligned(  dstGrid ) )
        self.dx = int( np.round( ( srcGrid.minCorner[0] - dstGrid.minCorner[0] ) / srcGrid.cellSize[0] ) )
        self.dy = int( np.round( ( srcGrid.minCorner[1] - dstGrid.minCorner[1] ) / srcGrid.cellSize[1] ) )

    def __call__( self, point ):
        '''Transform the point from srcGrid's space to dstGrid's space.

        @param      point       A 2-tuple-like object of INTs.  The address of a cell in the
                                space of srcGrid (see __init__).
        @returns    A 2-tuple-like object of INTs.  The same cell in dstGrid's space.
        '''
        return ( point[0] + self.dx, point[1] + self.dy )
        

class DataGrid( AbstractGrid) :
    """A Class to stroe information in grid based structure (i.e the one in Voronoi class ) """
    def __init__( self, minCorner=Vector2(0.0, 0.0), size=Vector2(1.0, 1.0), resolution=(1, 1), cellSize=None, initVal=0.0, arrayType=np.float32, leaveEmpty=False ):
        AbstractGrid.__init__( self, minCorner, size, resolution, cellSize )
        self.initVal = initVal
        self.clear( arrayType, leaveEmpty )

    def copy( self ):
        '''Produces a copy of itself - including underlying data'''
        grid = DataGrid( self.minCorner, self.size, self.resolution, self.cellSize, self.initVal, self.cells.dtype, True )
        grid.cells[ :, : ] = self.cells
        return grid
    
    def copyDomain( self, grid ):
        '''Copies the grid domain parameters from the provided grid.minCorner
        
        @param  grid            An instance of an AbstractGrid.  If provided, the previous parameters
                                are ignored and the values are copied from the provided grid.
        '''
        AbstractGrid.copyDomain( self, grid )
        self.initVal = grid.initVal
        self.clear( grid.cells.dtype )

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

    def setFromBinary( self, binary, arrayType ):
        """Populates the grid values from a binary string"""
        self.cells = np.fromstring( binary, arrayType )
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

    def clear( self, arrayType=np.float32, leaveEmpty=False ):
        # Cells are a 2D array accessible with (x, y) values
        #   x = column, y = row
        if ( leaveEmpty ):
            self.cells = np.empty( ( self.resolution[0], self.resolution[1] ), dtype=arrayType )
        else:
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