# this script computes the consistency metric for a crowd simulation
#
#   Consistency measure the amount of variance in actual velocity w.r.t. preferred velocity
#   In practical simulation scenarios, agent's actual velocity will actually significantly diverge
#   from its preferred velocity -- that's why we have local collision avoidance mechanisms.
#   The question isn't, are they different, but are they consistently different?  This is a measure
#   of the consistency of the agent's response to smoothly varying neighbors.
#
#  The computation is done in the following manner:
#       INPUTS:
#           SCBFile with N agents over M frames
#           time window, T (seconds or frames--converted to frames for this discussion)
#           intermediate file path
#       1. Compute velocity deviation
#           - it is the displacement vector from preferred velocity to actual velocity transformed by
#            the same transformation which changes the preferred velocity to the vector <v_p, 0>, where the magnitude (v_p) is maintained
#           QUESTION: 
#           - the deviation is saved to a file: intermediate file path.deviation
#           - there will be one R2 vector per agent per frame.
#       2. Compute consistency
#           - Consistency is the variance in the deviation over the given time window
#           - for frame f in the range [T/2, M-T/2]
#               for agent a in the range [0, N)
#                   compute the principal components of the deviations for agent a in the time range [ f - T/2, f + T/2 ]
#           - save all of this to a file called: itnermediate file path.consistency
#       3. Correlate with density
#           - For frame f in the range [T/2, M-T/2]
#               for each agent
#                   Find the density at the agent's position, look up the consistency - stash that pair into a list: (density, consistency)
#           - save the pairs, plot the pairs, lump the pairs by density and compute averages on those bins...etc.
#           * This requires the density calculations in Crowd.py
#
# This script can be run directly on an scb file or the functions can be used by another tool.

# THESE ARE THE COLUMNS OF THE SCB 2.2 FILE FORMAT
POS_X = 0
POS_Y = 1
ORIENT = 2
CLASS = 3
VPREF_X = 4
VPREF_Y = 5
VEL_X = 6
VEL_Y = 7

from trajectory.scbData import NPFrameSet
import numpy as np
import os
import struct
from matplotlib import mlab
import warnings

class DataReader:
    '''Base class for reading a data file based on frames of agent data'''
    AGT_SIZE_BYTES = 24    # number of bytes per agent in a frame: 6 floats = 24 bytes
    AGT_SIZE_FLOATS = 6
    HEADER_SIZE = 12 # two ints: time window, agent count, frame count
    def __init__( self, fileName ):
        '''Opens the file, reads agent and frame count, and prepares for reading frames'''
        self.file = open( fileName, 'rb' )
        self.agtCount = 0
        self.frameCount = 0
        self.readHeader()
        
        self.frameSizeBytes = self.agtCount * self.AGT_SIZE_BYTES
        self.frameSizeFloats = self.agtCount * self.AGT_SIZE_FLOATS
        self.currIdx = 0
        self.currFrame = np.zeros( ( self.agtCount, self.AGT_SIZE_FLOATS ), dtype=np.float32 )

    def readHeader( self ):
        '''Reads the header information from the file'''
        raise NotImplementedError( "Sub-class must implement readHeader" )

    def setNext( self, index ):
        '''Sets the reading point in the file to the index'd frame'''
        assert( index < self.frameCount )
        byteAddr = self.HEADER_SIZE + index * self.frameSizeBytes
        self.file.seek( byteAddr, os.SEEK_SET )

    def next( self ):
        '''Reads the next frame, returns an Nx2 numpy array of the data.agentCount
        Note: this data will be replaced with each call to next, so if two frames need
        to be maintained indepdently, the results must be copied.

        Raises a StopIteration exception when there are no more frames'''
        if ( self.currIdx >= self.frameCount ):
            raise StopIteration
        s = self.file.read( self.frameSizeBytes )
        self.currFrame[ :, : ] = np.reshape( np.fromstring( s, np.float32, self.frameSizeFloats ), ( self.agtCount, self.AGT_SIZE_FLOATS ) )
        self.currIdx += 1
        return self.currFrame

class DataWriter:
    '''Base class for writing a data file based on frames of agent data'''
    def __init__( self, fileName ):
        '''Opens the file and reserves space for the agent count and the frame count'''
        self.file = open( fileName, 'wb' )
        self.writeHeaderBlock()

    def writeHeaderBlock( self ):
        '''Write the initial memory block in the file for header information'''
        raise NotImplementedError( "Sub-class must implement writeHeaderBlock" )
    
    def close( self ):
        self.file.close()

    def write( self, data ):
        '''Writes the frame of deviation data'''
        self.file.write( data.tostring() )    


