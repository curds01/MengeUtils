# A simple data structure for working with height fields

import numpy as np
import Image
from trajectory import gaussian1D

class HeightField:
    def __init__( self ):
        self.cellSize = 0.0
        self.w = 0.0
        self.h = 0.0
        self.heights = None
        self.normals = None
        self.x = None
        self.y = None

    def loadImage( self, imgName, pixelSize, vertScale, x, y, kernel=0.0 ):
        '''Initializes the height field.

        @param      imgName     The name of the image with height data.
        @param      pixelSize   The size of the image pixel (in world units).
        @param      vertScale   The height of the maximally high point.
        @param      x           The position of the left most edge.
        @param      y           The position of the "bottom" most edge.
        @param      kernel      The size of the optional smoothing kernel.
        '''
        self.x = x
        self.y = y

        img = Image.open( imgName )
        self.cellSize = pixelSize
        self.w, self.h = img.size
        self.heights = np.empty( ( self.w, self.h ), dtype=np.float32 )
        self.normals = np.empty( ( self.w, self.h, 3 ), dtype=np.float32 )
        # population elevation
        self.populateElevation( img, vertScale )
        # smooth (as necessary )
        self.smoothElevation( kernel )
        # compute normals
        self.computeNormals()
        print "Image size:", img.size

    def populateElevation( self, img, scale ):
        '''Populates the height field.

        @param      img     An image containing the pixel information.
        @param      scale   The scale of the height field.
        '''
        scale /= 255.0  # normalize colors in the range 0-255
        for x in xrange( self.w ):
            for y in xrange( self.h ):
                color = img.getpixel( (x,y) )
                if ( isinstance( color, tuple ) ):
                    color = sum( color ) / 3.0
                self.heights[ x ][ y ] = color * scale

    def smoothElevation( self, kernel ):
        '''Smooths the normals according to kernel size.

        @param      kernel          Size of the smoothing kernel.
        '''
        if ( kernel > 0.0 ):
            k = gaussian1D( kernel, self.cellSize )
            halfCount = len( k ) / 2
            for row in xrange( self.h ):
                self.heights[ :, row ] = np.convolve( self.heights[ :, row ], k, 'same' )
            for col in xrange( self.w ):
                self.heights[ col, : ] = np.convolve( self.heights[ col, :], k, 'same' )
            
    def computeNormals( self ):
        '''Computes the normals from the elevation'''
        Nx = np.empty_like( self.heights )
        Ny = np.empty_like( self.heights )
        # compute the boundaries
        Nx[ 0,: ] = self.heights[ 1, : ] - self.heights[ 0, : ]
        Nx[ -1,: ] = self.heights[ -1, : ] - self.heights[ -2, : ]
        Ny[ :, 0 ] = self.heights[ :, 1 ] - self.heights[ :, 0 ]
        Ny[ -1,: ] = self.heights[ :, -1 ] - self.heights[ :, -2 ]
        # compute the centers
        Nx[ 1:-1, : ] = self.heights[ 2:, : ] - self.heights[ :-2, : ]
        Ny[ :, 1:-1 ] = self.heights[ :, 2: ] - self.heights[ :, :-2 ]
        # difference sizes
        diff = np.ones_like( self.heights ) * self.cellSize
        diff[ 1:-1, 1:-1 ] *= 2.0

        # cross product
        self.normals[ :, :, 0 ] = diff * Ny
        self.normals[ :, :, 1 ] = diff * diff
        self.normals[ :, :, 2 ] = diff * Nx

        # normalize
        len = np.sqrt( np.sum( self.normals * self.normals, 2 ) )
        len.shape = ( len.shape[0], len.shape[1], 1)
        self.normals[ :, :, : ] /= len
    
    def writeOBJ( self, fileName ):
        '''Writes the height field to an obj file.

        @param      A string.  The file name to write the obj file to.
        '''
        f = open( fileName, 'w' )
        normals = []
        # write vertices
        for w in xrange( self.w ):
            x = w * self.cellSize + self.x
            for h in xrange( self.h ):
                y = h * self.cellSize + self.y
                f.write( '\nv %.5f %.5f %.5f' % ( x, self.heights[ w, h ], y ) )
                normals.append( ( self.normals[ w, h, 0 ], self.normals[ w, h, 1 ], self.normals[ w, h, 2 ] ) )
        for x, y, z in normals:
            f.write( '\nn %.5f %.5f %.5f' % ( x, y, z ) )
        # write faces
        lower = 1
        upper = lower + self.w
        for h in xrange( self.h - 1):
            for w in xrange( self.w - 1 ):
                f.write( '\nf {0}/{0} {1}/{1} {2}/{2} {3}/{3}'.format( lower + w, lower + w + 1, upper + w + 1, upper + w )  )
            lower = upper
            upper = lower + self.w
                         
        f.close()

if __name__ == '__main__':
    hf = HeightField()
    hf.loadImage( 'D:\\projects\\fsmHacks\\examples\\terrain\\battlefield.png',
                  1.5,
                  150,
                  128,
                  256,
                  3.0
                  )
    hf.writeOBJ( 'mesh.obj' )
                      