# This file contain various different Kernels
# Uniform, Linear, Bi-weight, Gaussian (fixed and variable)

import numpy as np
from primitives import Vector2
import domains
import Signals

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

class KernelSizeError( KernelError ):
    '''Error indicating that the kernel is too large - support domain * cellSize is too large'''
    pass

KERNEL_EPS = 0.00001

IDENTITY_FUNCTION = lambda x, sigma: x

UNIFORM_FUNCTION = lambda x, sigma: np.zeros_like( x ) + (1.0 / sigma)

GAUSSIAN_FUNCTION = lambda x, sigma: np.exp( -( x * x ) / ( 2 * sigma * sigma ) ) / ( np.sqrt( 2.0 * np.pi ) * sigma )

def CIRCLE_FUNC_2D( x, y, sigma ):
    s2 = sigma * sigma
    return ( 1 / (np.pi * s2 ) ) * (( x * x + y * y) <= s2)

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

TRIANGLE_FUNC = lambda x, sigma: ( 1 - np.abs( x ) / sigma ) / sigma

class KernelBase( object ):
    '''The base class of a discrete convolution kernel.  It assumes uniform, square discretization of the domain'''
    # This is the class-wide function which defines the kernel.  Each instantiable sub-class must define a function
    #   The function may be 1D or 2D depending on whether it is separable or insperable
    FUNC = None

    # Maximum allowable kernel width - in cells
    # with a cell size of 1 cm, this allows a compact support of 50 m
    #   For pedestrian analysis, this seems a reasonable limit
    MAX_KERNEL_WIDTH = 5000     
    
    def __init__( self, smoothParam, cellSize, reflect=True ):
        '''Initializes the kernel with the smoothing parameter and boundary behavior.

        @param  smoothParam     A float.  The smoothing parameter.  The interpretation varies
                                based on the kernel type.
        @param  cellSize        A float. The size of the uniform sampling of the kernel.
        @param  reflect         A boolean.  Determines if the kernel reflects at boundaries.
                                Only supports simple, convex boundaries.
        '''
        self.sampleKernel( smoothParam, cellSize )
        self.reflectBoundaries = reflect

    def __str__( self ):
        s = '%s: smooth: %f, cellSize: %f' % ( self.__class__.__name__, self._smoothParam, self._cellSize )
        if ( self.reflectBoundaries ):
            s += " (reflective)"
        else:
            s += " (NO reflection)"
        return s

    @classmethod
    def smoothCharacteristic( self ):
        '''The smoothing parameter charcteristic for this kernel.  It is
        used to compute equivalent smoothing parameters across kernels.

        @returns        A float.  The smoothing characteristc of the kernel.
        '''
        raise KernelError, "Each implementable kernel must define its smooth characteristic"
        
    def needsInitOutput( self, signal ):
        '''This function reports if the output grid needs to be initialized.

        Depending on the nature of the signal, the output grid may or may not have to be
        convolved.  For example, convolving with a dirac signal basically splats copies
        of the kernel onto the grid domain.  So, it must start empty.  However, in convolving
        with a field signal, the whole domain is replaced wholesale, so no initialization
        is required.

        @param      signal      An instance of a Signal.  The signal to be convolved
                                against.
        @retuns    A 2-tuple ( boolean, value ).  The boolean indicates if the grid needs to
                    be initialized (True) or can be left empty (False), and, in the case
                    of initialization, the value is the initialiation value.
        '''
        if ( isinstance( signal, Signals.DiracSignal ) ):
            return ( True, 0.0 )
        elif ( isinstance( signal, Signals.FieldSignal ) ):
            return ( False, 0.0 )
        else:
            raise ValueError, "Invalid signal type"
    
    def sampleKernel( self, smoothParam, cellSize ):
        self._smoothParam = smoothParam
        self._cellSize = cellSize
        return self.computeSamples()

    def computeSamples( self ):
        '''Based on the nature of the kernel, pre-compute the discrete kernel for
        kernel's parameters.
        @returns  A n-tuple (x0, x1, ..., xn-1, y) where x_i spans the dimension of the
                  domain, and y is the kernel value at (x0, ..., xn-1).'''
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
        '''Convolves this kernel with the signal and places the result on the grid.

        @param  signal      An instance of Signal class (See Signal.py )
        @param  grid        An instance of grid (see Grid.py).  Convolution is computed over
                            the domain represented by the grid.  The grid's values will be
                            changed as a result of this operation.
        '''
        if ( isinstance( signal, Signals.DiracSignal ) ):
            self.convolveDirac( signal, grid )
        elif ( isinstance( signal, Signals.FieldSignal ) ):
            self.convolveField( signal, grid )
        else:
            raise KernelSignalError, "Unrecognized signal type %s" % ( str( type( signal ) ) )

    def truncateKernel( self, grid, pos, kSize=None ):
        '''Given the position of the center of the kernel,
        defines extant of kernel and grid to use in computation.

        @param      grid    An instance of DataGrid.  
        @param      pos     A 2-tuple-like object of two ints.
                            The x- and y-position of the kernel (in grid coords.)
        @returns    kSize   A 2-tuple-like object of ints.  Represents the width
                            and height of the kernel.  If no size is provided, it
                            uses the internal size value
        @returns    Two 4-tuples (l, r, t, b), (kl, kr, kt, kb) of the grid and
                    kernel extents ( left, right, top, bottom) respectively.
        @raises     KernelDomainError if the kernel does not overlap with the grid.
        '''
        if ( kSize is None ):
            halfW = self.data.shape[0] / 2
            halfH = self.data.shape[1] / 2
        else:
            halfW = kSize[0] / 2
            halfH = kSize[1] / 2
        return self.logicalTruncate( grid, pos, halfW, halfH )
        

    def logicalTruncate( self, grid, pos, halfW, halfH ):
        '''Given the position of the center of the kernel, and the logical half
        size of the kernel, defines extant of kernel and grid to use in computation.

        @param      grid    An instance of DataGrid.  
        @param      pos     A 2-tuple-like object of two ints.
                            The x- and y-position of the kernel (in grid coords.)
        @param      halfW   An int.  The number of cells to the left and right of
                            the center cell that the kernel reaches.
        @param      halfH   An int.  The number of cells above and below
                            the center cell that the kernel reaches.
        @returns    Two 4-tuples (l, r, t, b), (kl, kr, kt, kb) of the grid and
                    kernel extents ( left, right, top, bottom) respectively.
        @raises     KernelDomainError if the kernel does not overlap with the grid.
        '''
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
    
    def convolveDirac( self, signal, grid ):
        '''Convolve the kernel against a dirac signal.  It is "fast" because it approximates
        the agent's position by the nearest grid cell center.

        @param      signal      An instance of DiracSignal.  The kernel will be copied
                                centered at each position in the signal.
        @param      grid        The grid onto which the kernel is splatted.  It is assumed
                                that the grid has been initialized to zero.
        '''
        w, h = self.data.shape
        w /= 2
        h /= 2
        expandDist = Vector2( grid.cellSize[0] * w, grid.cellSize[1] * h )
        minPt = grid.minCorner - expandDist
        size = grid.size + ( 2 * expandDist )
        domain = domains.RectDomain( minPt, size )

        impulses = signal.getDomainSignal( grid, domain, self.reflectBoundaries )
        for pos in impulses:
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

