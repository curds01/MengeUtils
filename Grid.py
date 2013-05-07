# This file contain Abstract Grida and Grid which is used in computing density

import numpy as np
from domains import RectDomain
from primitives import Vector2
import copy

GRID_EPS = 0.00001

# Enumerations to indicate whether something is inside or outside the domain
#   Used by the DataGrid.getValue method to report if the evaluatio point
#   was inside or outside of the domain
INSIDE = 1
OUTSIDE = 2

def makeDomain( domainX, domainY, cellSize=None ):
    '''Defines a rectangular domain from the given specifications.

    If cellSize is not specified, the domain is a RectDomain, otherwise, it
    is an Abstract Grid.

    @param      domainX         A two-tuple like object of floats.  The range of the
                                test region on the x-axis as [minX, maxX]
    @param      domainY         A two-tuple like object of floats.  The range of the
                                test region on the y-axis as [minY, maxY]
    @param      cellSize        A float.  The size of the cells for the discretized
                                domain.
    @returns    An instance of RectDomain or AbstractGrid, depending on cellSize.
                If cellSize is not defined, then a RectDomain is constructed, otherwise
                an AbstractGrid.
    '''
    minCorner = Vector2( domainX[0], domainY[0] )
    size = Vector2( domainX[1] - domainX[0], domainY[1] - domainY[0] )
    if ( cellSize is None ):
        return RectDomain( minCorner, size )
    else:
        rX = int( np.floor( size[0] / cellSize ) ) # explicit truncation
        rY = int( np.floor( size[1] / cellSize ) ) # explicit truncation
        size = Vector2( rX * cellSize, rY * cellSize )
        return AbstractGrid( minCorner, size, (rX, rY) )

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

    def __str__( self ):
        return 'AbstractGrid from ( %.2f, %.2f ) to ( %.2f, %.2f ) - res: %d x %d' % ( self.minCorner[0], self.minCorner[1],
                                                                      self.minCorner[0] + self.size[0], self.minCorner[1] + self.size[1],
                                                                                       self.resolution[0], self.resolution[1] )

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

    def getRangeCenters( self, l, r, b, t ):
        '''Returns an MxNx2 array of world positions of cell centers in the region
        bounded by the cell coordiantes (l,b) and (r,t).

        @param      l       An int.  In grid coordinates, the left-most bound of the region.
        @param      r       An int.  In grid coordinates, the right-most bound of the region.
        @param      b       An int.  In grid coordinates, the bottom-most bound of the region.
        @param      t       An int.  In grid coordinates, the top-most bound of the region.
        @returns    An MxNx2 numpy array.  Where M = r - l, N = t - b.
        '''
        firstX = self.minCorner[0] + self.cellSize[0] * ( l + 0.5 )
        firstY = self.minCorner[1] + self.cellSize[1] * ( b + 0.5 )
        M = r - l
        N = t - b
        x = np.arange( M ) * self.cellSize[0] + firstX 
        y = np.arange( N ) * self.cellSize[1] + firstY
        X, Y = np.meshgrid( y, x )
        return np.dstack( (Y, X) )
        
    
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

    @property
    def rectDomain( self ):
        '''Returns the RectDomain data for this AbstractGrid.

        @returns        An instance of a RectDomain including this grid's minimum corner
                        position and world size.
        '''
        return RectDomain( self.minCorner, self.size )
        

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

    def getAbstractGrid( self ):
        '''Returns an AbstractGrid copy of this grid'''
        return AbstractGrid( self.minCorner, self.size, self.resolution, self.cellSize )
    
    def __str__( self ):
        return 'DataGrid from ( %.2f, %.2f ) to ( %.2f, %.2f ) - res: %d x %d' % ( self.minCorner[0], self.minCorner[1],
                                                                      self.minCorner[0] + self.size[0], self.minCorner[1] + self.size[1],
                                                                                       self.resolution[0], self.resolution[1] )

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

    def getValue( self, pos, fast=True ):
        '''Retrieves the value in the grid located at position.

        The grid has values at cell centers.  The value retrieved can either
        be the value at the center of the cell in which pos lies, or it can be the
        bilinear interpolation of several cell centers -- it depends on the fast argument.

        If pos lies outside the domain, then the value returned depends on the nearest
        cells.

        @param      pos     A 2-tuple-like object.  The x- and y-values of the point
                            in world space.
        @param      fast    A boolean.  If True, simply returns the value of the closest
                            center.  If false, uses bi-linear interpolation.
        @returns    A 2-tuple (int, value). The int is the enumeration INSIDE|OUTSIDE and the
                    second value (based on grid data type) is the value of the grid.  The caller
                    can interpret the INSIDE/OUTSIDE flag as it wishes.
        '''
        p = Vector2( pos[0], pos[1] )
        if ( fast ):
            return self.getValueFast( p )
        else:
            return self.getValueBilinear( p )

    def getValueFast( self, pos ):
        '''Retrieves the value in the grid located at cell center closest to pos.

        If pos lies outside the domain, then the value returned is the value of the
        nearest cell.

        @param      pos         A 2-tuple-like object.  The x- and y-values of the point
                                in world space.
        @returns    A 2-tuple (int, value). The int is the enumeration INSIDE|OUTSIDE and the
                    second value (based on grid data type) is the value of the grid.  The caller
                    can interpret the INSIDE/OUTSIDE flag as it wishes.
        '''
        state = INSIDE
        center = list( self.getCenter( pos ) )
        if ( center[0] < 0 ):
            state = OUTSIDE
            center[0] = 0
        elif ( center[0] >= self.resolution[0] ):
            state = OUTSIDE
            center[0] = self.resolution[0] - 1
        if ( center[1] < 0 ):
            state = OUTSIDE
            center[1] = 0
        elif ( center[1] >= self.resolution[1] ):
            state = OUTSIDE
            center[1] = self.resolution[1] - 1
        return state, self.cells[ center[0], center[1] ]

    def getValueBilinear( self, pos ):
        '''Retrieves the value in the grid located pos based on bilinear interpolation of
        the four nearest cell values.

        If pos lies outside the domain, then the value returned depends on the cells
        nearest pos.

        @param      pos         A 2-tuple-like object.  The x- and y-values of the point
                                in world space.
        @returns    A 2-tuple (int, value). The int is the enumeration INSIDE|OUTSIDE and the
                    second value (based on grid data type) is the value of the grid.  The caller
                    can interpret the INSIDE/OUTSIDE flag as it wishes.
        '''
        #
        #  Evaluates the point as follows
        #    |        |        |
        #   ---------------------
        #    |        |        |
        #    |   C    |   D    |
        #    |        | P      |
        #   ------------.-b------
        #    |        | .      |
        #    |   A....|.. B    |
        #    |      a |        |
        #   ---------------------
        #    |        |        |
        #
        #   P is the test point.  A, B, C, and D are the positions of the CENTERS of their corresponding
        #   cells.  We define the function f(P) as a bilinear weight
        #   Generally f(P) = b * ( a * D + (1-a) * C ) +
        #                   (1-b) * ( a * A + (1-a) * B )
        #
        #   There are special cases if A, B, C, or D are not well defined because P lies outside the domain
        #   spanned by the grid's CENTERS (which is slightly inset of the actual domain).
        #
        #   If P is to the left of the grid centers, then only centers DB are used, on the right only AC
        #   If P is above the grid centers, CD are used, if below AB
        #   If off in both directions, then only one of the corners is used.
        
        # Determine which cells contribute
        minCenter = self.minCorner + ( self.cellSize * 0.5 )
        Sx = ( pos[0] - minCenter[0] ) / self.cellSize[0]
        xBlend = None
        if ( Sx <= 0.0 ):  # point is on the left side of the centers domain
            Ax = 0
            xBlend = lambda left, right: left
        elif ( Sx >= self.resolution[0] - 1 ):   # point is on the RIGHT side of the centers domain
            Ax = self.resolution[0] - 2
            xBlend = lambda left, right: right
        else:       # point is nicely inside the well-behaved domain (on the x-axis)
            Ax = int( np.floor( Sx ) )
            alpha = Sx - Ax
            xBlend = lambda left, right: alpha * left + ( 1 - alpha ) * right

        Sy = ( pos[1] - minCenter[1] ) / self.cellSize[1]
        yBlend = None
        if ( Sy <= 0.0 ):  # point is on the left side of the centers domain
            Ay = 0
            yBlend = lambda bottom, top: bottom
        elif ( Sy >= self.resolution[1] - 1 ):   # point is on the RIGHT side of the centers domain
            Ay = self.resolution[1] - 2
            yBlend = lambda bottom, top: top
        else:       # point is nicely inside the well-behaved domain (on the x-axis)
            Ay = int( np.floor( Sy ) )
            beta = Sy - Ay
            yBlend = lambda bottom, top: beta * top + ( 1 - beta ) * bottom

        fA = self.cells[ Ax, Ay ]
        fB = self.cells[ Ax + 1, Ay ]
        bottom = xBlend( fA, fB )   # blend( A, B )
        fC = self.cells[ Ax, Ay + 1 ]
        fD = self.cells[ Ax + 1, Ay + 1 ]
        top = xBlend( fC, fD )   # blend( C, D )
        result = yBlend( bottom, top )
        state = INSIDE
        if ( Sx < -0.5 or Sx > self.resolution[0] - 0.5 or Sy < -0.5 or Sy > self.resolution[0] - 0.5 ):
            state = OUTSIDE
        return state, result

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

    def testValue():
        print 'Tests the value look-up of the grid'
        g = DataGrid( Vector2( -1, -1 ), Vector2( 2, 2 ), ( 2, 2 ) )
        data = np.array( ( ( 3, 1), (4, 2) ), dtype=np.float32 )
        g.cells[ :, : ] = data

        testPoints = (  (Vector2( -0.5, -0.5 ), 3, INSIDE ),
                        (Vector2( -0.5, 0.5 ), 1, INSIDE ),
                        (Vector2( 0.5, -0.5 ), 4, INSIDE ),
                        (Vector2( 0.5, 0.5 ), 2, INSIDE ),
                        (Vector2( -0.999, -0.999 ), 3, INSIDE ),
                        (Vector2( -1.1, -1.1 ), 3, OUTSIDE ),
                        (Vector2( -0.999, 0.999 ), 1, INSIDE ),
                        (Vector2( -1.1, 1.1 ), 1, OUTSIDE ),
                        (Vector2( 0.999, -0.999 ), 4, INSIDE ),
                        (Vector2( 1.1, -1.1 ), 4, OUTSIDE ),
                        (Vector2( 0.999, 0.999 ), 2, INSIDE ),
                        (Vector2( 1.1, 1.1 ), 2, OUTSIDE ),
                        )

        print "\tFast queries"
        for pt, soln, expState in testPoints:
            state, result = g.getValue( pt )
            if ( state != expState ):
                if ( state == INSIDE ):
                    print "\t\tFailed!  Misreported point %s inside the domain" % pt
                else:
                    print "\t\tFailed!  Misreported point %s outside the domain" % pt
            if ( soln != result ):
                print "\t\tFailed reading fast value at %s: Got %f, expected %f" % ( pt, result, soln )
            else:
                print "\t\tPassed: %s - %f" % ( pt, result )

        newTest = ( ( Vector2( 0, 0 ), 2.5, INSIDE ),
                    ( Vector2( 0, -0.6 ), 3.5, INSIDE ),
                    ( Vector2( 0, -1 ), 3.5, INSIDE ),
                    ( Vector2( 0, -1.1 ), 3.5, OUTSIDE ),
                    ( Vector2( 0, 0.6 ), 1.5, INSIDE ),
                    ( Vector2( 0, 1 ), 1.5, INSIDE ),
                    ( Vector2( 0, 1.1 ), 1.5, OUTSIDE ),
                    ( Vector2( 0.6, 0 ), 3, INSIDE ),
                    ( Vector2( 1, 0 ), 3, INSIDE ),
                    ( Vector2( 1.1, 0 ), 3, OUTSIDE ),
                    ( Vector2( -0.6, 0 ), 2, INSIDE ),
                    ( Vector2( -1, 0 ), 2, INSIDE ),
                    ( Vector2( -1.1, 0 ), 2, OUTSIDE ),
                    )
        testPoints = testPoints + newTest
        print "\tBilinearly interpolated queries"
        for pt, soln, expState in testPoints:
            state, result = g.getValue( pt, False )
            if ( state != expState ):
                if ( state == INSIDE ):
                    print "\t\tFailed!  Misreported point %s inside the domain" % pt
                else:
                    print "\t\tFailed!  Misreported point %s outside the domain" % pt
            if ( soln != result ):
                print "\t\tFailed reading fast value at %s: Got %f, expected %f" % ( pt, result, soln )
            else:
                print "\t\tPassed: %s - %f" % ( pt, result )
        
                
    testValue()
##    testIntersection()
    