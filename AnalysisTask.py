from primitives import Vector2, Segment, segmentsFromString
from trajectory.scbData import NPFrameSet
import Crowd
import os
import time

import Kernels
import Signals
from GFSVis import visualizeGFS
from Grid import makeDomain
from ColorMap import *
from domains import RectDomain

def flowLinesToString( lines, names ):
    '''Given the lines and names of flow lines, outputs a parsable string.'''
    assert( len( lines ) == len( names ) )
    s = ','.join( names ) + "~"
    for i, line in enumerate( lines ):
        s += ' %.5f %.5f %.5f %.5f' % ( line.p1.x, line.p1.y, line.p2.x, line.p2.y )
    return s

def flowLinesFromString( s, LineClass ):
    '''Given a string of the format provided by flowLinesToString produces
    a list of strings and names.

    @param      s           A formatted flow line string.  The string
                            can be of the old format (for which no names
                            are listed.  Names will be created ).
    @param      LineClass   The type of line class to instantiate.
    @return     A 2-tuple of lists: [ names, lines ]
                names: a list of strings, one per line
                lines: a list of instances of class LineClass
    '''
    tokens = s.split( '~' )
    if ( len( tokens ) == 1 ):
        # old format
        lines = segmentsFromString( tokens[0], LineClass )
        names = [ 'Line %d' % i for i in xrange( len( lines ) ) ]
    else:
        names = tokens[0].split(',')
        lines = segmentsFromString( tokens[1], LineClass )
    return names, lines

def getTaskClass( taskName ):
    '''Returns a class object for the given analysis task name'''
    if ( taskName == DensityAnalysisTask.typeStr() ):
        return DensityAnalysisTask
    elif ( taskName == FlowAnalysisTask.typeStr() ):
        return FlowAnalysisTask
    elif ( taskName == SpeedAnalysisTask.typeStr() ):
        return SpeedAnalysisTask
    elif ( taskName == PopulationAnalysisTask.typeStr() ):
        return PopulationAnalysisTask
    elif ( taskName == FundDiagAnalysisTask.typeStr() ):
        return FundDiagAnalysisTask
    else:
        self.rsrc.logger.error( "Unrecognized analysis task type: %s" % ( taskName ) )
        raise ValueError


def writeAnalysisProject( tasks, fileName ):
    '''Writes an analysis project file for the given list of tasks to the given
    filename.

    @param      tasks           A list of AnalysisTask instances.
    @param      fileName        A string.  The path to the file to parse.
    @raises     IOError if the file can't be accessed.
    '''
    file = open( fileName, 'w' )
    file.write( '# WARNING!  Editing this file can cause problems.  Order, case, and syntax all matter\n' )
    file.write( '# The only comments allowed are full line comments\n' )
    file.write( 'Task count || %d\n' % len( tasks ) )
    for task in tasks:
        task.writeConfig( file )
    file.close()
       
def readAnalysisProject( fileName ):
    '''Reads an analysis project file and returns a list of tasks.

    @param      fileName        A string.  The path to the file to parse.
    @returns    A list of AnalysisTask widgets.
    @raises     IOError if the file can't be accessed.
    @raises     ValueError if there is a problem in parsing the file
    '''
    file = open( fileName, 'r' )

    line = file.readline().strip()
    while ( line[0] == '#' ):
        line = file.readline().strip()
    try:
        tokens = map( lambda x: x.strip(), line.split( '||' ) )
    except:
        self.rsrc.logger.error( "Error parsing task count" )
        raise ValueError
    
    if ( len( tokens ) != 2 or tokens[0] != 'Task count' ):
        self.rsrc.logger.error( 'Expected to see "Task count" in configuration file, found %s' % ( tokens[0] ) )
        raise ValueError
    taskCount = int( tokens[1] )

    tasks = []    
    for i in xrange( taskCount ):
        taskType = file.readline().strip()
        TaskClass = getTaskClass( taskType )
        task = TaskClass()
        task.readConfig( file )
        tasks.append( task )  
    
    file.close()
    
    return tasks
    
