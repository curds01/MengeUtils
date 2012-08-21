# This file contain various different Kernels
# Uniform, Linear, Bi-weight, Gaussian (fixed and variable)

import numpy as np
from DistFuncs import *

class KernelError( Exception ):
    pass

class KernelSignalError( KernelError ):
    pass

IDENTITY_FUNCTION = lambda x, sigma: x
IDENTITY_FUNCTION_2D = lambda x, y, sigma: (x + y) * sigma

class KernelBase( object ):
    '''The base class of a discrete convolution kernel'''
    def __init__( self, smoothParam, cellSize, reflect=True, func=IDENTITY_FUNCTION ):
        '''Initializes the kernel with the smoothing parameter and boundary behavior.

        @param  smoothParam     A float.  The smoothing parameter.  The interpretation varies
                                based on the kernel type.
        @param  cellSize        The size of the uniform sampling of the kernel.
        @param  reflect         A boolean.  Determines if the kernel reflects at boundaries.
                                Only supports simple, convex boundaries.
        @param  func            A pointer to the function for the kernel.
        '''
        self.dFunc = func
        self.sampleKernel( smoothParam, cellSize )
        self.reflectBoundaries = reflect

    def __str__( self ):
        return 'Kernel: smooth: %f, cellSize: %f' % ( self._sigma, self._w )
    
    def sampleKernel( self, smoothParam, cellSize ):
        self._sigma = smoothParam
        self._w = cellSize
        self.computeSamples()

    def computeSamples( self ):
        '''Based on the nature of the kernel, pre-compute the discrete kernel for given parameters.'''
        raise KernelError, "Basic kernel is undefined"
        
    def getSupport( self ):
        '''Returns the size of the compact support of the function'''
        return 1.0
        
    @property
    def smoothParam( self ):
        '''Getter for the smoothing parameter'''
        return self._sigma

    @smoothParam.setter
    def smoothParam( self, value ):
        '''Setter for the smoothing parmaeter'''
        self.sampleKernel( value, self._w )

    @property
    def cellSize( self ):
        '''Getter for the smoothing parameter'''
        return self._w

    @cellSize.setter
    def cellSize( self, value ):
        '''Setter for the smoothing parmaeter'''
        self.sampleKernel( self._sigma, value )

    def convolve( self, signal, grid ):
        '''Convolves this kernel with the signal and places the result on the grid.normalize

        @param  signal      An instance of Signal class (See Signal.py )
        @param  grid        An instance of grid (see Grid.py).  Convolution is computed over
                            the domain represented by the grid.  The grid's values will be
                            changed as a result of this operation.
        '''
        if ( isinstance( signal, DiracSignal ) ):
            convolveDirac( signal, grid )
        elif ( isinstance( signal, FieldSignal ) ):
            convolveField( signal, grid )
        else:
            raise KernelSignalError, "Unrecognized signal type %s" % ( str( type( signal ) ) )

    def convolveDirac( self, signal, grid ):
        '''Convolve the kernel against a dirac signal'''
        w, h = self.data.shape
        w /= 2
        h /= 2
        for pos in signal.impulses:
            self.splatKernel( pos, w, h, self.data, grid )               

    def splatKernel( self, pos, halfW, halfH, kernelData, grid ):
        '''Used by the dirac convolution.  Splats the kernel at the given position.

        Splats the kernel into the given grid.        

        @param  pos     A numpy array of shape (2,1).  The position of the kernel
        @param  halfW   An int.  The width of the kernel / 2.  It should be true that halfW = kernelData.shape[0] / 2 
        @param  halfH   An int.  The height of the kernel / 2.  It should be true that halfH = kernelData.shape[1] / 2
        @param  kernelData  A kxk numpy array of the kernel data.max
        '''
        center = grid.getCenter( Vector2( pos[0], pos[1] ) )
        l = center[0] - halfW
        r = center[0] + halfW + 1
        b = center[1] - halfH
        t = center[1] + halfH + 1
        kl = 0
        kb = 0
        kr, kt = kernel.data.shape
        if ( l < 0 ):
            kl -= l
            l = 0
        if ( b < 0 ):
            kb -= b
            b = 0
        if ( r >= grid.resolution[0] ):
            kr -= r - grid.resolution[0]
            r = grid.resolution[0]
        if ( t >= grid.resolution[1] ):
            kt -= t - grid.resolution[1]
            t = grid.resolution[1]
        try:
            if ( l < r and b < t and kl < kr and kb < kt ):
                # Convolution
                self.cells[ l:r, b:t ] += kernelData[ kl:kr, kb:kt ]
        if ( self.reflectBoundaries ):
            if ( kl > 0 ):  # reflect around left boundary
                # reflect center piece
                reflKernel = kernelData[ :kl, kb:kt ][::-1, : ]
                tempR = min( r, reflKernel.shape[0] )
                self.cells[ l:tempR, b:t ] += reflKernel[ :tempR, kb:kt ]
                
                if ( kb > 0 ):  # also reflect around bottom
                    reflKernel = kernelData[ :kl, :kb ][::-1, ::-1]
                    tempT = min( t, reflKernel.shape[1] )
                    self.cells[ l:tempR, b:tempT ] += reflKernel[ :tempR, :tempT ]

                if ( kt < kernelData.shape[1] ):  # also reflect around top
                    reflKernel = kernelData[ :kl, kt: ][::-1, ::-1]
                    tempB = max( b, t - reflKernel.shape[1] )
                    tempKB = max( kb, kt - reflKernel.shape[1] )
                    self.cells[ l:tempR, tempB:t ] += reflKernel[ :tempR, tempKB:]

            if ( kr < kernelData.shape[0] ):  # reflect around right boundary
                # reflect center piece
                reflKernel = kernelData[ kr:, kb:kt ][::-1, : ]
                tempKL = max( 0, kernelData.shape[0] - reflKernel.shape[0] )
                tempL = max( l, r - reflKernel.shape[0] )
                self.cells[ tempL:r, b:t ] += reflKernel[ tempKL:, kb:kt ]
                
                if ( kb > 0 ):  # also reflect around bottom
                    reflKernel = kernelData[ kr:, :kb ][::-1, ::-1]
                    tempT = min( t, reflKernel.shape[1] )
                    self.cells[ tempL:r, b:tempT ] += reflKernel[ tempKL:, :tempT ]

                if ( kt < kernelData.shape[1] ):  # also reflect around top
                    reflKernel = kernelData[ kr:, kt: ][::-1, ::-1]
                    tempB = max( b, t - reflKernel.shape[1] )
                    tempKB = max( kb, kt - reflKernel.shape[1] )
                    self.cells[ tempL:r, tempB:t ] += reflKernel[ tempKL:, tempKB:]

            # todo if kb > 0 and kt < kernelData.shape[1]
            if ( kb > 0 ):      # reflect around the bottom
                reflKernel = kernelData[ :kb, kl:kr ][:, ::-1]
                tempT = min( t, reflKernel.shape[1] )
                self.cells[ l:r, b:tempT ] += reflKernel[ kl:kr, :tempT ]

            if ( kt < kerenlData.shape[1] ):        # reflect around the top
                reflKernel = kernelData[ kt:, kl:kr ][:, ::-1 ]
                tempB = max( b, t - reflKernel.shape[1] )
                tempKB = max( kb, kt - relfKernel.shape[1] )
                self.cells[ l:r, tempB:t ] += reflKernel[ kl:kr, tempKB: ]
            
