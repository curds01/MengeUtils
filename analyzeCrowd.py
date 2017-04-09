# GUI for analyzing crowd

from PyQt4 import QtGui, QtCore
import os
from GLWidget import *
import sys
from analyzeWidgets import AnlaysisWidget, SystemResource
from AnalysisTask import readAnalysisProject
from scb_qt_playback import PlayerController

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

class Logger( QtGui.QPlainTextEdit ):
    def __init__( self, parent=None ):
        QtGui.QPlainTextEdit.__init__( self, parent )
        self.setReadOnly( True )

    def htmlFriendly( self, msg ):
        '''Converts the string into an html-friendly format'''
        msg = msg.replace( '<', '&lt;' )
        msg = msg.replace( '>', '&gt;' )
        msg = msg.replace( '\t', '&nbsp;&nbsp;&nbsp;&nbsp;' )
        lines = msg.split( '\n' )
        if ( lines[-1] == '' ):
            lines.pop( -1 )
        return '<br>'.join( lines )

    def info( self, *printable ):
        '''Displays the list of items in printable as strings to the console, color-coded as information.'''
        s = '<font color="#008">'
        s += self.htmlFriendly( ' '.join( map( lambda x: str( x ), printable ) ) )
        s += '</font>'
        self.appendHtml( s )

    def warning( self, *printable ):
        '''Displays the list of items in printable as strings to the console, color-coded as a warning.'''
        s = '<font color="#A50">'
        s += self.htmlFriendly( ' '.join( map( lambda x: str( x ), printable ) ) )
        s += '</font>'
        self.appendHtml( s )

    def error( self, *printable ):
        '''Displays the list of items in printable as strings to the console, color-coded as an error.'''
        s = '<font color="#B00">'
        s += self.htmlFriendly( ' '.join( map( lambda x: str( x ), printable ) ) )
        s += '</font>'
        self.appendHtml( s )

class CrowdWindow( QtGui.QMainWindow):
    def __init__( self, parent = None ):
        self.workThread = None
        QtGui.QMainWindow.__init__( self, parent )
        self.setWindowTitle( 'Crowd Analysis' )

        mainFrame = QtGui.QFrame( self )
        mainFrame.setFrameShadow( QtGui.QFrame.Plain )
        mainFrame.setFrameShape( QtGui.QFrame.NoFrame )
        mainVLayout = QtGui.QHBoxLayout( mainFrame )
        mainVLayout.setSpacing( 3 )
        mainVLayout.setMargin( 0 )

        # Feedback panel
        splitter = QtGui.QSplitter( mainFrame )
        splitter.setOrientation( QtCore.Qt.Vertical )
        # GL Window
        wFrame = QtGui.QFrame(splitter)
        wLayout = QtGui.QGridLayout( wFrame )
        wLayout.setColumnStretch( 0, 0 )
        wLayout.setColumnStretch( 1, 1 )
        wLayout.setColumnStretch( 2, 0 )
        self.glWindow = GLWidget(  (10,10),(0,0), (10,10),(0,0), (1,1) )
        self.glWindow.setMinimumSize( QtCore.QSize( 640, 480 ) )
        wLayout.addWidget( self.glWindow, 0, 0, 1, 3 )
        self.playerWidget = PlayerController( self.glWindow )
        self.playerWidget.need3DUpdate.connect( self.glWindow.updateGL )
        wLayout.addWidget( self.playerWidget, 1, 0, 1, 3 )
        wLayout.setRowStretch( 0, 1 )
        wLayout.setRowStretch( 1, 0 )
        # Console
        self.console = Logger( splitter )
        QtCore.QObject.connect( self.console, QtCore.SIGNAL('cursorPositionChanged ()'), self.logExtended )

        # set up the shared resource
        self.rsrc = SystemResource()
        self.rsrc.glWindow = self.glWindow
        self.rsrc.logger = self.console
        sys.stdout = ConsoleFile()
        sys.stdout.processMessage.connect( self.console.info )
        
        # Main configuration panel                
        self.f = QtGui.QFrame()
        vLayout = QtGui.QVBoxLayout()
        vLayout.setMargin( 0 )
        self.analysisBox = AnlaysisWidget( self.rsrc, self )
        QtCore.QObject.connect( self.analysisBox, QtCore.SIGNAL('scbLoaded(PyQt_PyObject)'), self.scbLoaded )
        vLayout.addWidget( self.analysisBox )  
        vLayout.addStretch( 1 )
        self.f.setLayout( vLayout )

        mainVLayout.addWidget( self.f, 0 )  
        mainVLayout.addWidget( splitter, 1 )

        self.setCentralWidget( mainFrame )

        self.createActions()
        self.createMenus()
        self.createStatusBar()
        
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
        self.copyTaskAct = QtGui.QAction( "&Copy Task Settings",
                                          self, statusTip="Copy task parameters from another task into the current task",
                                          triggered=self.copyTaskDlg )

    def createMenus( self ):
        self.fileMenu = self.menuBar().addMenu("&Input")
        self.fileMenu.setEnabled( False )
        self.fileMenu.addAction( self.readInConfigAct )
        self.fileMenu.addAction( self.saveInConfigAct )
        self.settingsMenu = self.menuBar().addMenu("&Settings")
        self.settingsMenu.addAction( self.readConfigAct )
        self.settingsMenu.addAction( self.saveConfigAct )
        self.settingsMenu = self.menuBar().addMenu("&Tasks")
        self.settingsMenu.addAction( self.copyTaskAct )

    def createStatusBar(self):
        self.statusBar().showMessage("Ready")

    def readInConfigFileDlg( self ):
        """Spawns a dialog to read an input configuration file"""
        pass

    def readInConfigFile( self, fileName ):
        """Reads an input configuration file"""
        self.console.info( "Read input file" )

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
            self.analysisBox.readConfig( fileName )
            path, name = os.path.split( fileName )
            self.rsrc.lastFolder = path
            self.console.info( 'Read full config file %s\n' % fileName )
        except IOError, ValueError:
            self.console.error( 'Error reading full config file %s\n' % fileName )
            
    def saveConfigFile( self, fileName ):
        '''Saves the configuration file for the full application'''
        try:
            self.analysisBox.writeConfig( fileName )
        except IOError, ValueError:
            self.console.error( 'Error saving full config file %\n' % fileName )
            
    def saveConfigFileDlg( self ):
        """Spawns a dialog to save a full project configuration file"""
        fileName = QtGui.QFileDialog.getSaveFileName( self, "Save Full Config As...", self.rsrc.lastFolder, "Config files (*.cfg)" )
        if ( fileName ):
            self.saveConfigFile( fileName )
            path, fName = os.path.split( str( fileName ) )
            self.rsrc.lastFolder = path
                    

    def copyTaskDlg( self ):
        '''Creates a dialog for copying the settings of one task into another.'''
        self.analysisBox.copyTaskToCurrent()
    
    def logExtended( self ):
        '''Called when text has been added to the console'''
        # Make sure the scroll bar is set as low as possible
        sb = self.console.verticalScrollBar()
        maxVal = sb.maximum()
        sb.setSliderPosition( maxVal )

    def scbLoaded( self, frame_set ):
        self.playerWidget.setFrameSet( frame_set )
        self.glWindow.frameDrawables()

