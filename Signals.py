# module for handling signals for convolution

import numpy as np
import Grid
from GridFileSequence import GridFileSequenceReader
import domains

class SignalError( Exception ):
    '''Basic exception for signals'''
    pass

class SignalDataError( SignalError ):
    '''Exception indicating a problem with the signal data'''
    pass

class SignalImplementationError( SignalError ):
    '''Exception indicating that a function has not been implemented'''
    pass


class Signal:
    '''Base signal class'''
    def getDomain( self ):
        '''Reports the domain of the signal.

        @returns    Two 2-tuple-like values reporting the minimum value and the size of the domain.
                        (minX, minY) and (width, height).
        '''
        raise SignalImplementationError

    def __str__( self ):
        return self.__class__.__name__

    def reflectPoint ( self, point ):
        '''Given a point INSIDE the signal's domain, returns four points.  The reflection of the
            point over all domain boundaries.

            It is the caller's responsibility to only call this function on a point that is KNOWN
            to be inside the domain.  Otherwise, the reflection values will not be meaningful.

        @param      point       A 2-tuple like class with floats.  The x-and y-values of the point
                                in world space.
        @returns    A 4 x 2 numpy array.  Each row is a reflected point: left, right, bottom, top.
        '''
        raise SignalImplementationError

    def setData( self, data ):
        '''Sets the signal's data.'''
        raise SignalImplementationError

    def copy( self ):
        '''Creates a full copy of this signal'''
        raise SignalImplementationError

    def copyEmpty( self ):
        '''Creates an empty copy of this signal -- keeps the domain, but no
        data.'''
        raise SignalImplementationError

class DiracSignal( Signal ):
    '''A signal consisting of a sum of translated dirac functions'''
    def __init__( self, domain, data=None ):
        '''Constructor for the signal.

        @param  domain      An instance of RectDomain.  Defines the domain of the signal.
        @param  data        An Nx2 numpy array of flaots. The signal data.
        '''
        if ( not isinstance( domain, domains.RectDomain ) ):
            raise TypeError, "Dirac signals should only be initialized with RectDomain instances, given %s" % ( domain.__class__ )
        self.domain = domain
        self._data = data

    def __str__( self ):
        return '%s - %s' % ( self.__class__.__name__, self.domain )

    def reflectPoint ( self, point ):
        '''Given a point INSIDE the signal's domain, returns four points.  The reflection of the
            point over all domain boundaries.

            It is the caller's responsibility to only call this function on a point that is KNOWN
            to be inside the domain.  Otherwise, the reflection values will not be meaningful.

        @param      point       A 2-tuple like class with floats.  The x-and y-values of the point
                                in world space.
        @returns    A 4 x 2 numpy array.  Each row is a reflected point: left, right, bottom, top.
        '''
        return self.domain.reflectPoint( point )

    def copy( self ):
        '''Creates a full copy of this signal'''
        if ( self._data ):
            return self.__class__( self.domain, self._data.copy() )
        else:
            return self.__class__( self.domain, self._data )

    def copyEmpty( self ):
        '''Creates an empty copy of this signal -- keeps the domain, but no
        data.'''
        return self.__class__( self.domain )

    def getDomainSignal( self, convolveDomain, signalDomain, doReflection ):
        '''Returns signal to support the domain covered by the given grid.

        The dirac signal does not make any assumptions as to the tesselation of
        the domain.  The signal uses values in continuous space and, as such, is
        independent of tesselation.

        If the convolution domain extends beyond signal domain,
        and doReflection is equal to true, then any points who lie in the domain and
        its reflections which lie in the domain are included in the signal.
        Points which lie outside the domain, and their reflections, are not included.

        @param      convolveDomain  An instance of AbstractGrid, which corresponds to
                                    the convolution domain.  It should lie wholly within the
                                    signal domain.
        @param      signalDomain    An instance of AbstractGrid, which corresponds to
                                    the domain in which signal should be populated.
        @param      doReflection    A boolean.  Determines if signals are reflected over
                                    signal boundaries.  True will cause reflection, False
                                    means the result only includes the original signal.
        @returns    A numpy array of agents who all lie within the domain implied
                    by the expanded grid.
        @raises     AttributeError if the data for the signal has not been set.'''
        baseIntersection = convolveDomain.intersection( self.domain )
        if ( baseIntersection is None ):
            raise SignalDataError, "Trying to compute density in a region without signal"
        if ( not baseIntersection == convolveDomain ):
            raise SignalDataError, "The entire convolution domain must lie within the signal domain"
        
        count = 0
        if ( not doReflection ):
            point = np.empty_like( self._data )
            for row in self._data :
                if ( signalDomain.pointInside( row ) ):
                    point[ count, : ] = row
                    count += 1
        else:
            point = np.empty( ( self._data.shape[0] * 5, 2 ), dtype=np.float32 )
            for row in self._data:
                if ( signalDomain.pointInside( row ) ):   # the point is inside the signalDomain
                    point[ count, : ] = row
                    count += 1

                    reflection = self.domain.reflectPoint( row )
                    for r in reflection:
                        if ( signalDomain.pointInside( r ) ):
                            point[ count, : ] = r
                            count += 1
        return point[:count, : ]
    
    def getDomain( self ):
        '''Reports the domain of the signal.

        @returns    Two 2-tuple-like values reporting the minimum value and the size of the domain.
                        (minX, minY) and (width, height).
        '''
        return self.domain.minCorner, self.domain.size

    class ImpulseIterator:
        '''An iterator for the dirac impulses'''
        def __init__( self, diracSignal ):
            '''Constructor - initializes the iterator with a dirac signal.

            @param      diracSignal     A DiracSignal instance.
            '''
            self.signal = diracSignal
            self.nextID = 0

        def __iter__( self ):
            return self

        def next( self ):
            '''Returns the next 2d position'''
            if ( self.nextID >= self.signal._data.shape[0] ):
                raise StopIteration
            impulse = self.signal._data[ self.nextID, :2 ]
            self.nextID += 1
            return impulse

    @property
    def impulses( self ):
        if ( self._data is None ):
            raise StopIteration
        return DiracSignal.ImpulseIterator( self )

    def __getitem__( self, i ):
        '''Return the ith impulse in the data.

        @param      i       The index of the desired impulse.
        @returns    A numpy array with shape (2,).  The ith impulse.
        @raises     IndexError if the index is invalid.
        @raises     AttributeError if the data for the signal has not been set.
        '''
        return self._data[ i ]

    def __len__( self ):
        '''Returns the number of impulses in the signal.

        @returns    An int.  The count of impulses.
        @raises     AttributeError if the data for the signal has not been set.
        '''
        return self._data.shape[0]
    
    def setData( self, data ):
        '''Sets the signal's data.

        @param  data        An Nx2 numpy array of floats.
        '''
        self._data = data

