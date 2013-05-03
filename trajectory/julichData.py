# This reads the trajectories for Seyfried's data.  It provides a similar
#   interface as the scbData so it can be used in density analysis

import os
import numpy as np
import commonData

class FormatError( Exception ):
    '''There is a format problem with the trajectory file'''
    def __init__( self, lineNumber, line ):
        self.lineNumber = lineNumber
        self.line = line

    def __str__( self ):
        return "FormatError: Invalid format on line %d: %s" % ( self.lineNumber, self.line )

class Pedestrian:
    '''A class which wraps the trajectory of a single pedestrian'''
    def __init__( self, startTime, id ):
        self.start = startTime
        self.id = id
        self.traj = []

    def addPoint( self, x, y, z ):
        '''Adds a point to the trajectory'''
        self.traj.append( (x, y, z) )

    def finalize( self ):
        '''No more trajectories to add to the pedestrian'''
        self.traj = np.array( self.traj )

    def getPosition( self, frame ):
        '''Returns the pedestrian's position at the given frame.
        If the frame falls outside the time at which this pedestrian's trajectory
        is defined, None is returned.'''
        if ( frame < self.start or frame >= self.start + self.traj.shape[0] ):
            return None
        else:
            return self.traj[ frame - self.start, :2 ]

    def getNPTrajectory( self ):
        '''Returns the trajectory formatted in a numpy format'''
        return self.traj

    def format( self, scale ):
        '''Creates a string from this trajectory data.  The string format is the same
        as read from the trajectory file.close

        @param      scale       A float.  Scales the position by this value.
        @returns    A string.  The pedestrian data formatted.
        '''
        P = []
        for i, point in enumerate( self.traj ):
            P.append( '%d %d %f %f %f' % ( self.id, i + self.start, point[0] * scale, point[1] * scale, point[2] * scale ) )
        return '\n'.join( P )
        
