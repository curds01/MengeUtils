# This file contain various different Kernels
# Uniform, Linear, Bi-weight, Gaussian (fixed and variable)

import numpy as np
from DistFuncs import *
from Signals import *
from primitives import Vector2

class KernelError( Exception ):
    pass

class KernelSignalError( KernelError ):
    pass

class KernelImplementationError( KernelError ):
    '''Error for indicating access to an unimplemented function'''
    pass

class KernelDomainError( KernelError ):
    '''Error indicating that the kernel has alignment problems in the domain'''
    pass

KERNEL_EPS = 0.00001

IDENTITY_FUNCTION = lambda x, sigma: x
IDENTITY_FUNCTION_2D = lambda x, y, sigma: (x + y) * sigma
UNIFORM_FUNCTION = lambda x, sigma: np.zeros_like( x ) + (1.0 / sigma)
UNIFORM_FUNCTION_2D = lambda x, y, sigma: np.zeros_like( x ) + ( 1.0 / ( sigma * sigma ) )
GAUSSIAN_FUNCTION = lambda x, sigma: np.exp( -( x * x ) / ( 2 * sigma * sigma ) ) / ( np.sqrt( 2.0 * np.pi ) * sigma )
GAUSSIAN_FUNCTION_2D = lambda x, y, sigma: np.exp( -( x * x + y * y) / ( 2 * sigma * sigma ) ) / ( 2.0 * np.pi * sigma * sigma )
def POLAR_BIWEIGHT_FUNC_2D( x, y, sigma ):
    '''Defines a 2D biweight function f(x,y): 225/226s^2 * ( 1-x^2/s^2) * (1-y^2/s^2)
    in polar coordinates with CIRCULAR compact support with radius = sigma.'''
    d2 = x * x + y * y
    s2 = sigma * sigma
    value = ( 1 - d2 / s2 )
    value *= value
    # This normalization factor is not correct!  It's close, but not quite right.
    #   I've done the math several times and still can't get a different, better answer.
    norm = 15.0 / (16.0 * s2 )
    return norm * value * ( d2 <= s2 )  # zero out the regions outside the circle

def BIWEIGHT_FUNC( x, sigma ):
    '''Defines the classic 1D biweight function f(x): 15/16s * ( 1-x^2/s^2).
    It is only defined on the interval [-sigma, sigma] but relies on the computation
    mechanism to know that.
    '''
    s2 = sigma * sigma
    x2 = x * x / s2
    t1 = ( 1 - x2 )
    t1 *= t1
    return ( 15.0 / ( sigma * 16.0 ) ) * t1

def BIWEIGHT_FUNC_INT( x0, x1, sigma ):
    '''Defines the integral of the biweight function over the interval [x0, x1].
    (It assumes that x0, x1 lies within the range [-sigma, sigma], otherwise the
    integral value will not have any resonable interpretation.'''
    def intFunc( x, sigma ):
        '''The indefinite integral of the biweight evaluated at x0.
        @param  x      A numpy array or float.  The point at which to evaluate the integral.
        @param  sig2    The smoothing parameter of the biweight.
        '''
        x2 = x * x
        x3 = x * x2
        x5 = x2 * x3
        s2 = sigma * sigma
        s4 = s2 * s2
        return ((15.0/16.0) / sigma ) * ( x - (2.0/3.0) * x3 / s2 + x5 / ( 5.0 * s4 ) )
    return intFunc( x1, sigma ) - intFunc( x0, sigma )
        

def BIWEIGHT_FUNC_2D( x, y, sigma ):
    '''Defines the classic biweight function f(x,y): 225/226s^2 * ( 1-x^2/s^2) * (1-y^2/s^2)
    in polar coordinates.'''
    s2 = sigma * sigma
    x2 = x * x / s2
    y2 = y * y / s2
    t1 = ( 1 - x2 )
    t1 *= t1
    t2 = ( 1 - y2 )
    t2 *= t2
    return ( 225.0 / ( s2 * 256.0 ) ) * t1 * t2 * ( x2 + y2 <= s2 )

