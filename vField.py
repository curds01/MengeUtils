'''Representation of a 2D vector field'''

import numpy as np
from OpenGL.GL import *
from primitives import Vector2

FLOAT = np.float32

class VectorField:
    '''Vector field class.  A vector field is a regular 2D grid of values.  In this case,
    each value is a 2D vector.'''
    
    def __init__( self, minPoint, size, cellSize ):
        '''Constructor.  Initialize the grid, determining its dimensions, scales and
        degree of tesselation.

        @param minPoint: a list-like object with two floats. The tuple represents the
        minimum extent of the field in the x and y directions.
        @param size: a list-like object with two floats.  The tuple represents the minimum
        span of the vector field, starting from the minPoint (height, width).
        @param cellSize: a float.  The length of a square cell's side.

        Grid cells will ALWAYS be square.  The size of the domain will expand such that
        the dimensions of the span is an integer multiple of the cell size.'''
        self.minPoint = np.array( minPoint, dtype=FLOAT )
        self.resolution = np.zeros( 2, dtype=np.int )
        self.cellSize = cellSize
        self.setDimensions( size )

    def isValidCell(self, r, c):
        '''Reports True if (r, c) references a valid cell in the data'''
        return r >= 0 and c >= 0 and r < self.data.shape[0] and c < self.data.shape[1]

    def setMinX( self, value ):
        '''Sets the minimum x-value'''
        self.minPoint[0] = value

    def setMinY( self, value ):
        '''Sets the mininum y-value'''
        self.minPoint[1] = value

    def setWidth( self, value ):
        '''Sets the width value'''
        self.setDimensions( (self.size[0], value ) )

    def setHeight( self, value ):
        '''Sets the height value'''
        self.setDimensions( (value, self.size[1] ) )
    
    def getCorners( self ):
        '''Returns a list of 2d numpy arrays consisting of the corners in order of:
            minium point (mp), mp + (w, 0), mP + (w, h), mp + (0, h).

            This includes references to the minimum point; changes to corners[0] or
            corners[1] will change the underlying point.'''
        mp = self.minPoint
        sz = self.size
        return [ mp, mp + np.array( (sz[1], 0) ), mp + np.array( (sz[1], sz[0] ) ), mp + np.array( (0, sz[0]) ) ]

    def setCellSize( self, cellSize, size=None ):
        '''Given a cell size, recomputes the grid subject to specific constraints.
           1. Cell size changes to accomodate the change.
           2. Cells remain square
           The implication is that the effective size of the grid changes.  Computes the new size to
           bound the indicated size as closely as possible.

        @param cellSize: a float.  The size of the side of a square cell
        @param size: a list-like object with two ints.  The tuple represents the height and width of
        the target vector field.
        '''
        self.cellSize = cellSize
        if ( size is None ):
            self.setDimensions( self.size )
        else:
            self.setDimensions( size )
    
    def setDimensions( self, size ):
        '''Given a physical size and a cell size, modifies the physical size such that
        the grid consists of an integer number of cells in each dimension of the specified size.

        @param size: a list-like object with two floats.  The tuple represents the
        span of the vector field, starting from the minPoint.
        @param cellSize: a float.  The length of a square cell's side.
        '''
        size = np.array( size, dtype=FLOAT )
        self.resolution = np.array( np.ceil( size / self.cellSize ), dtype=np.int )#[::-1]
        self.data = np.zeros( ( self.resolution[0], self.resolution[1], 2 ), dtype=FLOAT )
        self.data[ :, :, 0 ] = 1.0
                
        self.size = self.resolution * self.cellSize
        self.gridChanged()

    def getCell( self, pt ):
        '''Given a point in space, determines the value of the vector field at that point.
        If the point is outside of the field, the value of the closest cell is returned.

        @param pt: a list-like object with two floats.  The (x, y) position to look up.
        
        @return: an array of size 2.  The col, row indices of the mapped cell.
        '''
        point = np.array( pt, dtype=FLOAT )
        offset = point - self.minPoint
        index = offset / self.cellSize
        # the x value goes with columns (the second dimension)
        # the y value goes with rows (the first dimension)
        index[0] = np.clip( index[0], 0, self.resolution[1] - 0.00001 )
        index[1] = np.clip( index[1], 0, self.resolution[0] - 0.00001 )
        index = np.array( np.floor( index ),dtype=np.int )
        return index[ ::-1 ]

    def getCells( self, points ):
        '''Given a point in space, determines the value of the vector field at that point.
        If the point is outside of the field, the value of the closest cell is returned.

        @param points: an Nx2 array of floats.  Each row is the (x,y) position of a point.

        @return: an Nx2 array of ints.  Each row is the column, row pair for each (x,y) point.     
        '''
        offset = points - self.minPoint
        index = offset / self.cellSize
        index[ :, 0 ] = np.clip( index[ :, 0 ], 0, self.resolution[ 1 ] - 0.00001 )
        index[ :, 1 ] = np.clip( index[ :, 1 ], 0, self.resolution[ 0 ] - 0.00001 )
        return np.array( np.floor( index[:,::-1] ), dtype=np.int )

    def getMagnitudes( self ):
        '''Returns the magnitudes of the vectors in the fields.

        @returns        A NxM numpy array of floats.  Each float is the magnitude of the
                        vector in cell[n,m].
        '''
        return np.sqrt( np.sum( self.data * self.data, 2 ) )

    def subRegion( self, minima, maxima ):
        '''Returns a portion of the field, defined by the index minima and maxima. The region is
        defined in the range [minima, maxima) -- in other words, the cell indices in maxima define
        the cells that the region goes up to, but does not include.

        If the sub region extends beyond the domain of the field, the "extra" cells will be
        populated with the zero value. The resulting region will be a unique, deep copy of the data.
        However, if the region is completely contained by the field, it will be a mutable slice
        into the data.

        @param minima:      A 2-tuple-like object of ints. The indices (i, j) represent the smallest
                            indices of the region to compute.
        @param maxima:      A 2-tuple-like object of ints. The indices (I, J) represent the largest
                            indices of the region to compute. The region is defined as
                            `field[i:I, j:J]`.

        @return: a (I-i) x (J-j) x 2 array of floats.  The sub-region of the field.

        @pre The maxima index values must be at least as large as the minima index values.
        '''
        assert(maxima[0] >= minima[0])
        assert(maxima[1] >= minima[1])
        if (minima[0] >= 0 and minima[1] >= 0 and
            maxima[0] < self.data.shape[0] and maxima[1] < self.data.shape[1]):
            return self.data[minima[0]:maxima[0], minima[1]:maxima[1], :]
        row_count = maxima[0] - minima[0]
        col_count = maxima[1] - minima[1]
        result = np.zeros((row_count, col_count, 2), dtype=self.data.dtype)
        # Compute the region to read from and the corresponding region to write to.
        min_r = max(0, minima[0])
        min_c = max(0, minima[1])
        # Note: min(shape[i], maxima[i]) can produce a value that's *less* than minima.
        # Specifically, it can produce a negative value. If min slice index is non-negative and the
        # max slice index is negative and valid (i.e., in the range [-1, -self.shape[i]]), then I'll
        # get a valid, non-empty slice. So, in this case, we confirm that the slice is logically
        # meaningful before we turn it over to numpy to slice.
        max_r = max(min(self.data.shape[0], maxima[0]), min_r)
        max_c = max(min(self.data.shape[1], maxima[1]), min_c)
        sub_region = self.data[min_r:max_r:1, min_c:max_c:1, :]
        if sub_region.size > 0:
            delta_r = max_r - min_r
            delta_c = max_c - min_c
            target_r = min_r - minima[0]
            target_c = min_c - minima[1]
            result[target_r:target_r + delta_r, target_c:target_c + delta_c, :] = sub_region
        return result

    def cellCenters( self, minima, maxima ):
        '''Returns the cell centers for a range of cell fields defined by index minima and maxima.

        @param minima: a 2-tuple-like object of ints.  The indices (i, j) represent the smallest indices of
        the region to compute.
        @param maxima: a 2-tuple-like object of ints.  The indices (I, J) represent the largest indices of the
        region to compute.  The region is defined as field[ i:I, j:J ].

        @return: a 2-tuple of (I-i) x (J-j) array of floats.  The positions of the cells in the indicated range.
        '''
        return self.centers[ minima[0]:maxima[0], minima[1]:maxima[1], : ]

    def cellSegmentDistance( self, minima, maxima, p1, p2 ):
        '''Returns a 2D array of distances from a line segment: (p1, p2).

        @param minima: a 2-tuple-like object of ints.  The indices (i, j) represent the smallest indices of
        the region to compute.
        @param maxima: a 2-tuple-like object of ints.  The indices (I, J) represent the largest indices of the
        region to compute.  The region is defined as field[ i:I, j:J ].
        @param p1: a 2-tuple of floats.  The first end point of the segment.
        @param p2: a 2-tuple of floats.  The second end point of the segment.

        @return: a (I-i) x (J-j) array of floats.  The distances from each cell center to point.
        '''
        centers = self.cellCenters( minima, maxima )
        # create the implicit equation of the line
        A = p1[1] - p2[1]
        B = p2[0] - p1[0]
        mag = np.sqrt( A * A + B * B )
        A /= mag
        B /= mag
        C = ( p1[0] * p2[1] - p2[0] * p1[1] ) / mag

        # create a vector in the direction of the line.  Use this to determine which points are near the
        #   line segment and which are near the end points
        dir = Vector2( p2[0], p2[1] ) - Vector2( p1[0], p1[1] )
        mag = dir.magnitude()
        dir = dir / mag
        dir = np.array( ( dir[0], dir[1] ) )
        relCenters = centers - np.array( p1 )
        projection = np.sum( relCenters * dir, axis=2 )
        nearP1 = projection < 0
        nearP2 = projection > mag
        nearSeg = ~( nearP1 | nearP2 )
        
        segDist = np.abs( A * centers[ nearSeg, 0 ] + B * centers[ nearSeg, 1 ] + C )
        dX = centers[ nearP1, 0 ] - p1[0]
        dY = centers[ nearP1, 1 ] - p1[1]
        p1Dist = np.sqrt( dX * dX + dY * dY )
        dX = centers[ nearP2, 0 ] - p2[0]
        dY = centers[ nearP2, 1 ] - p2[1]
        p2Dist = np.sqrt( dX * dX + dY * dY )
        distances = np.zeros( ( centers.shape[:-1] ) )
        distances[ nearSeg ] = segDist
        distances[ nearP1 ] = p1Dist
        distances[ nearP2 ] = p2Dist

        return distances        

    def cellDistances( self, minima, maxima, point ):
        '''Returns a 2D array of distances from a point.

        @param minima: a 2-tuple-like object of ints.  The indices (i, j) represent the smallest indices of
        the region to compute.
        @param maxima: a 2-tuple-like object of ints.  The indices (I, J) represent the largest indices of the
        region to compute.  The region is defined as field[ i:I, j:J ].
        @param point: a 2-tuple of floats.  The position from which distance is to be computed.

        @return: a (I-i) x (J-j) array of floats.  The distances from each cell center to point.
        '''
        centers = self.cellCenters( minima, maxima )
        dX = centers[ :, :, 0 ] - point[0]
        dY = centers[ :, :, 1 ] - point[1]
        return np.sqrt( dX * dX + dY * dY )
           
    
    def fieldChanged( self ):
        '''Reports a change to the field data'''
        self.endPoints = self.centers + self.data * self.cellSize * 0.4

    def write( self, fileName, ascii=True ):
        '''Writes the field out to the indicated file'''
        if ( ascii ):
            self.writeAscii( fileName )
        else:
            self.writeBinary( fileName )

    def gridChanged( self ):
        '''Updated when the grid parameters change'''
        self.centers = np.zeros( ( self.resolution[0], self.resolution[1], 2 ), dtype=FLOAT )
        xValues = self.minPoint[0] + ( np.arange( self.resolution[1] ) + 0.5 ) * self.cellSize
        yValues = self.minPoint[1] + ( np.arange( self.resolution[0] ) + 0.5 ) * self.cellSize
        X, Y = np.meshgrid( xValues, yValues )
        self.centers[ :, :, 0 ] = X
        self.centers[ :, :, 1 ] = Y
        self.endPoints = self.centers + self.data * self.cellSize * 0.4

    def writeAscii( self, fileName ):
        '''Writes the field out in ascii format to the indicated file'''
        f = open( fileName, 'w' )
        # resolution
        f.write( '{0} {1}\n'.format( self.resolution[0], self.resolution[1] ) )
        # cell size
        f.write( '{0}\n'.format( self.cellSize ) )
        # minimum point
        f.write( '{0} {1}\n'.format( self.minPoint[0], self.minPoint[1] ) )
        # data
        for y in xrange( self.resolution[0] ):
            for x in xrange( self.resolution[1] ):
                f.write( '{0} {1}\n'.format( self.data[y, x, 0], self.data[y, x, 1] ) )
        f.close()

    def writeBinary( self, fileName ):
        '''Writes the field out in ascii format to the indicated file'''
        raise AttributeError, "Binary vector field format not supported yet"

    def read( self, fileName, ascii=True ):
        '''Reads the vector field contained in the file'''
        if ( ascii ):
            self.readAscii( fileName )
        else:
            self.readinary( fileName )
        self.gridChanged()

    def readAscii( self, fileName ):
        '''Reads the field out in ascii format to the indicated file'''
        f = open( fileName, 'r' )
        line = f.readline()
        self.resolution = np.array( map( lambda x: int(x), line.split() ) )
        self.cellSize = float( f.readline() )
        self.minPoint = np.array( map( lambda x: float(x), f.readline().split() ) )
        self.size = self.resolution * self.cellSize
        self.data = np.zeros( (self.resolution[0],self.resolution[1],2), dtype=FLOAT )
        for y in xrange( self.resolution[0] ):
            for x in xrange( self.resolution[1] ):
                self.data[ y, x, : ] = map( lambda x: float(x), f.readline().split() )
        f.close()

    def readbinary( self, fileName ):
        '''Reads the field out in ascii format to the indicated file'''
        raise AttributeError, "Binary vector field format not supported yet"

                
    