class PedestrianSignal( DiracSignal ):
    '''A dirac signal, where the pedestrian positions are the impulses'''
    def __init__( self, domain, frameSet=None ):
        '''Constructor.

        @param      domain      An instance of RectDomain.
                                Defines the domain of the signal.
        @param      frameSet    A pedestrian data frame set (such as
                                scbData or SeyfriedTrajectoryReader.)
        @raises     StopIteration if the frameSet is out of frames.
        '''
        if ( not frameSet is None ):
            frameData, self.index = frameSet.next()
            DiracSignal.__init__( self, domain, frameData[:, :2] )
        else:
            DiracSignal.__init__( self, domain, None )

    def setData( self, data ):
        '''Sets the signal's data.

        @param      frameSet    A pedestrian data frame set (such as
                                scbData or SeyfriedTrajectoryReader.)
        @raises     StopIteration if the frameSet is out of frames.
        '''
        frameData, self.index = data.next()
        DiracSignal.setData( self, frameData[:, :2] )
        
class FieldSignal( Signal ):
    '''A discrete approximation of a continuous signal defined over a
        rectangular domain'''
    def __init__( self, fieldData=None ):
        '''Constructor based on the provided field data.shape

        @param  fieldData       An instance of the DataGrid.  Containing the signal
                                located in space with a particular tesselation.  The
                                grid is used as given -- it is not copied.
        '''
        self.data = fieldData

    def __str__( self ):
        if ( self.data ):
            return '%s - %s' % ( self.__class__.__name__, self.data )
        else:
            return '%s - Empty' % ( self.__class__.__name__ )
        
    def reflectPoint ( self, point ):
        '''Given a point INSIDE the signal's domain, returns four points.  The reflection of the
            point over all domain boundaries.

            It is the caller's responsibility to only call this function on a point that is KNOWN
            to be inside the domain.  Otherwise, the reflection values will not be meaningful.

        @param      point       A 2-tuple like class with floats.  The x-and y-values of the point
                                in world space.
        @returns    A 4 x 2 numpy array.  Each row is a reflected point: left, right, bottom, top.
        '''
        return self.data.reflectPoint( point )

    def copy( self ):
        '''Creates a full copy of this signal'''
        return self.__class__( self.data.copy() )

    def copyEmpty( self ):
        '''Creates an empty copy of this signal -- keeps the domain, but no
        data.'''
        return self.__class__()

    def getDomain( self ):
        '''Reports the domain of the signal.

        @returns    Two 2-tuple-like values reporting the minimum value and the size of the domain.
                        (minX, minY) and (width, height).
        @raises     AttributeError if the data for the signal has not been set.
        '''
        return self.data.minCorner, self.data.size
    
    @property
    def shape( self ):
        '''Reports the resolution of the field signal.

        @returns    A 2-tuple of ints.  The number of cells in the data in the x-
                    and y-directions.
        @raises     AttributeError if the data for the signal has not been set.
        '''
        return self.data.cells.shape

    def getDomainSignal( self, convolveDomain, k, doReflection ):
        '''Returns signal to support the domain covered by the given grid.
        
        It is assumed that data in the signal has the same \emph{resolution} as
        the grid, but may span a different region.  If the convolution domain is
        completely enclosed in the signal, then simply a sub-portion of the signal
        is returned.  If the domain extends beyond that of the signal, then the
        signal is reflected over those boundaries.  If the reflection still does
        not fill the region, then zeros are used to fill the rest of the domain.

        @param      convolveDomain      An instance of RectDomain, which corresponds to
                                        the convolution domain.  It is an M x N grid.
        @param      k                   The number of cells larger than the grid data is
                                        needed (related to convolution kernel size).
        @param      doReflection        A boolean reporting whether or not to reflect around
                                        the signal domain.
        @returns    An M+k x N+k numpy array.  Representing the signal in the domain.
        @raises     AttributeError if the data for the signal has not been set.
        '''
        baseIntersection = convolveDomain.intersection( self.data )
        if ( baseIntersection == None ):
            raise SignalDataError, "Trying to compute density in a region without signal"
        minPt, maxPt = baseIntersection
        if ( minPt[0] != 0 or minPt[1] != 0 or maxPt[0] != convolveDomain.resolution[0] or maxPt[1] != convolveDomain.resolution[1] ):
            raise SignalDataError, "The entire convolution domain must lie within the signal domain"
        
        expand = convolveDomain.cellSize * k
        supportCorner = convolveDomain.minCorner - expand
        supportSize = convolveDomain.size + ( 2 * expand )
        supportResolution = ( convolveDomain.resolution[0] + 2 * k, convolveDomain.resolution[1] + 2 * k )
        supportDomain = Grid.AbstractGrid( supportCorner, supportSize, supportResolution )
        result = np.zeros( supportDomain.resolution, dtype=convolveDomain.cells.dtype )

        # what section of signal domain overlaps support domain
        intersection = self.data.intersection( supportDomain )
        if ( intersection != None ):
            # the field only gets filled in if there is no intersection
            sigMin, sigMax = intersection
            xform = Grid.GridTransform( self.data, supportDomain )
            supMin = xform( sigMin )
            supMax = xform( sigMax )
            result[ supMin[0]:supMax[0], supMin[1]:supMax[1] ] = self.data.cells[ sigMin[0]:sigMax[0], sigMin[1]:sigMax[1] ]
            
            # if do reflection
            if ( doReflection ):
                # Reflection only necessary if the support domain isn't full of signal
                if ( supMin[0] > 0 or supMin[1] > 0 or
                     supMax[0] < supportResolution[0] or supMax[1] < supportResolution[1] ):
                    sigWidth  = self.data.resolution[ 0 ]
                    sigHeight = self.data.resolution[ 1 ]
                    supWidth  = supportDomain.resolution[ 0 ]
                    supHeight = supportDomain.resolution[ 1 ]
                    
                    if ( supMin[0] > 0 ):
                        # reflect left
                        rWidth = min( supMin[0], sigWidth )
                        reflKernel = self.data.cells[ :rWidth, sigMin[1]:sigMax[1] ][::-1, : ]
                        L = supMin[0]-rWidth
                        R = supMin[0]
                        result[ L:R, supMin[1]:supMax[1] ] = reflKernel

                        if ( supMin[1] > 0 ):
                            #reflect bottom-left
                            rHeight = min( supMin[1], sigHeight - sigMin[1] )
                            reflKernel = self.data.cells[ :rWidth, :rHeight ][ ::-1, ::-1 ]
                            result[ L:R, supMin[1]-rHeight:supMin[1] ] = reflKernel

                        if ( supMax[1] < supHeight ):
                            #reflect top-left
                            rHeight = min( sigHeight, supHeight - supMax[1] )
                            reflKernel = self.data.cells[ :rWidth, sigHeight-rHeight:sigHeight ][::-1,::-1]
                            result[ L:R, supMax[1]:supMax[1] + rHeight ] = reflKernel

                    if ( supMax[0] < supWidth ):
                        # reflect right
                        rWidth = min( supWidth - supMax[0], sigWidth )
                        reflKernel = self.data.cells[ -rWidth:, sigMin[1]:sigMax[1] ][::-1, :]
                        L = supMax[0]
                        R = supMax[0] + rWidth
                        result[ L:R, supMin[1]:supMax[1] ] = reflKernel

                        if ( supMin[1] > 0 ):
                            # reflect bottom-right
                            rHeight = min( supMin[1], sigHeight - sigMin[1] )
                            reflKernel = self.data.cells[ -rWidth:, :rHeight ][ ::-1, ::-1 ]
                            result[ L:R, supMin[1]-rHeight:supMin[1] ] = reflKernel

                        if ( supMax[1] < supHeight ):
                            # reflect top
                            rHeight = min( sigHeight, supHeight - supMax[1] )
                            reflKernel = self.data.cells[ -rWidth:, sigHeight-rHeight:sigHeight ][::-1,::-1]
                            result[ L:R, supMax[1]:supMax[1] + rHeight ] = reflKernel

                    if ( supMin[1] > 0 ):
                        # reflect bottom
                        rHeight = min( supMin[1], sigHeight - sigMin[1] )
                        reflKernel = self.data.cells[ sigMin[0]:sigMax[1], :rHeight ][:, ::-1]
                        result[ supMin[0]:supMax[0], supMin[1]-rHeight:supMin[1] ] = reflKernel

                    if ( supMax[1] < supHeight ):
                        # reflect top
                        rHeight = min( sigHeight, supHeight - supMax[1] )
                        reflKernel = self.data.cells[ sigMin[0]:sigMax[1], sigHeight-rHeight:sigHeight ][:, ::-1]
                        result[ supMin[0]:supMax[0], supMax[1]:supMax[1]+rHeight ] = reflKernel
        return result

    def getFieldData( self, expansion=0 ):
        '''Returns an image of the signal, possibly with reflection.

        @param      expansion       An non-negative int. Indicates how
                                    much the image should be expanded beyond
                                    the source signal.  The expanded region is
                                    a reflection, of the adjacent source signal.
        @returns    A M' x N' numpy array.  Where M' = M + 2 * expansion and
                    N' = N + 2 * expansion, where the source field is an
                    M x N field.
        '''
        sigData = self.data.cells
        if ( expansion ):
            expandW = sigData.shape[0] + 2 * expansion
            expandH = sigData.shape[1] + 2 * expansion
            data = np.empty( ( expandW, expandH ), dtype=sigData.dtype )
            # copy center
            data[ expansion:-expansion, expansion:-expansion ] = sigData
            # copy left
            hReflAmount = min( expansion, sigData.shape[0] )
            left = expansion - hReflAmount
            data[ left:expansion, expansion:-expansion ] = sigData[ :hReflAmount, : ][ ::-1, : ]
            # copy right
            right = expandW - expansion + hReflAmount
            data[ -expansion:right, expansion:-expansion ] = sigData[ -hReflAmount:, : ][ ::-1, : ]
            # copy top
            vReflAmount = min( expansion, sigData.shape[1] )
            top = expandH - expansion + vReflAmount
            data[ expansion:-expansion, -expansion:top ] = sigData[ :, -vReflAmount: ][ :, ::-1 ]
            # copy bottom
            bottom = expansion - vReflAmount
            data[ expansion:-expansion, bottom:expansion ] = sigData[ :, :vReflAmount ][ :, ::-1 ]
            # copy top-left
            data[ left:expansion, -expansion:top ] = sigData[ :hReflAmount, -vReflAmount: ] [::-1, ::-1 ]
            # copy top-right
            data[ -expansion:right, -expansion:top ] = sigData[ -hReflAmount:, -vReflAmount: ] [::-1, ::-1 ]
            # copy bottom-left
            data[ left:expansion, bottom:expansion ] = sigData[ :hReflAmount, :vReflAmount ] [::-1, ::-1 ]
            # copy bottom-right
            data[ -expansion:right, bottom:expansion ] = sigData[ -hReflAmount:, :vReflAmount ] [::-1, ::-1 ]
            # zero out outer ring
            data[ :left, : ] = 0.0
            data[ right:, : ] = 0.0
            data[ left:right, top: ] = 0.0
            data[ left:right, :bottom ] = 0.0
            return data
        else:
            return sigData
    def setData( self, data ):
        '''Sets the signal's data.

         @param  data           An instance of the DataGrid.  Contains the signal
                                located in space with a particular tesselation.  The
                                grid is used as given -- it is not copied.
        '''
        self.data = data
        