class SeparableKernel( KernelBase ):
    '''The base class of a separable convolution kernel'''
    
    def __init__( self, smoothParam, cellSize, reflect=True ):
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
        KernelBase.__init__( self, smoothParam, cellSize, reflect )

    def convolveField( self, signal, grid ):
        sigData = signal.getDomainSignal( grid, self.data1D.size / 2, self.reflectBoundaries )
        
        fieldW = sigData.shape[0]
        fieldH = sigData.shape[1]
        temp = np.empty( ( sigData.shape[0], grid.cells.shape[1] ), dtype=np.float32 )
        # vertical convolution
        for x in xrange( sigData.shape[0] ):
            result = np.convolve( self.data1D, sigData[x,:], 'valid' )
            temp[ x, : ] = result
            
        # horizontal convolution
        for y in xrange( temp.shape[1] ):
            result = np.convolve( self.data1D, temp[:,y], 'valid' )
            grid.cells[ :, y ]  = result
        
    def computeSamples( self ):
        '''Based on the nature of the kernel, pre-compute the discrete kernel for
        kernel's parameters. For the separable kernel the sample domain is 1 dimensional.
        @returns  A n-tuple (x0, x1, ..., xn-1, y) where x_i spans the dimension of the
                  domain, and y is the kernel value at (x0, ..., xn-1).'''
        # do work
        width = self.getSupport()
        ratio = width / self._cellSize
        hCount = int( ratio )
        if ( ratio - hCount > KERNEL_EPS ):
            hCount += 1
        
        if ( hCount % 2 == 0 ):  # make sure cell has an odd-number of samples
            hCount += 1
        if ( hCount >= self.MAX_KERNEL_WIDTH ):
            raise KernelSizeError
        
        x = np.arange( -(hCount/2), hCount/2 + 1, dtype=np.float32) * self._cellSize
        
        self.data1D = self.FUNC( x, self._smoothParam ) #* self._cellSize
        temp = np.reshape( self.data1D, (-1, 1 ) )
        self.data = np.empty( ( x.size, x.size ), dtype=np.float32 )
        np.dot( temp, temp.T, out=self.data )
        self.data1D *= self._cellSize
        return x, self.data1D

