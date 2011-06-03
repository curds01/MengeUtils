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
        index[ :, 1 ] = np.clip( index[ :, 1 ], 0, self.resolution[ 0 ] - 0.00001 )
        return np.array( np.floor( index ), dtype=np.int )
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
        print self.resolution
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
                x0 = minX + ( i + 0.5 ) * self.cellSize
                y0 = minY + ( j + 0.5 ) * self.cellSize
                dir = self.data[ j, i, : ]
                x1 = x0 + dir[0] * 0.4 * self.cellSize
                y1 = y0 + dir[1] * 0.4 * self.cellSize
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

    def drawGL( self, select=False, editable=False ):
        '''Draws the field into the gl context'''
        if ( not select ):
            glCallList( self.gridID )
            
            if ( editable ):
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
    for row in range( points.shape[0] ):
        print points[row,:], "maps to", cells[row,:]
        
if __name__ == '__main__':
    test()