# consistency correlation
#   I want to link correlation with density
#   For each agent, I compute the average density over the same time window the consistency
#       was computed.
#       A "consistency" score is basically going to be the area of the square with sides
#       equal to the sigma of the PCA
#   This goes into a single massive Qx2 array where Q = M * N, with N agents and M frames
#       (note that's M frames in the consistency file)
#   I can then take this MASSIVE data set and do the following:
#       1. plot all of it as data points (consistency on the y-axis, density on the x)
#       2. Clump it in bins based on density, and compute a bar plot based on the average
#           of each bin's contents.
#
#   - unknown
#       I should also be able to explore the kind of "inconsistency": speed, direction, etc.
#       How do I visualize this?

def correlateConsistency( config ):
    '''Computes the correlation between consistency and density'''
    pass

class ConsistencyReader( DataReader) :
    '''A class for reading the deviation file'''
    AGT_SIZE_BYTES = 24    # number of bytes per agent in a frame: 6 floats = 24 bytes
    AGT_SIZE_FLOATS = 6
    HEADER_SIZE = 12 # two ints: time window, agent count, frame count
    def __init__( self, fileName ):
        '''Opens the file, reads agent and frame count, and prepares for reading frames'''
        DataReader.__init__( self, fileName )
        
    def readHeader( self ):
        '''Reads the header information from the file'''
        self.file.seek( 0, os.SEEK_SET )
        self.T = struct.unpack( 'i', self.file.read( 4 ) )[ 0 ]
        self.agtCount = struct.unpack( 'i', self.file.read( 4 ) )[ 0 ]
        self.frameCount = struct.unpack( 'i', self.file.read( 4 ) )[ 0 ]

    def __str__( self ):
        return 'ConsistencyReader: %d agents in %d frames with T = %d' % ( self.agtCount, self.frameCount, self.T )

# consistency file format
#   HEADER:
#       window size, T, (in frames): integer (must be odd)
#       Number of agents, N: integer
#       number of frames, M: integer  -- note, this frame count will be T -1 fewer frames than
#           in the source deviation file.close
#   FRAME:
#       N x 6 numpy array of  consistency values
#           each row is an agent with the columns being:
#               x & y of first principal axis, x & y of second, first fraction of variance, second fraction

class ConsistencyWriter( DataWriter ):
    '''A class for managing the deviation file'''
    def __init__( self, fileName ):
        '''Opens the file and reserves space for the agent count and the frame count'''
        DataWriter.__init__( self, fileName )

    def writeHeaderBlock( self ):
        '''Write the initial memory block in the file for header information'''
        self.file.write( struct.pack( 'iii', 0, 0, 0 ) )

    def setWindowSize( self, window ):
        '''Sets the number of agents in the file and returns to end of file for continued appending'''
        self.file.seek( 0, os.SEEK_SET )
        self.file.write( struct.pack('i', window ) )
        self.file.seek( 0, os.SEEK_END )    # go to end of file

    def setAgentCount( self, agtCount ):
        '''Sets the number of agents in the file and returns to end of file for continued appending'''
        self.file.seek( 4, os.SEEK_SET )
        self.file.write( struct.pack('i', agtCount ) )
        self.file.seek( 0, os.SEEK_END )    # go to end of file

    def setFrameCount( self, frameCount ):
        '''Sets the number of frames in the file and returns to end of file for continued appending'''
        self.file.seek( 8, os.SEEK_SET )
        self.file.write( struct.pack('i', frameCount ) )
        self.file.seek( 0, os.SEEK_END )    # go to end of file
        
def consistencyFile( config ):
    '''Given the config specifications, creates the file for storing consistency
    Returns the file object.'''
    outPath = config[ 'tempDir' ]
    if ( not os.path.exists( outPath ) ):
        os.makedirs( outPath )
    return os.path.join( outPath, config[ 'tempName' ] + '.consistency' )