class AnalysisTask:
    # Work to be performed by the task
    NO_WORK = 0
    COMPUTE = 1
    VIS = 2
    COMPUTE_VIS = 3

    WORK_STRINGS = { COMPUTE:'Compute', VIS:'Visualize', COMPUTE_VIS:'Compute and Vis.' }
    WORK_IDS = { 'Compute':COMPUTE, 'Visualize':VIS, 'Compute and Vis.':COMPUTE_VIS }

    @staticmethod
    def taskStringID( text ):
        '''Converts the given text into an enumeration id for the work class.

        @param      text        A string.  The string to convert.
        @returns    An int.  The enumeration that maps to the given string.
        @raises     KeyError if the string has no mapping to an enumeration value.
        '''
        return AnalysisTask.WORK_IDS[ text ]

    @staticmethod
    def taskIDString( id ):
        '''Returns the string for the given task id.

        @param      id      An int.  An enumeration of task type.
        @returns    A string.  The string representation of the given work type.
        @raises     KeyError if the task enumeration is invalid.
        '''
        return AnalysisTask.WORK_STRINGS[ id ]

    @staticmethod
    def taskStrings():
        '''Returns a list of task strings.'''
        keys = self.WORK_STRINGS.keys()
        keys.sort()
        return [ AnalysisTask.WORK_STRINGS[ k ] for k in keys ]
    
    def __init__( self ):
        '''Constructor for basic Analysis Task.

        @param      input       An instance of analyzeWidgets.InputWidget.
                                Contains all input parameters.
        '''
        self.work = self.NO_WORK
        self.workName = ''
        self.scbName = ''
        self.timeStep = 0.0
        self.workFldr = '.'
        self.obstName = ''
        self.active = False

    def setSCBFile( self, fileName ):
        '''Sets the scb file name for the analysis task.

        @param      fileName        A string.  The path to the input scb file name.
        '''
        self.scbName = fileName

    def setTimeStep( self, timeStep ):
        '''Defines the time step of the analysis task.  This value will be ignored if
            the scb file contains time step information.

        @param      timeStep        A float.  The time step of the simulation data.
        '''
        self.timeStep = timeStep

    def setWorkFolder( self, fldr ):
        '''Defines the folder in which the analysis work is to be performed.

        @param      fldr        A string.  The path to the folder in which analysis
                                results is to be done.
        '''
        self.workFldr = fldr

    def setTaskName( self, name ):
        '''Sets the name of the task.  The work files will bear this name.

        @param      name        A string.  The name of the task.
        '''
        self.workName = name

    def setWork( self, work ):
        '''Sets the work to be done by this task.

        @param      work        An enumeration on AnalysisTask.  Must be one of:
                                    ( COMPUTE, VIS, COMPUTE_VIS )
        '''
        self.work = work

    def setObstFile( self, fileName ):
        '''Sets the obstacle file name for the analysis task.

        @param      fileName        A string.  The path to the input scb file name.
        '''
        # TODO: This data isn't currently passed to the analysis
        #   Future versions will make use of this.
        self.obstName = fileName

    def setActiveState( self, state ):
        '''Sets the active state of the task - the active state determines whether the task
        work should be performed or not.

        @param      state       A boolean.  True if the task is to be evaluated, False otherwise.
        '''
        self.active = state
        
    def execute( self ):
        '''Execute the task'''
        raise NotImplementedError

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        raise NotImplementedError

    def getWorkPath( self, typeName ):
        '''Produces the work path for this task, given the type name and guarantees that it
        exists.

        @param      typeName        A string.  The name of the subfolder based on the type of
                                    analysis.'''
        print "WORK FOLDER:", self.workFldr
        workPath = os.path.join( self.workFldr, typeName, self.workName )
        if ( not os.path.exists( workPath ) ):
            os.makedirs( workPath )
        return workPath

    def _parseConfigLine( self, file, name, convertFunc=None ):
        '''Parses a key-value line from the config file.  The string value is optionally converted
        via the convertFunc and passed as a parameter to the setFunc callable.

        @param      file            An open file object.  The file to read the line from.
        @param      name            The name of the expected key.
        @param      convertFunc     A callable.  If provided, the string value will be passed to this
                                    function and the RESULT is passed to setFunc.
        @return     The key value, a string if convertFunc is None, otherwise the output of
                    convertFunc.
        @raises     ValueError if there is difficulty parsing the expected value.
        '''
        line = file.readline().strip()
        while ( line[0] == '#' ):
            line = file.readline().strip()
        try:
            tokens = map( lambda x: x.strip(), line.split( '||' ) )
        except:
            self.rsrc.logger.error( "Error parsing key %s" % name )
            self.rsrc.logger.error( '\tRead: %s' % line )
            raise ValueError, "Couldn't identify key-value pair in line"
        if ( len( tokens ) != 2 ):
            self.rsrc.logger.error( "Too many values found for key: %s" % ( name ) )
            self.rsrc.logger.error( '\tRead: %s' % line )
            raise ValueError, "Too many values to form a key-value pair"
        if ( tokens[0] != name ):
            self.rsrc.logger.error( "Looking for key %s, found %s" % ( name, tokens[0] ) )
            self.rsrc.logger.error( '\tRead: %s' % line )
            raise ValueError, "Found wrong key value"
        value = tokens[1]
        if ( convertFunc ):
            try:
                value = convertFunc( value )
            except ValueError as e: 
                self.rsrc.logger.error( "Error converting the value for %s: %s" % ( name, value ) )
                self.rsrc.logger.error( '\tRead: %s' % line )
                raise e
        return value
    
    def readConfig( self, file ):
        '''Reads the common TaskWidget parameters from the file'''
        # I/O info
        active = True
        try:
            self.scbName = self._parseConfigLine( file, 'SCB' )
        except ValueError:
            active = False
            
        try:
            self.timeStep = self._parseConfigLine( file, 'timeStep', float )
        except ValueError:
            active = False
            
        try:
             self.obstName = self._parseConfigLine( file, 'obstacle' )
        except ValueError:
            active = False
            
        try:
            self.workFldr = self._parseConfigLine( file, 'outFldr' )
        except ValueError:
            active = False

        # work info
        try:
            self.workName = self._parseConfigLine( file, 'workName' )
        except ValueError:
            active = False
            
        try:
            self.work = self._parseConfigLine( file, 'task', self.taskStringID )
        except ValueError:
            active = False
            
        def isActive( txt ):
            return txt == '1'
        self.active = self._parseConfigLine( file, 'active', isActive ) and active

    def writeConfig( self, file ):
        '''Writes the AnalysisTask state to the given file'''
        # Write TYPE
        file.write( '%s\n' % self.typeStr()  )
        # Write I/O (scb name, time step, obstacle file, output folder)
        file.write( 'SCB || %s\n' % ( self.scbName ) )
        file.write( 'timeStep || %.5f\n' % ( self.timeStep ) )
        file.write( 'obstacle || %s\n' % ( self.obstName ) )
        file.write( 'outFldr || %s\n' % ( self.workFldr ) )
        # action info: work name,
        file.write( 'workName || %s\n' % ( self.workName ) )
        file.write( 'task || %s\n' % ( self.taskIDString( self.work ) ) )
        file.write( 'active || ' )
        if ( self.active ):
            file.write( '1\n' )
        else:
            file.write( '0\n' )

