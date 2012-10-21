# add fake rotation to the scb file
#
#   Given an scb file, overwrites the current orientation values
#    based on the inter-frame velocity and some angular acceleration
#    limit

import numpy as np
from trajectory.scbData import NPFrameSet, writeNPSCB

DEF_VEL_LIMIT = 10.0 * np.pi / 180.0  # 10 degrees per sec

# The minimum distance an agent has to travel in order to consider a possible angular change
MOVE_THRESH = 0.001

def addOrientation( data, maxThetaDelta, window=1 ):
    '''Given an M x N x K array of simulation data,
    computes orientation of each agent such that between timesteps the agent's orientation cannot change
    by more than maxThetaDelta. The data is modified IN PLACE.

    @param data: an M x N x K numpy array.  Where there are M agents with N float attributes over K frames.
    @param maxThetaDelta: a float.  The maximum allowable change in orientation for a single timestep.
    @param window: an int.  The size of the window used to compute the finite differences.  I.e., the
            angular change at frame i is the difference of the direction of velocity at i and i + window.
    '''
    TWO_PI = 2.0 * np.pi
    # compute the original orientation based on the first two time steps
    disp = data[ :, :2, window ] - data[ :, :2, 0 ]
    dist = np.sqrt( np.sum( disp * disp, axis=1 ) )
    k = window
    while ( np.sum( dist < MOVE_THRESH ) > 0 and k < data.shape[2] ):
        disp = data[ :, :2, k ] - data[ :, :2, 0 ]
        dist = np.sqrt( np.sum( disp * disp, axis=1 ) )
        k += 1
    
    # make sure I have meaningful displacements for EVERYONE
    print "Initial direction computed from frame %d" % k 
        
    angles = np.arctan2( disp[:,1], disp[:,0] )
    angles[ angles < 0 ] += TWO_PI
    data[ :, 2, 0 ] = angles
    
    # for each successive frame,
    #   1. compute the direction of travel from frame i to frame i + 1
    #   2. Compute delta = the angular difference between orientation at i and the orientation of the direction 
    #   3. Increment the orientation by max( maxThetaDelta, delta )
    for f in xrange( 1, data.shape[2] - window ):
        disp = data[ :, :2, f + window ] - data[ :, :2, f ]
        dist = np.sqrt( np.sum( disp * disp, axis=1 ) )
        noMovement = dist < MOVE_THRESH
        angles = np.arctan2( disp[:,1], disp[:,0] )
##        angles[ angles < 0 ] += TWO_PI
        angles[ noMovement ] = data[ noMovement, 2, f - 1 ]

        # detect the ones that have gone around the the periodic        
        prevAngles = data[ :, 2, f - 1 ]
        delta = prevAngles - angles
        absDelta = np.abs( delta )
        periodic = absDelta > np.pi # all of the items where I've split over the period
        bigger = delta < 0  # the new angle is bigger than the prev angle
        smaller = delta > 0  # the new angle is smaller than the prev angle
        angles[ bigger & periodic ] -= TWO_PI
        angles[ smaller & periodic ] += TWO_PI

        delta = prevAngles - angles
        absDelta = np.abs( delta )
        periodic = absDelta > np.pi # all of the items where I've split over the period
        assert( np.sum( periodic ) == 0 )

        # now clamp it to maximum velocity        
        delta = prevAngles - angles
        absDelta = np.abs( delta )
        clamp = absDelta > maxThetaDelta
        delta[ clamp ] *= maxThetaDelta / absDelta[ clamp ]
        angles = prevAngles - ( delta / window )

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
    for f in range( -window, 0 ):
        data[ :, 2, f ] = data[ :, 2, f-1 ]

def addSCBOrientation( inFile, outFile, maxVel, window=1 ):
    '''Given an scb file, adds orientation to it based on max angular velocity, saving the result to
    the outFile.'''
    scbData = NPFrameSet( inFile )
    fullData = scbData.fullData()
    addOrientation( fullData, scbData.simStepSize * maxVel * window, window)

    scbData.close()
    writeNPSCB( outFile, fullData, scbData, scbData.version )  

def main():
    import optparse, sys
    parser = optparse.OptionParser()
    parser.set_description( 'Computes orientation for the agents trajectories after the fact.' )
    parser.add_option( '-i', '--in', help='The name of the file to add orientation to (must be valid scb file)',
                       action='store', dest='inFileName', default='' )
    parser.add_option( '-o', '--out', help='The name of the output scb file (defaults to overwriting input file)',
                       action='store', dest='outFileName', default='' )
    parser.add_option( '-a', '--angularVelocity', help='The maximum angular velocity allowed (in radians/s).  Default is %g' % DEF_VEL_LIMIT,
                       action='store', dest='velocity', type='float', default=DEF_VEL_LIMIT )
    parser.add_option( '-w', '--window', help='Number of frames overwhich to compute angular velocity.  This smooths the signal (default is 1)',
                       action='store', dest='window', type='int', default=1 )

    options, args = parser.parse_args()

    if ( options.inFileName == '' ):
        print "You must specify an input name"
        parser.print_help()
        sys.exit( 1 )

    outFile = options.outFileName
    if ( options.outFileName == '' ):
        outFile = options.inFileName

    print
    print "Adding orientation to:", options.inFileName
    print "\tOutput to:", outFile
    print "\tMaximum angular velocity: %g radians/s (%g deg/s)" % ( options.velocity, options.velocity / np.pi * 180.0 )

    addSCBOrientation( options.inFileName, outFile, options.velocity, options.window )


if __name__ == '__main__':
    main()
    