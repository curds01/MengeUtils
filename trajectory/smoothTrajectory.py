# given a trajectory file and a smoothing parameter, smooths the
#   trajectories using a gaussian kernel

from dataLoader import loadTrajectory
import numpy as np
import commonData
from scbData import SCBDataMemory
import pylab as plt
from copy import deepcopy

def gaussian1D( sigma, cellSize ):
    """Computes a discrete gaussian kernel with standard deviation sigma and mean zero discretized
    to the given cellSize.  The kernel spans a width of 6 * sigma and is normalized to sum to one.

    @param      sigma       A float.  The standard deviation of the gaussian distribution.
    @param      cellSize    A float.  The size of the discrete cell.
    @return     A numpy array of floats of shape ( k, ), where k is the smallest odd number 
                such that k * cellSize >= 6 * sigma.  The values are the normalized evaluations
                of the Gaussian function: e(x) = e^(-x^2/2sigma^2)
    """
    kernelSize = int( np.ceil( 6 * sigma / cellSize ) )
    if ( kernelSize % 2 == 0 ):     # make sure the kernel size is odd numbered
        kernelSize += 1
        range = ( kernelSize / 2 ) * cellSize
    else:
        range = ( ( kernelSize / 2 ) - 0.5 ) * cellSize
    x = np.linspace( -range, range, kernelSize )
    k = np.exp( -( x * x )/( 2.0 * sigma * sigma ) )
    k *= 1.0 / k.sum()
    return k

def findIntervals( path, threshSqd=1.0 ):
    '''Find the continuous intervals in the given path.

    @param      path        A numpy array of floats with shape (N, 2).  The path is a
                            sequence of N positions in R^2.  The first column is the x-position.
                            The second is the y-position.
    @param      thresh      The maximum SQUARED displacement between two subsequent positions
                            that is considered to be continuous.
    @returns    A list of 2-tuples.  Each 2-tuple is a pair of ints: ( start, end ), such that a
                continuous path can be accessed by the slice [start:end].  If the full path is
                continuous, then a single 2-tuple is returned in the list.
    '''
    delta = np.diff( path, axis=0 )
    dSqd = np.sum( delta * delta, axis=1 )
    breaks = np.where( dSqd > threshSqd )[0]
    start = 0
    intervals = []
    if ( breaks.size > 0 ):
        # there are intervals to be created
        for t in breaks:
            intervals.append( ( start, t + 1 ) )
            start = t + 1
    intervals.append( ( start, path.shape[0] ) )
    return intervals

def smooth( path, kernel ):
    '''Use convolution to smooth the given path with the given kernel.  The end result will be
    the same length as path.  

    @param      path        A numpy array of floats with shape (N, 2).  The path is a
                            sequence of N positions in R^2.  The first column is the x-position.
                            The second is the y-position.
    @param      kernel      A numpy array of floats with shape (K, ).  A kernel with K samples.
    @return     A NEW numpy array of floats with shape (N, 2) which represents the convolution of
                path with kernel.  Typically, if we assume N > K, then the first and last K/2 entries
                in the smooth data will be "garbage".  In this case, the amount of change applied
                to index K/2 and -K/2 is proportionately applied to the end values so that there is
                a "smooth"(ish) change across the entire domain.
    '''
    newData = np.empty_like( path )
    newData[ :, 2: ] = path[ :, 2: ]
    if ( path.shape[0] > kernel.size ):
        halfK = kernel.size / 2
        newData[ halfK:-halfK, 0 ] = np.convolve( path[:, 0], kernel, 'valid' )
        newData[ halfK:-halfK, 1 ] = np.convolve( path[:, 1], kernel, 'valid' )
        # linearly interpolate the first half and the last half
        # leading set
        delta = newData[ halfK, :2 ] - path[ halfK, :2 ]
        weights = np.linspace( 0.0, 1.0, halfK + 1 )[:-1]
        weights.shape = (-1, 1 )
        delta = delta * weights
        newData[ :halfK, :2 ] = delta + path[ :halfK, :2 ]
        # trailing set
        delta = newData[ -(halfK+1), :2 ] - path[ -(halfK+1), :2 ]
        weights = np.linspace( 1.0, 0.0, halfK + 1 )[1:]
        weights.shape = (-1, 1 )
        delta = delta * weights
        newData[ -halfK:, :2 ] = delta + path[ -halfK:, :2 ]
    else:
        # TODO: Do something "smart" here - currently leaving the data unfiltered
        newData[:, :2 ] = path [:, :2 ]
    return newData

