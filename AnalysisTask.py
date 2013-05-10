from primitives import Vector2
from trajectory.scbData import NPFrameSet
import Crowd
import os
import time

import Kernels
import Signals
from GFSVis import visualizeGFS
from Grid import makeDomain
from ColorMap import *

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
        self.timeStep = 0.0
        self.workFldr = '.'

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
    def execute( self ):
        '''Execute the task'''
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
        if ( self.work ):
            print 'Flow analysis: %s' % ( self.workName )
            print "\tAccessing scb file:", self.scbName
            frameSet = NPFrameSet( self.scbName )
            names = [ x[0] for x in self.lines ]
            lines = [ x[1] for x in self.lines ]
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

class PopulationAnalysisTask( AnalysisTask ):
    def __init__( self ):
        AnalysisTask.__init__( self )
        self.rects = []

    def addRectDomain( self, rect, name ):
        '''Adds a rectangular domain to the task

        @param      rect        An instance of RectDomain.
        @param      name        A string.  The name of the flow line.
        '''
        self.rects.append( ( name, rect ) )
        
    def execute( self ):
        '''Perform the work of the task'''
        if ( self.work ):
            print 'Population analysis: %s' % ( self.workName )
            print "\tAccessing scb file:", self.scbName
            frameSet = NPFrameSet( self.scbName )
            names = [ x[0] for x in self.rects ]
            rects = [ x[1] for x in self.rects ]
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

class FundDiagAnalysisTask( AnalysisTask ):
    def __init__( self ):
        AnalysisTask.__init__( self )
        self.rects = []

    def addRectDomain( self, rect, name ):
        '''Adds a rectangular domain to the task

        @param      rect        An instance of RectDomain.
        @param      name        A string.  The name of the flow line.
        '''
        self.rects.append( ( name, rect ) )
        
    def execute( self ):
        '''Perform the work of the task'''
        if ( self.work ):
            print "Accessing scb file:", self.scbName
            frameSet = NPFrameSet( self.scbName )
            names = [ x[0] for x in self.rects ]
            rects = [ x[1] for x in self.rects ]
            workPath = self.getWorkPath( 'fundDiag' )
            tempFile = os.path.join( workPath, self.workName )
            if ( self.work & AnalysisTask.COMPUTE ):
                print 'Computing fundamental diagram analysis: %s' % ( self.workName )
                s = time.clock()
                Crowd.computeFundDiag( frameSet, rects, tempFile, names )
                print '    done in %.2f seconds' % ( time.clock() - s )
            if ( self.work & AnalysisTask.VIS ):
                print 'Computing population plots: %s'  % ( self.workName )
                s=time.clock()
                Crowd.plotFundDiag( tempFile, rects, names )
                print '    done in %.2f seconds' % ( time.clock() - s )
                
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