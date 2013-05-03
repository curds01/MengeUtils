# given a trajectory file and a smoothing parameter, smooths the
#   trajectories using a gaussian kernel

from dataLoader import loadTrajectory
import numpy as np
import commonData
from scbData import SCBDataMemory
import pylab as plt

def gaussian1D( sigma, cellSize, kWidth ):
    """Computes a discrete gaussian kernel with standard deviation sigma and mean zero discretized
    to the given cellSize.  The kernel spans a width of 6 * sigma and is normalized to sum to one.

    @param      sigma       A float.  The standard deviation of the gaussian distribution.
    @param      cellSize    A float.  The size of the discrete cell.
    @param      kWidth      An int.  The minimum size of the required kernel.
    @return     A numpy array of floats of shape ( k, ), where k is the smallest odd number 
                such that k * cellSize >= 6 * sigma.  The values are the normalized evaluations
                of the Gaussian function: e(x) = e^(-x^2/2sigma^2)
    """
    kernelSize = max( int( np.ceil( 6 * sigma / cellSize ) ), kWidth )
    if ( kernelSize % 2 == 0 ):     # make sure the kernel size is odd numbered
        kernelSize += 1
        range = ( kernelSize / 2 ) * cellSize
    else:
        range = ( ( kernelSize / 2 ) - 0.5 ) * cellSize
    x = np.linspace( -range, range, kernelSize )
    k = np.exp( -( x * x )/( 2.0 * sigma * sigma ) )
    k *= 1.0 / k.sum()
    return k

def smoothSCB( data, sigma ):
    '''Smooths the trajectories in the given SCB data using a gaussian kernel with
    the given standard deviation (sigma).

    @param      data            An instance of SCBData.
    @param      sigma           A float.  The size of the standard deviation (in frames).
    @return     A new instance of SCBData containing smoothed trajectories.  The duration of the
                two trajectories is the same.
    @raises:    ValueError if the data is not of a recognizable format.
    '''
    print "smoothSCB"
    window = int( sigma * 3 )
    rawData = data.fullData()
    smoothData = np.empty( rawData.shape, dtype=np.float32 )
    kernel = gaussian1D( sigma, 1.0, rawData.shape[2] )
    kFFT = np.abs( np.fft.rfft( kernel ) )
    kFFT.shape = (1,-1)
    print "\tKernel:"
    print "\t\tSigma:", sigma
    print "\t\tKernel shape:", kernel.shape
    print "\t\tkFFT shape:", kFFT.shape
    print "\tData:"
    print "\t\tData shape:", rawData.shape

    # TODO: This causes periodic issues - I'd be better off convolving the kernel with each frame
    # TODO: Handle big discontinuities and don't smooth over them.
    for i in range( 2 ):
        dataFFT = np.fft.rfft( rawData[:,i,:], axis=1 )
        smoothFFT = dataFFT * kFFT
        smoothData[ :, i, : ] = np.fft.irfft( smoothFFT, smoothData.shape[2], axis=1 )
    # orientation data
    smoothData[:, 2:, : ] = rawData[:, 2:, : ]
    
    if ( True ):
        SAMPLE = 10
        plt.figure()
        plt.subplot( 2, 1, 1 )
        for i in range( 10 ):#rawData.shape[0] ):
            plt.plot( rawData[i, 0, window:-window:SAMPLE ], rawData[i, 1, window:-window:SAMPLE], 'b' )
        plt.xlim( (-10, 10) )
        plt.ylim( ( -4, 8 ) )
        plt.title( 'raw trajectory' )
        plt.subplot( 2, 1, 2 )
        for i in range( 10 ): #rawData.shape[0] ):
            plt.plot( smoothData[i, 0, window:-window:SAMPLE ], smoothData[i, 1, window:-window:SAMPLE],'r' )
        plt.title( 'Smoothed trajectory' )
        plt.xlim( (-10, 10) )
        plt.ylim( ( -4, 8 ) )
        plt.show()
    newData = SCBDataMemory()
    newData.setData( agtData, data.version, data.simStepSize )
    return newData

    
def smoothJulich( data, sigma ):
    '''Smooths the trajectories in the given SCB data using a gaussian kernel with
    the given standard deviation (sigma).

    @param      data            An instance of JulichData.
    @param      sigma           A float.  The size of the standard deviation (in frames).
    @return     A new instance of JulichData containing smoothed trajectories.
    @raises:    ValueError if the data is not of a recognizable format.
    '''
    return data
    
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
    