class GFSSignal( FieldSignal ):
    '''A discrete approximation of the voronoi diagram.  This one knows how to
    read voronoi data from a GridFileSequenceReader.'''
    def setData( self, data ):
        '''Sets the signal's data.

         @param  data           This is overloaded.  It can be one of:
                                     1) an instance of a DataGrid,
                                     2) a numpy array which has the same resolution
                                as the current data grid, or
                                    3) A GridFileSequenceReader
                                In all cases, the data is COPIED into the signal.
        @raises     StopIteration if the frameSet is out of frames.
        @raises     ValueError if the data cannot be set due to data format issues (wrong array size, etc.)
        '''
        if ( isinstance( data, Grid.DataGrid ) ):
            self.data = data.copy()
        elif ( isinstance( data, np.ndarray ) ):
            if ( not self.data is None ):
                self.data.cells[:, :] = data
            else:
                raise ValueError, 'Cannot set the data for a VoronoiSignal with a numpy array without first setting the data grid.'
        elif ( isinstance( data, GridFileSequenceReader ) ):
            gridData, self.index = data.next()
            if ( self.data is None ):
                self.data = gridData.copy()
            else:
                self.data.cells[:, :] = gridData.cells
        else:
            raise ValueError, 'Bad data type for setting Voronoi signal: %s' % ( str( data ) )