def main():
    def taskListArg( option, opt_str, value, parser, *args, **kwargs ):
        '''Having seen the flag to indicate a list of task indices, parses a list of non-negative ints
        of unknown length.

        See definition of optparser callbacks for explanation of parameters.
        '''
        tasks = []
        while ( parser.rargs ):
            try:
                taskID = int( parser.rargs[0] )
            except ValueError:
                break
            else:
                tasks.append( taskID )
                parser.rargs.pop( 0 )
        parser.values.tasks = tasks
    
    parser = optparse.OptionParser()
    parser.set_description( 'Perform analysis on pedestrian trajectory data - using the scb file format' )
    parser.add_option( '-n', '--noGui', help='If this argument is provided, the given analysis project file will be run without the gui.  It does require a project file to be specified.',
                       action='store_true', dest='noGui', default=False )
    parser.add_option( '-p', '--project', help='An optional project file.  If --noGui/-n is specified, this is required.  If not, the gui will be initialized with the project data',
                       action='store', dest='projFile', default=None )
    parser.add_option( '-t', '--tasks', help='A list of task indices (starting at zero) to explicitly run.  Only works in conjunction with the --noGui flag.  This list replaces the active state indicated in the analysis configuration file',
                       action='callback', callback=taskListArg, dest='tasks', default=None )

    options, args = parser.parse_args()
    
    if ( options.noGui ):
        print "No gui!"

        if ( not options.projFile ):
            parser.print_help()
            print "\n*** When running in no gui mode, you must specify a project file"
            sys.exit( 1 )
            
        # load tasks
        print "\tProject file:", options.projFile
        tasks = readAnalysisProject( options.projFile )
        # if tasks exists, reset activity
        if ( options.tasks ):
            print "\t\tExecuting user-specified tasks:", options.tasks
            for taskID in options.tasks:
                try:
                    task = tasks[ taskID ]
                except IndexError:
                    print "\t\t\tThe project file doesn't have task %d" % taskID
                    print '\t\t\t\tProject only has %d tasks.  Valid ids are in the range: [%d, %d].' % ( len( tasks ), -len( tasks ), len( tasks ) - 1 )
                else:
                    task.execute()
        else:
            print "\t\tExecuting active tasks in project file"
            for task in tasks:
                task.execute()
    else:
        pygame.init()
        app = QtGui.QApplication( sys.argv )
        configName = options.projFile
        gui = CrowdWindow()
        gui.show()
        if ( configName ):
            gui.readConfigFile( configName )
        gui.resize( 1024, 480 )
        app.exec_()        
    
if __name__ == '__main__':
    import optparse
    import pygame
    main()

    