class SeparableKernel( KernelBase ):
    '''The base class of a separable convolution kernel'''
    
    def __init__( self, smoothParam, cellSize, reflect=True, func=IDENTITY_FUNCTION ):
        '''Initializes the kernel with the smoothing parameter and boundary behavior.

        @param  smoothParam     A float.  The smoothing parameter.  The interpretation varies
                                based on the kernel type.
        @param  cellSize        The size of the uniform sampling of the kernel.
        @param  reflect         A boolean.  Determines if the kernel reflects at boundaries.
                                Only supports simple, convex boundaries.
        @param  func            A pointer to the function for the kernel.  Must be a function
                                in two arguments: x and smoothing parameter.
        '''
        #TODO: Validate that the func has the correct interface
        KernelBase.__init__( self, smoothParam, cellSize, reflect, func )

    def __str__( self ):
        return 'SeparableKernel: smooth: %f, cellSize: %f' % ( self._sigma, self._w )
    
    def convolveField( self, signal, grid ):
        pass

    def computeSamples( self ):
        '''Based on the nature of the kernel, pre-compute the discrete kernel for given parameters.'''
        # do work
        width = self.getSupport() 
        hCount = int( width / self._w )
        if ( hCount % 2 == 0 ):  # make sure cell has an odd-number of samples
            hCount += 1
        x = np.arange( -(hCount/2), hCount/2 + 1) * self._w
        
        self.data1D = self.dFunc( x, self._sigma )
        temp = np.reshape( self.data1D, (-1, 1 ) )
        self.data = temp * temp.T

class InseparableKernel( KernelBase ):
    '''The base class of an inseparable convolution kernel'''
    def __init__( self, smoothParam, cellSize, reflect=True, func=IDENTITY_FUNCTION_2D ):
        '''Initializes the kernel with the smoothing parameter and boundary behavior.

        @param  smoothParam     A float.  The smoothing parameter.  The interpretation varies
                                based on the kernel type.
        @param  cellSize        The size of the uniform sampling of the kernel.
        @param  reflect         A boolean.  Determines if the kernel reflects at boundaries.
                                Only supports simple, convex boundaries.
        @param  func            A pointer to the function for the kernel.  Must be a function
                                in three arguments: x, y and smoothing parameter.
        '''
        #TODO: Validate that the func has the correct interface
        KernelBase.__init__( self, smoothParam, cellSize, reflect, func )

    def __str__( self ):
        return 'InseparableKernel: smooth: %f, cellSize: %f' % ( self._sigma, self._w )
    
    def convolveField( self, signal, grid ):
        pass

    def computeSamples( self ):
        '''Based on the nature of the kernel, pre-compute the discrete kernel for given parameters.'''
        # do work
        width = self.getSupport() 
        hCount = int( width / self._w )
        if ( hCount % 2 == 0 ):  # make sure cell has an odd-number of samples
            hCount += 1
        o = np.arange( -(hCount/2), hCount/2 + 1) * self._w
        X, Y = np.meshgrid( o, o )

        self.data = self.dFunc( X, Y, self._sigma )