class DomainAnalysisTask( AnalysisTask ):
    '''An analysis task which relies on a domain.'''
    def __init__( self ):
        AnalysisTask.__init__( self )
        self.domainX = None
        self.domainY = None

    def setDomain( self, minX, minY, maxX, maxY):
        '''Defines the analysis domain.

        @param      minX        A float.  The minimum point of the rectangular domain
                                along the x-axis.
        @param      minY        A float.  The minimum point of the rectangular domain
                                along the y-axis.
        @param      maxX        A float.  The maximum point of the rectangular domain
                                along the x-axis.
        @param      maxY        A float.  The maximum point of the rectangular domain
                                along the y-axis.
        '''
        self.domainX = Vector2( minX, maxX )
        self.domainY = Vector2( minY, maxY )

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        raise NotImplementedError

    def readConfig( self, file ):
        '''Reads the common TaskWidget parameters from the file'''
        AnalysisTask.readConfig( self, file )
        minX = self._parseConfigLine( file, 'minPtX', float )
        minY = self._parseConfigLine( file, 'minPtY', float )
        w = self._parseConfigLine( file, 'sizeX', float )
        h = self._parseConfigLine( file, 'sizeY', float )
        self.setDomain( minX, minY, minX + w, minY + h )   

    def writeConfig( self, file ):
        AnalysisTask.writeConfig( self, file )
        # domain extent
        file.write( 'minPtX || %.5f\n' % ( self.domainX[0] ) )
        file.write( 'minPtY || %.5f\n' % ( self.domainY[0] ) )
        file.write( 'sizeX || %.5f\n' % ( self.domainX[1] - self.domainX[0] ) )
        file.write( 'sizeY || %.5f\n' % ( self.domainY[1] - self.domainY[0] ) )        

