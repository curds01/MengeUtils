# GUI for analyzing crowd

from PyQt4 import QtGui, QtCore
from ColorMap import *
import Crowd
from math import pi, exp
import time
import os
from GLWidget import *
##from obstacles import readObstacles
from qtcontext import *
from CrowdWork import CrowdAnalyzeThread
from config import Config
import sys
from analyzeWidgets import CollapsableWidget, VFlowLayout, InputWidget, AnlaysisWidget, SystemResource
    
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
        mainVLayout = QtGui.QHBoxLayout( mainFrame )

        # Feedback panel
        splitter = QtGui.QSplitter( mainFrame )
        splitter.setOrientation( QtCore.Qt.Vertical )
        # GL Window
        self.glWindow = GLWidget(  (10,10),(0,0), (10,10),(0,0), (1,1), splitter )
        self.glWindow.setMinimumSize( QtCore.QSize( 640, 480 ) )
        # Console
        self.console = QtGui.QPlainTextEdit( splitter )
        self.console.setReadOnly( True )
        sys.stdout = ConsoleFile()
        sys.stdout.processMessage.connect( self.logMessage )

        # set up the shared resource
        self.rsrc = SystemResource()
        self.rsrc.glWindow = self.glWindow
        self.rsrc.logMessage = self.logMessage
        
        # Main configuration panel                
        self.f = QtGui.QFrame()
        vLayout = QtGui.QVBoxLayout()        
        self.inputBox = InputWidget( self.rsrc, self )
        vLayout.addWidget( self.inputBox )
        self.analysisBox = AnlaysisWidget( self.rsrc, self )
        vLayout.addWidget( self.analysisBox )  
        vLayout.addStretch( 1 )
        self.f.setLayout( vLayout )

        mainVLayout.addWidget( self.f, 0 )  
        mainVLayout.addWidget( splitter, 1 )

        self.setCentralWidget( mainFrame )

        self.createActions()
        self.createMenus()
        self.createStatusBar()

        if ( configName == '' ):        
            self.readConfigFile( configName )

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

    def readInConfigFileDlg( self ):
        """Spawns a dialog to read an input configuration file"""
        pass

    def readInConfigFile( self, fileName ):
        """Reads an input configuration file"""
        print "Read input file"

    def saveInConfigFileDlg( self ):
        """Spawns a dialog to save an input configuration file"""
        pass
    
    def readConfigFileDlg( self ):
        """Spawns a dialog to read a full project configuration file"""
        fileName = QtGui.QFileDialog.getOpenFileName( self, "Read application config file", self.lastFolder, "Config files (*.cfg)" )
        if ( fileName ):
            self.readConfigFile( fileName )
            path, fName = os.path.split( str( fileName ) )
            self.lastFolder = path
    
    def readConfigFile( self, fileName ):
        """Reads a configuration file for the full application"""
        try:
            f = open( fileName, 'r' )
            cfg = Config()
            cfg.fromFile( f )
            print('Read full config file %s\n' % fileName )
            self.setFullConfig( cfg )
        except IOError:
            print('Error reading full config file %s\n' % fileName )
            
    def saveConfigFileDlg( self ):
        """Spawns a dialog to save a full project configuration file"""
        fileName = QtGui.QFileDialog.getSaveFileName( self, "Save Full Config As...", self.lastFolder, "Config files (*.cfg)" )
        if ( fileName ):
            config = self.collectFullConfig()
            file = open( fileName, 'w' )
            config.toFile( file )
            file.close()
            path, fName = os.path.split( str( fileName ) )
            self.lastFolder = path
    
    def setFullConfig( self, cfg ):
        """Given a config object for the full application, sets the application state"""
        self.inputBox.setFromConfig( cfg )

