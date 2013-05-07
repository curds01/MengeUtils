# GUI for analyzing crowd

from PyQt4 import QtGui, QtCore
import os
from GLWidget import *
import sys
from analyzeWidgets import InputWidget, AnlaysisWidget, SystemResource
    
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
        self.rsrc.inputWidget = self.inputBox
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

        if ( configName ):        
            self.readConfigFile( configName )
            path, name = os.path.split( configName )
            self.rsrc.lastFolder = path

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

    def saveInConfigFile( self, fileName ):
        '''Returns a Config object reflecting the configuration of the input panel'''
        pass

    def readConfigFileDlg( self ):
        """Spawns a dialog to read a full project configuration file"""
        fileName = QtGui.QFileDialog.getOpenFileName( self, "Read application config file", self.rsrc.lastFolder, "Config files (*.cfg)" )
        if ( fileName ):
            self.readConfigFile( fileName )
            path, fName = os.path.split( str( fileName ) )
            self.rsrc.lastFolder = path
    
    def readConfigFile( self, fileName ):
        """Reads a configuration file for the full application"""
        try:
            f = open( fileName, 'r' )
            self.inputBox.readConfig( f )
            self.analysisBox.readConfig( f )
            f.close()
            print('Read full config file %s\n' % fileName )
        except IOError, ValueError:
            print('Error reading full config file %s\n' % fileName )

    def saveConfigFile( self, fileName ):
        '''Saves the configuration file for the full application'''
        try:
            file = open( fileName, 'w' )
            self.inputBox.writeConfig( file )
            self.analysisBox.writeConfig( file )
            file.close()
        except IOError, ValueError:
            print( 'Error saving full config file %\n' % fileName )
            
    def saveConfigFileDlg( self ):
        """Spawns a dialog to save a full project configuration file"""
        fileName = QtGui.QFileDialog.getSaveFileName( self, "Save Full Config As...", self.rsrc.lastFolder, "Config files (*.cfg)" )
        if ( fileName ):
            self.saveConfigFile( fileName )
            path, fName = os.path.split( str( fileName ) )
            self.rsrc.lastFolder = path
                    
    def logMessage( self, msg ):
        '''Append a message to the console'''
        self.console.insertPlainText( msg )

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