class KernelBase( object ):
    '''The base class of a discrete convolution kernel.  It assumes uniform, square discretization of the domain'''
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
        return '%s: smooth: %f, cellSize: %f' % ( self.__class__.__name__, self._smoothParam, self._cellSize )
    
    def sampleKernel( self, smoothParam, cellSize ):
        self._smoothParam = smoothParam
        self._cellSize = cellSize
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
        return self._smoothParam

    @smoothParam.setter
    def smoothParam( self, value ):
        '''Setter for the smoothing parmaeter'''
        self.sampleKernel( value, self._cellSize )

    @property
    def cellSize( self ):
        '''Getter for the smoothing parameter'''
        return self._cellSize

    @cellSize.setter
    def cellSize( self, value ):
        '''Setter for the smoothing parmaeter'''
        self.sampleKernel( self._smoothParam, value )

    def convolve( self, signal, grid ):
        '''Convolves this kernel with the signal and places the result on the grid.normalize

        @param  signal      An instance of Signal class (See Signal.py )
        @param  grid        An instance of grid (see Grid.py).  Convolution is computed over
                            the domain represented by the grid.  The grid's values will be
                            changed as a result of this operation.
        '''
        if ( isinstance( signal, DiracSignal ) ):
            self.convolveDirac( signal, grid )
        elif ( isinstance( signal, FieldSignal ) ):
            self.convolveField( signal, grid )
        else:
            raise KernelSignalError, "Unrecognized signal type %s" % ( str( type( signal ) ) )

    def truncateKernel( self, grid, pos ):
        '''Given the position of the center of the kernel,
        defines extant of kernel and grid to use in computation.

        @param      grid    An instance of DataGrid.  
        @param      pos     A 2-tuple-like object of two floats.
                            The x- and y-position of the kernel (in grid coords.)
        @returns    Two 4-tuples (l, r, t, b), (kl, kr, kt, kb) of the grid and
                    kernel extents ( left, right, top, bottom) respectively.
        @raises     KernelDomainError if the kernel does not overlap with the grid.
        '''
        halfW = self.data.shape[0] / 2
        halfH = self.data.shape[1] / 2
        l = pos[0] - halfW
        r = pos[0] + halfW + 1
        b = pos[1] - halfH
        t = pos[1] + halfH + 1
        gW = int( grid.resolution[0] )
        gH = int( grid.resolution[1] )

        if ( l > gW or r < 0 or b > gH or t < 0 ):
            raise KernelDomainError
                  
        kl = 0
        kb = 0
        kr, kt = self.data.shape
        if ( l < 0 ):
            kl -= l
            l = 0
        if ( b < 0 ):
            kb -= b
            b = 0
        if ( r >= gW ):
            kr -= r - gW
            r = gW
        if ( t >= gH ):
            kt -= t - gH
            t = gH
        return (l, r, t, b), (kl, kr, kt, kb)
            
    def convolveField( self, signal, grid ):
        '''The convolution of the 2D kernel with the grid (slow, slow, slow)'''
        # TODO: This seems to mistakenly pick up signal on the boundaries.  FIND WHY!
        fieldData = signal.getFieldData()
        for y in xrange( grid.cells.shape[1] ):
            for x in xrange( grid.cells.shape[0] ):
                gridExtent, kernelExtent = self.truncateKernel( grid, ( x, y ) )
                l, r, t, b = gridExtent
                kl, kr, kt, kb = kernelExtent
                value = np.sum( fieldData[ l:r, b:t ] * self.data[ kl:kr, kb:kt ] )
                grid.cells[ x, y ] = value
                

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
        gW = int( grid.resolution[0] )
        gH = int( grid.resolution[1] )

        if ( l > gW or r < 0 or b > gH or t < 0 ):
            return
                  
        kl = 0
        kb = 0
        kr, kt = kernelData.shape
        if ( l < 0 ):
            kl -= l
            l = 0
        if ( b < 0 ):
            kb -= b
            b = 0
        if ( r >= gW ):
            kr -= r - gW
            r = gW
        if ( t >= gH ):
            kt -= t - gH
            t = gH
        
        if ( l < r and b < t and kl < kr and kb < kt ):
            # Convolution
            grid.cells[ l:r, b:t ] += kernelData[ kl:kr, kb:kt ]

        if ( self.reflectBoundaries ):
            reflectTop = kt < kernelData.shape[1] and center[1] < gH
            reflectBtm = kb > 0 and center[1] > 0
            if ( kl > 0 and center[0] > 0 ):  # reflect around left boundary
                # reflect center piece
                reflKernel = kernelData[ :kl, : ][::-1, : ]
                tempR = min( r, reflKernel.shape[0] )
                grid.cells[ l:tempR, b:t ] += reflKernel[ :tempR, kb:kt ]
                
                if ( reflectBtm ):  # also reflect around bottom
                    reflKernel = kernelData[ :kl, :kb ][::-1, ::-1]
                    tempT = min( t, reflKernel.shape[1] )
                    grid.cells[ l:tempR, b:tempT ] += reflKernel[ :tempR, :tempT ]

                if ( reflectTop ):  # also reflect around top
                    reflKernel = kernelData[ :kl, kt: ][::-1, ::-1]
                    tempB = max( b, t - reflKernel.shape[1] )
                    tempKB = max( 0, reflKernel.shape[1] - gH )
                    grid.cells[ l:tempR, tempB:t ] += reflKernel[ :tempR, tempKB:]

            if ( kr < kernelData.shape[0] and center[0] < gW ):  # reflect around right boundary
                # reflect center piece
                reflKernel = kernelData[ kr:, : ][::-1, : ]
                tempKL = max( 0, reflKernel.shape[0] - gW )
                tempL = max( l, r - reflKernel.shape[0] )
                grid.cells[ tempL:r, b:t ] += reflKernel[ tempKL:, kb:kt ]
                
                if ( reflectBtm ):  # also reflect around bottom
                    reflKernel = kernelData[ kr:, :kb ][::-1, ::-1]
                    tempT = min( t, reflKernel.shape[1] )
                    grid.cells[ tempL:r, b:tempT ] += reflKernel[ tempKL:, :tempT ]

                if ( reflectTop ):  # also reflect around top
                    reflKernel = kernelData[ kr:, kt: ][::-1, ::-1]
                    tempB = max( b, t - reflKernel.shape[1] )
                    tempKB = max( 0, reflKernel.shape[1] - gH )
                    grid.cells[ tempL:r, tempB:t ] += reflKernel[ tempKL:, tempKB:]

            if ( reflectBtm ):      # reflect around the bottom
                reflKernel = kernelData[ :, :kb ][:, ::-1]
                tempT = min( t, reflKernel.shape[1] )
                grid.cells[ l:r, b:tempT ] += reflKernel[ kl:kr, :tempT ]

            if ( reflectTop ):        # reflect around the top
                reflKernel = kernelData[ :, kt: ][:, ::-1 ]
                tempB = max( b, t - reflKernel.shape[1] )
                tempKB = max( 0, reflKernel.shape[1] - gH )
                grid.cells[ l:r, tempB:t ] += reflKernel[ kl:kr, tempKB: ]    

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

    def convolveField( self, signal, grid ):
        # TODO: THIS CAUSES BANDING!!!!  Don't let it.
        assert( signal.shape == grid.cells.shape )
        fieldW = signal.shape[0]
        fieldH = signal.shape[1]
        if ( self.reflectBoundaries ):
            expansion = self.data1D.size / 2
            fieldData = signal.getFieldData( expansion )
            temp = np.empty( (fieldData.shape[0], fieldH ), dtype=np.float32 )
            # vertictal convolution
            for x in xrange( fieldData.shape[0] ):
                result = np.convolve( self.data1D, fieldData[x,:], 'valid' )
                try:
                    temp[ x, : ] = result
                except:
                    print "Signal shape:", signal.shape
                    print "Convolution result shape:", result.shape
                    print "Kernel shape:", self.data1D.shape
                    print "Reflected Signal shape:", fieldData[r,:].shape
                    raise
            
            # horizontal convolution
            for y in xrange( temp.shape[1] ):
                result = np.convolve( self.data1D, temp[:,y], 'valid' )
                try:
                    grid.cells[ :, y ]  = result
                except:
                    print "Signal shape:", signal.shape
                    print "Convolution result shape:", result.shape
                    print "Kernel shape:", self.data1D.shape
                    print "Reflected Signal shape:", fieldData[r,:].shape
                    raise
        else:
            fieldData = signal.getFieldData()
            temp = np.empty_like( fieldData )
            # vertictal convolution
            for r in xrange( temp.shape[0] ):
                                                # select a VERTICAL column with a fixed x value.
                result = np.convolve( self.data1D, fieldData[r,:], 'same' )
                if ( fieldH < self.data1D.size ):
                    delta = ( self.data1D.size - fieldH ) / 2
                    temp[ r, : ] = result[ delta:delta + fieldH ]
                else:
                    temp[ r,:] = result
            # horizontal convolution
            for c in xrange( temp.shape[1] ):
                                            # select a HORIZONTAL column with a fixed x value.
                result = np.convolve( self.data1D, temp[:,c], 'same' )
                if ( fieldW < self.data1D.size ):
                    delta = ( self.data1D.size - fieldW ) / 2
                    grid.cells[ :, c ] = result[ delta:delta + fieldW ]
                else:
                    grid.cells[ :, c ] = result
        
    def computeSamples( self ):
        '''Based on the nature of the kernel, pre-compute the discrete kernel for given parameters.'''
        # do work
        width = self.getSupport()
        ratio = width / self._cellSize
        hCount = int( ratio )
        if ( ratio - hCount > KERNEL_EPS ):
            hCount += 1
        
        if ( hCount % 2 == 0 ):  # make sure cell has an odd-number of samples
            hCount += 1
        x = np.arange( -(hCount/2), hCount/2 + 1) * self._cellSize
        
        self.data1D = self.dFunc( x, self._smoothParam ) * self._cellSize
        # fix boundaries
        self.fix1DBoundaries()
        temp = np.reshape( self.data1D, (-1, 1 ) )
        self.data = temp * temp.T

    def fix1DBoundaries( self ):
        '''Examines the boundaries of the discretized kernel, and if it extends past the compact
            support of the continuous kernel, properly integrates the correct value.
            Default functionality is to do nothing.
            '''
        pass

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

    def convolveField( self, signal, grid ):
        raise KernelImplementationError, "This hasn't been implemented yet"

    def computeSamples( self ):
        '''Based on the nature of the kernel, pre-compute the discrete kernel for given parameters.'''
        # TODO: If the cells do not align perfectly with the support domain of the kernel, there will be
        #       error at the edges.
        #       The "correct" thing to do is examine the edges and integrate the function and place that
        #       value in the cell.  
        width = self.getSupport()
        ratio = width / self._cellSize
        hCount = int( ratio )
        if ( ratio - hCount > KERNEL_EPS ):
            hCount += 1
            
        if ( hCount % 2 == 0 ):  # make sure cell has an odd-number of samples
            hCount += 1
        o = np.arange( -(hCount/2), hCount/2 + 1) * self._cellSize
        X, Y = np.meshgrid( o, o )

        self.data = self.dFunc( X, Y, self._smoothParam ) * ( self._cellSize * self._cellSize )

