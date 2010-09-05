## Reads SCB data
from primitives import Vector2
import struct

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

class FrameSet:
    """A pseudo iterator for frames in an scb file"""
    def __init__( self, scbFile ):
        self.file = open( scbFile, 'rb' )
        data = self.file.read( 4 )
        print "SCB file version:", data
        data = self.file.read( 4 )
        self.agtCount = struct.unpack( 'i', data )[0]
        print "\t%d agents" % ( self.agtCount )
        self.frameSize = self.agtCount * 12 # three floats per agent, 4 bytes per float
        self.currFrameIndex = -1
        self.currFrame = None

    def next( self, updateFrame=None ):
        """Returns the next frame in sequence from current point"""
        self.currFrameIndex += 1
        if ( not updateFrame or self.currFrame == None):
            self.currFrame = Frame( self.agtCount )
        for i in range( self.agtCount ):
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
        return self.currFrame, self.currFrameIndex

    def setNext( self, index ):
        """Sets the set so that the call to next frame will return frame index"""
        if ( index < 0 ):
            index = 0
        self.currFrameIndex = index
        byteAddr = self.currFrameIndex * self.frameSize + 8      # +8 is the header offset
        self.file.seek( byteAddr )
        self.currFrameIndex -= 1