##class ConstKernel:
##    pass
##
##class VariableKernel:
##    def getImpulseKernel( self, impulse ):
##        '''Returns the kernel appropriate for this impulse'''
##        return self.data
##    

class SeparableConstKernel( SeparableKernel, ConstKernel ):
    pass

class ConstGaussianKernel( SeparableKernel, ConstKernel ):
    pass

class Plaue11Kernel( KernelBase ):
    def __init__( self, smoothParam, cellSize, reflect, obstacles=None  ):
        # TODO: Needs obstacles, needs the full set of data
        self.obstacles = obstacles
        dFunc = lambda x, y, z: x + y + z   #todo, use the real function
        KernelBase.__init__( self, smoothParam, cellSize, reflect, dFunc )

    def convolveDirac( self, signal, grid ):
        '''Convolve the kernel against a dirac signal'''
        for pos in signal.impulses:
            k = self.getImpulseKernel( pos )
            w, h = k.shape
            w /= 2
            h /= 2
            self.splatKernel( pos, w, h, k, grid )               
        
    def getImpulseKernel( self, impulse ):
        '''Returns the kernel appropriate for this impulse.

        @param      A numpy array of shape (2,).  The 2D impulse position.
        @returns    A kxk numpy array representing the discrete kernel.
                        k is odd.
        '''
        # find nearest neighbor
        # use self.signal to find nearest neighbors
        pass

    def convolveDirac( self, signal, grid ):
        '''Convolve the kernel against a dirac signal'''
        w, h = self.data.shape
        w /= 2
        h /= 2
        for dirac in signal.impulses:
            
            

        
    
class Kernel:
    """Distance function kernel"""
    def __init__( self, radius, smoothParam, dFunc, cSize):
        """Creates a kernel to add into the grid.normalize
        The kernel is a 2d grid (with odd # of cells in both directions.)
        The cell count is determined by the radius and cell size.x
        The cellsize is a tuple containing the width and height of a cell.
        (it need not be square.)  The values in each cell are determined
        by the distance of each cell from the center cell computed with
        dFunc.  Each cell is given a logical size of cSize"""
        if (dFunc == FUNCS_MAP['gaussian'] or dFunc == FUNCS_MAP['variable-gaussian']):
            hCount = int( 6 * radius / cSize.x )
        elif (dFunc == FUNCS_MAP['linear'] or dFunc == FUNCS_MAP['biweight'] ):
            hCount = int( 2 * radius / cSize.x )
        else:
            hCount = int( radius / cSize.x )
        if ( hCount % 2 == 0 ):
            hCount += 1

        o = np.arange( -(hCount/2), hCount/2 + 1) * cSize.x
        X, Y = np.meshgrid( o, o )
        if( dFunc == FUNCS_MAP['variable-gaussian'] ):
            if( smoothParam == None ):
                print '\n Please specify smoothing parameter '
                exit(1)
            self.data = dFunc( X, Y, radius, smoothParam )
        else:
            self.data = dFunc( X, Y, radius )

    def max( self ):
        return self.data.max()

    def min( self ):
        return self.data.min()

    def sum( self ):
        return self.data.sum()
    
    def __str__( self ):
        return str( self.data )

class Kernel2:
    """Computes the contribution of an agent to it's surrounding neighborhood"""
    # THE BIG DIFFERENCE between Kernel2 and Kernel:
    #   Kernel assumes that every agent is centered on a cell, so the contribution
    #   is a fixed contribution to the neighborhood
    #   This kernel has fixed size, but the values change because it's computed based
    #   on the actual world position of the agent w.r.t. the world position of the kernel center
    #   So, this creates a generic kernel of the appropriate size, but then given a particular
    #   center value and a particular position, computes the unique kernel (instance method)
    def __init__( self, radius, cSize ):
        # compute size: assume cSize is square
        self.k = int( 6 * radius / cSize.x )
        if ( self.k % 2 == 0 ):
            self.k += 1
        self.data = np.zeros( (self.k, self.k), dtype=np.float32 )
        # world offsets from the center of the kernel
        o = np.arange( -(self.k/2), self.k/2 + 1) * cSize.x
        self.localX, self.localY = np.meshgrid( o, o )
        
    def instance( self, dfunc, center, position ):
        '''Creates an instance of the sized kernel for this center and position'''
        localPos = position - center
        deltaX = ( self.localX - localPos.x ) ** 2
        deltaY = ( self.localY - localPos.y ) ** 2
        distSqd = deltaX + deltaY
        # the distance function must take an array as an argument.
        self.data = dfunc( distSqd )

if __name__ == '__main__':
    def test():
        k = SeparableKernel( 1.0, 0.2 )
        print k
        k.cellSize = 0.4
        print k
        print k.data


    test()
    
