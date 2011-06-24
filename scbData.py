## Reads SCB data
from primitives import Vector2
import struct
import numpy as np

class Agent:
    """Basic agent class"""
    def __init__( self, position ):
        self.pos = position             # a Vector2 object
        self.vel = None
        self.value = 0.0                # a per-agent value which can be rasterized

    def __str__( self ):
        return '%s' % ( self.pos )

    def setPosition( self, pos ):
        self.pos = pos

class Frame:
    """A set of agents for a given time frame"""
    def __init__( self, agentCount ):
        self.agents = []
        self.setAgentCount( agentCount )

    def setAgentCount( self, agentCount ):
        """Sets the number of agents in the frame"""
        self.agents = [ Agent( Vector2(0,0) ) for i in range( agentCount ) ]
        
    def __str__( self ):
        s = 'Frame with %d agents' % ( len(self.agents) )
        for agt in self.agents:
            s += '\n\t%s' % agt
        return s

    def setPosition( self, i, pos ):
        self.agents[ i ].pos = pos

    def computeVelocity( self, prevFrame, dt ):
        """Computes the velocity for each agent based ona previous frame"""
        for i, agent in enumerate( self.agents ):
            agent.vel = ( agent.pos - prevFrame.agents[ i ].pos ) / dt

    def getPosition( self, i ):
        return self.agents[ i ].pos

    def numpyArray( self, _type=np.float32 ):
        """Returns the data as an NX2 numpy array"""
        data = np.empty( (len( self.agents ), 2 ), dtype=_type )
        for i, agt in enumerate( self.agents ):
            data[i,0] = agt.pos.x
            data[i,1] = agt.pos.y
        return data