class GLVectorField( VectorField ):
    '''A Vector field which knows how to draw itself in an OpenGL context'''
    def __init__( self, minPoint, size, cellSize ):
        '''Constructor.  Initialize the grid, determining its dimensions, scales and
        degree of tesselation.

        @param minPoint: a list-like object with two floats. The tuple represents the
        minimum extent of the field in the x and y directions.
        @param size: a list-like object with two floats.  The tuple represents the minimum
        span of the vector field, starting from the minPoint.
        @param cellSize: a float.  The length of a square cell's side.

        Grid cells will ALWAYS be square.  The size of the domain will expand such that
        the dimensions of the span is an integer multiple of the cell size.'''
        self.has_context = False
        VectorField.__init__( self, minPoint, size, cellSize )
        
        self.arrowID = 0    # the identifier for the arrow display list
        self.gridID = 0     # the identifier for the grid
        self.editable = False   # determines whether it should display in full edit mode

    def fieldChanged( self ):
        '''Reports a change to the grid'''
        VectorField.fieldChanged( self )
        self.genArrowDL()

    def gridChanged( self ):
        '''Reports a change to the grid'''
        VectorField.gridChanged( self )
        if self.has_context:
            self.genArrowDL()
            self.genGridDL()
    
    def newGLContext( self ):
        '''When a new OpenGL context is created, this gives the field the chance to update
        its OpenGL objects'''
        self.has_context = True
        self.genArrowDL()
        self.genGridDL()

    def genArrowDL( self ):
        '''Generates the display list for the grid's vectors'''
        minX = self.minPoint[0]
        maxX = minX + self.size[0]
        minY = self.minPoint[1]
        maxY = minY + self.size[1]
        self.arrowID = glGenLists(1)
        try:
            glNewList( self.arrowID, GL_COMPILE )
        except:
            self.arrowID = 0
        glBegin( GL_LINES )
        glColor3f( 0.9, 0.45, 0.0 )
        # draw arrows
        for i in xrange( self.resolution[1] ):
            for j in xrange( self.resolution[0] ):
                x0 = self.centers[ j, i, 0 ]
                y0 = self.centers[ j, i, 1 ]
                x1 = self.endPoints[ j, i, 0 ]
                y1 = self.endPoints[ j, i, 1 ]
                glVertex3f( x0, y0, 0.0 )
                glVertex3f( x1, y1, 0.0 )
        glEnd()
        glEndList()
        
    def genGridDL( self ):
        minX = self.minPoint[0]
        maxX = minX + self.size[1]
        minY = self.minPoint[1]
        maxY = minY + self.size[0]

        self.gridID = glGenLists(1)
        try:
            glNewList( self.gridID, GL_COMPILE )
        except:
            self.gridID = 0
        glColor3f( 0.25, 0.25, 0.25 )
        glBegin( GL_LINES )
        # horizontal lines
        for i in xrange( self.resolution[0] + 1 ):
            y = minY + i * self.cellSize
            glVertex3f( minX, y, 0.0 )
            glVertex3f( maxX, y, 0.0 )
        # vertical lines
        for i in xrange( self.resolution[1] + 1 ):
            x = minX + i * self.cellSize
            glVertex3f( x, minY, 0.0 )
            glVertex3f( x, maxY, 0.0 )
        glEnd()
        glEndList()

    def drawGL( self, select=False, dummy=False ):
        '''Draws the field into the gl context'''
        if ( not select ):
            glCallList( self.gridID )
            
            if ( self.editable ):
                glCallList( self.arrowID )

    def readField( self, fileName, ascii=True ):
        '''Populates the field from the field file given'''
        VectorField.readField( self, fileName, ascii )
        self.newGLContext()
        
    
def test():
    '''test the functiaonlity of the grid'''
    vf = VectorField( (0,0), (10, 10), 1.0 )
    vf.read( "field.txt" )
    points = np.array( ( ( 0,0 ),
                         (-30, -30 ),
                         ( -30, 0 ),
                         ( -30, 30 ),
                         ) )
    cells = vf.getCells( points )
    for i in range( points.shape[0] ):
        print "point", points[i], "=", vf.data[ cells[i][0], cells[i][1], :]
                         
##    vf = VectorField( (0,0), (10, 10), 1.0 )
##    points = np.array( ( ( -0.5, -0.5 ),
##                         (-0.5, 5.1 ),
##                         ( 3.5, 4.7 ),
##                         (11.1, 12.1 ) ) )
##    cells = vf.getCells( points )
##    print "10x10 grid goes from (0,0) to (10,10)"
##    for row in range( points.shape[0] ):
##        print points[row,:], "maps to", cells[row,:]
        
if __name__ == '__main__':
    test()