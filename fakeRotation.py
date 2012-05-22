# add fake rotation to the scb file
#
#   Given an scb file, overwrites the current orientation values
#    based on the inter-frame velocity and some angular acceleration
#    limit

import numpy as np
from scbData import NPFrameSet, writeNPSCB

DEFAULT_OUTPUT = 'output.scb'
DEF_VEL_LIMIT = 10.0 * np.pi / 180.0  # 10 degrees per sec

# The minimum distance an agent has to travel in order to consider a possible angular change
MOVE_THRESH = 0.001

def addOrientation( data, maxThetaDelta ):
    '''Given an M x N x K array of simulation data,
    computes orientation of each agent such that between timesteps the agent's orientation cannot change
    by more than maxThetaDelta. The data is modified IN PLACE.

    @param data: an M x N x K numpy array.  Where there are M agents with N float attributes over K frames.
    @param maxThetaDelta: a float.  The maximum allowable change in orientation for a single timestep
    '''
    TWO_PI = 2.0 * np.pi
    # compute the original orientation based on the first two time steps
    k = 2
    disp = data[ :, :2, k ] - data[ :, :2, 0 ]
    dist = np.sqrt( np.sum( disp * disp, axis=1 ) )
    while ( np.sum( dist < MOVE_THRESH ) > 0 ):
        k += 1
        disp = data[ :, :2, k ] - data[ :, :2, 0 ]
        dist = np.sqrt( np.sum( disp * disp, axis=1 ) )

    # make sure I have meaningful displacements for EVERYONE
    print "Initial direction computed from frame %d" % k 
        
    angles = np.arctan2( disp[:,1], disp[:,0] )
    angles[ angles < 0 ] += TWO_PI
    data[ :, 2, 0 ] = angles
    
    # for each successive frame,
    #   1. compute the direction of travel from frame i to frame i + 1
    #   2. Compute delta = the angular difference between orientation at i and the orientation of the direction 
    #   3. Increment the orientation by max( maxThetaDelta, delta )
    for f in xrange( 1, data.shape[2] - 1 ):
        disp = data[ :, :2, f + 1 ] - data[ :, :2, f ]
        dist = np.sqrt( np.sum( disp * disp, axis=1 ) )
        noMovement = dist < MOVE_THRESH
        angles = np.arctan2( disp[:,1], disp[:,0] )
        angles[ angles < 0 ] += TWO_PI
        angles[ noMovement ] = data[ noMovement, 2, f - 1 ]

        # detect the ones that have gone around the the periodic        
        prevAngles = data[ :, 2, f - 1 ]
        delta = prevAngles - angles
        absDelta = np.abs( delta )
        periodic = absDelta > np.pi # all of the items where I've split over the period
        bigger = delta < 0  # the new angle is bigger than the prev angle
        smaller = delta > 0  # the new angle is smaller than the prev angle
        angles[ bigger & periodic ] += TWO_PI
        angles[ smaller & periodic ] -= TWO_PI

        # now clamp it to maximum velocity        
        delta = prevAngles - angles
        absDelta = np.abs( delta )
        clamp = absDelta > maxThetaDelta
        delta[ clamp ] *= maxThetaDelta / absDelta[ clamp ]
        angles = prevAngles - delta

        # now clamp it to the range [0, 2pi]
        tooSmall = angles < 0
        while ( np.sum( tooSmall ) > 0 ):
            angles[ tooSmall ] += TWO_PI
            tooSmall = angles < 0
        tooBig = angles >= TWO_PI
        while ( np.sum( tooBig ) > 0 ):
            angles[ tooBig ] -= TWO_PI
            tooBig = angles < 0
        # set orientation
        data[ :, 2, f ] = angles

    # final orientation is simply copied from second to last
    data[ :, 2, -1 ] = data[ :, 2, -2 ]

def addSCBOrientation( inFile, outFile, maxVel ):
    '''Given an scb file, adds orientation to it based on max angular velocity, saving the result to
    the outFile.'''
    scbData = NPFrameSet( inFile )
    fullData = scbData.fullData()
    addOrientation( fullData, scbData.simStepSize * maxVel)

    scbData.close()
    writeNPSCB( outFile, fullData, scbData, scbData.version )  

def main():
    import optparse, sys
    parser = optparse.OptionParser()
    parser.set_description( 'Computes orientation for the agents trajectories after the fact.' )
    parser.add_option( '-i', '--in', help='The name of the file to add orientation to (must be valid scb file)',
                       action='store', dest='inFileName', default='' )
    parser.add_option( '-o', '--out', help='The name of the output scb file (defaults to %s)' % DEFAULT_OUTPUT,
                       action='store', dest='outFileName', default=DEFAULT_OUTPUT )
    parser.add_option( '-a', '--angularVelocity', help='The maximum angular velocity allowed (in radians/s).  Default is %g' % DEF_VEL_LIMIT,
                       action='store', dest='velocity', type='float', default=DEF_VEL_LIMIT )

    options, args = parser.parse_args()

    if ( options.inFileName == '' ):
        print "You must specify an input name"
        parser.print_help()
        sys.exit( 1 )

    print
    print "Adding orientation to:", options.inFileName
    print "\tOutput to:", options.outFileName
    print "\tMaximum angular velocity: %g radians/s (%g deg/s)" % ( options.velocity, options.velocity / np.pi * 180.0 )

    addSCBOrientation( options.inFileName, options.outFileName, options.velocity )


if __name__ == '__main__':
    main()
    