def computeConsistency( config ):
    '''Computes the consistency, assuming that the deviation has already been computed'''
    try:
        devFile = DeviationReader( deviationFile( config ) )
    except:
        raise IOError( "Unable to load the deviation file for computing consistency" )

    T = int( config[ 'consistencyWindow' ] )
    if ( T % 2 != 1 and T <= 0 ):
        raise ValueError( "The window size for consistency calculation must be positive and odd.  Given %d." % T )
    if ( T > devFile.frameCount ):
        raise ValueError( "The consistency window size is larger than the number of frames: T = %d, frame count = %d" % ( T, devFile.frameCount) )

    conFile = ConsistencyWriter( consistencyFile( config ) )    
    conFile.setWindowSize( T )
    conFile.setAgentCount( devFile.agtCount )
    
    print "\nCONSISTENCY"
    print "\tWindow:", T
    print "\tTotal frames:", devFile.frameCount
    print "\tTotal agents:", devFile.agtCount
    deviations = np.zeros( ( devFile.agtCount, 2, T ), dtype=np.float32 )
    print "\tLoading %d deviations:" % ( T )
    for t in xrange( T ):
        # no need to put this in a try block, because I know that I will be able to read all of these.
        deviations[ :, :, t ] = devFile.next()
        print "\t\t", deviations[:,:,t]

    replaceID = 0
    consistency = np.zeros( ( devFile.agtCount, 6 ), dtype=np.float32 )
    print "\tComputing consistency"
    count = 0
    while ( True ):
        # The PCA class performs the mean for me -- in fact, I can't stop it.
        #   So, although I'm sure it would be cheaper to compute the mean myself in one huge
        #   block, I can't stop PCA from doing so.
        # NOTE: Not currently using PCA because I can't figure out what the damn AXES are
        mean = deviations.mean( axis=2 )
        print "\t\tMean:", mean
        mean.shape = ( -1, 2, 1 )
        centered = deviations - mean
        for a in xrange( devFile.agtCount ):
##            p = mlab.PCA( centered[ a, :, : ].T )
##            print p.Wt
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                components, trace, fracVar = mlab.prepca( centered[ a, :, : ].T )
                sig2 = np.sqrt( np.sum( components ** 2, axis=1 ) )
                sig = np.sqrt( sig2 )
                a0 = components[0] / sig[0]
                a1 = components[1] / sig[1]
                consistency[ a, :2 ] = a0
                consistency[ a, 2:4 ] = a1
                consistency[ a, 4: ] = fracVar
        conFile.write( consistency )
        count += 1
        try:
            deviations[ :, :, replaceID ] = devFile.next()
        except StopIteration:
            break
        else:
            replaceID = ( replaceID + 1 ) % T
    conFile.setFrameCount( count )
    conFile.close()
        
    
# deviation file format
#   HEADER:
#       agent count: integer
#       frame count: integer
#   FRAME
#       N x 2 numpy array of deviation values (where N = agent count)
#           each row is an agent, with the columns being the x & y components of deviation
#
#   Deviation is the offset from preferred velocity to actual velocity, rotated
#       by the transform that would make preferred velocity align with the positive x-axis
#
#   \V{d} & = & R_{v^{0}} \V{v} - \V{v}^0
#   R_{v^{0}} & = & \left[ \begin{array}{cc} \hat{v}^0_x & \hat{v}^0_y\\ -\hat{v}^0_y & \hat{v}^0_x \end{array} \right].
#   \hat{v}^0 & = & \frac{ \V{v}^0 }{ |\\V{v}^0\|}

class DeviationReader( DataReader ):
    '''A class for reading the deviation file'''
    AGT_SIZE_BYTES = 8      # number of bytes per agent in a frame: 2 floats = 8 bytes
    AGT_SIZE_FLOATS = 2
    HEADER_SIZE = 8         # two ints: agent count, frame count
    def __init__( self, fileName ):
        '''Opens the file, reads agent and frame count, and prepares for reading frames'''
        DataReader.__init__( self, fileName )

    def readHeader( self ):
        '''Reads the header information from the file'''
        self.file.seek( 0, os.SEEK_SET )
        self.agtCount = struct.unpack( 'i', self.file.read( 4 ) )[ 0 ]
        self.frameCount = struct.unpack( 'i', self.file.read( 4 ) )[ 0 ]

    def __str__( self ):
        return 'DeviationReader: %d agents in %d frames' % ( self.agtCount, self.frameCount )
    
        
class DeviationWriter( DataWriter ):
    '''A class for managing the deviation file'''
    def __init__( self, fileName ):
        '''Opens the file and reserves space for the agent count and the frame count'''
        DataWriter.__init__( self, fileName )

    def writeHeaderBlock( self ):
        '''Write the initial memory block in the file for header information'''
        self.file.write( struct.pack( 'ii', 0, 0 ) )

    def setAgentCount( self, agtCount ):
        '''Sets the number of agents in the file and returns to end of file for continued appending'''
        self.file.seek( 0, os.SEEK_SET )
        self.file.write( struct.pack('i', agtCount ) )
        self.file.seek( 0, os.SEEK_END )    # go to end of file

    def setFrameCount( self, frameCount ):
        '''Sets the number of frames in the file and returns to end of file for continued appending'''
        self.file.seek( 4, os.SEEK_SET )
        self.file.write( struct.pack('i', frameCount ) )
        self.file.seek( 0, os.SEEK_END )    # go to end of file