class InseparableKernel( KernelBase ):
    '''The base class of an inseparable convolution kernel'''
    def __init__( self, smoothParam, cellSize, reflect=True ):
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
        KernelBase.__init__( self, smoothParam, cellSize, reflect )

    def computeSamples( self ):
        '''Based on the nature of the kernel, pre-compute the discrete kernel for
        kernel's parameters. For an inseparable kernel, the sample domain is two dimensional.
        @returns  A n-tuple (x0, x1, ..., xn-1, y) where x_i spans the dimension of the
                  domain, and y is the kernel value at (x0, ..., xn-1).'''
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

        if ( hCount >= self.MAX_KERNEL_WIDTH ):
            raise KernelSizeError
        
        o = np.arange( -(hCount/2), hCount/2 + 1) * self._cellSize
        X, Y = np.meshgrid( o, o )

        self.data = self.FUNC( X, Y, self._smoothParam ) #* ( self._cellSize * self._cellSize )
        self.normData = self.data * ( self._cellSize * self._cellSize )
        return X, Y, self.normData

    def convolveField( self, signal, grid ):
        '''The convolution of the 2D kernel with the grid (slow, slow, slow)'''
        kSize = self.normData.shape[0]  #assuming square kernel
        halfK = kSize / 2
        dSignal = signal.getDomainSignal( grid, halfK, self.reflectBoundaries )

        for y in xrange( grid.cells.shape[1] ):
            for x in xrange( grid.cells.shape[0] ):
                value = np.sum( dSignal[ x:x+kSize, y:y+kSize ] * self.normData )
                grid.cells[ x, y ] = value

class UniformCircleKernel( InseparableKernel ):
    '''A uniform kernel with circular support.  The smoothing parameter is the RADIUS of
    the circle.'''
    FUNC = staticmethod( CIRCLE_FUNC_2D )
    
    def __init__( self, smoothParam, cellSize, reflect=True ):
        InseparableKernel.__init__( self, smoothParam, cellSize, reflect )

    def getSupport( self ):
        '''The circle kernel's support is twice the smoothing parameter'''
        return 2 * self._smoothParam

    @classmethod
    def smoothCharacteristic( self ):
        '''The smoothing parameter charcteristic for this kernel.  It is
        used to compute equivalent smoothing parameters across kernels.

        @returns        A float.  The smoothing characteristc of the kernel.
        '''
        # TODO: Determine the TRUE answer for this
        return 1 / np.sqrt( 3.0 )
        
    