class JulichData:
    '''Class for reading the trajectory data stored in Seyfried's data'''
    def __init__( self, timeStep=1.0/16.0, convertToMeters=True, startFrame=0, maxFrames=-1, frameStep=1, maxAgents=-1 ):
        '''Initialize the trajectory reader.  Responsible for reading the trajectory data in
        the Julich format and give access, through an iterator-like interface, each frames' data.

        @param  timeStep            A float.  The time step inherent in the data.
        @param  convertToMeters     A bool.   Assumes that the underlying data's units is
                                    centimeters.  If True, convers to meters.  If False
                                    leaves as current units.
        @param  startFrame          An int.  The first frame in the data reported as frame 0.
                                    Defaults to zero, the first frame.
        @param  maxFrames           An int.  The maximum number of frames the frame set will
                                    report.  If negative, the full trajectory will be considered.
                                    Otherwise, N agents, where N = min( number of frames, maxFrames).
        @param  frameStep           An int.  The stride between data frames reported as sequential
                                    frames.  Defaults to 1: every frame.
        @param  maxAgents           An int.  The maximum number of agents to report.  If negative
                                    all agents are handled.  Otherwise, it only reports on the
                                    first N agents, where N = min( number of agents, maxAgents)
        
        '''
        
        # the data is typically stored in centimeters, this will automatically
        #   convert them to meters.
        self.toMeters = convertToMeters
        self.pedestrians = []
        # functionality for retrieving the data
        self.timeStep = timeStep    # duration of a single frame
        self.duration = 0           # in frames
        self.currFrameID = 0        # What is the interpretation of this?  The last frame read or the id of the one that will be read when next is called?
        self.currFrame = None
        self.currIDs = None
        self.framePop = 0
        self.startFrame = startFrame
        # generic attributes
        if ( maxFrames == -1 ):
            self.maxFrames = 0x7FFFFFFF
        else:
            self.maxFrames = maxFrames
        self.frameStep = frameStep
        self.maxAgents = maxAgents

    def getType( self ):
        '''Returns the identifier for this type of trajectory data.

        @returns        An enumeration representing the Julichd ata.
        '''
        return commonData.JULICH_DATA
    
    def _setTimeStep( self, ts ):
        self.timeStep = ts

    def __str__( self ):
        return self.summary()

    @staticmethod
    def isValid( fileName ):
        '''Reports if the given file is a julich data file.

        @param      fileName        A string.  The name of the file to check.
        @returns    A boolean.  True if the data adheres to julich data file format
        '''
        LINES_TO_READ = 10
        f = open( fileName, 'r' )
        num = 0

        valid = True
        for line in f.xreadlines():
            if ( line == '' ):
                continue
            
            # Test by looking at the format at LINES_TO_READ number of lines

            LINES_TO_READ -= 1
            tokens = line.strip().split()
            if ( len( tokens ) < 4 ):
                valid = False
                break
            try:
                pedID = int( tokens[0] )
                frameNum = int( tokens[1] )
                x = float( tokens[2] )
                y = float( tokens[3] )
                try:
                    z = float( tokens[4] )
                except IndexError:
                    z = 0.0
            except ValueError:
                valid = False
                break
            
            if ( LINES_TO_READ <= 0 ):
                break
        return valid
    
    # This property is an alias for timeStep -- it is because the NPFrameSet provides
    #   this (badly named) property and I want them to be equivalent in this manner
    simStepSize = property( lambda self: self.timeStep, lambda self, ts: self._setTimeStep( ts ) )

    def readFile( self, fileName ):
        '''Reads the file indicated.
        Raises an OSError if file can't be opened.
        Raises a FormatError if the file has formatting issues.'''

        if ( not os.path.exists( fileName ) ):
            raise OSError
        
        f = open( fileName, 'r' )
        currPed = None
        startFrame = 1 << 30        # in the data, the frame can start at
                                    # arbitrarily high values (i.e. it is not normalized)
        originFrame = None          # serves as the origin of the data - it is from this point
                                    # that frame strides and frame counts are performed.
        num = 0
        for line in f.xreadlines():
            num += 1
            if ( line == '' ):
                continue
            tokens = line.strip().split()
            if ( len( tokens ) < 4 ):
                raise FormatError( num, line )
            try:
                pedID = int( tokens[0] )
                frameNum = int( tokens[1] )
                x = float( tokens[2] )
                y = float( tokens[3] )
                try:
                    z = float( tokens[4] )
                except IndexError:
                    z = 0.0
            except ValueError:
                raise FormatError( num, line )
            if ( self.toMeters ):
                x *= 0.01
                y *= 0.01
                z *= 0.01
            # this assumes that the first frame seen serves as an appropriate origin
            #   if the agents were not reported in increasing start times, later agents
            #   could have start times before this. 
            if ( originFrame == None ): 
                originFrame = frameNum
            if ( frameNum < startFrame ):
                startFrame = frameNum
            localFrame = frameNum - originFrame
            if ( ( localFrame % self.frameStep != 0 ) ):
                continue
            localFrame /= self.frameStep
            if ( localFrame > self.maxFrames ):
                continue
            if ( currPed == None or pedID != currPed.id ):
                if ( self.maxAgents >= 0  and len( self.pedestrians ) >= self.maxAgents ):
                    break
                currPed = Pedestrian( frameNum, pedID )
                self.pedestrians.append( currPed )
            currPed.addPoint( x, y, z )

        # normalize all start times
        #   produce numpy arrays of each trajectory
        #   Determine duration of sequence
        for i, ped in enumerate( self.pedestrians ):
            ped.id = i
            ped.start = (ped.start - startFrame) / self.frameStep
            ped.finalize()
            end = ped.start + ped.traj.shape[0]
            if ( end > self.duration ):
                self.duration = end
        f.close()
        # create a frame that is the size of all the agents (the biggest possible frame)
        #   during calls to next, windows of this data will be returned
        self.currFrame = np.empty( ( len( self.pedestrians ), 2 ), dtype=np.float32 )
        self.currIDs = np.empty( len( self.pedestrians ), dtype=np.int )
        self.setNext( 0 )

    def summary( self ):
        '''Creates a simple summary of the trajectory data'''
        s = 'Julich Trajectory data'
        s += '\n\t%d pedestrians' % ( len( self.pedestrians ) )
        s += '\n\t%d frames of  data' % self.duration
        return s

    # These functions should make this object compatible with my crowd analysis
    #   tools
    def setNext( self, index ):
        """Sets the set so that the call to next frame will return frame index"""
        if ( index < 0 ):
            index = 0
        self.currFrameID = index - 1

    def next( self, stride=1 ):
        """Returns the next frame in sequence from current point.  If there are
        no more frames, raises a StopIteration"""
        if ( self.currFrameID >= self.duration - 1 ):
            raise StopIteration
        # advance the identifier
        self.currFrameID += stride
        a = 0
        id = -1
        for p in self.pedestrians:
            id += 1
            pos = p.getPosition( self.currFrameID )
            if ( pos != None ):
                self.currFrame[ a, : ] = pos
                self.currIDs[ a ] = id
                a += 1
        self.framePop = a
        # TODO: This copy is for multi-threaded applications.  Pull the copy out
        #   of here and place it in the multi-threading.
        return np.copy( self.currFrame[ :a, : ] ), self.currFrameID

    def getFrameIds( self ):
        '''Returns the ids associated with the last frame read'''
        # TODO: This copy is for multi-threaded applications.  Pull the copy out
        #   of here and place it in the multi-threading.
        return np.copy( self.currIDs[ :self.framePop ] )

    def totalFrames( self ):
        """Reports the total number of frames in the file"""
        return self.duration

    def agentCount( self ):
        '''Returns the agent count'''
        return len( self.pedestrians )

    def hasStateData( self ):
        '''Reports if the scb data contains state data'''
        return False

    def getNPTrajectory( self, i ):
        '''Returns an Nx2 numpy array representing the trajectory of the ith agent'''
        return self.pedestrians[ i ].traj

    def write( self, output ):
        '''Writes this data to the file with the given name.

        @param  output      A string.  The name of the file.
        '''
        multiplier = 1.0
        if ( self.toMeters ):
            # Undo scaling that was done upon loading -
            #   Julich should always be stored in cm, for consistency.
            multiplier = 100.0
        f = open( output, 'w' )
        for ped in self.pedestrians:
            f.write( ped.format( multiplier ) + '\n' )
        f.close()

    def writeAgent( self, output, agentID ):
        '''Writes a single agent to an output file.

        @param  output      A string.  The name of the file.
        @param  agentID     An int.  The id of the agent to write.
        @raises     ValueError if no agent with the given ID exists.
        '''
        f = open( output, 'w' )
        for ped in self.pedestrians:
            if ( ped.id == agentID ):
                f.write( ped.format() )
                f.close()
                return
        f.close()
        raise ValueError, "No pedestrian with id: %d" % ( agentID )
        

if __name__ == '__main__':
    import optparse
    import sys
    def main():
        parser = optparse.OptionParser()
        parser.set_description( 'Tests the trajectory reading ability of the class' )

        parser.add_option( '-i', '--inFile', help='The file to read',
                           action='store', dest='inFile', default='' )
        options, args = parser.parse_args()

        if ( options.inFile == '' ):
            print "Please specify an input file"
            parser.print_help()
            sys.exit( 1 )

        reader = JulichData()
        try:
            reader.readFile( options.inFile )
        except OSError:
            print "Unable to find input file:", options.inFile
            sys.exit( 1 )
        except FormatError as e:
            print e
            sys.exit( 1 )

        print reader.summary()

        while( True ):
            try:
                frame, index = reader.next()
                ids = reader.getFrameIds()
            except StopIteration:
                break
            else:
                print "Frame %d has %d agents" % ( index, frame.shape[0] ), ids

    main()            

            
            