class FrameSet:
    """A pseudo iterator for frames in an scb file"""
    def __init__( self, scbFile, maxFrames=-1, maxAgents=-1, frameStep=1 ):
        """Initializes an interator for walking through a an scb file.close
        By default, it creates a frame for every frame in the scb file, each
        frame consisting of all agents.
        Optional arguments can reduce the number of framse as well as number of agents.
        maxFrames limits the total number of frames output.
        maxAgents limits the total number of agents per frame.
        frameStep dictates the stride of between returned frames."""
        # TODO: self.maxFrames isn't currently USED!!!
        # version 2.0 data
        self.ids = []       # in scb2.0 we support ids for each agent.
        self.simStepSize = -0.1
        # generic attributes
        if ( maxFrames == -1 ):
            self.maxFrames = 0x7FFFFFFF
        else:
            self.maxFrames = maxFrames
        self.file = open( scbFile, 'rb' )
        self.version = self.file.read( 4 )
        print "SCB file version:", self.version
        if ( self.version == '1.0\x00' ):
            self.readHeader1_0( scbFile )
        elif ( self.version == '2.0\x00' ):
            self.readHeader2_0( scbFile )
        else:
            raise AttributeError, "Unrecognized scb version: %s" % ( version )
        
        self.readAgtCount = self.agtCount
        # this is how many bytes need to be read to get to the next frame
        # after reading self.readAgtCount agents worth of data
        self.readDelta = 0
        if ( maxAgents > 0 and maxAgents < self.agtCount ):
            self.readAgtCount = maxAgents
            # number of unread agents * size of agent (12 bytes)
            self.readDelta = ( self.agtCount - maxAgents ) * 12
        print "\t%d agents" % ( self.agtCount )
        # this is the size of the frame in the scbfile (and doesn't necessarily reflect how many
        # agents are in the returned frame.
        self.frameSize = self.agtCount * 12 # three floats per agent, 4 bytes per float
        self.strideDelta = ( frameStep - 1 ) * self.frameSize
        self.currFrameIndex = -1
        self.currFrame = None

    def readHeader1_0( self, scbFile ):
        '''Reads the header for a version 1.0 scb file'''
        data = self.file.read( 4 )
        self.agtCount = struct.unpack( 'i', data )[0]

    def readHeader2_0( self, scbFile ):
        '''Reads the header for a version 1.0 scb file'''
        data = self.file.read( 4 )
        self.agtCount = struct.unpack( 'i', data )[0]
        self.ids = [ 0 for i in range( self.agtCount ) ]
        data = self.file.read( 4 )
        self.simStepSize = struct.unpack( 'f', data )[0]
        for i in range( self.agtCount ):
            data = self.file.read( 4 )
            self.ids[ i ] = struct.unpack( 'i', data )[0]

    def headerOffset( self ):
        '''Reports the number of bytes for the header'''
        if ( self.version == '1.0\x00' ):
            return 8
        elif ( self.version == '2.0\x00' ):
            return 8 + 4 + 4 * self.agtCount
        raise ValueError, "Can't compute header for version: %s" % ( self.version )

    def next( self, updateFrame=None ):
        """Returns the next frame in sequence from current point"""
        if ( self.currFrameIndex >= self.maxFrames ):
            return None, self.currFrameIndex
        self.currFrameIndex += 1
        if ( not updateFrame or self.currFrame == None):
            self.currFrame = Frame( self.readAgtCount )
        for i in range( self.readAgtCount ):
            data = self.file.read( 12 ) # three 4-byte floats
            if ( data == '' ):
                self.currFrame = None
                break
            else:
                try:
                    x, y, o = struct.unpack( 'fff', data )                  
                    self.currFrame.setPosition( i, Vector2( x, y ) )
                except struct.error:
                    self.currFrame = None
                    break
        # seek forward based on skipping
        self.file.seek( self.readDelta, 1 ) # advance to next frame
        self.file.seek( self.strideDelta, 1 ) # advance according to stride
        
        return self.currFrame, self.currFrameIndex

    def setNext( self, index ):
        """Sets the set so that the call to next frame will return frame index"""
        if ( index < 0 ):
            index = 0
        # TODO: if index > self.maxFrames
        self.currFrameIndex = index
        byteAddr = self.currFrameIndex * self.frameSize + self.headerOffset()      # +8 is the header offset
        self.file.seek( byteAddr )
        self.currFrameIndex -= 1

    def totalFrames( self ):
        """Reports the total number of frames in the file"""
        # does this by scanning the whole file
        currentPos = self.file.tell()
        #TODO: make this dependent on the version
        self.file.seek( 8 ) # scan to the end of the head
        frameCount = 0
        data = self.file.read( self.frameSize )
        while ( len( data ) == self.frameSize ):
            frameCount += 1
            self.file.seek( self.readDelta, 1 ) # advance to next frame
            self.file.seek( self.strideDelta, 1 ) # advance according to stride
            data = self.file.read( self.frameSize )
        self.file.seek( currentPos )

        if ( frameCount > self.maxFrames ):
            return self.maxFrames
        else:
            return frameCount

    def agentCount( self ):
        '''Returns the agent count'''
        # NOTE: it returns the number of read agents, not total agents, in case
        #   I'm only reading a sub-set
        return self.readAgtCount
        
class NPFrameSet( FrameSet ):
    """A frame set that uses numpy arrays instead of frames as the underlying structure"""
    def __init__( self, scbFile, maxFrames=-1, maxAgents=-1, frameStep=1 ):
        FrameSet.__init__( self, scbFile, maxFrames, maxAgents, frameStep )

    def next( self, updateFrame=None ):
        """Returns the next frame in sequence from current point"""
        self.currFrameIndex += 1
        if ( not updateFrame or self.currFrame == None):
            self.currFrame = np.empty( ( self.readAgtCount, 3 ), dtype=np.float32 )
        try:
            self.currFrame[:,:] = np.reshape( np.fromstring( self.file.read( self.frameSize ), np.float32, self.readAgtCount * 3 ), ( self.readAgtCount, 3 ) )
            # seek forward based on skipping
            self.file.seek( self.readDelta, 1 ) # advance to next frame
            self.file.seek( self.strideDelta, 1 ) # advance according to stride
        except ValueError:
            # this will happen when the file runs out
            self.setNext( 0 )
            self.currFrameIndex = 1
            self.currFrame[:,:] = np.reshape( np.fromstring( self.file.read( self.frameSize ), np.float32, self.readAgtCount * 3 ), ( self.readAgtCount, 3 ) )
            # seek forward based on skipping
            self.file.seek( self.readDelta, 1 ) # advance to next frame
            self.file.seek( self.strideDelta, 1 ) # advance according to stride
        
        return self.currFrame, self.currFrameIndex

    def fullData( self ):
        """Returns an N X 3 X K array consisting of all trajectory info for the frame set"""
        frameCount = self.totalFrames()
        data = np.empty( ( self.readAgtCount, 3, frameCount ) )
        self.setNext( 0 )
        for i in range( frameCount ):
            frame, idx = self.next()
            data[ :, :, i ] = frame
        return data

