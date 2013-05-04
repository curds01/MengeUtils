# GUI for analyzing crowd

from PyQt4 import QtGui, QtCore
from ColorMap import *
import Crowd
from math import pi, exp
import time
import os
from GLWidget import *
from obstacles import readObstacles
from qtcontext import *
from CrowdWork import CrowdAnalyzeThread
from config import Config
import sys
    
STDOUT = sys.stdout

class ConsoleFile( QtCore.QObject ):
    processMessage = QtCore.pyqtSignal(str)
    def __init__( self ):
        QtCore.QObject.__init__( self )
        self.buffer = ''

    def write( self, s ):
        self.buffer += s
        if ( s == '\n' ):
            self.processMessage.emit( self.buffer )
            self.buffer = ''

    def flush( self ):
        self.processMessage.emit( self.buffer )
        self.buffer = ''

class CrowdWindow( QtGui.QMainWindow):
    def __init__( self, configName='', parent = None ):
        self.workThread = None
        self.lastFolder = '.'
        QtGui.QMainWindow.__init__( self, parent )
        self.setWindowTitle( 'Crowd Analysis' )

        mainFrame = QtGui.QFrame( self )
        mainVLayout = QtGui.QVBoxLayout( mainFrame )
                
        splitter = QtGui.QSplitter( mainFrame )
        f = QtGui.QFrame( splitter )
        vLayout = QtGui.QVBoxLayout( f )

        self.createInputBox( vLayout )
        self.createOutputBox( vLayout )
        self.createAnalysisBox( vLayout )
        self.createRasterBox( vLayout )
        self.goBtn = QtGui.QPushButton( "GO!", f )
        QtCore.QObject.connect( self.goBtn, QtCore.SIGNAL('clicked(bool)'), self.process )
        
        vLayout.addWidget( self.goBtn, 2 )

        self.glWindow = GLWidget(  (10,10),(0,0), (10,10),(0,0), (1,1), splitter )        

        splitter.setStretchFactor( 0, 0 )
        splitter.setStretchFactor( 1, 1 )

        self.console = QtGui.QPlainTextEdit( mainFrame )
        self.console.setReadOnly( True )
        sys.stdout = ConsoleFile()
        sys.stdout.processMessage.connect( self.logMessage )
        
        mainVLayout.addWidget( splitter, 0 )
        mainVLayout.addWidget( self.console, 1 )

        self.setCentralWidget( mainFrame )

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
        fLayout.setColumnStretch( 3, 1 )
        
        # density
        fLayout.addWidget( QtGui.QLabel("Density"), 0, 0, 1, 1 )
        self.doDensityGUI = QtGui.QComboBox( box )
        self.doDensityGUI.addItems( ("No action", "Compute", "Visualize", "Compute and Vis." ) )
        fLayout.addWidget( self.doDensityGUI, 0, 1, 1, 3 )
        # speed
        
        fLayout.addWidget( QtGui.QLabel("Speed"), 1, 0, 1, 1 )
        self.doSpeedGUI = QtGui.QComboBox( box )
        self.doSpeedGUI.addItems( ("No action", "Compute", "Visualize", "Compute and Vis." ) )
        QtCore.QObject.connect( self.doSpeedGUI, QtCore.SIGNAL('currentIndexChanged(int)'), self.toggleSpeed )
        fLayout.addWidget( self.doSpeedGUI, 1, 1, 1, 3 )
        fLayout.addWidget( QtGui.QLabel( "Temporal window" ), 2, 1, 1, 1, QtCore.Qt.AlignRight )
        self.speedWindowGUI = QtGui.QSpinBox( box )
        self.speedWindowGUI.setMinimum( 1 )
        self.speedWindowGUI.setEnabled( False )
        fLayout.addWidget( self.speedWindowGUI, 2, 2, 1, 2 )

        # flow analysis - draw some lines and count the agents that cross the line
        fLayout.addWidget( QtGui.QLabel("Flow"), 3, 0, 1, 1 )
        self.doFlowGUI = QtGui.QComboBox( box )
        self.doFlowGUI.addItems( ("No action", "Compute", "Visualize", "Compute and Vis." ) )
        QtCore.QObject.connect( self.doFlowGUI, QtCore.SIGNAL('currentIndexChanged(int)'), self.flowChangedCB )
        fLayout.addWidget( self.doFlowGUI, 3, 1, 1, 1 )

        # line control
        self.linesGUI = QtGui.QComboBox( box )
        self.linesGUI.setEnabled( False )
        QtCore.QObject.connect( self.linesGUI, QtCore.SIGNAL('currentIndexChanged(int)'), self.lineChangedCB )
        fLayout.addWidget( QtGui.QLabel("Line No."), 3, 2, 1, 1, QtCore.Qt.AlignRight )
        fLayout.addWidget( self.linesGUI, 3, 3, 1, 1 )
        # buttons
        self.addFlowLineBtn = QtGui.QPushButton( 'Add' )
        self.addFlowLineBtn.setEnabled( False )
        QtCore.QObject.connect( self.addFlowLineBtn, QtCore.SIGNAL('clicked()'), self.addFlowLineCB )
        self.delFlowLineBtn = QtGui.QPushButton( 'Delete' )
        self.delFlowLineBtn.setEnabled( False )
        QtCore.QObject.connect( self.delFlowLineBtn, QtCore.SIGNAL('clicked()'), self.delFlowLineCB )
        self.editFlowLineBtn = QtGui.QPushButton( 'Edit' )
        self.editFlowLineBtn.setCheckable( True )
        self.editFlowLineBtn.setEnabled( False )
        QtCore.QObject.connect( self.editFlowLineBtn, QtCore.SIGNAL('toggled(bool)'), self.editFlowLineCB )
        self.flipFlowLineBtn = QtGui.QPushButton( 'Flip' )
        self.flipFlowLineBtn.setEnabled( False )
        QtCore.QObject.connect( self.flipFlowLineBtn, QtCore.SIGNAL('clicked()'), self.flipFlowLineCB )
        fLayout.addWidget( self.addFlowLineBtn, 4, 2, 1, 1 )
        fLayout.addWidget( self.delFlowLineBtn, 4, 3, 1, 1 )
        fLayout.addWidget( self.editFlowLineBtn, 5, 2, 1, 1 )
        fLayout.addWidget( self.flipFlowLineBtn, 5, 3, 1, 1 )
        fLayout.addWidget( QtGui.QLabel("Line Name"), 6, 1, 1, 1, QtCore.Qt.AlignRight )
        self.flowNameGUI = QtGui.QLineEdit()
        self.flowNameGUI.setEnabled( False )
        QtCore.QObject.connect( self.flowNameGUI, QtCore.SIGNAL('editingFinished()'), self.flowLineNameChangeCB )
        # TODO: Call back on editing the box
        fLayout.addWidget( self.flowNameGUI, 6, 2, 1, 2 )
        
        self.flowLineCtx = LineContext( self.cancelAddFlowLine )
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
        self.colorMapGUI.setCurrentIndex( 1 )
        fLayout.addWidget( self.colorMapGUI, 2, 1, 1, 1 )
        
        fLayout.addWidget( QtGui.QLabel( "Image format" ), 3, 0, 1, 1, QtCore.Qt.AlignRight )
        self.imgFormatGUI = QtGui.QComboBox( box )
        self.imgFormatGUI.addItems( ( 'jpg', 'bmp', 'png' ) )
        def formatIdxChanged( idx ):
            if ( idx == 2 ):
                self.logMessage( 'There is a memory leak for png format!' )
        QtCore.QObject.connect( self.imgFormatGUI, QtCore.SIGNAL('currentIndexChanged(int)'), formatIdxChanged )
        fLayout.addWidget( self.imgFormatGUI, 3, 1, 1, 1 )        
        
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
        self.fileMenu.setEnabled( False )
        self.fileMenu.addAction( self.readInConfigAct )
        self.fileMenu.addAction( self.saveInConfigAct )
        self.settingsMenu = self.menuBar().addMenu("&Settings")
        self.settingsMenu.addAction( self.readConfigAct )
        self.settingsMenu.addAction( self.saveConfigAct )

    def createStatusBar(self):
        self.statusBar().showMessage("Ready")

    def selectObstDlg( self ):
        """Spawns a dialog to select an obstacle file"""
        fileName = QtGui.QFileDialog.getOpenFileName( self, "Open obstacle file", self.lastFolder, "All Files (*.*)")
        if ( fileName ):
            self.obstFilePathGUI.setText( fileName )
            path, fName = os.path.split( str( fileName ) )
            self.lastFolder = path
            
    def selectSCBDlg( self ):
        """Spawns a dialog to select an scb file"""
        fileName = QtGui.QFileDialog.getOpenFileName( self, "Open SCB file", self.lastFolder, "SCB Files (*.scb)")
        if ( fileName ):
            self.scbFilePathGUI.setText( fileName )
            path, fName = os.path.split( str( fileName ) )
            self.lastFolder = path

    def selectOutPathDlg( self ):
        """Spawns a dialog to select an scb file"""
        fileName = QtGui.QFileDialog.getExistingDirectory( self, "Select Output Folder", self.lastFolder )
        if ( fileName ):
            self.outPathGUI.setText( fileName )
            self.lastFolder = fileName

    def selectIntPathDlg( self ):
        """Spawns a dialog to select an scb file"""
        fileName = QtGui.QFileDialog.getExistingDirectory( self, "Select Folder for Intermediate Files", self.lastFolder )
        if ( fileName ):
            self.tempPathGUI.setText( fileName )
            self.lastFolder = fileName

    def toggleSpeed( self ):
        self.speedWindowGUI.setEnabled( self.doSpeedGUI.currentIndex() != 0 )

    def flowChangedCB( self ):
        """When the flow computation state changes, update gui state"""
        active = self.doFlowGUI.currentIndex() != 0
        self.linesGUI.setEnabled( active )
        self.flowNameGUI.setEnabled( active )
        self.addFlowLineBtn.setEnabled( active )
        lineSelected = self.linesGUI.currentIndex() >= 0
        self.delFlowLineBtn.setEnabled( active and lineSelected )
        self.editFlowLineBtn.setEnabled( active and lineSelected )
        self.flipFlowLineBtn.setEnabled( active and lineSelected )
        if ( active ):
            self.glWindow.setUserContext( self.flowLineCtx )
        else:
            self.linesGUI.setCurrentIndex( -1 )
            self.editFlowLineBtn.setChecked( False )
            self.glWindow.setUserContext( None )
        self.glWindow.updateGL()

    def flowLineNameChangeCB( self ):
        '''Called when the name of a flow line is edited.'''
        idx = self.linesGUI.currentIndex()
        if ( idx > -1 ):
            self.flowLineCtx.setLineName( idx, str( self.flowNameGUI.text() ) )
            
    def lineChangedCB( self ):
        '''Called when the line number changes'''
        idx = self.linesGUI.currentIndex()
        active = idx > -1
        self.delFlowLineBtn.setEnabled( active )
        self.editFlowLineBtn.setEnabled( active )
        self.flipFlowLineBtn.setEnabled( active )
        if ( active ):
            self.flowNameGUI.setText( self.flowLineCtx.getName( idx ) )
        self.flowLineCtx.setActive( idx )
        self.glWindow.updateGL()
        if ( not active ):
            self.editFlowLineBtn.setChecked( False )

    def cancelAddFlowLine( self ):
        '''Called when an add flow line action is canceled'''
        self.linesGUI.removeItem( self.linesGUI.count() - 1 )
        self.linesGUI.setCurrentIndex( -1 )

    def addFlowLineCB( self ):
        '''When the add flow line is clicked, we add the flow line and update the GUI appropriately'''
        nextIdx = self.linesGUI.count()
        self.flowLineCtx.addLine()
        self.linesGUI.addItem( '%d' % nextIdx )
        self.linesGUI.setCurrentIndex( nextIdx )
        self.editFlowLineBtn.setChecked( True ) # this should call the callback and automatically enable the context to draw a line
        self.glWindow.updateGL()

    def delFlowLineCB( self ):
        '''Remove the current selected line'''
        idx = self.linesGUI.currentIndex()
        assert( idx > -1 )  # this button shouldn't be enabled if this isn't true
        self.flowLineCtx.deleteLine( idx )
        self.glWindow.updateGL()
        self.linesGUI.removeItem( self.linesGUI.count() - 1 )
        self.linesGUI.setCurrentIndex( -1 )

    def flipFlowLineCB( self ):
        '''Flip the current line'''
        idx = self.linesGUI.currentIndex()
        assert( idx > -1 )  # this button shouldn't be enabled if this isn't true
        self.flowLineCtx.flipLine( idx )
        self.glWindow.updateGL()

    def editFlowLineCB( self, checked ):
        '''Cause the current line to be editable'''
        idx = self.linesGUI.currentIndex()
        if ( checked ):
            assert( idx > -1 )  # this button shouldn't be enabled if this isn't true
            self.flowLineCtx.editLine( idx )
        else:
            self.flowLineCtx.stopEdit()
        self.glWindow.updateGL()
        
    def readInConfigFileDlg( self ):
        """Spawns a dialog to read an input configuration file"""
        pass

    def saveInConfigFileDlg( self ):
        """Spawns a dialog to save an input configuration file"""
        pass
    
    def readConfigFileDlg( self ):
        """Spawns a dialog to read an input configuration file"""
        fileName = QtGui.QFileDialog.getOpenFileName( self, "Read application config file", self.lastFolder, "Config files (*.cfg)" )
        if ( fileName ):
            self.readConfigFile( fileName )
            path, fName = os.path.split( str( fileName ) )
            self.lastFolder = path
    
    def saveConfigFileDlg( self ):
        """Spawns a dialog to save an input configuration file"""
        fileName = QtGui.QFileDialog.getSaveFileName( self, "Save Full Config As...", self.lastFolder, "Config files (*.cfg)" )
        if ( fileName ):
            config = self.collectFullConfig()
            file = open( fileName, 'w' )
            config.toFile( file )
            file.close()
            path, fName = os.path.split( str( fileName ) )
            self.lastFolder = path
    
    def readInConfigFile( self, fileName ):
        """Reads an input configuration file"""
        print "Read input file"

    def readConfigFile( self, fileName ):
        """Reads a configuration file for the full application"""
        try:
            f = open( fileName, 'r' )
            cfg = Config()
            cfg.fromFile( f )
            self.logMessage('Read full config file %s\n' % fileName )
            self.setFullConfig( cfg )
        except IOError:
            self.logMessage('Error reading full config file %s\n' % fileName )
            
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
            self.colorMapGUI.setCurrentIndex( self.colorMapGUI.findText( cfg[ 'colorMap' ].lower() ) )
        except:
            self.colorMapGUI.setCurrentIndex( 0 )
        try:
            self.doFlowGUI.setCurrentIndex( self.doFlowGUI.findText( cfg[ 'flow' ] ) )
        except:
            pass
        try:
            self.flowLineCtx.setFromString( cfg[ 'flowLines' ] )
            ids = range( self.flowLineCtx.getLineCount() )
            ids = map( lambda x: str( x ), ids )
            self.linesGUI.addItems( ids )
        except:
            pass
        try:
            self.imgFormatGUI.setCurrentIndex( self.imgFormatGUI.findText( cfg[ 'imgFormat' ] ) )
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
        cfg[ 'flow' ] = str( self.doFlowGUI.currentText() )
        cfg[ 'flowLines' ] = self.flowLineCtx.toConfigString()
        cfg[ 'imgFormat' ] = self.imgFormatGUI.currentText()
        return cfg

    def collectInputConfig( self ):
        '''Returns a Config object reflecting the configuration of the input panel'''
        pass

    def logMessage( self, msg ):
        '''Append a message to the console'''
        self.console.appendPlainText( msg )

    def workDone( self ):
        '''Work has finished, reactivate the button'''
        self.goBtn.setEnabled( True )
        QtCore.QObject.disconnect( self.workThread, QtCore.SIGNAL('finished()'), self.workDone )
        self.workThread = None
        

    def process( self ):
        if ( self.workThread == None ):
            self.goBtn.setEnabled( False )
            cfg = self.collectFullConfig()
            cfg[ 'DENSE_ACTION' ] = self.doDensityGUI.currentIndex()
            cfg[ 'SPEED_ACTION' ] = self.doSpeedGUI.currentIndex()
##            cfg[ 'ADVEC_ACTION' ] = self.doFlowAdvecGUI.currentIndex()
##            cfg[ 'ADVEC_LINES' ] = self.flowAdvecLineCtx.lines
            cfg[ 'FLOW_ACTION' ] = self.doFlowGUI.currentIndex()
            self.workThread = CrowdAnalyzeThread( cfg )
            # Make connections that allow the thread to inform the gui when finished and output messages
            QtCore.QObject.connect( self.workThread, QtCore.SIGNAL('finished()'), self.workDone )
            self.workThread.start()
            self.logMessage( '\nStarting processing' )
        else:
            self.logMessage( 'Already running' )


    def loadObstacle( self ):
        """Causes the indicated obstacle file to be loaded into the OpenGL viewer"""
        obstFileName = str( self.obstFilePathGUI.text() )
        if ( obstFileName ):
            self.logMessage('Reading obstacle file: %s' % obstFileName )
            try:
                flipY = False
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
                self.logMessage('Error reading obstacle file: %s' % obstFileName )
        else:
            self.logMessage('No obstacle file to load' )
                                          

if __name__ == '__main__':
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