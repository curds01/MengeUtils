'''Representation of a 2D vector field'''

import numpy as np
from OpenGL.GL import *

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
        span of the vector field, starting from the minPoint.
        @param cellSize: a float.  The length of a square cell's side.

        Grid cells will ALWAYS be square.  The size of the domain will expand such that
        the dimensions of the span is an integer multiple of the cell size.'''
        self.minPoint = np.array( minPoint, dtype=FLOAT )
        self.resolution = np.zeros( 2, dtype=np.int )
        self.cellSize = cellSize
        self.setDimensions( size )
        self.data = np.zeros( ( self.resolution[1], self.resolution[0], 2 ), dtype=FLOAT )
        self.data[ :, :, 0 ] = 1.0
        self.centers = np.zeros( ( self.resolution[1], self.resolution[0], 2 ), dtype=FLOAT )
        xValues = self.minPoint[0] + ( np.arange( self.resolution[1] ) + 0.5 ) * self.cellSize
        yValues = self.minPoint[1] + ( np.arange( self.resolution[0] ) + 0.5 ) * self.cellSize
        X, Y = np.meshgrid( xValues, yValues )
        self.centers[ :, :, 0 ] = X
        self.centers[ :, :, 1 ] = Y
        self.endPoints = self.centers + self.data * self.cellSize * 0.4

    def setDimensions( self, size ):
        '''Given a physical size and a cell size, modifies the physical size such that
        the grid consists of an integer number of cells in each dimension of the specified size.

        @param size: a list-like object with two floats.  The tuple represents the
        span of the vector field, starting from the minPoint.
        @param cellSize: a float.  The length of a square cell's side.
        '''
        size = np.array( size, dtype=FLOAT )
        self.resolution = np.array( np.ceil( size / self.cellSize ), dtype=np.int )
        self.size = self.resolution * self.cellSize

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
        return index

    def getCells( self, points ):
        '''Given a point in space, determines the value of the vector field at that point.
        If the point is outside of the field, the value of the closest cell is returned.

        @param points: an Nx2 array of floats.  Each row is the (x,y) position of a point.

        @return: an Nx2 array of ints.  Each row is the column, row pair for each (x,y) point.     
        '''
        offset = points - self.minPoint
        index = offset / self.cellSize
        index[ :, 0 ] = np.clip( index[ :, 0 ], 0, self.resolution[ 0 ] - 0.00001 )
        index[ :, 1 ] = np.clip( index[ :, 1 ], 0, self.resolution[ 1 ] - 0.00001 )
        return np.array( np.floor( index[:,::-1] ), dtype=np.int )

    def boundCircle( self, center, radius ):
        '''Given a center and radius, returns the indices of the cells that bound the circle.

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
        cells = self.getCells( extrema )
        minima = cells.min( axis=0 )
        maxima = cells.max( axis=0 ) + 1
        return minima, maxima

    def subRegion( self, minima, maxima ):
        '''Returns a portion of the field, defined by the index minima and maxima.

        @param minima: a 2-tuple-like object of ints.  The indices (i, j) represent the smallest indices of
        the region to compute.
        @param maxima: a 2-tuple-like object of ints.  The indices (I, J) represent the largest indices of the
        region to compute.  The region is defined as field[ i:I, j:J ].

        @return: a (I-i) x (J-j) x 2 array of floats.  The sub-region of the field.
        '''
        return self.data[ minima[0]:maxima[0], minima[1]:maxima[1], : ]

    def cellCenters( self, minima, maxima ):
        '''Returns the cell centers for a range of cell fields defined by index minima and maxima.

        @param minima: a 2-tuple-like object of ints.  The indices (i, j) represent the smallest indices of
        the region to compute.
        @param maxima: a 2-tuple-like object of ints.  The indices (I, J) represent the largest indices of the
        region to compute.  The region is defined as field[ i:I, j:J ].

        @return: a 2-tuple of (I-i) x (J-j) array of floats.  The positions of the cells in the indicated range.
        '''
        return self.centers[ minima[0]:maxima[0], minima[1]:maxima[1], : ]
##        size = maxima - minima
##        xValues = self.minPoint[0] + ( minima[1] + np.arange( size[1] ) + 0.5 ) * self.cellSize
##        yValues = self.minPoint[1] + ( minima[0] + np.arange( size[0] ) + 0.5 ) * self.cellSize
##        
##        return np.meshgrid( xValues, yValues )
##
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
    
    def writeField( self, fileName, ascii=True ):
        '''Writes the field out to the indicated file'''
        if ( ascii ):
            self.writeAsciiField( fileName )
        else:
            self.writeBinaryField( fileName )

    def writeAsciiField( self, fileName ):
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

    def writeBinaryField( self, fileName ):
        '''Writes the field out in ascii format to the indicated file'''
        raise AttributeError, "Binary vector field format not supported yet"

    def readField( self, fileName, ascii=True ):
        '''Reads the vector field contained in the file'''
        if ( ascii ):
            self.readAsciiField( fileName )
        else:
            self.readinaryField( fileName )

    def readAsciiField( self, fileName ):
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

    def readbinaryField( self, fileName ):
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
        VectorField.__init__( self, minPoint, size, cellSize )
        
        self.arrowID = 0    # the identifier for the arrow display list
        self.gridID = 0     # the identifier for the grid
        self.editable = False   # determines whether it should display in full edit mode

    def fieldChanged( self ):
        '''Reports a change to the grid'''
        VectorField.fieldChanged( self )
        self.genArrowDL()
    
    def newGLContext( self ):
        '''When a new OpenGL context is created, this gives the field the chance to update
        its OpenGL objects'''
        self.genArrowDL()
        self.genGridDL()

    def genArrowDL( self ):
        '''Generates the display list for the grid's vectors'''
        minX = self.minPoint[0]
        maxX = minX + self.size[0]
        minY = self.minPoint[1]
        maxY = minY + self.size[1]
        self.arrowID = glGenLists(1)
        glNewList( self.arrowID, GL_COMPILE )
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
        maxX = minX + self.size[0]
        minY = self.minPoint[1]
        maxY = minY + self.size[1]

        self.gridID = glGenLists(1)
        glNewList( self.gridID, GL_COMPILE )
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
    points = np.array( ( ( -0.5, -0.5 ),
                         (-0.5, 5.1 ),
                         ( 3.5, 4.7 ),
                         (11.1, 12.1 ) ) )
    cells = vf.getCells( points )
    print "10x10 grid goes from (0,0) to (10,10)"
    for row in range( points.shape[0] ):
        print points[row,:], "maps to", cells[row,:]
        
if __name__ == '__main__':
    test()