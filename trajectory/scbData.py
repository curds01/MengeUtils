## Reads SCB data
try:
    from primitives import Vector
except ImportError:
    import sys
    OBJ_READER_PATH = '../.'
    if ( not OBJ_READER_PATH in sys.path ):
        sys.path.insert( 0, OBJ_READER_PATH )
    from primitives import Vector2
import os
import struct
import numpy as np
import commonData

class SCBVersion:
    V1 = '1.0'
    V2_0 = '2.0'
    V2_1 = '2.1'
    V2_2 = '2.2'
    V2_3 = '2.3'
    V2_4 = '2.4'
    VERSIONS = [ V1, V2_0, V2_1, V2_2, V2_3, V2_4 ]

    @staticmethod
    def versionList():
        '''Return a list of valid versions'''
        return ', '.join( SCBVersion.VERSIONS )
    
class SCBError( Exception ):
    pass

# In order for the scbData to offer the same interface as the trajectories from Julich,
# where each frame can consist of a DIFFERENT number of agents, for each frame generated,
#   a mapping from their index in the frame to their global identifier is provided.
#   In the case of the scbData, it the ids identical.  So, this class simply reflects back
#   the index when accessed.  (i.e. ids[i] returns i
class IDMap:
    '''Maps the frame index to the full simulation index'''
    def __init__( self, agentCount ):
        '''Constructor for the IDMap.  Serves as a read-only, dictionary-like
        object for pinging back the agent identifiers.

        @param      agentCount      An int.  The number of agents in the set.
        '''
        self.agtCount = agentCount
        self.currAgent = 0

    def __iter__( self ):
        '''Treats this as its own iterator.

        Resets the map to the beginning of the set (i.e. -1) and returns
        itself.
        '''
        self.currAgent = -1
        return self

    def next( self ):
        '''Returns the next agent id in the set.

        @returns        An int.  The id of the next agent.pos
        @raises     StopIteration when it has been called self.agtCount times.
        '''
        self.currAgent += 1
        if ( self.currAgent >= self.agtCount ):
            raise StopIteration
        return self.currAgent
    
    def __getitem__( self, i ):
        '''The id map echoes the index of the position back as the id.  This assumes
        that every frame has data for every agent.pos

        @param      i       An overloaded type.  It represents a selector
                            
        @returns    An int.  The id of the agent.  In this case, it's the same.
        '''
        if ( isinstance( i, np.ndarray ) ):
            if ( i.dtype == np.bool ):
                if ( i.size <= self.agtCount ):
                    return np.where( i )
                else:
                    raise ValueError, "Selection boolean array is too large - given %d elements for %d agents" % ( i.size, self.agtCount )
            else:
                raise ValueError, "Only arrays of bool type can index into an IDMap"
        if ( isinstance(i, int ) and ( i >= self.agtCount ) ):
            return KeyError, "Invalid agent index: %s" % str( i )
        return i
    
class Agent:
    """Basic agent class"""
    def __init__( self, position ):
        self.pos = position             # a Vector2 object
        self.vel = None
        self.value = 0.0                # a per-agent value which can be rasterized
        self.state = 0

    def __str__( self ):
        return '%s' % ( self.pos )

    def setPosition( self, pos ):
        self.pos = pos

    def toBinary( self, version ):
        '''Returns a binary string representing this agent'''
        # ORIENTATION GETS LOST
        return struct.pack( 'fff', self.pos.x, self.pos.y, 0.0 )

class Frame:
    """A set of agents for a given time frame"""
    def __init__( self, agentCount ):
        self.agents = []
        self.setAgentCount( agentCount )

    def ids( self ):
        return IDMap()

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

    def toBinary( self, version, agent=-1 ):
        '''Produces a binary string of the data in this frame'''
        if ( agent > -1 ):
            return self.agents[ agent ].toBinary( version )
        else:
            s = ''
            for agt in self.agents:
                s += agt.toBinary( version )
            return s