class DiscreteAnalysisTask( DomainAnalysisTask ):
    '''An analysis task which relies on a discretization of a domain'''
    def __init__( self ):
        DomainAnalysisTask.__init__( self )
        self.cellSize = 0.0
        self.colorMapName = ''
        self.outImgType = ''

    def setCellSize( self, h ):
        '''Sets the discretized cell size of the domain.

        @param      h       A float.  The size of a square cell.
        '''
        self.cellSize = h

    def setColorMap( self, mapName ):
        '''Sets the name of the color map to use in visualization.

        @param      mapName     A string.  The name of a valid color map.
        '''
        self.colorMapName = mapName

    def setOutImg( self, imgExt ):
        '''Sets the output image format based on the extension: 'jpg', 'png', or 'bmp'.

        @param      imgExt          A string.  The extention of the output image type.
        '''
        self.outImgType = imgExt.lower()
    def requiresDomain( self ):
        '''Reports if this particular task requires domain information - the default is true.'''
        return True

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        raise NotImplementedError

    def readConfig( self, file ):
        '''Reads the common TaskWidget parameters from the file'''
        DomainAnalysisTask.readConfig( self, file )
        self.cellSize = self._parseConfigLine( file, 'cellSize', float )
        self.colorMapName = self._parseConfigLine( file, 'colorMap' )
        self.outImgType = self._parseConfigLine( file, 'imgType' )  

    def writeConfig( self, file ):
        DomainAnalysisTask.writeConfig( self, file )
        # raster properties
        file.write( 'cellSize || %.5f\n' % ( self.cellSize ) )
        file.write( 'colorMap || %s\n' % ( self.colorMapName ) )
        file.write( 'imgType || %s\n' % ( self.outImgType ) ) 
    
class DensityAnalysisTask( DiscreteAnalysisTask ):
    def __init__( self ):
        DiscreteAnalysisTask.__init__( self )
        self.smoothParam = 0.0

    def setSmoothParam( self, h):
        '''Sets the smoothing parameter.  The exact interpretation of the smoothing parameter
        depends on the smoothing kernel.

        @param      h       A float.  The smoothing parameter.
        '''
        self.smoothParam = h

    def execute( self ):
        '''Perform the work of the task'''
        if ( self.work ):
            print 'Density analysis: %s' % ( self.workName )
            print "\tAccessing scb file:", self.scbName
            frameSet = NPFrameSet( self.scbName )
            workPath = self.getWorkPath( 'density' )
            tempFile = os.path.join( workPath, self.workName )
            grids = Crowd.GridFileSequence( tempFile )
            if ( self.work & AnalysisTask.COMPUTE ):
                print "\tComputing"
                kernel = Kernels.GaussianKernel( self.smoothParam, self.cellSize, False )
                domain = makeDomain( self.domainX, self.domainY, self.cellSize )
                sigDomain = makeDomain( self.domainX, self.domainY )
                signal = Signals.PedestrianSignal( sigDomain ) # signal domain is the same as convolution domain
                
                s = time.clock()
                grids.convolveSignal( domain, kernel, signal, frameSet )
                print '\t\tdone in %.2f seconds' % ( time.clock() - s )
            if ( self.work & AnalysisTask.VIS ):
                dataFile = grids.outFileName + ".density"
                if ( not os.path.exists( dataFile ) ):
                    print "\tCan't visualize density - unable to locate file: %s" % dataFile
                    return
                imageName = os.path.join( workPath, '%s_density_' % self.workName )
                s = time.clock()
                reader = Crowd.GridFileSequenceReader( dataFile )
                try:
                    colorMap = COLOR_MAPS[ self.colorMapName ]
                except:
                    print '\tError loading color map: "%s", loading flame instead' % ( self.colorMapName )
                    colorMap = COLOR_MAPS[ 'flame' ]
                print '\tCreating images'
                visualizeGFS( reader, colorMap, imageName, self.outImgType, 1.0, None )
                print '\t\tdone in %.2f seconds' % ( time.clock() - s ) 

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return "DENSITY"

    def readConfig( self, file ):
        '''Reads the common TaskWidget parameters from the file'''
        DiscreteAnalysisTask.readConfig( self, file )
        self.smoothParam = self._parseConfigLine( file, 'smoothParam', float ) 

    def writeConfig( self, file ):
        DiscreteAnalysisTask.writeConfig( self, file )
        # raster properties
        file.write( 'smoothParam || %.5f\n' % ( self.smoothParam ) )
    