##        try:
##            self.outPathGUI.setText( cfg[ 'outDir' ] )
##        except:
##            pass
##        try:
##            self.tempPathGUI.setText( cfg[ 'tempDir' ] )
##        except:
##            pass
##        try:
##            self.tempNameGUI.setText( cfg[ 'tempName' ] )
##        except:
##            pass
##        try:
##            self.doDensityGUI.setCurrentIndex( self.doDensityGUI.findText( cfg[ 'density' ] ) )
##        except:
##            pass
##        try:
##            self.doSpeedGUI.setCurrentIndex( self.doSpeedGUI.findText( cfg[ 'speed' ] ) )
##        except:
##            pass
##        try:
##            self.speedWindowGUI.setValue( int( cfg['speedWindow'] ) )
##        except:
##            pass
##        try:
##            self.kernelSizeGUI.setValue( float( cfg[ 'kernelSize' ] ) )
##        except:
##            pass
##        try:
##            self.cellSizeGUI.setValue( float( cfg[ 'cellSize' ] ) )
##        except:
##            pass
##        try:
##            self.colorMapGUI.setCurrentIndex( self.colorMapGUI.findText( cfg[ 'colorMap' ].lower() ) )
##        except:
##            self.colorMapGUI.setCurrentIndex( 0 )
##        try:
##            self.doFlowGUI.setCurrentIndex( self.doFlowGUI.findText( cfg[ 'flow' ] ) )
##        except:
##            pass
##        try:
##            self.flowLineCtx.setFromString( cfg[ 'flowLines' ] )
##            ids = range( self.flowLineCtx.getLineCount() )
##            ids = map( lambda x: str( x ), ids )
##            self.linesGUI.addItems( ids )
##        except:
##            pass
##        try:
##            self.imgFormatGUI.setCurrentIndex( self.imgFormatGUI.findText( cfg[ 'imgFormat' ] ) )
##        except:
##            pass
##        self.glWindow.updateGL()

                    
    def collectFullConfig( self ):
        '''Returns a Config object reflecting the full configuration of the application'''
        cfg = Config()
        self.inputBox.setConfig( cfg )
##        cfg[ 'outDir' ] = str( self.outPathGUI.text() )
##        cfg[ 'tempDir' ] = str( self.tempPathGUI.text() )
##        cfg[ 'tempName' ] = str( self.tempNameGUI.text() )
##        cfg[ 'density' ] = str( self.doDensityGUI.currentText() )
##        cfg[ 'speed' ] = str( self.doSpeedGUI.currentText() )
##        cfg[ 'speedWindow' ] = self.speedWindowGUI.value()
##        cfg[ 'kernelSize' ] = self.kernelSizeGUI.value()
##        cfg[ 'cellSize' ] = self.cellSizeGUI.value()
##        cfg[ 'colorMap' ] = str( self.colorMapGUI.currentText() )
##        cfg[ 'flow' ] = str( self.doFlowGUI.currentText() )
##        cfg[ 'flowLines' ] = self.flowLineCtx.toConfigString()
##        cfg[ 'imgFormat' ] = self.imgFormatGUI.currentText()
        return cfg

    def collectInputConfig( self ):
        '''Returns a Config object reflecting the configuration of the input panel'''
        pass

    def logMessage( self, msg ):
        '''Append a message to the console'''
        self.console.appendPlainText( msg )

    def workDone( self ):
        '''Work has finished, reactivate the button'''
##        self.goBtn.setEnabled( True )
        QtCore.QObject.disconnect( self.workThread, QtCore.SIGNAL('finished()'), self.workDone )
        self.workThread = None

    def process( self ):
        if ( self.workThread == None ):
            self.goBtn.setEnabled( False )
            cfg = self.collectFullConfig()
##            cfg[ 'DENSE_ACTION' ] = self.doDensityGUI.currentIndex()
##            cfg[ 'SPEED_ACTION' ] = self.doSpeedGUI.currentIndex()
##            cfg[ 'ADVEC_ACTION' ] = self.doFlowAdvecGUI.currentIndex()
##            cfg[ 'ADVEC_LINES' ] = self.flowAdvecLineCtx.lines
##            cfg[ 'FLOW_ACTION' ] = self.doFlowGUI.currentIndex()
            self.workThread = CrowdAnalyzeThread( cfg )
            # Make connections that allow the thread to inform the gui when finished and output messages
            QtCore.QObject.connect( self.workThread, QtCore.SIGNAL('finished()'), self.workDone )
            self.workThread.start()
            self.logMessage( '\nStarting processing' )
        else:
            self.logMessage( 'Already running' )


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