class FrameSet:
    """A pseudo iterator for frames in an scb file"""
    def __init__( self, scbFile, startFrame=0, maxFrames=-1, maxAgents=-1, frameStep=1, agtStep=1, verbose=False ):
        """Initializes an interator for walking through an scb file.
        By default, it creates a frame for every frame in the scb file, each
        frame consisting of all agents.
        Optional arguments can reduce the number of framse as well as number of agents.
        maxFrames limits the total number of frames output.
        maxAgents limits the total number of agents per frame.
        frameStep dictates the stride of between returned frames.
        agtStep dictates the stride between selected agents.
        """
        # TODO: self.maxFrames isn't currently USED!!!
        # version 2.0 data
        self.is3D = False
        self.hasScalarOrient = True
        if ( not self.isValid( scbFile ) ):
            raise SCBError
        self.ids = []       # in scb2.0 we support ids for each agent.
        self.simStepSize = 0.1
        self.startFrame = startFrame
        # generic attributes
        if ( maxFrames == -1 ):
            self.maxFrames = 0x7FFFFFFF
        else:
            self.maxFrames = maxFrames
        self.file = open( scbFile, 'rb' )
        self.version = self.file.read( 4 )[:-1]
        if verbose:
            print "SCB file version:", self.version
        if ( self.version == SCBVersion.V1 ):
            self.readHeader1_0( scbFile )
        elif ( self.version == SCBVersion.V2_0 ):
            self.readHeader2_0( scbFile )
        elif ( self.version == SCBVersion.V2_1 ):
            self.readHeader2_1( scbFile )
        elif ( self.version == SCBVersion.V2_2 ):
            self.readHeader2_2( scbFile )
        elif ( self.version == SCBVersion.V2_3 ):
            self.readHeader2_3( scbFile )
        elif ( self.version == SCBVersion.V2_4 ):
            self.readHeader2_4( scbFile )
        else:
            raise AttributeError, "Unrecognized scb version: %s" % ( version )

        self.effectiveTimeStep = self.simStepSize * frameStep
        self.readAgtStride = agtStep
        selectableCount = self.agtCount / self.readAgtStride
        self.readAgtCount = selectableCount
        # this is how many bytes need to be read to get to the next frame
        # after reading self.readAgtCount agents worth of data
        self.readDelta = 0
        if verbose:
            print "Original file has %d agents" % ( self.agtCount )
        # number of bytes necessary to read one agent's worth of data
        self.singleAgentRead = self.agentByteSize * self.readAgtStride
        if ( maxAgents > 0 and maxAgents < selectableCount ):
            self.readAgtCount = maxAgents
            # number of unread agents * size of agent
            self.readDelta = ( self.agtCount - maxAgents ) * self.singleAgentRead
            if verbose:
                print "\tReading only %d agents" % ( self.readAgtCount )
                print "\tAgent byte size:", self.agentByteSize
                print "\tReading every %d-th agents" % ( self.readAgtStride )
                print "\tBlock of memory, per frame, not read:", self.readDelta
        # this is the size of the frame in the scbfile (and doesn't necessarily reflect how many
        # agents are in the returned frame.
        self.frameSize = self.agtCount * self.agentByteSize
        self.readFrameSize = self.readAgtCount * self.singleAgentRead
        if verbose:
            print "\tFull frame size:", self.frameSize, "bytes"
            print "\tRead frame size:", self.readFrameSize, "bytes"
        self.strideDelta = ( frameStep - 1 ) * self.frameSize
        self.agentDelta = self.frameSize - self.readFrameSize
        if verbose:
            print "\tFrame stride size:    ", self.strideDelta, "bytes"
            print "\tAgent stride size:    ", self.agentDelta, "bytes"
        self.currFrame = None
        self.setNext( 0 )
        if ( verbose ):
            print "\nNPFRAMESET"
            print "\tTotal agents:", self.agtCount
            print "\tAgent stride:", self.readAgtStride
            print "\tNumber of agents to read:", self.readAgtCount
            print "\tBytes per agent:", self.agentByteSize
            print "\tBytes to read to get single agent:", self.singleAgentRead
            print "\tNumber of agents to read with stride", self.readAgtStride * self.readAgtCount
            print "\tFull frame size (in bytes):", self.frameSize
            print "\tNumber of bytes to read for each agent:", self.readFrameSize
            print "\tBytes left over (in frame):", self.agentDelta        

    def getType( self ):
        '''Returns the identifier for this type of trajectory data.

        @returns        An enumeration representing the Julichd ata.
        '''
        return commonData.SCB_DATA
    
    @staticmethod
    def isValid( fileName ):
        '''Reports if the given file is an scb file.

        @param      fileName        A string.  The name of the file to check.
        @returns    A boolean.  True if the first four bytes of the file conform to a
                    valid scb data file format (i.e. the scb version number.)
        '''
        with open( fileName, 'rb' ) as f:
            data = f.read( 4 )
            version = data[:-1]
            return version in SCBVersion.VERSIONS and data[-1] == '\x00'

    def summary( self ):
        '''Creates a simple summary of the trajectory data'''
        s = 'SCB Trajectory data'
        s += '\n\t%d pedestrians' % self.agentCount()
        s += '\n\t%d frames of  data' % self.totalFrames()
        return s
    
    def readHeader1_0( self, scbFile ):
        '''Reads the header for a version 1.0 scb file'''
        data = self.file.read( 4 )
        self.agtCount = struct.unpack( 'i', data )[0]
        self.ids = [ 0 for i in range( self.agtCount ) ]
        # three floats per agent, 4 bytes per float
        self.agentByteSize = 12

    def readHeader2_0( self, scbFile ):
        '''The 2.1 version is just like the 2.0 version.  However, the per-agent data consists of FOUR values:
            1. float: x position
            2. float: y position
            3. float: orientation
            
            The header information is exactly the same.
        '''
        data = self.file.read( 4 )
        self.agtCount = struct.unpack( 'i', data )[0]
        self.ids = [ 0 for i in range( self.agtCount ) ]
        data = self.file.read( 4 )
        self.simStepSize = struct.unpack( 'f', data )[0]
        for i in range( self.agtCount ):
            data = self.file.read( 4 )
            self.ids[ i ] = struct.unpack( 'i', data )[0]
        # three floats per agent, 4 bytes per float
        self.agentByteSize = 12

    def readHeader2_1( self, scbFile ):
        '''The 2.1 version is just like the 2.0 version.  However, the per-agent data consists of FOUR values:
            1. float: x position
            2. float: y position
            3. float: orientation
            4. float: state  (although it is an integer value)
            
            The header information is exactly the same.
        '''
        self.readHeader2_0( scbFile )
        self.agentByteSize = 16

    def readHeader2_2( self, scbFile ):
        '''The 2.2 header is the same as 2.0  But the per-agent data is SIGNIFICANTLY
        different:
            1. float: x position
            2. float: y position
            3. float: orientation angle
            4. float: state  (although it is an integer value)
            5. float: pref vel x
            6. float: pref vel y
            7. float: vel x
            8. float: vel y
        '''
        self.readHeader2_0( scbFile )
        self.agentByteSize = 32

    
    def readHeader2_3( self, scbFile ):
        '''The 2.3 header is the same as 2.0.  But the per-agent data is a bit different
        from 2.0.  The orientation orientation representation is changed.
        Instead of an angle, it's a normalized direction vector.
        The per-agent data consists of FOUR values:
            1. float: x position
            2. float: y position
            3. float: orientation x
            4. float: orientation y
            
            The header information is exactly the same.
        '''
        self.hasScalarOrient = False
        self.readHeader2_0( scbFile )
        self.agentByteSize = 16

    def readHeader2_4( self, scbFile ):
        '''The 2.4 header is the same as 2.0.  But the per-agent data is a bit different
        from 2.0; the trajectory is 3D.  The trajectories are defined in a y-up world.
        The per-agent data consists of FOUR values:
            1. float: x position
            2. float: y position    (the elevation)
            3. float: z position    (the y position in previous versions)
            4. float: orientation   (in radians)
            
            The header information is exactly the same.
        '''
        self.is3D = True
        self.readHeader2_0( scbFile )
        self.agentByteSize = 16

    def getClasses( self ):
        '''Returns a dictionary mapping class id to each agent with that class'''
        ids = {}
        for i, id in enumerate( self.ids ):
            if ( not ids.has_key( id ) ):
                ids[ id ] = [ i ]
            else:
                ids[ id ].append( i )
        return ids

    def headerOffset( self ):
        '''Reports the number of bytes for the header'''
        majorVersion = self.version.split('.')[0]
        if ( majorVersion == '1' ):
            return 8
        elif ( majorVersion == '2' ):
            return 8 + 4 + 4 * self.agtCount
        elif ( majorVersion == '3' ):
            return 8 + 4 + 4 * self.agtCount
        raise ValueError, "Can't compute header for version: %s" % ( self.version )

    def next( self, stride=1, newInstance=True ):
        """Returns the next frame in sequence from current point"""
        if ( self.currFrameIndex >= self.maxFrames - 1 ):
            raise StopIteration
        self.currFrameIndex += stride
        if ( newInstance or self.currFrame == None):
            self.currFrame = Frame( self.readAgtCount )
        for i in range( 0, self.readAgtCount, self.readAgtStride ):
            data = self.file.read( self.singleAgentRead )
            if ( data == '' ):
                self.currFrame = None
                raise StopIteration
            else:
                try:
                    if ( self.agentByteSize == 12 ):
                        x, y, o = struct.unpack( 'fff', data )
                    elif ( self.agentByteSize == 16 ):
                        x, y, o, s = struct.unpack( 'ffff', data )
                        self.currFrame.agents[i].pos = Vector2( x, y )
                        self.currFrame.agents[i].state = s
                except struct.error:
                    self.currFrame = None
                    raise StopIteration
                
        # seek forward based on skipping
        self.file.seek( self.agentDelta, 1 ) # advance to next frame
        self.file.seek( self.strideDelta, 1 ) # advance according to stride
        return self.currFrame, self.currFrameIndex

    def setNext( self, index ):
        """Sets the set so that the call to next frame will return frame index"""
        if ( index < 0 ):
            index = 0
        # TODO: if index > self.maxFrames
        self.currFrameIndex = index
        byteAddr = ( self.startFrame + self.currFrameIndex ) * self.frameSize + self.headerOffset()
        self.file.seek( byteAddr )
        self.currFrameIndex -= 1

    def totalFrames( self ):
        """Reports the total number of frames in the file"""
        # does this by scanning the whole file
        currentPos = self.file.tell()
        self.setNext( 0 )
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
    
    def hasStateData( self ):
        '''Reports if the scb data contains state data'''
        #TODO: This might evolve
        return self.version == SCBVersion.V2_1 or self.version == SCBVersion.V2_2

    def getHeader( self, targetAgent=-1 ):
        '''Returns a binary string representing the header of this data set'''
        if ( self.version == SCBVersion.V1 ):
            return self.getHeader1_0( targetAgent )
        elif ( self.version == SCBVersion.V2_0 ):
            return self.getHeader2_0( targetAgent )
        elif ( self.version == SCBVersion.V2_1 ):
            return self.getHeader2_1( targetAgent )
        elif ( self.version == SCBVersion.V2_2 ):
            return self.getHeader2_2( targetAgent )
        elif ( self.version == SCBVersion.V2_3 ):
            return self.getHeader2_3( targetAgent )
        elif ( self.version == SCBVersion.V2_4 ):
            return self.getHeader2_4( targetAgent )

    def getHeader1_0( self, targetAgent ):
        '''Produces a header for version 1.0 of this data'''
        s = '1.0\x00'
        if ( targetAgent > -1 ):
            s += struct.pack( 'i', targetAgent )
        else:
            s += struct.pack( 'i', self.readAgtCount )
        return s

    def getHeader2Style( self, version, targetAgent ):
        '''Produces a header for all headers that have the version 2 style.
            agent count, time step, and class ids for each agent'''
        s = version
        if ( targetAgent > -1 ):
            s += struct.pack( 'i', 1 )
        else:
            s += struct.pack( 'i', self.readAgtCount )
        s += struct.pack( 'f', self.effectiveTimeStep )
        if ( targetAgent > -1 ):
            s += struct.pack( 'i', self.ids[ targetAgent ] )
        else:
            last = self.readAgtCount * self.readAgtStride
            for id in self.ids[ :last:self.readAgtStride ]:
                s += struct.pack( 'i', id )
        return s

    def getHeader2_0( self, targetAgent ):
        '''Produces a header for version 2.0 of this data'''
        return self.getHeader2Style( '2.0\x00', targetAgent )

    def getHeader2_1( self, targetAgent ):
        '''Produces a header for version 2.1 of this data'''
        return self.getHeader2Style( '%s\x00' % SCBVersion.V2_1, targetAgent )

    def getHeader2_2( self, targetAgent ):
        '''Produces a header for version 2.2 of this data'''
        return self.getHeader2Style( '%s\x00' % SCBVersion.V2_2, targetAgent )

    def getHeader2_3( self, targetAgent ):
        '''Produces a header for version 2.3 of this data'''
        return self.getHeader2Style( '%s\x00' % SCBVersion.V2_3, targetAgent )

    def getHeader2_4( self, targetAgent ):
        '''Produces a header for version 2.4 of this data'''
        return self.getHeader2Style( '%s\x00' % SCBVersion.V2_4, targetAgent )

    def write( self, output ):
        '''Writes this data to the target file'''
        f = open( output, 'wb' )
        f.write( self.getHeader() )
        prevIdx = -1
        frame, idx = self.next()
        while ( idx != prevIdx and frame != None ):
            self.writeFrame( frame, f )
            prevIdx = idx
            try:
                frame, idx = self.next()
            except StopIteration:
                break
        f.close()

    def writeAgent( self, output, agentID ):
        '''Writes a single agent to the target file'''
        f = open( output, 'wb' )
        f.write( self.getHeader( 1 ) )
        prevIdx = -1
        frame, idx = self.next()
        while ( True ):
            self.writeFrame( frame, f, agentID )
            prevIdx = idx
            try:
                frame, idx = self.next()
            except StopIteration:
                break
        f.close()

    def writeFrame( self, frame, file, agent=-1 ):
        '''Writes the generic frame to the file provided'''
        if ( version != '1.0' ):
            raise AttributeError, 'FrameSet only able to output version 1.0'
        f.write( frame.toBinary( agent ) )

    def close( self ):
        '''Closes the file'''
        self.file.close()
    