class SpeedAnalysisTask( DiscreteAnalysisTask ):
    def __init__( self ):
        DiscreteAnalysisTask.__init__( self )

    def execute( self ):
        '''Perform the work of the task'''
        if ( self.work ):
            print 'Speed analysis: %s' % ( self.workName )
            print "\tAccessing scb file:", self.scbName
            frameSet = NPFrameSet( self.scbName )
            workPath = self.getWorkPath( 'speed' )
            tempFile = os.path.join( workPath, self.workName )
            grids = Crowd.GridFileSequence( tempFile )
            if ( self.work & AnalysisTask.COMPUTE ):
                print "\tComputing"
                domain = makeDomain( self.domainX, self.domainY, self.cellSize )
                s = time.clock()
                grids.computeSpeeds( domain, frameSet, self.timeStep )
                print '\t\tdone in %.2f seconds' % ( time.clock() - s )
            if ( self.work & AnalysisTask.VIS ):
                dataFile = grids.outFileName + ".speed"
                if ( not os.path.exists( dataFile ) ):
                    print "\tCan't visualize speed - unable to locate file: %s" % dataFile
                    return
                imageName = os.path.join( workPath, '%s_speed_' % self.workName )
                s = time.clock()
                reader = Crowd.GridFileSequenceReader( dataFile  )
                try:
                    colorMap = COLOR_MAPS[ self.colorMapName ]
                except:
                    print '\tError loading color map: "%s", loading flame instead' % ( self.colorMapName )
                    colorMap = COLOR_MAPS[ 'flame' ]
                print '\tCreating images'
                visualizeGFS( reader, colorMap, imageName, self.outImgType, 1.0, None )
                print '\t\tdone in %.2f seconds' % ( time.clock() - s ) 

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return "SPEED"   

class FlowAnalysisTask( AnalysisTask ):
    def __init__( self ):
        AnalysisTask.__init__( self )
        self._lines = []

    def addFlowLine( self, line, name ):
        '''Adds a flow line to the task.  A flow line is an ORIENTED segment.

        @param      line        An instance of FlowLine.
        @param      name        A string.  The name of the flow line.
        '''
        self._lines.append( ( name, line ) )
        
    def execute( self ):
        '''Perform the work of the task'''
        if ( self.work ):
            print 'Flow analysis: %s' % ( self.workName )
            print "\tAccessing scb file:", self.scbName
            frameSet = NPFrameSet( self.scbName )
            names = self.lineNames
            lines = self.lines
            workPath = self.getWorkPath( 'flow' )
            tempFile = os.path.join( workPath, self.workName )
            if ( self.work & AnalysisTask.COMPUTE ):
                print '\tComputing'
                s = time.clock()
                Crowd.computeFlow( frameSet, lines, tempFile, names )
                print '\t\tdone in %.2f seconds' % ( time.clock() - s )
            if ( self.work & AnalysisTask.VIS ):
                if ( not os.path.exists( tempFile + ".flow" ) ):
                    print "\tCan't create flow plots - unable to locate file: %s" % tempFile
                    return
                print '\tComputing plots'
                s=time.clock()
                # this gives the ability to change the pre-computed names
                timeStep = frameSet.simStepSize
                if ( frameSet.version[0] == '1' ):
                    timeStep = self.timeStep
                Crowd.plotFlow( tempFile, frameSet.simStepSize, titlePrefix=self.workName, legendStr=names )
                print '\t\tdone in %.2f seconds' % ( time.clock() - s )

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return "FLOW"

    def readConfig( self, file ):
        '''Reads the common TaskWidget parameters from the file'''
        AnalysisTask.readConfig( self, file )
        names, lines = flowLinesFromString( file.readline(), Segment )
        self._lines = zip( names, lines )

    def writeConfig( self, file ):
        '''Writes the widget state to the given file'''
        AnalysisTask.writeConfig( self, file )
        names = self.lineNames
        lines = self.lines
        lineData = ','.join( names ) + "~"
        for i, line in enumerate( lines ):
            lineData += ' %.5f %.5f %.5f %.5f' % ( line.p1.x, line.p1.y, line.p2.x, line.p2.y )
        file.write( '%s\n' % lineData )

    @property
    def lineNames( self ):
        return [ x[0] for x in self._lines ]

    @property
    def lines( self ):
        return [ x[1] for x in self._lines ]