def writeNPSCB( fileName, array, frameSet, version=1 ):
    """Given an N X 3 X K array, writes out an scb file with the given data"""
    print "Writing %s with %d agents and %d frames" % ( fileName, array.shape[0], array.shape[2] )
    print "Writing version %.1f" % ( version )
    if ( version == 1 ):
        _writeNPSCB_1_0( fileName, array )
    elif ( version == 2 ):
        _writeNPSCB_2_0( fileName, array, frameSet )
    else:
        raise Exception, "Invalid write version for data: %s" % ( version )
    

def _writeNPSCB_1_0( fileName, array ):
    """Given an N X 3 X K array, writes out a version 1.0 scb file with the given data"""
    f = open( fileName, 'wb' )
    f.write( '1.0\x00' )
    f.write( struct.pack( 'i', array.shape[0] ) )
    for frame in range( array.shape[2] ):
        f.write( array[:,:,frame].tostring() )
    f.close()

def _writeNPSCB_2_0( fileName, array, frameSet ):
    """Given an N X 3 X K array, writes out a version 1.0 scb file with the given data"""
    f = open( fileName, 'wb' )
    f.write( '2.0\x00' )
    agtCount = array.shape[0]
    f.write( struct.pack( 'i', agtCount ) )   # agent count
    
    if ( frameSet.simStepSize < 0 ):
        print 'Frame set was version 1.0, using default sim step size: 0.1'
        f.write( struct.pack( 'f', 0.1 ) )   # sim step size
    else:
        f.write( struct.pack( 'f', frameSet.simStepSize ) )   # sim step size

    # agent ids
    if ( frameSet.ids ):
        # this assertion won't be true if I'm sub-sampling the agents!
        assert( len( frameSet.ids ) == agtCount )
        for id in frameSet.ids:
            f.write( struct.pack( 'i', id ) )
    else:
        print 'Frame set was version 1.0, assigning every agent id 0'
        for i in range( agtCount ):
            f.write( struct.pack( 'i', 0 ) )
            
    # now write the data
    for frame in range( array.shape[2] ):
        f.write( array[:,:,frame].tostring() )
    f.close()



    
def testNP():
    """Tests the NPFrameSet's functionality with the baseline frameset"""
    # loads all of the data into a numpy array and then compares it with
    #   the normal frameset's data step by step.
    #   The comparision is by checks the squared distance between what each
    #   set read in for each agent.
    import sys    
    f = sys.argv[1]
    f1 = FrameSet( f )
    f2 = NPFrameSet( f )

    frame, idx = f1.next()
    fullData = f2.fullData()

    for i in range( fullData.shape[2] ):
        error = 0
        for a in range( f1.readAgtCount ):
            error += np.sum( np.array( [ frame.agents[a].pos.x - fullData[a,0,i], frame.agents[a].pos.y - fullData[a,1,i] ] ) ** 2 )
        frame, idx = f1.next()
        if ( error > 1e-5 ):
            print "Error on frame %d: %f" % ( i + 1, error )
        
if __name__ == '__main__':
    testNP()
    