class UniformKernel( SeparableKernel ):
    '''A simple uniform kernel'''
    FUNC = staticmethod( UNIFORM_FUNCTION )
    
    def __init__( self, smoothParam, cellSize, reflect=True ):
        SeparableKernel.__init__( self, smoothParam, cellSize, reflect )

    @classmethod
    def smoothCharacteristic( self ):
        '''The smoothing parameter charcteristic for this kernel.  It is
        used to compute equivalent smoothing parameters across kernels.

        @returns        A float.  The smoothing characteristc of the kernel.
        '''
        return 1 / np.sqrt( 3.0 )
        
    def convolveDirac( self, signal, grid ):
        '''Convolve the kernel against a dirac signal.  It is "fast" because it approximates
        the agent's position by the nearest grid cell center.

        @param      signal      An instance of DiracSignal.  The kernel will be copied
                                centered at each position in the signal.
        @param      grid        The grid onto which the kernel is splatted.  It is assumed
                                that the grid has been initialized to zero.
        '''
        w = self.data1D.size
        w /= 2
        expandDist = Vector2( grid.cellSize[0] * w, grid.cellSize[1] * w )
        minPt = grid.minCorner - expandDist
        size = grid.size + ( 2 * expandDist )
        domain = domains.RectDomain( minPt, size )

        impulses = signal.getDomainSignal( grid, domain, self.reflectBoundaries )
        kernelValue = 1.0 / ( self._smoothParam * self._smoothParam )
        for pos in impulses:
            self.splatKernel( pos, w, grid, kernelValue )

    def splatKernel( self, pos, halfW, grid, value ):
        '''Used by the dirac convolution.  Splats the kernel at the given position.

        Splats the kernel into the given grid.        

        @param      pos             A numpy array of shape (2,1).  The position of the kernel
        @param      halfW           An int.  The width of the kernel / 2.  It should be true that halfW = kernelData.shape[0] / 2 
        @param      kernelData      A kxk numpy array of the kernel data.max
        @param      value           A float.  The value of the kernel (in all locations)
        '''
        center = grid.getCenter( Vector2( pos[0], pos[1] ) )
        gW = int( grid.resolution[0] )
        gH = int( grid.resolution[1] )

        l = max( 0, center[0] - halfW )
        r = min( gW, center[0] + halfW + 1 )
        b = max( 0, center[1] - halfW )
        t = min( gH, center[1] + halfW + 1 )
        
        if ( l >= gW or r < 0 or b >= gH or t < 0 ):
            return
        
        if ( l < r and b < t ):
            # Convolution
            grid.cells[ l:r, b:t ] += value            

    def getSupport( self ):
        '''The uniform kernel's support is equal to the smooth parameter'''
        return self._smoothParam


class BiweightKernel( SeparableKernel ):
    '''A 2D biweight kernel with square support.  The smoothing parameter is the HALF width of
    the square of support.'''
    FUNC = staticmethod( BIWEIGHT_FUNC )
    
    def __init__( self, smoothParam, cellSize, reflect=True ):
        SeparableKernel.__init__( self, smoothParam, cellSize, reflect )
        
    @classmethod
    def smoothCharacteristic( self ):
        '''The smoothing parameter charcteristic for this kernel.  It is
        used to compute equivalent smoothing parameters across kernels.

        @returns        A float.  The smoothing characteristc of the kernel.
        '''
        return 1 / np.sqrt( 7.0 )
        
    def getSupport( self ):
        '''The circle kernel's support is twice the smoothing parameter'''
        return 2 * self._smoothParam