if __name__ == '__main__':
    import domains
    import numpy as np
    from primitives import Vector2
    def test():
        print "Testing signals!"
        if ( True ):
            print "\n\tTesting dirac signals"
            data = np.random.rand( 10, 2 )
            pedDomain = domains.RectDomain( ( -2.0, -2.0 ), (4.0, 4.0 ) )
            s = DiracSignal( pedDomain, data )
            for i, pos in enumerate( s.impulses ):
                print '\t\t', i, pos, data[i, :]

        if ( True ):
            print "\n\tTesting field signal"
            data = np.array( ( (1, 2, 3), (10, 20, 30) ), dtype=np.float32 )
            grid = Grid.DataGrid( (0.0, 0.0), (2.0, 3.0 ), (2, 3) )
            grid.cells[:, :] = data
            s = FieldSignal( grid )
            convolve = Grid.DataGrid( Vector2(1.0, 1.0), Vector2( 1.0, 1.0 ), (1,1) )
            domSig = s.getDomainSignal( convolve, 2, False )
            expected = np.array( ( ( 0, 0, 0, 0, 0 ),
                                   ( 0, 1, 2, 3, 0 ),
                                   ( 0, 10, 20, 30, 0 ),
                                   ( 0, 0, 0, 0, 0 ),
                                   ( 0, 0, 0, 0, 0 ) ), dtype=np.float32 )
##            print data
            print "\nNO REFLECTION"
            different = expected != domSig
            if ( different.sum() != 0 ):
                print "\t\tFAILED"
            else:
                print "\t\tPASSED"
##            print domSig
            domSig = s.getDomainSignal( convolve, 2, True )
            print "WITH REFLECTION"
            expected = np.array( ( (  1,  1,  2,  3,  3 ),
                                   (  1,  1,  2,  3,  3 ),
                                   ( 10, 10, 20, 30, 30 ),
                                   ( 10, 10, 20, 30, 30 ),
                                   (  1,  1,  2,  3,  3 ) ), dtype=np.float32 )
##            different = expected != domSig
            if ( different.sum() != 0 ):
                print "\t\tFAILED"
            else:
                print "\t\tPASSED"
            

    test()