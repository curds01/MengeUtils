# translate between julich and scb data formats

from julichData import JulichData
import scbData
import numpy as np
try:
    import fakeRotation
except ImportError:
    import sys
    sys.path.insert( 0, '../.' )
    import fakeRotation
from bound import AABB2D
from primitives import Vector2

# default location for undefined agents
DEF_X = -1000.0
DEF_Y = -1000.0

class DummyFrameSet:
    '''This class serves as a minimal scbData.FrameSet replacement for the
    purpose of writing out a frameSet.  It defines timestep and an empty
    set of ids so that the scb writer code can make the correct decisions.'''
    def __init__( self, timeStep, ids=[] ):
        self.simStepSize = timeStep
        self.ids = ids
        
def convert( inputName, outputName, undefined, version, maxAngVel, angleVelWindow ):
    '''Converts scb file to a corresponding julich trajectory file.

    @param      inputName       A string.  The name of the input julich file to convert.
    @param      outputName      A string.  The name of the output SCB
                                file to write to.
    @param      undefined       A 2-tuple of floats.  The location to place agents with undetermined
                                location.
    @param      version         A string.  The version of the scb file.
    @param      maxAngVel       A float.  The maximum allowed angular velocity.
    @param      angleVelWindow  An int.  The size of the window (in frames) over which angular velocity
                                is computed.
    @raises     OSError if the input file cannot be opened.
    '''
    print "Converting:"
    print "\t", inputName
    print "to"
    print "\t", outputName
    X, Y = undefined
    data = JulichData()
    try:
        data.readFile( inputName )
    except OSError:
        print '\n*** No file written!'
        print '*** Unable to read input file:', inputName, '***'
        return
    print data.summary()
    
    # determine the start and end positions for each agent.
    starts = []
    ends = []
    for ped in data.pedestrians:
        starts.append( ped.traj[0, :2] )
        ends.append( ped.traj[-1, :2] )

    starts = np.array( starts )
    ends = np.array( ends )
    disp = ends - starts
    dists = np.sqrt( np.sum( disp * disp, axis=1 ) )
    dists.shape = (-1, 1)
    disp /= dists
    starts -= disp * 1000
    ends += disp * 1000
        
    # now build data
    agtCount = data.agentCount()
    frameCount = data.totalFrames()
    outData = np.empty( ( agtCount, 3, frameCount ), dtype=np.float32 )
    data.setNext( 0 )

    hasEntered = np.zeros( agtCount, dtype=np.bool )
    
    while ( True ):
        try:
            frame, frameID = data.next()
        except StopIteration:
            break
        frameIDs = data.getFrameIds()
        # default position depends on whether it has entered the domain yet
        outData[ hasEntered, :2, frameID ] = ends[ hasEntered, : ]
        outData[ ~hasEntered, :2, frameID ] = starts[ ~hasEntered, : ]
        outData[ :, 2, frameID ] = 0.0 # orientation
        hasEntered[ frameIDs ] = True
        for i, id in enumerate( frameIDs ):
            outData[ id, :2, frameID ] = frame[ i, :2 ]

    # add orientation
    fakeRotation.addOrientation( outData, data.simStepSize * maxAngVel * angleVelWindow, angleVelWindow )
    
    # output file
    frameSet = DummyFrameSet( data.simStepSize )
    try:
        scbData.writeNPSCB( outputName, outData, frameSet, version )
    except ValueError as e:
        print "\n*** FILE NOT WRITTEN! ", e, '***'


if __name__ == '__main__':

    import optparse, sys
    parser = optparse.OptionParser()
    parser.set_description( 'Convert from julich to scb data' )
    parser.add_option( '-i', '--input', help='The input julich trajectory file.',
                       action='store', dest='inputName', default='' )
    parser.add_option( '-o', '--output', help='The output scb file.',
                       action='store', dest='outputName', default='' )
    parser.add_option( '-u', '--undefinedPos', help='The location to place agents when the position is undefined.  Defaults to <%.f, %.f>' % ( DEF_X, DEF_Y ),
                       nargs=2, action='store', type='float', dest='undefined', default=( DEF_X, DEF_Y ) )
    parser.add_option( '-v', '--version', help='The version of the scb file.  Valid values are: %s.  Default is %s' % ( scbData.SCBVersion.versionList(), scbData.SCBVersion.V2_0 ),
                       action='store', dest='version', default=scbData.SCBVersion.V2_1 )
    parser.add_option( '-a', '--angularVelocity', help='The maximum angular velocity for introducing orientation.  Default is %f' % fakeRotation.DEF_VEL_LIMIT,
                       action='store', type='float', dest='maxOmega', default=fakeRotation.DEF_VEL_LIMIT )
    parser.add_option( '-w', '--window', help='Number of frames overwhich to compute angular velocity.  This smooths the signal (default is 1)',
                       action='store', dest='window', type='int', default=1 )
    options, args = parser.parse_args()

    if ( options.inputName == '' ):
        parser.print_help()
        print '\n *** You must specify an input file.'
        sys.exit(1)

    if ( options.outputName == '' ):
        parser.print_help()
        print '\n *** You must specify an output file.'
        sys.exit(1)

    convert( options.inputName, options.outputName, options.undefined, options.version, options.maxOmega, options.window )
    