class TriangleKernel( SeparableKernel ):
    '''A 2D triangle kernel with square support.  The smoothing parameter is the HALF width of
    the square of support.'''
    FUNC = staticmethod( TRIANGLE_FUNC )
    
    def __init__( self, smoothParam, cellSize, reflect=True ):
        SeparableKernel.__init__( self, smoothParam, cellSize, reflect )
        
    @classmethod
    def smoothCharacteristic( self ):
        '''The smoothing parameter charcteristic for this kernel.  It is
        used to compute equivalent smoothing parameters across kernels.

        @returns        A float.  The smoothing characteristc of the kernel.
        '''
        return 1 / np.sqrt( 6.0 )
        
    def getSupport( self ):
        '''The circle kernel's support is twice the smoothing parameter'''
        return 2 * self._smoothParam

class GaussianKernel( SeparableKernel ):
    '''A simple gaussian kernel - it implies a compact support of 6*sigma'''
    FUNC = staticmethod( GAUSSIAN_FUNCTION )
    
    def __init__( self, smoothParam, cellSize, reflect=True ):
        SeparableKernel.__init__( self, smoothParam, cellSize, reflect )

    def getSupport( self ):
        '''The gaussian kernel's support is equal to six times the smooth parameter'''
        return 6 * self._smoothParam

    @classmethod
    def smoothCharacteristic( self ):
        '''The smoothing parameter charcteristic for this kernel.  It is
        used to compute equivalent smoothing parameters across kernels.

        @returns        A float.  The smoothing characteristc of the kernel.
        '''
        return 1.0