##class ConstKernel:
##    pass
##
##class VariableKernel:
##    def getImpulseKernel( self, impulse ):
##        '''Returns the kernel appropriate for this impulse'''
##        return self.data
##    


##class SeparableConstKernel( SeparableKernel ):
##    pass
##
##class ConstGaussianKernel( SeparableKernel ):
##    pass


    
class UniformKernel( SeparableKernel ):
    '''A simple uniform kernel'''
    def __init__( self, smoothParam, cellSize, reflect=True ):
        SeparableKernel.__init__( self, smoothParam, cellSize, reflect, UNIFORM_FUNCTION )

    def getSupport( self ):
        '''The uniform kernel's support is equal to the smooth parameter'''
        return self._smoothParam

    def fix1DBoundaries( self ):
        '''Examines the boundaries of the discretized kernel, and if it extends past the compact
            support of the continuous kernel, properly integrates the correct value.'''
        support = self.getSupport()
        cellCount = self.data1D.size
        k = cellCount / 2       # cellCount = 2k + 1
        if ( cellCount * self._cellSize > support ):
            # handle boundaries
            # right edge of compact support
            rightSupport = support / 2.0
            # left boundary of right most cell
            cellBoundary = self._cellSize * ( k - 0.5 )
            # width of supported region in final cell
            assert( rightSupport > cellBoundary )
            w = rightSupport - cellBoundary
            # exploit the knowlege of the constant function
            self.data1D[ 0 ] = self.data1D[ -1 ] = w * self.dFunc( cellBoundary, self._smoothParam )

