# module for handling signals for convolution

import numpy as np

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

class DiracSignal( Signal ):
    '''A signal consisting of a sum of translated dirac functions'''
    def __init__( self, data, domain ):
        '''Constructor for the signal.

        @param  data        An Nx2 numpy array of flaots. The signal data.
        @param  domain      An instance of Grids.RectDomain.  Defines the domain of the signal.
        '''
        self._data = data
        self.domain = domain

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
        return DiracSignal.ImpulseIterator( self )

    def __getitem__( self, i ):
        '''Return the ith impulse in the data.

        @param      i       The index of the desired impulse.
        @returns    A numpy array with shape (2,).  The ith impulse.
        @raises     IndexError if the index is invalid.
        '''
        return self._data[ i ]

    def __len__( self ):
        '''Returns the number of impulses in the signal.NSIG

        @returns    An int.  The count of impulses.
        '''
        return self._data.shape[0]

class FieldSignal( Signal ):
    '''A discrete approximation of a continuous signal defined over a
        rectangular domain'''
    def __init__( self, fieldData ):
        '''Constructor based on the provided field data.shape

        @param  fieldData       An instance of the DataGrid.  Containing the signal
                                located in space with a particular tesselation.  The
                                grid is used as given -- it is not copied.
        '''
        self.data = fieldData

    def getDomain( self ):
        '''Reports the domain of the signal.

        @returns    Two 2-tuple-like values reporting the minimum value and the size of the domain.
                        (minX, minY) and (width, height).
        '''
        return self.data.minCorner, self.data.size
    
    @property
    def shape( self ):
        return self.data.cells.shape

    def getFieldData( self, expansion=0 ):
        '''Returns an image of the signal, possibly with reflection.

        @param      expansion       An non-negative int. Indicates how
                                    much the image should be expanded beyond
                                    the source signal.  The expanded region is
                                    a reflection, of the adjacent source signal.NSIG
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

class PedestrianSignal( DiracSignal ):
    '''A dirac signal, where the pedestrian positions are the impulses'''
    def __init__( self, frameSet, domain ):
        '''Constructor.

        @param      frameSet    A pedestrian data frame set (such as
                                scbData or SeyfriedTrajectoryReader.)
        @raises     StopIteration if the frameSet is out of frames.
        '''
        frameData, frameID = frameSet.next()
        DiracSignal.__init__( self, frameData[:, :2], domain )

##class VoronoiSignal( FieldSignal ):
##    '''A field signal comprising of a pre-computed voronoi diagram.'''
##    pass

if __name__ == '__main__':
    import numpy as np
    def test():
        print "Testing signals!"
        if ( False ):
            print "\n\tTesting dirac signals"
            data = np.random.rand( 10, 2 )
            s = DiracSignal( data )
            for i, pos in enumerate( s.impulses ):
                print '\t\t', i, pos, data[i, :]

        if ( True ):
            print "\n\tTesting field signal"
            data = np.array( ( (1, 2, 3), (10, 20, 30) ), dtype=np.float32 )
            s = FieldSignal( data )
            field = s.getFieldData( 4 )
            print field
            print

    test()