def deviationFile( config ):
    '''Given the config specifications, returns the name of the deviation file'''
    outPath = config[ 'tempDir' ]
    if ( not os.path.exists( outPath ) ):
        os.makedirs( outPath )
    return os.path.join( outPath, config[ 'tempName' ] + '.deviation' )

def computeDeviation( scbData, config ):
    '''Given a set of scbData and a config file, computes the deviation and caches it in an intermediate file'''
    file = DeviationWriter( deviationFile( config ) )
        
    scbData.setNext( 0 )    # don't assume I'm at the beginning

    agtCount = scbData.agentCount()
    file.setAgentCount( agtCount )
    # pre-allocate arrays to save time
    displacement = np.zeros( (agtCount,2), dtype=np.float32 )
    prefSpeed = np.zeros( (agtCount, 1), dtype=np.float32 )
    xform = np.zeros( (agtCount, 2), dtype=np.float32 )
    deviation = np.zeros( (agtCount, 2), dtype=np.float32 )
    frameCount = 0
    print "\nDEVIATION"
    print "\t%d agents:" % agtCount
    while ( True ):
        try:
            frame, idx = scbData.next()
        except StopIteration:
            break
        displacement[:,:] = frame[:, VEL_X:] - frame[:, VPREF_X:VEL_X]
        # transform deviation
        prefSpeed[:] = np.sqrt( frame[:,VPREF_X:VPREF_Y] ** 2 + frame[:,VPREF_Y:VEL_X] ** 2 )
        xform[:,:] = frame[:, VPREF_X:VEL_X ] / prefSpeed
        deviation[:,0] = displacement[:,0] * xform[:,0] + displacement[:,1] * xform[:,1]
        deviation[:,1] = displacement[:,1] * xform[:,0] - displacement[:,0] * xform[:,1]
        file.write( deviation )
        print '\t',deviation
        frameCount += 1
    file.setFrameCount( frameCount )
    file.close()


def processConsistency( config, scbFile=None ):
    '''Performs the work of deviation from data in the config file, with an optional
    override on the scbFile to process'''
    
    if ( scbFile == None ):
        scbFile = config[ 'SCB' ]
        
    # TODO: ultimately extract start, max frames, max agents, target agent, frame sample from config
    try:
        # TODO: for testing purposes, I've got these arguments to facilitate testing
##        data = NPFrameSet( scbFile )
        data = NPFrameSet( scbFile, startFrame=5, maxFrames=15, maxAgents=1 )
    except IOError:
        raise IOError( 'No such scb file: %s' % ( scbFile ) )
    except:
        raise IOError("Unable to read scb file: %s" % ( scbFile ) )

    if ( data.version != '2.2' ):
        raise ValueError( 'Can only perform consistency analysis on scb version 2.2. Indicated scb file is version %s' % ( data.version ) )

    print "SCB file: ", scbFile
    print "\tNumber of agents:", data.agentCount()

    # compute the deviation, producing a .deviation file
    computeDeviation( data, config )
    # compute the consistency, producing a .consistency file
    computeConsistency( config )
    # compute correlation between density and consistency
    correlateConsistency( config )

def main():
    from config import Config
    import sys
    import optparse
    parser = optparse.OptionParser()
    parser.set_description( 'Evaluate consistency of agent simulation' )
    parser.add_option( '-c', '--config', help='The config file to load giving analysis configuration (required)',
                       action='store', dest='configFileName', default='' )
    parser.add_option( '-s', '--scbFile', help='The scb file to analyze (if not specified, the scb file in the config file is processed)',
                       action='store', dest='scbFileName', default=None )
    options, args = parser.parse_args()

    if ( options.configFileName == '' ):
        print "\n!!! Requires an analysis configuration file to be specified with -c/--config"
        parser.print_help()
        sys.exit(1)

    config = Config()
    try:
        f = open( options.configFileName, 'r' )
        config.fromFile( f )
    except IOError:
        print "\n!!! No such configuration file: %s" % ( options.configFileName )
        parser.print_help()
        config = None
    except:
        print "\n!!! Unable to read configuration file: %s" % ( options.configFileName )
        parser.print_help()
        config = None

    f.close()
    if ( config == None ):
        sys.exit(1)

    processConsistency( config, options.scbFileName )
##    try:
##        processConsistency( config, options.scbFileName )
##    except Exception as inst:
##        print "Error processing consistency!"
##        print inst
    

if __name__ == '__main__':
    main()