class BiweightKernel( SeparableKernel ):
    '''A 2D biweight kernel with circular support.  The smoothing parameter is the RADIUS of
    the circle of support.'''
    def __init__( self, smoothParam, cellSize, reflect=True ):
        SeparableKernel.__init__( self, smoothParam, cellSize, reflect, BIWEIGHT_FUNC )
        
    def getSupport( self ):
        '''The circle kernel's support is twice the smoothing parameter'''
        return 2 * self._smoothParam

    def fix1DBoundaries( self ):
        '''Examines the boundaries of the discretized kernel, and if it extends past the compact
            support of the continuous kernel, properly integrates the correct value.
            Default functionality is to do nothing.
            '''
        support = self.getSupport()
        cellCount = self.data1D.size
        k = cellCount / 2       # cellCount = 2k + 1
        if ( cellCount * self._cellSize > support ):
            # handle boundaries
            # right edge of compact support
            rightSupport = support / 2.0
            # left boundary of right most cell
            cellBoundary = self._cellSize * ( k - 0.5 )
            # width of supported region in final cell
            assert( rightSupport > cellBoundary )
            # integrate the biweight function from cellBoundary to rightSupport
            value = BIWEIGHT_FUNC_INT( cellBoundary, rightSupport, self._smoothParam )
            self.data1D[ 0 ] = self.data1D[ -1 ] = value
    