class NPFrameSet( FrameSet ):
    """A frame set that uses numpy arrays instead of frames as the underlying structure"""
    def __init__( self, scbFile, startFrame=0, maxFrames=-1, maxAgents=-1, frameStep=1, agtStep=1 ):
        FrameSet.__init__( self, scbFile, startFrame, maxFrames, maxAgents, frameStep, agtStep )
        # number of columns, per-frame, for the data
        self.colCount = self.agentByteSize / 4
        
    def next( self, stride=1 ):
        """Returns the next frame in sequence from current point"""
        if ( self.currFrameIndex >= self.maxFrames - 1 ):
            raise StopIteration  # TODO: make everything rely on this exception
        
        if ( self.currFrame is None):
            self.currFrame = np.empty( ( self.readAgtCount, self.colCount ), dtype=np.float32 )

        skipAmount = stride - 1
        original_pos = self.file.tell()
        if ( skipAmount ):
            # TODO: Are the semantics of "readDelta" and 'strideDelta" correct here?
            seek_address = skipAmount * (self.readDelta + self.strideDelta + self.frameSize)
            self.file.seek(seek_address, os.SEEK_CUR)
        try:
            floatCount = self.readAgtCount * self.colCount * self.readAgtStride
            data = np.fromstring( self.file.read( self.readFrameSize ), np.float32, floatCount )
            readAgents = self.readAgtCount * self.readAgtStride
            self.currFrame[:,:] = np.reshape( data, ( readAgents, self.colCount ) )[ ::self.readAgtStride, : ]
        except ValueError:
            # We failed to read data; let's put the head back to where it was originally.
            self.file.seek(original_pos, os.SEEK_SET)
            raise StopIteration
        self.currFrameIndex += stride

        # seek forward based on skipping
        if ( self.agentDelta ):
            self.file.seek( self.agentDelta, 1 ) # advance to next frame
        if ( self.strideDelta ):
            self.file.seek( self.strideDelta, 1 ) # advance according to stride

        return self.currFrame, self.currFrameIndex

    def prev( self, stride=1 ):
        """Returns the next frame in sequence from current point"""
        if ( self.currFrameIndex >= stride ):
            self.colCount = self.agentByteSize / 4
            
            self.currFrameIndex -= stride
            self.file.seek( -(stride+1) * ( self.readDelta + self.strideDelta+ self.frameSize ), 1 )
            if ( self.currFrame is None):
                self.currFrame = np.empty( ( self.readAgtCount, self.colCount ), dtype=np.float32 )
            self.currFrame[:,:] = np.reshape( np.fromstring( self.file.read( self.frameSize ), np.float32, self.readAgtCount * self.colCount ), ( self.readAgtCount, self.colCount ) )
            # seek forward based on skipping
            self.file.seek( self.readDelta, 1 ) # advance to next frame
            self.file.seek( self.strideDelta, 1 ) # advance according to stride
        
        return self.currFrame, self.currFrameIndex

    def fullData( self ):
        """Returns an N X M X K array consisting of all trajectory info for the frame set, for
        N agents, M floats per agent and K time steps"""
        # TODO: This should return an instance of SCBDataMemory
        #   The end result should support the normal "SCBData" oeprations.
        M = self.agentByteSize / 4
        frameCount = self.totalFrames()
        data = np.empty( ( self.readAgtCount, M, frameCount ), dtype=np.float32 )
        self.setNext( 0 )
        for i in range( frameCount ):
            frame, idx = self.next()
            data[ :, :, i ] = frame
        return data

    def writeFrame( self, frame, file, agent=-1 ):
        '''Writes the numpy array representing the agent data to the file'''
        if ( agent > -1 ):
            file.write( frame[ agent, : ].tostring() )
        else:
            file.write( frame.tostring() )
            
    def getFrameIds( self ):
        '''Returns a mapping from index in the frame to global identifier'''
        # For this data set, it's tautological
        return IDMap( self.agentCount() )

