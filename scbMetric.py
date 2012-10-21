# Measure various quantities in an scb file.close

import trajectory.scbData as scbData
import numpy as np
import pylab as plt

def totalSimTime( rawData, step ):
    '''Compute the total duration of the simuation'''
    return rawData.shape[2] * step

def findNaNPos( rawData ):
    '''Finds all of the agents that have NaN in their position information.
    Reports the total number found and returns two values:
        1. A 1D array of the indices of all bad agents
        2. A new M X 3 X K matrix were M <= N with the bad agents removed'''
    goodAgents = np.sum( np.sum( np.isnan( rawData[:, :2, : ] ), axis=1), axis=1 ) == 0
    newData = rawData[ goodAgents, :, : ]
    return np.where( ~goodAgents )[0], newData

def segmentLength( rawData ):
    '''Returns the lengths of each segment for each agent (An N X K matrix)'''
    assert( np.sum( np.isnan( rawData[:,:2,:] ) ) == 0 )
    deltas = np.diff( rawData[ :, :2, : ], axis = 2 ) # ignore rotations
    assert( np.sum( np.isnan( deltas ) ) == 0 )
    distSq = np.sum( deltas * deltas, axis = 1 )
    assert( np.sum( np.isnan( distSq ) ) == 0 )
    dist = np.sqrt( distSq )
    assert( np.sum( np.isnan( dist ) ) == 0 )
    assert( dist.shape[0] == rawData.shape[0] )
    assert( dist.shape[1] == rawData.shape[2] - 1 )
    return dist

def segmentSpeeds( segLength, stepSize ):
    '''Returns the speeds of each segment for each agent (An N X K matrix)'''
    invStep = 1.0 /stepSize
    return segLength * invStep

def trajectoryExtrema( segLength ):
    '''Compute the shortest and longest trajectories

    Returns two tuples: (id, minLength) (id, minSpeed )'''
    trajLen = np.sum( segLength, 1 )
    return ( np.argmin( trajLen ), np.min( trajLen )), ( np.argmax(trajLen), np.max( trajLen ) )

def avgSpeedExtrema( segLength, simTime ):
    '''Compute the lowest and highest average speeds

    Returns two tuples: (id, minSpeed) (id, maxSpeed)'''
    avgSpeed = np.sum( segLength, 1 ) / simTime
    return ( np.argmin( avgSpeed ), np.min( avgSpeed )), ( np.argmax(avgSpeed), np.max( avgSpeed ) )

def instSpeedExtrema( segLength, stepTime ):
    '''Compute the lowest and highest instantaneous speeds

    retuns two tuples: (id, frame, minSpeed) (id, frame, maxSpeed )
    '''
    frameCount = segLength.shape[1]
    speeds = segLength / stepTime
    
    minID = np.argmin( speeds )
    minVal = np.min( speeds )
    minFrame = minID % frameCount
    minID = minID / frameCount

    maxID = np.argmax( speeds )
    maxVal = np.max( speeds )
    maxFrame = maxID % frameCount
    maxID = maxID / frameCount

    return ( minID, minFrame, minVal ), (maxID, maxFrame, maxVal )    
    
def printMetrics( frames ):
    print '\tNumber of agents:', frames.agtCount

    rawData = frames.fullData()
    badAgents, newData = findNaNPos( rawData )
    print "\tNumber of agents with nan values in position:", badAgents.size, badAgents
    print "\tNew number of agents:", newData.shape[0]
    
    step = frames.simStepSize
    while ( step < 0 ):
        ans = raw_input('\tPlease enter simulation time step: ' )
        try:
            step = float( ans )
        except:
            pass
    print '\tSimulation time step: %.3f' % step
    segments = segmentLength( newData )
    segSpeeds = segmentSpeeds( segments, step )
    simTime = totalSimTime( rawData, step )
    print '\tTotal simulation time: %.2f seconds' % simTime
    ( mID, m ), ( MID, M ) = trajectoryExtrema( segments )
    print '\tShortest trajectory:', m
    print '\tLongest trajectory:', M
    ( mID, m ), ( MID, M ) = avgSpeedExtrema( segments, simTime )
    print '\tLowest average speed:', m
    print '\tHighest average speed:', M
    ( mID, mFrame, m ), ( MID, MFrame, M ) = instSpeedExtrema( segments, step )
    print '\tLowest instantanesous speed:', m
    print '\tHighest instantaneous speed:', M
    
def main():
    import sys
    import optparse

    parser = optparse.OptionParser()
    parser.add_option( "-s", "--scb", help="Name of the scb file to operate on (required)",
                       action="store", dest="scbName", default='' )
    parser.add_option( "-p", "--plot", help="Index of the agent to plot.  In the range [0, N-1]",
                       action="store", dest="plotID", default=-1, type='int' )
    options, args = parser.parse_args()

    if ( options.scbName == '' ):
        parser.print_help()
        sys.exit(1)

    print "Options:"
    print "\tInput:", options.scbName
    print
    
    try:
        frames = scbData.NPFrameSet( options.scbName, maxFrames=10 )
        printMetrics( frames )
        if ( options.plotID != -1 ):
            rawData = frames.fullData()
            plt.plot( rawData[ options.plotID, 0, :], rawData[ options.plotID, 1, : ], 'b-o' )
            plt.show()
    except IOError, e:
        print "\nError trying to open %s:" % ( options.scbName ), e
        sys.exit(1)

if __name__ == '__main__':
    main()