def smoothSCB( data, sigma ):
    '''Smooths the trajectories in the given SCB data using a gaussian kernel with
    the given standard deviation (sigma).

    @param      data            An instance of SCBData.
    @param      sigma           A float.  The size of the standard deviation (in frames).
    @return     A new instance of SCBData containing smoothed trajectories.  The duration of the
                two trajectories is the same.
    @raises:    ValueError if the data is not of a recognizable format.
    '''
    rawData = data.fullData()
    smoothData = np.empty( rawData.shape, dtype=np.float32 )
    kernel = gaussian1D( sigma, 1.0 )
    for a in xrange( rawData.shape[0] ):
        path = rawData[ a, :2, : ].T
        intervals = findIntervals( path )
        for iVal in intervals:
            iValData = path[ iVal[0]:iVal[1], : ]
            smoothIVal = smooth( iValData, kernel )
            smoothData[ a, :2, iVal[0]:iVal[1] ] = smoothIVal.T
    newData = SCBDataMemory()
    newData.setData( smoothData, data.version, data.simStepSize )
    return newData
    
def smoothJulich( data, sigma ):
    '''Smooths the trajectories in the given SCB data using a gaussian kernel with
    the given standard deviation (sigma).

    @param      data            An instance of JulichData.
    @param      sigma           A float.  The size of the standard deviation (in frames).
    @return     A new instance of JulichData containing smoothed trajectories.
    @raises:    ValueError if the data is not of a recognizable format.
    '''
    newData = deepcopy( data )
    kernel = gaussian1D( sigma, 1.0 )
    for ped in newData.pedestrians:
        path = ped.traj[:, :2]
        intervals = findIntervals( path )
        for iVal in intervals:
            iValData = path[ iVal[0]:iVal[1], : ]
            smoothIVal = smooth( iValData, kernel )
            path[ iVal[0]:iVal[1], :2 ] = smoothIVal
    return newData
    
def smoothTrajectory( data, sigma ):
    '''Smooths the trajectories in the given trajectory data using a gaussian kernel with
    the given standard deviation (sigma).

    @param      data            An instance of trajectory data.
    @param      sigma           A float.  The size of the standard deviation (in frames).
    @return     A new instance of trajectory data containing smoothed trajectories.
    @raises:    ValueError if the data is not of a recognizable format.
    '''
    if ( data.getType() == commonData.SCB_DATA ):
        return smoothSCB( data, sigma )
    elif ( data.getType() == commonData.JULICH_DATA ):
        return smoothJulich( data, sigma )
    else:
        raise ValueError, "Unrecognized trajectory data"
    
    
def smoothTrajFile( fileName, sigma ):
    '''Smooths the trajectories in the named trajectory file using a gaussian kernel with
    the given standard deviation (sigma).

    @param      fileName        A string.  The path to the trajectory file.
    @param      sigma           A float.  The size of the standard deviation (in frames).
    @return     A new instance of trajectory data containing smoothed trajectories.
    '''
    # load trajectory
    data = loadTrajectory( fileName )
    # transform
    return smoothTrajectory( data, sigma )

def main():
    parser = optparse.OptionParser()
    parser.set_description( 'Smooth the trajectories of the input trajectory file, writing the results out to a new file' )
    parser.add_option( "-i", "--inFile", help="Name of the trajectory file to operate on (required)",
                       action="store", dest="inFileName", default='' )
    parser.add_option( "-s", "--sigma", help="The standard deviation of the smoothing kernl (in frames) - defaults to 1.0 if non specified",
                       action="store", type="float", dest='sigma', default=1.0 )
    parser.add_option( "-o", "--outFile", help="Name of the trajectory file to save the filtered result - defaults to outFile.ext (where ext is the same extension as the input) if none specified.",
                       action="store", dest="outFileName", default=None )

    options, args = parser.parse_args()

    # validate
    if ( options.inFileName is None ):
        parser.print_help()
        print '\n!!! You must specify an input file'
        sys.exit(1)

    # smooth the data
    
    newData = smoothTrajFile( options.inFileName, options.sigma )

    # export the data
    outName = None
    if ( options.outFileName is None ):
        path, fileName = os.path.split( options.inFileName )
        name, ext = os.path.splitext( fileName )
        outName = 'output' + ext
    else:
        outName = options.outFileName

    newData.write( outName )
if __name__ == '__main__':
    import optparse
    import sys
    main()
    