class GaussianKernel( SeparableKernel ):
    '''A simple gaussian kernel - it implies a compact support of 6*sigma'''
    def __init__( self, smoothParam, cellSize, reflect=True ):
        SeparableKernel.__init__( self, smoothParam, cellSize, reflect, GAUSSIAN_FUNCTION )

    def getSupport( self ):
        '''The uniform kernel's support is equal to the smooth parameter'''
        return 6 * self._smoothParam

class Plaue11Kernel( KernelBase ):
    '''This is the adaptive kernel mechamism proposed by Plaue et al. (2011).conjugate
    It changes the smoothing parameter based on nearest neighbor information per agent.'''
    # A coarse approximation of infinity
    INFTY = 10000.0

    # lower bound on the sigma value
    DIST_BOUND = 0.1
    
    def __init__( self, smoothParam, cellSize, reflect, obstacles=None  ):
        # TODO: Needs obstacles, needs the full set of data
        self.obstacles = obstacles
        
        KernelBase.__init__( self, smoothParam, cellSize, reflect, GAUSSIAN_FUNCTION )
        
    def getSupport( self ):
        '''The uniform kernel's support is equal to the smooth parameter'''
        return self._cellSize

    def convolveField( self, signal, grid ):
        '''Plaue11Kernel cannot be used with a Field signal'''
        raise KernelImplementationError, "Plaue11Kernel cannot convolve with a field"

    def convolveDirac( self, signal, grid ):
        '''Convolve the kernel against a dirac signal'''

        for i, pos in enumerate( signal.impulses ):
            k = self.getImpulseKernel( i, signal, grid )
            w, h = k.shape
            w /= 2
            h /= 2
            self.splatKernel( pos, w, h, k, grid )

    def computeSamples( self, minDist=1.0 ):
        '''Based on the nature of the kernel, pre-compute the discrete kernel for given parameters.'''
        # do work
        # In the variable kernel the standard deviation of the underlying gaussian is the
        #   product of the minimum distance and a smoothing parameter (\lambda in the paper)
        gaussSigma = self._smoothParam * minDist 
        width = 6 * gaussSigma
        ratio = width / self._cellSize
        hCount = int( ratio )
        if ( ratio - hCount > KERNEL_EPS ):
            hCount += 1
        if ( hCount % 2 == 0 ):  # make sure cell has an odd-number of samples
            hCount += 1
        x = np.arange( -(hCount/2), hCount/2 + 1) * self._cellSize
        
        data1D = self.dFunc( x, gaussSigma ) * self._cellSize
        temp = np.reshape( data1D, (-1, 1 ) )
        self.data = temp * temp.T
        
    def getImpulseKernel( self, idx, signal, grid ):
        '''Returns the kernel appropriate for this impulse.

        @param      idx     An int.  The index of the impulse in the signal for which
                            we are computing the kernel.
        @param      A DiracSignal instance.  The full set of impulses.
        @param      An instance of DataGrid.  The grid spans the computation domain.
        @returns    A kxk numpy array representing the discrete kernel.
                        k is odd.
        '''
        impulse = signal[ idx ]
        minDist = self.INFTY
        if ( self.obstacles ):
            distObst = self.obstacles.findClosestObject( Vector2(impulse[0], impulse[1]) )
            if ( distObst < minDist ):
                minDist = distObst
        #distance to closest neighbor
        distNei = self.distanceToNearestNeighbor( idx, impulse, signal )
        # minRadius is the smallest distance to either obstacle or neighbor
        if ( distNei < minDist ):
            minDist = distNei
        if ( minDist < self.DIST_BOUND ):
            minDist = self.DIST_BOUND
        self.computeSamples( minDist )
        return self.data
    
    def distanceToNearestNeighbor( self, idx, impulse, signal ):
        '''Find the minimum distance between the impulse with the given index/value and its
        neighboring impulses.

        @param  idx         The index of the source impules.
        @param  impules     The value of the idx impulse.
        @param  signal      An instance of a DiracSignal (including the source impulse idx)
        '''
        minDist = self.INFTY
        if ( len( signal ) == 1 ):
            # Distance to the closet boundary
            return minDist
        for j, nbr in enumerate( signal.impulses ):
            if ( idx == j ):
                continue
            # get position of the agent the world grid
            diff = nbr - impulse
            localMin = np.sum( diff * diff, axis=0 )
            if ( localMin < minDist ):
                minDist = localMin
        return np.sqrt( minDist )

