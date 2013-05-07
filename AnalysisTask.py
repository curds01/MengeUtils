from primitives import Vector2
from trajectory.scbData import NPFrameSet
import Crowd
import os
import time

class AnalysisTask:
    # Work to be performed by the task
    NO_WORK = 0
    COMPUTE = 1
    VIS = 2
    COMPUTE_VIS = 3
    
    def __init__( self ):
        '''Constructor for basic Analysis Task.

        @param      input       An instance of analyzeWidgets.InputWidget.
                                Contains all input parameters.
        '''
        self.work = self.NO_WORK
        self.workName = ''
        self.scbName = ''
        self.domainMin = None
        self.domainMax = None
        self.timeStep = 0.0
        self.workFldr = ''

    def requiresDomain( self ):
        '''Reports if this particular task requires domain information - the default is true.'''
        return False

    def setSCBFile( self, fileName ):
        '''Sets the scb file name for the analysis task.

        @param      fileName        A string.  The path to the input scb file name.
        '''
        self.scbName = fileName

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
        self.domainMin = Vector2( minX, minY )
        self.domainmax = Vector2( maxX, maxY )

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
    def execute( self ):
        '''Execute the task'''
        raise NotImplementedError
    
class DiscreteAnalysisTask( AnalysisTask ):
    '''An analysis task which relies on a discretization of the domain'''
    def __init__( self ):
        AnalysisTask.__init__( self )
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
        pass

class SpeedAnalysisTask( DiscreteAnalysisTask ):
    def __init__( self ):
        DiscreteAnalysisTask.__init__( self )

    def execute( self ):
        '''Perform the work of the task'''
        pass

class FlowAnalysisTask( AnalysisTask ):
    def __init__( self ):
        AnalysisTask.__init__( self )
        self.lines = []

    def addFlowLine( self, line, name ):
        '''Adds a flow line to the task.  A flow line is an ORIENTED segment.

        @param      line        An instance of FlowLine.
        @param      name        A string.  The name of the flow line.
        '''
        self.lines.append( ( name, line ) )
        
    def execute( self ):
        '''Perform the work of the task'''
        print "Accessing scb file:", self.scbName
        frameSet = NPFrameSet( self.scbName )
        if ( self.work ):
            names = [ x[0] for x in self.lines ]
            lines = [ x[1] for x in self.lines ]
            tempFile = os.path.join( self.workFldr, self.workName )
            if ( self.work & AnalysisTask.COMPUTE ):
                print 'Computing flow analysis: %s' % ( self.workName )
                s = time.clock()
                Crowd.computeFlow( frameSet, lines, tempFile, names )
                print '    done in %.2f seconds' % ( time.clock() - s )
            if ( self.work & AnalysisTask.VIS ):
                print 'Computing flow plots: %s'  % ( self.workName )
                s=time.clock()
                # this gives the ability to change the pre-computed names
                timeStep = frameSet.simStepSize
                if ( frameSet.version[0] == '1' ):
                    timeStep = self.timeStep
                Crowd.plotFlow( tempFile, frameSet.simStepSize, legendStr=names )
                print '    done in %.2f seconds' % ( time.clock() - s )