class RectRegionAnalysisTask( AnalysisTask ):
    '''A task which operates on a named set of rectangular regions'''
    def __init__( self ):
        AnalysisTask.__init__( self )
        self._rects = []

    def addRectDomain( self, rect, name ):
        '''Adds a rectangular domain to the task

        @param      rect        An instance of RectDomain.
        @param      name        A string.  The name of the flow line.
        '''
        self._rects.append( ( name, rect ) )
        
    def readConfig( self, file ):
        '''Reads the common TaskWidget parameters from the file'''
        AnalysisTask.readConfig( self, file )
        line = file.readline()
        tokens = line.split( '~' )
        assert( len( tokens ) == 2 )
        names = tokens[0].split( ',' )
        tokens = tokens[1].split()
        assert( len( tokens ) == len( names ) * 4 )
        rects = []
        while ( tokens ):
            minX, minY, w, h = map( lambda x: float(x), tokens[:4] )
            rects.append( RectDomain( ( minX, minY ), ( w, h ) ) )
            tokens = tokens[4:]
        self._rects = zip( names, rects )

    def writeConfig( self, file ):
        '''Writes the widget state to the given file'''
        AnalysisTask.writeConfig( self, file )
        names = self.rectNames
        rects = self.rects
        rectData = ','.join( names ) + "~"
        for rect in rects:
            rectData += ' %.5f %.5f %.5f %.5f' % ( rect.minCorner[0], rect.minCorner[1], rect.size[0], rect.size[1] )
        file.write( '%s\n' % rectData )

    @property
    def rectNames( self ):
        return [ x[0] for x in self._rects ]

    @property
    def rects( self ):
        return [ x[1] for x in self._rects ]
    

class PopulationAnalysisTask( RectRegionAnalysisTask ):
    def __init__( self ):
        RectRegionAnalysisTask.__init__( self )

    def execute( self ):
        '''Perform the work of the task'''
        if ( self.work ):
            print 'Population analysis: %s' % ( self.workName )
            print "\tAccessing scb file:", self.scbName
            frameSet = NPFrameSet( self.scbName )
            names = self.rectNames
            rects = self.rects
            workPath = self.getWorkPath( 'population' )
            tempFile = os.path.join( workPath, self.workName )
            if ( self.work & AnalysisTask.COMPUTE ):
                print '\tComputing'
                s = time.clock()
                Crowd.computePopulation( frameSet, rects, tempFile, names )
                print '\t\tdone in %.2f seconds' % ( time.clock() - s )
            if ( self.work & AnalysisTask.VIS ):
                if ( not os.path.exists( tempFile + ".pop" ) ):
                    print "\tCan't create population plots - unable to locate file: %s" % tempFile
                    return
                print '\tComputing plots'
                s=time.clock()
                Crowd.plotPopulation( tempFile, frameSet.simStepSize, titlePrefix=self.workName, legendStr=names )
                print '\t\tdone in %.2f seconds' % ( time.clock() - s )

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return "POPULATION"


class FundDiagAnalysisTask( RectRegionAnalysisTask ):
    def __init__( self ):
        RectRegionAnalysisTask.__init__( self )

    def execute( self ):
        '''Perform the work of the task'''
        if ( self.work ):
            print 'Fundamental diagram analysis: %s' % ( self.workName )
            print "\tAccessing scb file:", self.scbName
            frameSet = NPFrameSet( self.scbName )
            names = self.rectNames
            rects = self.rects
            workPath = self.getWorkPath( 'fundDiag' )
            tempFile = os.path.join( workPath, self.workName )
            if ( self.work & AnalysisTask.COMPUTE ):
                print '\tComputing'
                s = time.clock()
                Crowd.computeFundDiag( frameSet, rects, tempFile, names )
                print '\t\tdone in %.2f seconds' % ( time.clock() - s )
            if ( self.work & AnalysisTask.VIS ):
                print '\tCreating plots'
                s=time.clock()
                Crowd.plotFundDiag( tempFile, rects, names )
                print '\t\tdone in %.2f seconds' % ( time.clock() - s )

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return "FUND DIAG"
                
if __name__ == '__main__':
    task = DensityAnalysisTask()
    task.setSCBFile( 'M:/anisotropic/experiment/stadium/mo11_smoothShift.scb' )
    task.setDomain( -10.00000, -3.80000, 12.4, 8.4 )
    task.setTimeStep( 0.1 )
    task.setWorkFolder( 'M:/anisotropic/experiment/stadium/data' )
    task.setTaskName( 'lores' )
    task.setWork( AnalysisTask.COMPUTE )
    task.setCellSize( 0.25 )
    task.setColorMap( 'black_body' )
    task.setOutImg( 'jpg' )
    task.setSmoothParam( 1.5 )
    task.execute()