class SCBDataMemory:
    '''A version of SCBData that has the full data set loaded into memory as a numpy array.'''
    def __init__( self ):
        '''Constructor.'''
        self.version = None
        self.simStepSize = None
        self.data = None
        self.ids = None
        self.nextFrame = -1

    def setData( self, data, version, timeStep, ids=None ):
        '''Sets the data for the SCBData

        @param      data        A numpy array of floats of shape (N, M, K ) with N agents,
                                M floats per agent, over K frames.
        @param      version     A string.  The version of the underlying data representation.
        @param      timeStep    A float.  The duration of each frame of data.
        @param      ids         An optional tuple-like object of ints.  Its length must be N.
        '''
        self.data = data
        self.version = version
        self.simStepSize = timeStep
        self.ids = None
        self.nextFrame = 0
        if ( not self.ids is None ):
            if ( len( self.ids ) != data.shape[0] ):
                raise AttributeError, "The agent class id list doesn't match the number of agents in the data.  Data has %d, ids has %d" % ( len( self.ids ), data.shape[0] )

    def fullData( self ):
        """Returns an N X M X K array consisting of all trajectory info for the frame set, for
        N agents, M floats per agent and K time steps"""
        return self.data
    
    def setNext( self, frameIdx ):
        '''Sets the next frame to be retrieved to the given index.

        @param      frameIdx        An int.  The next frame to return when calling "next".
        @raises     AttributeError if the data hasn't been set yet.
        @raises     ValueError if the frameIdx isn't "valid".
        '''
        # TODO: TEST THIS!
        if ( self.data is None ):
            raise AttributeError, "Can't set next frame; no data has been set"
        self.nextFrame = frameIdx
        if ( self.nextFrame < 0 ):
            self.nextFrame += self.data.shape[2]
        if ( self.nextFrame < 0 or frameIdx > self.data.shape[2] ):
            raise ValueError, 'The index %d is outside of the feasible range: [%d, %d]' % ( -self.data.shape[2], self.data.shape[2] )

    def next( self ):
        '''Returns the next frame in the data.agentCount

        @return     A 2-tuple (data, index)
                        data:   A numpy array of data of shape (N, M), for N agents and M floats
                                per agent, based on the version of the data.
                        index:  The index of the next frame to return. TODO: Confirm this.
        '''
        # TODO: TEST THIS!
        if ( self.nextFrame >= self.data.shape[ 2 ] ):
            raise StopIteration
        data = self.data[ :, :, self.nextFrame ]
        self.nextFrame += 1
        return data
    
    def getType( self ):
        '''Returns the identifier for this type of trajectory data.

        @returns        An enumeration representing the Julichd ata.
        '''
        return commonData.SCB_DATA
    
    def write( self, output ):
        '''Writes the associated data out to a file.

        @param      output      A string.  The name of the file to write the data to.
        @raises     AttributeError if there is no data contained.
        '''
        if ( self.data is None ):
            raise AttributeError, "Cannot write scb data - none defined"
        writeNPSCB( output, self.data, self, self.version )
        
