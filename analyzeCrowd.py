# GUI for analyzing crowd

from PyQt4 import QtGui, QtCore
from ColorMap import *
import Crowd
from math import pi, exp
import time
import os
from GLWidget import *
from roadmapBuilder import readObstacles
from Context import *

class Config:
    """An analysis configuration state"""
    # use to execute a run, can also be saved and read to a file
    def __init__( self ):
        self.state = {}

    def __getitem__( self, key ):
        return self.state[ key ]

    def __setitem__( self, key, value ):
        self.state[ key ] = value

    def __str__( self ):
        s = ''
        for key, val in self.state.items():
            s += '%s || %s\n' % ( key, val )
        return s

    def toFile( self, f ):
        f.write( str( self ) )

    def fromFile( self, f ):
        self.state = {}
        for x in f.xreadlines():
            tok = x.split('||')
            self.state[ tok[0].strip() ] = tok[1].strip()
        
class CrowdWindow( QtGui.QMainWindow):
    def __init__( self, configName='', parent = None ):
        QtGui.QMainWindow.__init__( self, parent )
        self.setWindowTitle( 'Crowd Analysis' )
        splitter = QtGui.QSplitter( self )

        f = QtGui.QFrame( splitter )
        vLayout = QtGui.QVBoxLayout( f )

        self.createInputBox( vLayout )
        self.createOutputBox( vLayout )
        self.createAnalysisBox( vLayout )
        self.createRasterBox( vLayout )
        self.goBtn = QtGui.QPushButton( "GO!", f )
        QtCore.QObject.connect( self.goBtn, QtCore.SIGNAL('clicked(bool)'), self.process )
        
        vLayout.addWidget( self.goBtn, 2 )

        self.console = QtGui.QPlainTextEdit( splitter )
        self.console.setReadOnly( True )

        self.glWindow = GLWidget(  (10,10),(0,0), (10,10),(0,0), (1,1), splitter )        

        self.setCentralWidget(splitter )
        splitter.setStretchFactor( 0, 0 )
        splitter.setStretchFactor( 1, 0 )
        splitter.setStretchFactor( 2, 1 )

        self.createActions()
        self.createMenus()
        self.createStatusBar()

        if ( configName == '' ):        
            self.readConfigFile( 'default.cfg' )
        else:
            self.readConfigFile( configName )

    def createInputBox( self, vLayout ):
        # input frame
        inputBox = QtGui.QGroupBox("Input")
        fLayout = QtGui.QGridLayout( inputBox )
        fLayout.setColumnStretch( 0, 0 )
        fLayout.setColumnStretch( 1, 1 )
        fLayout.setColumnStretch( 2, 0 )
        # scb file
        fLayout.addWidget( QtGui.QLabel( "SCB file" ), 0, 0, 1, 1, QtCore.Qt.AlignRight )
        self.scbFilePathGUI = QtGui.QPushButton( '', inputBox )
        QtCore.QObject.connect( self.scbFilePathGUI, QtCore.SIGNAL('clicked(bool)'), self.selectSCBDlg )
        fLayout.addWidget( self.scbFilePathGUI, 0, 1, 1, 2 )

        # domain
        fLayout.addWidget( QtGui.QLabel( "Min. Point" ), 1, 0, 1, 1, QtCore.Qt.AlignRight )
        self.domainMinXGUI = QtGui.QDoubleSpinBox( inputBox )
        self.domainMinXGUI.setRange( -1e6, 1e6 )
        fLayout.addWidget( self.domainMinXGUI, 1, 1, 1, 1 )
        self.domainMinYGUI = QtGui.QDoubleSpinBox( inputBox )
        self.domainMinYGUI.setRange( -1e6, 1e6 )
        fLayout.addWidget( self.domainMinYGUI, 1, 2, 1, 1 )

        fLayout.addWidget( QtGui.QLabel( "Domain Size" ), 2, 0, 1, 1, QtCore.Qt.AlignRight )
        self.domainSizeXGUI = QtGui.QDoubleSpinBox( inputBox )
        self.domainSizeXGUI.setRange( -1e6, 1e6 )
        fLayout.addWidget( self.domainSizeXGUI, 2, 1, 1, 1 )
        self.domainSizeYGUI = QtGui.QDoubleSpinBox( inputBox )
        self.domainSizeYGUI.setRange( -1e6, 1e6 )
        fLayout.addWidget( self.domainSizeYGUI, 2, 2, 1, 1 )        

        # timestep
        fLayout.addWidget( QtGui.QLabel( "Time step" ), 3, 0, 1, 1, QtCore.Qt.AlignRight )
        self.timeStepGui = QtGui.QDoubleSpinBox( inputBox )
        self.timeStepGui.setDecimals( 4 )
        fLayout.addWidget( self.timeStepGui, 3, 1, 1, 2 )

        # obstacle file
        fLayout.addWidget( QtGui.QLabel( "Obstacle file" ), 4, 0, 1, 1, QtCore.Qt.AlignRight )
        self.obstFilePathGUI = QtGui.QPushButton( '', inputBox )
        QtCore.QObject.connect( self.obstFilePathGUI, QtCore.SIGNAL('clicked(bool)'), self.selectObstDlg )
        fLayout.addWidget( self.obstFilePathGUI, 4, 1, 1, 1 )
        self.loadObstBtn = QtGui.QPushButton( "Load", inputBox )
        QtCore.QObject.connect( self.loadObstBtn, QtCore.SIGNAL('clicked(bool)'), self.loadObstacle )
        fLayout.addWidget( self.loadObstBtn, 4, 2, 1, 1 )

        
        vLayout.addWidget( inputBox, 0 )   

    def createOutputBox( self, vLayout ):
        # input frame
        inputBox = QtGui.QGroupBox("Output")
        fLayout = QtGui.QGridLayout( inputBox )
        fLayout.setColumnStretch( 0, 0 )
        fLayout.setColumnStretch( 1, 1 )
        # Folder path for output image files
        fLayout.addWidget( QtGui.QLabel( "Output folder" ), 0, 0, 1, 1, QtCore.Qt.AlignRight )
        self.outPathGUI = QtGui.QPushButton( '', inputBox )
        QtCore.QObject.connect( self.outPathGUI, QtCore.SIGNAL('clicked(bool)'), self.selectOutPathDlg )
        fLayout.addWidget( self.outPathGUI, 0, 1, 1, 1 )

        # Folder path for intermediary files
        fLayout.addWidget( QtGui.QLabel( "Interm. File Path" ), 1, 0, 1, 1, QtCore.Qt.AlignRight )
        self.tempPathGUI = QtGui.QPushButton( '', inputBox )
        QtCore.QObject.connect( self.tempPathGUI, QtCore.SIGNAL('clicked(bool)'), self.selectIntPathDlg )
        fLayout.addWidget( self.tempPathGUI, 1, 1, 1, 1 )

        # Folder name for intermediary files
        fLayout.addWidget( QtGui.QLabel( "Interm. File Name" ), 2, 0, 1, 1, QtCore.Qt.AlignRight )
        self.tempNameGUI = QtGui.QLineEdit( inputBox )
        fLayout.addWidget( self.tempNameGUI, 2, 1, 1, 1 )        

        vLayout.addWidget( inputBox, 0 )         

    def createAnalysisBox( self, vLayout ):
        # input frame
        box = QtGui.QGroupBox("Analysis")
        fLayout = QtGui.QGridLayout( box )
        fLayout.setColumnStretch( 0, 0 )
        fLayout.setColumnStretch( 1, 0 )
        fLayout.setColumnStretch( 2, 1 )
        
        # density
        fLayout.addWidget( QtGui.QLabel("Density"), 0, 0, 1, 1 )
        self.doDensityGUI = QtGui.QComboBox( box )
        self.doDensityGUI.addItems( ("No action", "Compute", "Visualize", "Compute and Vis." ) )
        fLayout.addWidget( self.doDensityGUI, 0, 1, 1, 2 )
        # speed
        
        fLayout.addWidget( QtGui.QLabel("Speed"), 1, 0, 1, 1 )
        self.doSpeedGUI = QtGui.QComboBox( box )
        self.doSpeedGUI.addItems( ("No action", "Compute", "Visualize", "Compute and Vis." ) )
        QtCore.QObject.connect( self.doSpeedGUI, QtCore.SIGNAL('currentIndexChanged(int)'), self.toggleSpeed )
        fLayout.addWidget( self.doSpeedGUI, 1, 1, 1, 2 )
        fLayout.addWidget( QtGui.QLabel( "Temporal window" ), 2, 1, 1, 1, QtCore.Qt.AlignRight )
        self.speedWindowGUI = QtGui.QSpinBox( box )
        self.speedWindowGUI.setMinimum( 1 )
        self.speedWindowGUI.setEnabled( False )
        fLayout.addWidget( self.speedWindowGUI, 2, 2, 1, 1 )

        # flow advection
        fLayout.addWidget( QtGui.QLabel("Advec. Flow"), 3, 0, 1, 1 )
        self.doFlowAdvecGUI = QtGui.QComboBox( box )
        self.doFlowAdvecGUI.addItems( ("No action", "Compute", "Visualize", "Compute and Vis." ) )
        QtCore.QObject.connect( self.doFlowAdvecGUI, QtCore.SIGNAL('currentIndexChanged(int)'), self.flowAdvecChanged )
        fLayout.addWidget( self.doFlowAdvecGUI, 3, 1, 1, 1 )
        self.setFlowAdvecLine = QtGui.QPushButton( 'Set line' )
        self.setFlowAdvecLine.setCheckable( True )
        self.setFlowAdvecLine.setEnabled( False )
        QtCore.QObject.connect( self.setFlowAdvecLine, QtCore.SIGNAL('toggled(bool)'), self.setFlowAdvecLineCB )
        fLayout.addWidget( self.setFlowAdvecLine, 3, 2, 1, 1 )
        fLayout.addWidget( QtGui.QLabel( "Number of lines" ), 4, 1, 1, 1, QtCore.Qt.AlignRight )
        self.advecFlowCountGui = QtGui.QSpinBox( box )
        self.advecFlowCountGui.setMinimum( 1 )
        self.advecFlowCountGui.setEnabled( False )
        QtCore.QObject.connect( self.advecFlowCountGui, QtCore.SIGNAL('valueChanged(int)'), self.flowCountChange )
        fLayout.addWidget( self.advecFlowCountGui, 4, 2, 1, 1 )
        self.flowAdvecLineCtx = LineContext( 1 )
        vLayout.addWidget( box, 0 )

    def createRasterBox( self, vLayout ):
        # input frame
        box = QtGui.QGroupBox("Raster Settings")
        fLayout = QtGui.QGridLayout( box )
        fLayout.setColumnStretch( 0, 0 )
        fLayout.setColumnStretch( 1, 1 )

        fLayout.addWidget( QtGui.QLabel( "Kernel Size" ), 0, 0, 1, 1, QtCore.Qt.AlignRight )
        self.kernelSizeGUI = QtGui.QDoubleSpinBox( box )
        fLayout.addWidget( self.kernelSizeGUI, 0, 1, 1, 1 )

        fLayout.addWidget( QtGui.QLabel( "Cell Size" ), 1, 0, 1, 1, QtCore.Qt.AlignRight )
        self.cellSizeGUI = QtGui.QDoubleSpinBox( box )
        fLayout.addWidget( self.cellSizeGUI, 1, 1, 1, 1 )

        fLayout.addWidget( QtGui.QLabel( "Color Map" ), 2, 0, 1, 1, QtCore.Qt.AlignRight )
        self.colorMapGUI = QtGui.QComboBox( box )
        cmaps = COLOR_MAPS.keys()
        cmaps.sort()
        self.colorMapGUI.addItems( cmaps )
        fLayout.addWidget( self.colorMapGUI, 2, 1, 1, 1 )        
        
        vLayout.addWidget( box, 0 )
                
    def createActions( self ):
        """Creates the actions for menu actions"""
        self.readInConfigAct = QtGui.QAction( "&Read Input Config",
                                            self, statusTip="Read config file for input",
                                            triggered=self.readInConfigFileDlg )
        self.saveInConfigAct = QtGui.QAction( "&Save Input Config",
                                            self, statusTip="Save config file for input",
                                            triggered=self.saveInConfigFileDlg )
        self.readConfigAct = QtGui.QAction( "&Read Full Config",
                                            self, statusTip="Read config file for full application",
                                            triggered=self.readConfigFileDlg )
        self.saveConfigAct = QtGui.QAction( "&Save Full Config",
                                            self, statusTip="Save config file for full application",
                                            triggered=self.saveConfigFileDlg )

    def createMenus( self ):
        self.fileMenu = self.menuBar().addMenu("&Input")
        self.fileMenu.addAction( self.readInConfigAct )
        self.fileMenu.addAction( self.saveInConfigAct )
        self.fileMenu = self.menuBar().addMenu("&Settings")
        self.fileMenu.addAction( self.readConfigAct )
        self.fileMenu.addAction( self.saveConfigAct )

    def createStatusBar(self):
        self.statusBar().showMessage("Ready")

    def selectObstDlg( self ):
        """Spawns a dialog to select an obstacle file"""
        startPath = '.'
        currPath = str( self.obstFilePathGUI.text() )
        if ( currPath ):
            startPath = os.path.split( currPath )[0]
        fileName = QtGui.QFileDialog.getOpenFileName( self, "Open obstacle file", startPath, "All Files (*.*)")
        if ( fileName ):
            self.obstFilePathGUI.setText( fileName )
            
    def selectSCBDlg( self ):
        """Spawns a dialog to select an scb file"""
        fileName = QtGui.QFileDialog.getOpenFileName( self, "Open SCB file", ".", "SCB Files (*.scb)")
        if ( fileName ):
            self.scbFilePathGUI.setText( fileName )

    def selectOutPathDlg( self ):
        """Spawns a dialog to select an scb file"""
        fileName = QtGui.QFileDialog.getExistingDirectory( self, "Select Output Folder", ".")
        if ( fileName ):
            self.outPathGUI.setText( fileName )

    def selectIntPathDlg( self ):
        """Spawns a dialog to select an scb file"""
        fileName = QtGui.QFileDialog.getExistingDirectory( self, "Select Folder for Intermediate Files", ".")
        if ( fileName ):
            self.tempPathGUI.setText( fileName )

    def toggleSpeed( self ):
        self.speedWindowGUI.setEnabled( self.doSpeedGUI.currentIndex() != 0 )

    def flowCountChange( self, count ):
        '''Changes the number of lines that can be drawn in the context'''
        if ( self.flowAdvecLineCtx.setMaximumLineCount( count) ):
            self.glWindow.updateGL()
        
    def flowAdvecChanged( self ):
        """When the flow advec computation state changes, the button might deactivate"""
        active = self.doFlowAdvecGUI.currentIndex() != 0
        self.setFlowAdvecLine.setEnabled( active )
        self.advecFlowCountGui.setEnabled( active )

    def setFlowAdvecLineCB( self, checked ):
        """Flow advection works by marking agents with a line"""
        if ( checked ):
            self.glWindow.setUserContext( self.flowAdvecLineCtx )
        else:
            self.glWindow.setUserContext( None )
        self.glWindow.updateGL()
    
    def readInConfigFileDlg( self ):
        """Spawns a dialog to read an input configuration file"""
        pass

    def saveInConfigFileDlg( self ):
        """Spawns a dialog to save an input configuration file"""
        pass
    
    def readConfigFileDlg( self ):
        """Spawns a dialog to read an input configuration file"""
        fileName = QtGui.QFileDialog.getOpenFileName( self, "Read application config file", ".", "Config files (*.cfg)" )
        if ( fileName ):
            self.readConfigFile( fileName )
    
    def saveConfigFileDlg( self ):
        """Spawns a dialog to save an input configuration file"""
        fileName = QtGui.QFileDialog.getSaveFileName( self, "Save Full Config As...", ".", "Config files (*.cfg)" )
        if ( fileName ):
            config = self.collectFullConfig()
            file = open( fileName, 'w' )
            config.toFile( file )
            file.close()
            
    
    def readInConfigFile( self, fileName ):
        """Reads an input configuration file"""
        print "Read input file"

    def readConfigFile( self, fileName ):
        """Reads a configuration file for the full application"""
        try:
            f = open( fileName, 'r' )
            cfg = Config()
            cfg.fromFile( f )
            self.console.appendPlainText('Read full config file %s\n' % fileName )
            self.setFullConfig( cfg )
        except IOError:
            self.console.appendPlainText('Error reading full config file %s\n' % fileName )
            
    def setFullConfig( self, cfg ):
        """Given a config object for the full application, sets the application state"""
        try:
            self.scbFilePathGUI.setText( cfg[ 'SCB' ] )
        except:
            pass
        try:
            self.domainMinXGUI.setValue( float( cfg[ 'minPtX' ] ) )
        except:
            pass
        try:
            self.domainMinYGUI.setValue( float( cfg[ 'minPtY' ] ) )
        except:
            pass
        try:
            self.domainSizeXGUI.setValue( float( cfg[ 'sizeX' ] ) )
        except:
            pass
        try:
            self.domainSizeYGUI.setValue( float( cfg[ 'sizeY' ] ) )
        except:
            pass
        try:
            self.timeStepGui.setValue( float( cfg[ 'timeStep' ] ) )
        except:
            pass
        try:
            self.obstFilePathGUI.setText( cfg[ 'obstacle' ] )
        except:
            pass
        try:
            self.outPathGUI.setText( cfg[ 'outDir' ] )
        except:
            pass
        try:
            self.tempPathGUI.setText( cfg[ 'tempDir' ] )
        except:
            pass
        try:
            self.tempNameGUI.setText( cfg[ 'tempName' ] )
        except:
            pass
        try:
            self.doDensityGUI.setCurrentIndex( self.doDensityGUI.findText( cfg[ 'density' ] ) )
        except:
            pass
        try:
            self.doSpeedGUI.setCurrentIndex( self.doSpeedGUI.findText( cfg[ 'speed' ] ) )
            self.toggleSpeed()
        except:
            pass
        try:
            self.speedWindowGUI.setValue( int( cfg['speedWindow'] ) )
        except:
            pass
        try:
            self.kernelSizeGUI.setValue( float( cfg[ 'kernelSize' ] ) )
        except:
            pass
        try:
            self.cellSizeGUI.setValue( float( cfg[ 'cellSize' ] ) )
        except:
            pass
        try:
            self.colorMapGUI.setCurrentIndex( self.colorMapGUI.findText( cfg[ 'colorMap' ] ) )
        except:
            pass
        try:
            self.doFlowAdvecGUI.setCurrentIndex( self.doFlowAdvecGUI.findText( cfg[ 'advecFlow' ] ) )
        except:
            pass
        try:
            self.flowAdvecLineCtx.setFromString( cfg[ 'advecFlowLines' ] )
        except:
            pass
        try:
            self.advecFlowCountGui.setValue( self.flowAdvecLineCtx.getMaxLineCount() )
        except:
            pass
        self.glWindow.updateGL()

                    
    def collectFullConfig( self ):
        '''Returns a Config object reflecting the full configuration of the application'''
        cfg = Config()
        cfg[ 'SCB' ] = str( self.scbFilePathGUI.text() )
        cfg[ 'minPtX' ] = self.domainMinXGUI.value()
        cfg[ 'minPtY' ] = self.domainMinYGUI.value()
        cfg[ 'sizeX' ] = self.domainSizeXGUI.value()
        cfg[ 'sizeY' ] = self.domainSizeYGUI.value()
        cfg[ 'timeStep' ] = self.timeStepGui.value()
        cfg[ 'obstacle' ] = str( self.obstFilePathGUI.text() )
        cfg[ 'outDir' ] = str( self.outPathGUI.text() )
        cfg[ 'tempDir' ] = str( self.tempPathGUI.text() )
        cfg[ 'tempName' ] = str( self.tempNameGUI.text() )
        cfg[ 'density' ] = str( self.doDensityGUI.currentText() )
        cfg[ 'speed' ] = str( self.doSpeedGUI.currentText() )
        cfg[ 'speedWindow' ] = self.speedWindowGUI.value()
        cfg[ 'kernelSize' ] = self.kernelSizeGUI.value()
        cfg[ 'cellSize' ] = self.cellSizeGUI.value()
        cfg[ 'colorMap' ] = str( self.colorMapGUI.currentText() )
        cfg[ 'advecFlow' ] = str( self.doFlowAdvecGUI.currentText() )
        cfg[ 'advecFlowLines' ] = self.flowAdvecLineCtx.toConfigString()
        return cfg

    def collectInputConfig( self ):
        '''Returns a Config object reflecting the configuration of the input panel'''
        pass    

    def process( self ):
        self.console.appendPlainText( '\nStarting processing' )
        cfg = self.collectFullConfig()
        cellSize = float( cfg[ 'cellSize' ] )
        domainSize = Crowd.Vector2( float( cfg[ 'sizeX' ] ), float( cfg[ 'sizeY' ] ) )
        domainMin = Crowd.Vector2( float( cfg[ 'minPtX' ] ), float( cfg[ 'minPtY' ] ) )
        res = (int( domainSize.x / cellSize ), int( domainSize.y / cellSize ) )
        scbFile = cfg[ 'SCB' ] 

        frameSet = Crowd.FrameSet( scbFile )
        print cfg['tempDir'], cfg['tempName']
        tempFile = os.path.join( cfg[ 'tempDir' ], cfg[ 'tempName' ] )
        grids = Crowd.GridFileSequence( tempFile )
        colorMap = COLOR_MAPS[ cfg[ 'colorMap' ] ]()

        R = cfg[ 'kernelSize' ]
        
        def distFunc( dist, radiusSqd ):
            """Constant distance function"""
            # This is the local density function provided by Helbing
            return 1.0 / ( pi * radiusSqd ) * exp( - (dist * dist / radiusSqd ) )        

        dfunc = lambda x: distFunc( x, R * R )

        densityAction = self.doDensityGUI.currentIndex()
        if ( densityAction == 1 or densityAction == 3 ):
            self.console.appendPlainText( 'Computing densities...' )
            s = time.clock()
            grids.computeDensity( domainMin, domainSize, res, dfunc, 3 * R, frameSet )
            self.console.appendPlainText( 'done in %.2f seconds' % ( time.clock() - s ) )
        if ( densityAction >= 2 ):
            imageName = os.path.join( cfg[ 'outDir' ], 'density_' )
            self.console.appendPlainText( 'Creating density images...' )
            s = time.clock()
            grids.makeImages( colorMap, imageName, 'density' )
            pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
            self.console.appendPlainText( 'done in %.2f seconds' % ( time.clock() - s ) )

        speedAction = self.doSpeedGUI.currentIndex()
        if ( speedAction == 1 or speedAction == 3 ):
            self.console.appendPlainText( 'Computing speeds...' )
            s = time.clock()
            grids.computeSpeeds( domainMin, domainSize, res, dfunc, 3 * R, frameSet, float( cfg[ 'timeStep' ] ), int( cfg[ 'speedWindow' ] ) )
            self.console.appendPlainText( 'done in %.2f seconds' % ( time.clock() - s ) )
        if ( speedAction >= 2 ):
            imageName = os.path.join( cfg[ 'outDir' ], 'speed_' )
            self.console.appendPlainText( 'Creating speed images...' )
            s = time.clock()
            grids.makeImages( colorMap, imageName, 'speed' )
            pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
            self.console.appendPlainText( 'done in %.2f seconds' % ( time.clock() - s ) )            

        advecAction = self.doFlowAdvecGUI.currentIndex()
        if ( advecAction == 1 or advecAction == 3 ):
            self.console.appendPlainText( 'Computing advection...' )
            s = time.clock()
            grids.computeAdvecFlow( domainMin, domainSize, res, dfunc, 3.0, 3 * R, frameSet, self.flowAdvecLineCtx.lines )
            self.console.appendPlainText( 'done in %.2f seconds' % ( time.clock() - s ) )
        if ( advecAction >= 2 ):
            imageName = os.path.join( cfg[ 'outDir' ], 'advec_' )
            self.console.appendPlainText( 'Creating flow advection images...' )
            s = time.clock()
            grids.makeImages( colorMap, imageName, 'advec' )
            pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
            self.console.appendPlainText( 'done in %.2f seconds' % ( time.clock() - s ) )            

    def loadObstacle( self ):
        """Causes the indicated obstacle file to be loaded into the OpenGL viewer"""
        obstFileName = str( self.obstFilePathGUI.text() )
        if ( obstFileName ):
            self.console.appendPlainText('Reading obstacle file: %s' % obstFileName )
            try:
                flipY = True
                obstacles, bb = readObstacles( obstFileName, flipY )                
                self.glWindow.addDrawables( obstacles )
                w = bb.max.x - bb.min.x
                h = bb.max.y - bb.min.y
                self.glWindow.setBG( (w,h), (bb.min.x, bb.min.y) )
                self.glWindow.setView( (w,h), (bb.min.x, bb.min.y) )
                glSize = self.glWindow.size()
                self.glWindow.resizeGL( glSize.width(), glSize.height() )
                self.glWindow.updateGL()
            except:
                self.console.appendPlainText('Error reading obstacle file: %s' % obstFileName )
        else:
            self.console.appendPlainText('No obstacle file to load' )
                                          

if __name__ == '__main__':
    import sys
    import pygame
    pygame.init()
    app = QtGui.QApplication( sys.argv )
    configName = ''
    if ( len( sys.argv ) > 1 ):
        configName = sys.argv[1]
    gui = CrowdWindow( configName )
    gui.show()
    gui.resize( 1024, 480 )
    app.exec_()