class Plaue11Kernel( KernelBase ):
    '''This is the adaptive kernel mechamism proposed by Plaue et al. (2011).conjugate
    It changes the smoothing parameter based on nearest neighbor information per agent.'''
    # A coarse approximation of infinity
    INFTY = 10000.0

    # Bounds on the distances used in the computation of the kernel
    #   The lower bound prevents impossibly small but high-valued kernels
    #   The upper bound prevents incredibly diffuse and huge kernels
    MIN_PLAUE_DIST = 0.1    # meters
    MAX_PLAUE_DIST = 20.0   # meters
    
    FUNC = staticmethod( GAUSSIAN_FUNCTION )
    
    def __init__( self, smoothParam, cellSize, reflect, obstacles=None ):
        # TODO: Needs obstacles, needs the full set of data
        self.obstacles = obstacles
        
        KernelBase.__init__( self, smoothParam, cellSize, reflect )

    @classmethod
    def smoothCharacteristic( self ):
        '''The smoothing parameter charcteristic for this kernel.  It is
        used to compute equivalent smoothing parameters across kernels.

        @returns        A float.  The smoothing characteristc of the kernel.
        '''
        return 1.0
        
    def getSupport( self ):
        '''The uniform kernel's support is equal to the smooth parameter'''
        return self._cellSize

    def convolveField( self, signal, grid ):
        '''Plaue11Kernel cannot be used with a Field signal'''
        raise KernelImplementationError, "Plaue11Kernel cannot convolve with a field"

    def convolveDirac( self, signal, grid ):
        '''Convolve this kernel with the dirac signal provided, placing the result on the provided grid.
        
        @param  signal      An instance of Signal class (See Signal.py )
        @param  grid        An instance of grid (see Grid.py).  Convolution is computed over
                            the domain represented by the grid.  The grid's values will be
                            changed as a result of this operation.
        '''
        for i, pos in enumerate( signal.impulses ):
            k, sigma = self.getImpulseKernel( i, signal, grid )
            halfK = k / 2
            try:
                self.splatTruncatedKernel( pos, grid, halfK, sigma )
            except KernelDomainError:
                pass
            if ( self.reflectBoundaries ):
                
                # compute domain in which the reflection matters
                w = ( halfK + 0.5 ) * self._cellSize
                corner = Vector2( grid.minCorner[0] - w, grid.minCorner[1] - w )
                size = Vector2( grid.size[0] + 2 * w, grid.size[1] + 2 * w )
                tgtDomain = domains.RectDomain( corner, size )
                
                # compute reflection
                reflection = signal.reflectPoint( pos ) 
                for p in reflection:
                    if ( tgtDomain.pointInside( p ) ):
                        self.splatTruncatedKernel( p, grid, halfK, sigma )


    def splatTruncatedKernel( self, pos, grid, halfK, smoothParm ):
        '''Splats the kernel onto the domain -- computing only that portion of it
        required to fit onto the domain.

        @param      pos         An 2-tuple-like object of floats.  The x,y position
                                of the signal in world space.
        @param      grid        An instance of DataGrid.  The kernel will be added 
                                into this kernel.
        @param      halfK       An int.  The kernel half size (where the kernel
                                is 2k + 1 cells wide.
        @param      smoothParam     A float.  The smoothing parameter used in the
                                    kernel function.
        '''
        center = grid.getCenter( Vector2( pos[0], pos[1] ) )
        l = center[0] - halfK
        r = center[0] + halfK + 1
        b = center[1] - halfK
        t = center[1] + halfK + 1
        gW = int( grid.resolution[0] )
        gH = int( grid.resolution[1] )

        if ( l > gW or r < 0 or b > gH or t < 0 ):
            raise KernelDomainError
                  
        kl = 0
        kb = 0
        kr = kt = 2 * halfK + 1
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

        # compute the minimum 1D kernel section
        rangeMin = min( kl, kb )
        rangeMax = max( kr, kt )

        x = np.arange( rangeMin - halfK, rangeMax - halfK, dtype=np.float32 ) * self._cellSize
        data1D = self.FUNC( x, smoothParm )
        X = data1D[ kl-rangeMin:kr-rangeMin ]
        X.shape = (-1, 1)
        Y = data1D[ kb-rangeMin:kt-rangeMin ]
        Y.shape = (1, -1 )
        kernel = np.dot( X, Y )
        grid.cells[ l:r, b:t ] += kernel
        
    def computeSamples( self ):
        '''Based on the nature of the kernel, pre-compute the discrete kernel for
        kernel's parameters.
        @returns  A n-tuple (x0, x1, ..., xn-1, y) where x_i spans the dimension of the
                  domain, and y is the kernel value at (x0, ..., xn-1).'''
        pass
        
    def getImpulseKernel( self, idx, signal, grid ):
        '''Returns the kernel size appropriate for this signal - size is in cells.

        @param      idx         An int.  The index of the impulse in the signal for which
                                we are computing the kernel.
        @param      signal      A DiracSignal instance.  The full set of impulses.
        @param      grid        An instance of DataGrid.  The grid spans the computation domain.
        @returns    A 2-tuple (int, float)  The int is the width of the kernel (in cells);
                    k is odd.  The float is the smoothing parameter used in the function.
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
        minDist = min( distNei, minDist )
        minDist = max( minDist, self.MIN_PLAUE_DIST )
        minDist = min( minDist, self.MAX_PLAUE_DIST )
        
        gaussSigma = self._smoothParam * minDist 
        width = 6 * gaussSigma
        ratio = width / self._cellSize
        hCount = int( ratio )
        if ( ratio - hCount > KERNEL_EPS ):
            hCount += 1
        if ( hCount % 2 == 0 ):  # make sure cell has an odd-number of samples
            hCount += 1
            
##        if ( hCount >= self.MAX_KERNEL_WIDTH ):
##            raise KernelSizeError
        
        return hCount, gaussSigma
    
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

if __name__ == '__main__':
    def test():

        sigma = 1.0
        cellSize = 0.11
        k = UniformKernel( sigma, cellSize )
        print k
        print k.data1D, k.data1D.sum()
        print k.data, k.data.sum()


    test()
    