class Kernel:
    """Distance function kernel"""
    # TODO : CHANGE THE DFUNC AND MULTIPLY WITH AREA FACTOR
    def __init__( self, smoothParam, dFunc, cSize):
        """Creates a kernel to add into the grid.normalize
        The kernel is a 2d grid (with odd # of cells in both directions.)
        The cell count is determined by the radius and cell size.x
        The cellsize is a tuple containing the width and height of a cell.
        (it need not be square.)  The values in each cell are determined
        by the distance of each cell from the center cell computed with
        dFunc.  Each cell is given a logical size of cSize"""
        if (dFunc == FUNCS_MAP['gaussian'] or dFunc == FUNCS_MAP['variable-gaussian']):
            hCount = int( 6 * smoothParam / cSize.x )
        elif (dFunc == FUNCS_MAP['linear'] or dFunc == FUNCS_MAP['biweight'] ):
            hCount = int( 2 * smoothParam / cSize.x )
        else:
            hCount = int( smoothParam / cSize.x )
        if ( hCount % 2 == 0 ):
            hCount += 1

        o = np.arange( -(hCount/2), hCount/2 + 1) * cSize.x
        X, Y = np.meshgrid( o, o )
        self.data = dFunc( X, Y, smoothParam )


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

        sigma = 1.0
        cellSize = 0.11
        k = UniformKernel( sigma, cellSize )
        print k
        print k.data1D, k.data1D.sum()
        print k.data, k.data.sum()


    test()
    