def writeNPSCB( fileName, array, frameSet, version='1.0' ):
    """Given an N X M X K array, writes out an scb file with the given data.
    There are N agents over K frames.  M defines the number of data points per agent.
    Each version requires a certain number of floats.  If the indicated version 
    isn't satisifed by M, an exception (ValueError) is raised."""
    print "Writing %s with %d agents and %d frames" % ( fileName, array.shape[0], array.shape[2] )
    print "Writing version %s" % ( version )
    if ( version == SCBVersion.V1 ):
        _writeNPSCB_1_0( fileName, array )
    elif ( version == SCBVersion.V2_0 ):
        _writeNPSCB_2_0( fileName, array, frameSet )
    elif ( version == SCBVersion.V2_1 ):
        _writeNPSCB_2_1( fileName, array, frameSet )
    elif ( version == SCBVersion.V2_2 ):
        _writeNPSCB_2_2( fileName, array, frameSet )
    elif ( version == SCBVersion.V2_3 ):
        _writeNPSCB_2_3( fileName, array, frameSet )
    elif ( version == SCBVersion.V2_4 ):
        _writeNPSCB_2_4( fileName, array, frameSet )
    else:
        raise Exception, "Invalid write version for data: %s" % ( version )
    

def _writeNPSCB_1_0( fileName, array ):
    """Given an N X 3 X K array, writes out a version 1.0 scb file with the given data"""
    if ( array.shape[1] < 3 ):
        raise ValueError, "Version 1.0 requires three floats per agent"
    f = open( fileName, 'wb' )
    f.write( '%s\x00' % SCBVersion.V1 )
    f.write( struct.pack( 'i', array.shape[0] ) )
    for frame in range( array.shape[2] ):
        f.write( array[:,:3,frame].tostring() )
    f.close()

def _writeNPSCB_2( fileName, array, frameSet, version, fieldCount ):
    """Given an N X 3 X K array, writes out a version 2.* scb file with the given data.
    It is assumed that all file versions with the same major version have the same header"""
    if ( array.shape[1] < fieldCount ):
        raise ValueError, "Version %s requires %d floats per agent" % ( version, fieldCount )
    f = open( fileName, 'wb' )
    f.write( version )
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
        f.write( array[:,:fieldCount,frame].tostring() )
    f.close()

def _writeNPSCB_2_0( fileName, array, frameSet ):
    """Given an N X 3 X K array, writes out a version 1.0 scb file with the given data"""
    _writeNPSCB_2( fileName, array, frameSet, '%s\x00' % SCBVersion.V2_0, 3 )
  
def _writeNPSCB_2_1( fileName, array, frameSet ):
    """Given an N X 4 X K array, writes out a version 1.0 scb file with the given data"""
    _writeNPSCB_2( fileName, array, frameSet, '%s\x00' % SCBVersion.V2_1, 4 )

def _writeNPSCB_2_2( fileName, array, frameSet ):
    """Given an N X 8 X K array, writes out a version 1.0 scb file with the given data"""
    _writeNPSCB_2( fileName, array, frameSet, '%s\x00' % SCBVersion.V2_2, 8 )

def _writeNPSCB_2_3( fileName, array, frameSet ):
    """Given an N X 4 X K array, writes out a version 1.0 scb file with the given data"""
    _writeNPSCB_2( fileName, array, frameSet, '%s\x00' % SCBVersion.V2_3, 4 )

def _writeNPSCB_2_4( fileName, array, frameSet ):
    """Given an N X 4 X K array, writes out a version 1.0 scb file with the given data"""
    _writeNPSCB_2( fileName, array, frameSet, '%s\x00' % SCBVersion.V2_4, 4 )

    
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

def main():
    '''A simple script for summarizing the script'''
    import sys
    if ( len( sys.argv ) < 1 ):
        print "Provide the name of an scb file to get summary"
        sys.exit(1)

    data = NPFrameSet( sys.argv[ 1 ] )
    print "SCB file loaded"
    print "\tVersion:", data.version
    print "\tAgents: ", data.agentCount()
    classes = data.getClasses()
    print "\t%d classes:" % ( len( classes ) ), classes.keys()
    print "\tTime step:", data.simStepSize
    print "\tDuration (frames):", data.totalFrames()
    print "\tInitial positions:"
    
if __name__ == '__main__':
    main()
    
