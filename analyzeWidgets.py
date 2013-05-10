# I'm trying to construct an app with a big window on the right and a scrollable window of widgets
#    on the left.

from PyQt4 import QtGui, QtCore
import os
from obstacles import readObstacles
from ColorMap import *
from qtcontext import *
from AnalysisTask import *
from CrowdWork import CrowdAnalyzeThread
from trajectory.scbData import NPFrameSet

class SystemResource:
    '''A simple class for sharing resources across elements of the app.'''
    def __init__( self ):
        # A string representing the last folder accessed
        self.lastFolder = '.'
        # A callable for loggin messages
        self.logMessage = None

        # GL WINDOW COMMANDS
        # An instance of GLWidget
        self.glWindow = None

class TaskCopyDialog( QtGui.QDialog ):
    '''A dialog for choosing a task'''
    def __init__( self, tasks, parent=None ):
        '''Constructor.

        @param      tasks       A list of TaskWidgets, used to populate the combo box.
        '''
        QtGui.QDialog.__init__( self, parent, QtCore.Qt.WindowTitleHint|QtCore.Qt.WindowSystemMenuHint )
        self.tasks = tasks
        self.setWindowTitle( "Select Task" )
        layout = QtGui.QVBoxLayout()
        layout.addWidget( QtGui.QLabel( "Task name" ), alignment=QtCore.Qt.AlignLeft )
        self.taskSelector = QtGui.QListWidget( self )
        self.taskSelector.setSelectionMode( QtGui.QAbstractItemView.SingleSelection )
        self.taskSelector.addItems( map( lambda x: '%s - %s' % ( x.typeStr(), x.title() ), tasks ) )
        layout.addWidget( self.taskSelector )
        btns = QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Cancel
        buttons = QtGui.QDialogButtonBox( btns, QtCore.Qt.Horizontal, self )
        QtCore.QObject.connect( buttons, QtCore.SIGNAL('accepted()'), self.accept )
        QtCore.QObject.connect( buttons, QtCore.SIGNAL('rejected()'), self.reject )
        layout.addWidget( buttons )
        self.setLayout( layout )
        self.setModal( True )

    def getSelectedTask( self ):
        '''Return the text'''
        return self.tasks[ self.taskSelector.currentIndex().row() ]
        
class AnlaysisWidget( QtGui.QGroupBox ):
    '''The widget for controlling the analysis'''
    # Enumerations of the type of analysis
    DENSITY = 0
    FLOW = 1
    SPEED = 2
    POPULATION = 3
    
    TECHNIQUES = ( 'Density', 'Flow', 'Speed', 'Population' )
    def __init__( self, rsrc, parent=None ):
        '''Constructor.

        @param      rsrc        An instance of SystemResource.  Used to coordinate
                                system-wide data.
        '''
        QtGui.QGroupBox.__init__( self, 'Analysis', parent )
        self.rsrc = rsrc
        self.build()
        self.tasks = []
        self.workThread = None

    def build( self ):
        layout = QtGui.QGridLayout()
        layout.setColumnStretch( 0, 0 )
        layout.setColumnStretch( 1, 1 )
        layout.setMargin( 2 )

        ####################################
        # Control for adding widgets
        addBtn = QtGui.QPushButton( 'Add', self )
        layout.addWidget( addBtn, 0, 0 )
        QtCore.QObject.connect( addBtn, QtCore.SIGNAL('clicked(bool)'), self.addTaskCB )

        self.toolGUI = QtGui.QComboBox( self )
        self.toolGUI.addItems( self.TECHNIQUES )
        layout.addWidget( self.toolGUI, 0, 1 )
        layout.addWidget( QtGui.QLabel("Task name"), 1, 0 )
        self.taskNameGUI = QtGui.QLineEdit()
        regExp = QtCore.QRegExp( "[^~\\|]*" )
        validator = QtGui.QRegExpValidator( regExp, self )
        self.taskNameGUI.setValidator( validator )
        layout.addWidget( self.taskNameGUI, 1, 1 )

        # This should be greyed out if no actions exist
        self.goBtn = QtGui.QPushButton( 'Perform All Active Analysis Tasks', self )
        self.goBtn.setEnabled( False )
        layout.addWidget( self.goBtn, 3, 0, 1, 2 )
        QtCore.QObject.connect( self.goBtn, QtCore.SIGNAL('clicked(bool)'), self.runAllActive )

        div = QtGui.QFrame( self )
        div.setFrameShape( QtGui.QFrame.HLine )
        div.setFrameShadow( QtGui.QFrame.Sunken )
        layout.addWidget( div, 4, 0, 1, 2 )
        taskLabel = QtGui.QLabel( "Tasks" )
        layout.addWidget( taskLabel, 5, 0, 1, 2 )

        self.taskGUIs = QtGui.QTabWidget()
        QtCore.QObject.connect( self.taskGUIs, QtCore.SIGNAL('currentChanged(int)'), self.changeActiveTask )
        layout.addWidget( self.taskGUIs, 6, 0, 1, 2 )
        
        self.setLayout( layout )

    def runAllActive( self ):
        '''Runs all active tasks'''
        try:
            tasks = self.getTasks()
        except ValueError:
            print "No tasks to run"
        else:
            self.executeWork( tasks )

    def runCurrent( self ):
        '''Runs the current task - it must be active, otherwise this function couldn't be called.'''
        cWidget = self.taskGUIs.currentWidget()
        try:
            t = cWidget.getTask()
        except ValueError:
            pass
        else:
            self.executeWork( [ t ])

    def executeWork( self, tasks ):
        '''Runs the list of given tasks.

        @param      tasks       A list of instances of AnalysisTasks.
        '''
        if ( self.workThread == None ):
            self.goBtn.setEnabled( False )
            # disable all task-specific "Run" buttons
            for task in self.tasks:
                task.goBtn.setEnabled( False )
            self.workThread = CrowdAnalyzeThread( tasks )
            # Make connections that allow the thread to inform the gui when finished and output messages
            QtCore.QObject.connect( self.workThread, QtCore.SIGNAL('finished()'), self.workDone )
            print "Starting task execution..."
            self.workThread.start()
        else:
            print "Already running"

    def workDone( self ):
        '''Called when the analysis work has finished'''
        QtCore.QObject.disconnect( self.workThread, QtCore.SIGNAL('finished()'), self.workDone )
        self.workThread = None
        self.goBtn.setEnabled( True )
        for task in self.tasks:
            task.goBtn.setEnabled( True )
        
    def changeActiveTask( self, active ):
        '''Called when the tab of a task is selected'''
        self.taskGUIs.currentWidget().activate()
    
    def deleteTask( self, task ):
        '''Deletes the given task from the analysis.

        @param      task        An instance of a TaskWidget (or subclass).  The task to be
                                deleted.
        '''
        assert( task in self.tasks )
        self.tasks.pop( self.tasks.index( task ) )
        idx = self.taskGUIs.indexOf( task )
        self.taskGUIs.removeTab( idx )
        if ( self.taskGUIs.count() == 0 ):
            self.goBtn.setEnabled( False )

    def addTaskCB( self ):
        '''Adds a block of work'''
        name = str( self.taskNameGUI.text() )
        if ( not name ):
            name = 'junk'
        self.taskNameGUI.setText( '' )
        
        index = self.toolGUI.currentIndex()
        if ( index == self.DENSITY ):
            TaskClass = DensityTaskWidget
        elif ( index == self.FLOW ):
            TaskClass = FlowTaskWidget
        elif ( index == self.SPEED ):
            TaskClass = SpeedTaskWidget
        elif ( index == self.POPULATION ):
            TaskClass = PopulationTaskWidget
        
        task = TaskClass( name, rsrc=self.rsrc, delCB=self.deleteTask )
        self.addTask( task, TaskClass.typeStr() )

    def addTask( self, task, tabLabel ):
        '''Adds a task to the widget'''
        self.taskGUIs.addTab( task, tabLabel )
        self.goBtn.setEnabled( True )
        QtCore.QObject.connect( task.goBtn, QtCore.SIGNAL('clicked(bool)'), self.runCurrent )
        self.tasks.append( task )
        self.taskGUIs.setCurrentWidget( task )
        
    def writeConfig( self, file ):
        '''Writes the input configuration to the given file object.

        @param      file        An open file-like object.  Supports "write" operations.
        '''
        file.write( '# WARNING!  Editing this file can cause problems.  Order, case, and syntax all matter\n' )
        file.write( '# The only comments allowed are full line comments\n' )
        file.write( 'Task count || %d\n' % len( self.tasks ) )
        for task in self.tasks:
            task.writeConfig( file )
        
    def readConfig( self, file ):
        '''Reads the input configuration from the given file object.

        @param      file        An open file-like object.  Supports "readline" operations.
        @raises     ValueError if there is a problem in parsing the values.
        '''
        line = file.readline().strip()
        while ( line[0] == '#' ):
            line = file.readline().strip()
        try:
            tokens = map( lambda x: x.strip(), line.split( '||' ) )
        except:
            print "Error parsing task count"
            raise ValueError
        
        if ( len( tokens ) != 2 or tokens[0] != 'Task count' ):
            print 'Expected to see "Task count" in configuration file, found %s' % ( tokens[0] )
            raise ValueError
        taskCount = int( tokens[1] )
        
        for i in xrange( taskCount ):
            taskType = file.readline().strip()
            TaskClass = getTaskClass( taskType )
            task = TaskClass( '', rsrc=self.rsrc, delCB=self.deleteTask )
            task.readConfig( file )
            self.addTask( task, taskType )
            
    def getTasks( self ):
        '''Returns a list of AnalysisTasks for the active task widgets.  If there are any
        errors (incomplete data, etc.) a ValueError is raised.

        @returns        A list of AnalysisTasks.
        @raises         ValueError if there are data problems with ANY task.
        '''
        aTasks = []
        for task in self.tasks:
            if ( task.isChecked() ):
                t = task.getTask()               
                aTasks.append( t )
        return aTasks

    def copyTaskToCurrent( self ):
        '''Copies the parameters from one task to the current task'''
        # construct task list
        currWidget = self.taskGUIs.currentWidget()
        tasks = filter( lambda x: x != currWidget, self.tasks )
        dlg = TaskCopyDialog( tasks, self )
        if ( dlg.exec_() == QtGui.QDialog.Accepted ):
            srcTask = dlg.getSelectedTask()
            dstTask = currWidget
            dstTask.copySettings( srcTask )
            
def getTaskClass( taskName ):
    '''Returns a class object for the given analysis task name'''
    if ( taskName == DensityTaskWidget.typeStr() ):
        return DensityTaskWidget
    elif ( taskName == FlowTaskWidget.typeStr() ):
        return FlowTaskWidget
    elif ( taskName == SpeedTaskWidget.typeStr() ):
        return SpeedTaskWidget
    elif ( taskName == PopulationTaskWidget.typeStr() ):
        return PopulationTaskWidget
    else:
        print "Unrecognized analysis task type: %s" % ( taskName )
        raise ValueError
        

class TaskNameDialog( QtGui.QDialog ):
    '''Dialog for changing task name - validates the name against delimieter characters.'''
    def __init__( self, parent=0x0 ):
        QtGui.QDialog.__init__( self, parent, QtCore.Qt.WindowTitleHint|QtCore.Qt.WindowSystemMenuHint )
        self.setWindowTitle( "Change Task Name" )
        layout = QtGui.QVBoxLayout()
        layout.addWidget( QtGui.QLabel( "Task name" ), alignment=QtCore.Qt.AlignLeft )
        self.nameEditor = QtGui.QLineEdit( self )
        regExp = QtCore.QRegExp( "[^~\\|]*" )
        validator = QtGui.QRegExpValidator( regExp, self )
        self.nameEditor.setValidator( validator )
        layout.addWidget( self.nameEditor )
        btns = QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Cancel
        buttons = QtGui.QDialogButtonBox( btns, QtCore.Qt.Horizontal, self )
        QtCore.QObject.connect( buttons, QtCore.SIGNAL('accepted()'), self.accept )
        QtCore.QObject.connect( buttons, QtCore.SIGNAL('rejected()'), self.reject )
        layout.addWidget( buttons )
        self.setLayout( layout )
        self.setModal( True )

    def getName( self ):
        '''Return the text'''
        return str( self.nameEditor.text() )

class TaskWidget( QtGui.QGroupBox ):
    '''The basic widget for doing analysis work'''
    def __init__( self, name, parent=None, delCB=None, rsrc=None ):
        '''Constructor.

        @param  name        A string.  The default name of the task, used in the output files.
        @param  parent      An instance of QWidget.  The optional parent widget.
        @param  delCB       A callable.  The optional function to call when the delete button
                            is hit.
        @param  rsrc        An instance of SystemResource
        '''
        QtGui.QGroupBox.__init__( self, name, parent )
        self.setCheckable( True )
        self.setToolTip( "Double-click to change task name" )
        self.delCB = delCB
        self.context = None
        self.rsrc = rsrc
        assert( not self.rsrc is None )
        
        self.bodyLayout = QtGui.QVBoxLayout( self )
        self.body()
        self.bodyLayout.addStretch( 10 )

    def deleteCB( self ):
        '''Called when the delete button is clicked'''
        if ( self.delCB ):
            self.delCB( self )
            
    def mouseDoubleClickEvent( self, event ):
        # Spawn a dialog to change the task name
        dlg = TaskNameDialog( self )
        if ( dlg.exec_() == QtGui.QDialog.Accepted ):
            self.setTitle( dlg.getName() )

    def ioBox( self ):
        '''Creates the QGroupBox containing the I/O widgets'''
        # scb file
        ioBox = QtGui.QGroupBox( "Input/Output" )
        fLayout = QtGui.QGridLayout( ioBox )
        fLayout.setColumnStretch( 0, 0 )
        fLayout.setColumnStretch( 1, 1 )
        fLayout.setColumnStretch( 0, 2 )

        # SCB input
        fLayout.addWidget( QtGui.QLabel( "SCB file" ), 0, 0, 1, 1, QtCore.Qt.AlignRight )
        self.scbFilePathGUI = QtGui.QPushButton( '', self )
        QtCore.QObject.connect( self.scbFilePathGUI, QtCore.SIGNAL('clicked(bool)'), self.selectSCBDlg )
        fLayout.addWidget( self.scbFilePathGUI, 0, 1, 1, 2 )

        # Time Step
        # TODO: Set this value based on the scb file
        fLayout.addWidget( QtGui.QLabel( "Time step" ), 1, 0, 1, 1, QtCore.Qt.AlignRight )
        self.timeStepGui = QtGui.QDoubleSpinBox( self )
        self.timeStepGui.setDecimals( 5 )
        fLayout.addWidget( self.timeStepGui, 1, 1, 1, 2 )

        # obstacle file
        fLayout.addWidget( QtGui.QLabel( "Obstacle file" ), 2, 0, 1, 1, QtCore.Qt.AlignRight )
        self.obstFilePathGUI = QtGui.QPushButton( '', self )
        QtCore.QObject.connect( self.obstFilePathGUI, QtCore.SIGNAL('clicked(bool)'), self.selectObstDlg )
        fLayout.addWidget( self.obstFilePathGUI, 2, 1, 1, 1 )
        self.loadObstBtn = QtGui.QPushButton( "Load", self )
        QtCore.QObject.connect( self.loadObstBtn, QtCore.SIGNAL('clicked(bool)'), self.loadObstacle )
        fLayout.addWidget( self.loadObstBtn, 2, 2, 1, 1 )

        # Output foloder
        fLayout.addWidget( QtGui.QLabel( "Output Folder" ), 3, 0, 1, 1, QtCore.Qt.AlignRight )
        self.outPathGUI = QtGui.QPushButton( '', self )
        QtCore.QObject.connect( self.outPathGUI, QtCore.SIGNAL('clicked(bool)'), self.selectOutPathDlg )
        fLayout.addWidget( self.outPathGUI, 3, 1, 1, 2 )
        return ioBox
        
    def actionBox( self ):
        '''Create the QGroupBox containing the action widgets'''
        inputBox = QtGui.QGroupBox("Action")
        fLayout = QtGui.QGridLayout( inputBox )

        self.goBtn = QtGui.QPushButton( "Perform This Analysis", self )
        fLayout.addWidget( self.goBtn, 0, 0 )
        QtCore.QObject.connect( self.goBtn, QtCore.SIGNAL('released()'), self.launchTask )
        # TODO connect this
        
        self.delBtn = QtGui.QPushButton( "Del", self )
        fLayout.addWidget( self.delBtn, 0, 1 )
        QtCore.QObject.connect( self.delBtn, QtCore.SIGNAL('released()'), self.deleteCB )

        # Folder path for output image files
        self.actionGUI = QtGui.QComboBox( self )
        self.actionGUI.addItems( ( "Compute", "Visualize", "Compute and Vis." ) )
        fLayout.addWidget( self.actionGUI, 1, 0, 1, 2 )

        return inputBox

    def launchTask( self ):
        print "Launching %s - %s" % ( self.typeStr(), self.title() )
  
    def body( self ):
        '''Build the task-specific GUI.  This should be overwritten by subclass'''
        self.bodyLayout.addWidget( self.actionBox() )
        self.bodyLayout.addWidget( self.ioBox() )

    def activate( self ):
        '''Called when the work widget is activated'''
        if ( self.isChecked ):
            self.rsrc.glWindow.setUserContext( self.context )
        else:
            self.rsrc.glWindow.setUserContext( None )
        self.rsrc.glWindow.updateGL()

    def selectSCBDlg( self ):
        """Spawns a dialog to select an scb file"""
        fileName = QtGui.QFileDialog.getOpenFileName( self, "Open SCB file", self.rsrc.lastFolder, "SCB Files (*.scb)")
        if ( fileName ):
            if ( os.path.exists( fileName ) ):
                self.scbFilePathGUI.setText( fileName )
                path, fName = os.path.split( str( fileName ) )
                self.rsrc.lastFolder = path
                frameSet = NPFrameSet( fileName )
                if ( frameSet.version[0] == '1' ):
                    print "SCB data is version %s, you must set the time step explicitly"
                    self.timeStepGui.setEnabled( True )
                    self.timeStepGui.setValue( 0.0 )
                else:
                    self.timeStepGui.setEnabled( False )
                    self.timeStepGui.setValue( frameSet.simStepSize )

    def selectObstDlg( self ):
        """Spawns a dialog to select an obstacle file"""
        fileName = QtGui.QFileDialog.getOpenFileName( self, "Open obstacle file", self.rsrc.lastFolder, "All Files (*.*)")
        if ( fileName ):
            self.obstFilePathGUI.setText( fileName )
            path, fName = os.path.split( str( fileName ) )
            self.rsrc.lastFolder = path

    def loadObstacle( self ):
        """Causes the indicated obstacle file to be loaded into the OpenGL viewer"""
        obstFileName = str( self.obstFilePathGUI.text() )
        if ( obstFileName ):
            self.rsrc.logMessage('Reading obstacle file: %s' % obstFileName )
            try:
                flipY = False
                obstacles, bb = readObstacles( obstFileName, flipY )                
                self.rsrc.glWindow.addDrawables( obstacles )
                w = bb.max.x - bb.min.x
                h = bb.max.y - bb.min.y
                self.rsrc.glWindow.setBG( (w,h), (bb.min.x, bb.min.y) )
                self.rsrc.glWindow.setView( (w,h), (bb.min.x, bb.min.y) )
                glSize = self.rsrc.glWindow.size()
                self.rsrc.glWindow.resizeGL( glSize.width(), glSize.height() )
                self.rsrc.glWindow.updateGL()
            except:
                self.rsrc.logMessage('Error reading obstacle file: %s' % obstFileName )
        else:
            self.rsrc.logMessage('No obstacle file to load' )
    
    def selectOutPathDlg( self ):
        """Spawns a dialog to select an scb file"""
        fileName = QtGui.QFileDialog.getExistingDirectory( self, "Select Output Folder", self.rsrc.lastFolder )
        if ( fileName ):
            self.outPathGUI.setText( fileName )
            self.rsrc.lastFolder = str( fileName )

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return 'TASK'
    
    def writeConfig( self, file ):
        '''Writes the widget state to the given file'''
        # Write TYPE
        file.write( '%s\n' % self.typeStr()  )
        # Write I/O (scb name, time step, obstacle file, output folder)
        file.write( 'SCB || %s\n' % ( self.scbFilePathGUI.text() ) )
        file.write( 'timeStep || %.5f\n' % ( self.timeStepGui.value() ) )
        file.write( 'obstacle || %s\n' % ( self.obstFilePathGUI.text() ) )
        file.write( 'outFldr || %s\n' % ( self.outPathGUI.text() ) )
        # action info: work name,
        file.write( 'workName || %s\n' % ( self.title() ) )
        file.write( 'task || %s\n' % ( self.actionGUI.currentText() ) )
        file.write( 'active || ' )
        if ( self.isChecked() ):
            file.write( '1\n' )
        else:
            file.write( '0\n' )

    def _parseConfigLine( self, file, name, setFunc, convertFunc=None ):
        '''Parses a key-value line from the config file.  The string value is optionally converted
        via the convertFunc and passed as a parameter to the setFunc callable.

        @param      file            An open file object.  The file to read the line from.
        @param      name            The name of the expected key.
        @param      setFunc         A callable.  The (possibly converted) value is passed as a parameter.
        @param      convertFunc     A callable.  If provided, the string value will be passed to this
                                    function and the RESULT is passed to setFunc.
        @return     A string.  The value in the key-value pair.
        '''
        line = file.readline().strip()
        while ( line[0] == '#' ):
            line = file.readline().strip()
        try:
            tokens = map( lambda x: x.strip(), line.split( '||' ) )
        except:
            print "Error parsing %s" % name
            print '\tRead: %s' % line
            return
        if ( len( tokens ) != 2 ):
            print "Too many values found for key: %s" % ( name )
            print '\tRead: %s' % line
            return
        if ( tokens[0] != name ):
            print "Looking for key %s, found %s" % ( name, tokens[0] )
            print '\tRead: %s' % line
            return
        value = tokens[1]
        if ( convertFunc ):
            try:
                value = convertFunc( value )
            except ValueError:
                print "Error converting the value for %s: %s" % ( name, value )
                print '\tRead: %s' % line
        setFunc( value )
    
    def readConfig( self, file ):
        '''Reads the common TaskWidget parameters from the file'''
        # I/O info
        self._parseConfigLine( file, 'SCB', self.scbFilePathGUI.setText )
        self._parseConfigLine( file, 'timeStep', self.timeStepGui.setValue, float )
        frameSet = NPFrameSet( str( self.scbFilePathGUI.text() ) )
        if ( frameSet.version[0] == '1' ):
            self.timeStepGui.setEnabled( True )
            self.timeStepGui.setValue( 0.0 )
        else:
            self.timeStepGui.setEnabled( False )
            self.timeStepGui.setValue( frameSet.simStepSize )
        self._parseConfigLine( file, 'obstacle', self.obstFilePathGUI.setText )
        self._parseConfigLine( file, 'outFldr', self.outPathGUI.setText )

        # work info
        self._parseConfigLine( file, 'workName', self.setTitle )
        self._parseConfigLine( file, 'task', self.actionGUI.setCurrentIndex, self.actionGUI.findText )
        def isActive( txt ):
            return txt == '1'
        self._parseConfigLine( file, 'active', self.setEnabled, isActive )

    def copySettings( self, task ):
        '''Copy the settings from the given task into this task'''
        assert( isinstance( task, TaskWidget ) )
        self.scbFilePathGUI.setText( task.scbFilePathGUI.text() )
        self.timeStepGui.setValue( task.timeStepGui.value() )
        self.obstFilePathGUI.setText( task.obstFilePathGUI.text() )
        self.outPathGUI.setText( task.outPathGUI.text() )
        self.timeStepGui.setEnabled( task.timeStepGui.isEnabled() )
        # don't copy task name, activity or enabled state

    def setTaskParameters( self, task ):
        '''Sets the parameters in the task based on this widget.
        If there is a problem with the parameters, a ValueError exception is raised.

        @raises     ValueError if there is a problem in setting the parameters.
        '''
        # input scb file
        task.setTaskName( str( self.title() ) )
        # action
        actIndex = self.actionGUI.currentIndex()
        if ( actIndex == 0 ):
            task.setWork( AnalysisTask.COMPUTE )
        elif ( actIndex == 1 ):
            task.setWork( AnalysisTask.VIS )
        elif ( actIndex == 2 ):
            task.setWork( AnalysisTask.COMPUTE_VIS )
        else:
            print "Unrecognized value for task action %s for %s" % ( self.actionGUI.currentText(), self.title() )
            raise ValueError
        # scb file
        scbFile = str( self.scbFilePathGUI.text() ).strip()
        if ( not scbFile ):
            print "No scb file specified for analysis"
            raise ValueError
        task.setSCBFile( scbFile )
        dt = self.timeStepGui.value()
        if ( dt == 0.0 ):
            print "No time step specified!"
            raise ValueError
        # time step
        task.setTimeStep( dt )
        # output folder
        outFldr = str( self.outPathGUI.text() )
        if ( not outFldr ):
            print "No output folder specified for %s - %s" % ( self.typeStr(), self.title() )
            raise ValueError
        task.setWorkFolder( outFldr )

class DomainTaskWidget( TaskWidget ):
    '''A TaskWidget that requires a rectangular domain over which to perform analysis.'''
    def __init__( self, name, parent=None, delCB=None, rsrc=None ):
        TaskWidget.__init__( self, name, parent, delCB, rsrc )

    def domainBox( self ):
        '''Creates the rectangular domain widgets'''
        domainBox = QtGui.QGroupBox( "Analysis Domain" )
        fLayout = QtGui.QGridLayout( domainBox )
        fLayout.setColumnStretch( 0, 0 )
        fLayout.setColumnStretch( 1, 1 )
        
        # Domain minimum point
        fLayout.addWidget( QtGui.QLabel( "Min. Point" ), 0, 0, 1, 1, QtCore.Qt.AlignRight )
        rowLayout = QtGui.QHBoxLayout()
        fLayout.addLayout( rowLayout, 0, 1, 1, 2 )        
        self.domainMinXGUI = QtGui.QDoubleSpinBox( self )
        self.domainMinXGUI.setValue( 0.0 )
        self.domainMinXGUI.setRange( -1e6, 1e6 )
        rowLayout.addWidget( self.domainMinXGUI )
        self.domainMinYGUI = QtGui.QDoubleSpinBox( self )
        self.domainMinYGUI.setRange( -1e6, 1e6 )
        self.domainMinYGUI.setValue( 0.0 )
        rowLayout.addWidget( self.domainMinYGUI )

        # Domain size
        fLayout.addWidget( QtGui.QLabel( "Domain Size" ), 1, 0, 1, 1, QtCore.Qt.AlignRight )
        rowLayout = QtGui.QHBoxLayout()
        fLayout.addLayout( rowLayout, 1, 1, 1, 2 ) 
        self.domainSizeXGUI = QtGui.QDoubleSpinBox( self )
        self.domainSizeXGUI.setRange( -1e6, 1e6 )
        self.domainSizeXGUI.setValue( 0.0 )
        rowLayout.addWidget( self.domainSizeXGUI )
        self.domainSizeYGUI = QtGui.QDoubleSpinBox( self )
        self.domainSizeYGUI.setRange( -1e6, 1e6 )
        self.domainSizeYGUI.setValue( 0.0 )
        rowLayout.addWidget( self.domainSizeYGUI )

        return domainBox
    
    def rasterBox( self ):
        '''Create the widgets for the rasterization settings'''
        box = QtGui.QGroupBox("Raster Settings")
        fLayout = QtGui.QGridLayout( box )
        fLayout.setColumnStretch( 0, 0 )
        fLayout.setColumnStretch( 1, 1 )

        # Cell size
        fLayout.addWidget( QtGui.QLabel( "Cell Size" ), 1, 0, 1, 1, QtCore.Qt.AlignRight )
        self.cellSizeGUI = QtGui.QDoubleSpinBox( box )
        fLayout.addWidget( self.cellSizeGUI, 1, 1, 1, 1 )

        # Color map
        fLayout.addWidget( QtGui.QLabel( "Color Map" ), 2, 0, 1, 1, QtCore.Qt.AlignRight )
        self.colorMapGUI = QtGui.QComboBox( box )
        cmaps = COLOR_MAPS.keys()
        cmaps.sort()
        self.colorMapGUI.addItems( cmaps )
        self.colorMapGUI.setCurrentIndex( 0 )
        fLayout.addWidget( self.colorMapGUI, 2, 1, 1, 1 )

        # image format
        fLayout.addWidget( QtGui.QLabel( "Image format" ), 3, 0, 1, 1, QtCore.Qt.AlignRight )
        self.imgFormatGUI = QtGui.QComboBox( box )
        self.imgFormatGUI.addItems( ( 'jpg', 'bmp', 'png' ) )
        def formatIdxChanged( idx ):
            if ( idx == 2 ):
                self.rsrc.logMessage( 'There is a memory leak for png format!' )
        QtCore.QObject.connect( self.imgFormatGUI, QtCore.SIGNAL('currentIndexChanged(int)'), formatIdxChanged )
        fLayout.addWidget( self.imgFormatGUI, 3, 1, 1, 1 )        

        return box
        
    def body( self ):
        TaskWidget.body( self )
        self.bodyLayout.addWidget( self.domainBox() )
        self.bodyLayout.addWidget( self.rasterBox() )

    def writeConfig( self, file ):
        TaskWidget.writeConfig( self, file )
        # domain extent
        file.write( 'minPtX || %.5f\n' % ( self.domainMinXGUI.value() ) )
        file.write( 'minPtY || %.5f\n' % ( self.domainMinYGUI.value() ) )
        file.write( 'sizeX || %.5f\n' % ( self.domainSizeXGUI.value() ) )
        file.write( 'sizeY || %.5f\n' % ( self.domainSizeYGUI.value() ) )
        # raster properties
        file.write( 'cellSize || %.5f\n' % ( self.cellSizeGUI.value() ) )
        file.write( 'colorMap || %s\n' % ( self.colorMapGUI.currentText() ) )
        file.write( 'imgType || %s\n' % ( self.imgFormatGUI.currentText() ) )

    def readConfig( self, file ):
        TaskWidget.readConfig( self, file )
        # domain extent
        self._parseConfigLine( file, 'minPtX', self.domainMinXGUI.setValue, float )
        self._parseConfigLine( file, 'minPtY', self.domainMinYGUI.setValue, float )
        self._parseConfigLine( file, 'sizeX', self.domainSizeXGUI.setValue, float )
        self._parseConfigLine( file, 'sizeY', self.domainSizeYGUI.setValue, float )
        # raster properties
        self._parseConfigLine( file, 'cellSize', self.cellSizeGUI.setValue, float )
        self._parseConfigLine( file, 'colorMap', self.colorMapGUI.setCurrentIndex, self.colorMapGUI.findText )
        self._parseConfigLine( file, 'imgType', self.imgFormatGUI.setCurrentIndex, self.imgFormatGUI.findText )

    def copySettings( self, task ):
        '''Copy the settings from the given task into this task'''
        TaskWidget.copySettings( self, task )
        if ( isinstance( task, DomainTaskWidget ) ):
            self.domainMinXGUI.setValue( task.domainMinXGUI.value() )
            self.domainMinYGUI.setValue( task.domainMinYGUI.value() )
            self.domainSizeXGUI.setValue( task.domainSizeXGUI.value() )
            self.domainSizeYGUI.setValue( task.domainSizeYGUI.value() )
            self.cellSizeGUI.setValue( task.cellSizeGUI.value() )
            self.colorMapGUI.setCurrentIndex( task.colorMapGUI.currentIndex() )
            self.imgFormatGUI.setCurrentIndex( task.imgFormatGUI.currentIndex() )

    def setTaskParameters( self, task ):
        '''Sets the parameters in the task based on this widget.
        If there is a problem with the parameters, a ValueError exception is raised.

        @raises     ValueError if there is a problem in setting the parameters.
        '''
        TaskWidget.setTaskParameters( self, task )
        w = self.domainSizeXGUI.value()
        h = self.domainSizeYGUI.value()
        if ( w <= 0.0 or h <= 0.0 ):
            print "Invalid domain defined for analysis - zero area"
            raise ValueError
        minX = self.domainMinXGUI.value()
        minY = self.domainMinYGUI.value()
        task.setDomain( minX, minY, minX + w, minY + h )
        task.setCellSize( self.cellSizeGUI.value() )
        task.setColorMap( str( self.colorMapGUI.currentText() ) )
        task.setOutImg( str( self.imgFormatGUI.currentText() ) )
                      
class DensityTaskWidget( DomainTaskWidget ):
    def __init__( self, name, parent=None, delCB=None, rsrc=None ):
        DomainTaskWidget.__init__( self, name, parent, delCB, rsrc )

    def kernelBox( self ):
        '''Create the widgets for the rasterization settings'''
        box = QtGui.QGroupBox("Density Estimation Kernel")
        fLayout = QtGui.QGridLayout( box )
        fLayout.setColumnStretch( 0, 0 )
        fLayout.setColumnStretch( 1, 1 )

        fLayout.addWidget( QtGui.QLabel( "Smooth Param." ), 0, 0, 1, 1, QtCore.Qt.AlignRight )
        self.kernelSizeGUI = QtGui.QDoubleSpinBox( box )
        fLayout.addWidget( self.kernelSizeGUI, 0, 1, 1, 1 )

        return box
        
    def body( self ):
        '''Build the task-specific GUI.  This should be overwritten by subclass'''
        DomainTaskWidget.body( self )
        self.bodyLayout.addWidget( self.kernelBox() )

    def readConfig( self, file ):
        '''Reads the widget state from the given file'''
        DomainTaskWidget.readConfig( self, file )
        self._parseConfigLine( file, 'smoothParam', self.kernelSizeGUI.setValue, float )

    def writeConfig( self, file ):
        '''Writes the widget state to the given file'''
        DomainTaskWidget.writeConfig( self, file )
        file.write( 'smoothParam || %.5f\n' % ( self.kernelSizeGUI.value() ) )
    
    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return 'DENSITY'

    def getTask( self ):
        '''Returns a task for this widget.

        @return     An instance of DensityAnalysisTask.
        @raises     ValueError if there is a problem in instantiating the task.addLine
        '''
        task = DensityAnalysisTask()
        self.setTaskParameters( task )
        return task

    def copySettings( self, task ):
        '''Copy the settings from the given task into this task'''
        TaskWidget.copySettings( self, task )
        if ( isinstance( task, DensityTaskWidget ) ):
            self.kernelSizeGUI.setValue( task.kernelSizeGUI.value() )

    def setTaskParameters( self, task ):
        '''Sets the parameters in the task based on this widget.
        If there is a problem with the parameters, a ValueError exception is raised.

        @raises     ValueError if there is a problem in setting the parameters.
        '''
        DomainTaskWidget.setTaskParameters( self, task )
        task.setSmoothParam( self.kernelSizeGUI.value() )

class SpeedTaskWidget( DomainTaskWidget ):
    def __init__( self, name, parent=None, delCB=None, rsrc=None ):
        DomainTaskWidget.__init__( self, name, parent, delCB, rsrc )

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return 'SPEED'

    def readConfig( self, file ):
        '''Reads the widget state from the given file'''
        DomainTaskWidget.readConfig( self, file )

    def writeConfig( self, file ):
        '''Writes the widget state to the given file'''
        DomainTaskWidget.writeConfig( self, file )

    def getTask( self ):
        '''Returns a task for this widget.

        @return     An instance of SpeedAnalysisTask.
        @raises     ValueError if there is a problem in instantiating the task.addLine
        '''
        task = SpeedAnalysisTask()
        self.setTaskParameters( task )
        return task

class FlowTaskWidget( TaskWidget ):
    def __init__( self, name, parent=None, delCB=None, rsrc=None ):
        TaskWidget.__init__( self, name, parent, delCB, rsrc )
        # TODO: This needs a context
        self.context = QTFlowLineContext( self.cancelAddFlowLine )

    def createFlowLineBox( self ):
        '''Creates the GroupBox containing the widgets for controlling lines'''
        box = QtGui.QGroupBox( "Flow Lines" )
        layout = QtGui.QGridLayout( box )
        layout.setColumnStretch( 0, 0 )
        layout.setColumnStretch( 1, 1 )
        layout.setColumnStretch( 2, 1 )

        # Line selector
        self.linesGUI = QtGui.QComboBox( box )
        self.linesGUI.setEnabled( False )
        QtCore.QObject.connect( self.linesGUI, QtCore.SIGNAL('currentIndexChanged(int)'), self.lineChangedCB )
        layout.addWidget( QtGui.QLabel("Line No."), 0, 1, 1, 1, QtCore.Qt.AlignRight )
        layout.addWidget( self.linesGUI, 0, 2 )

        # add button
        self.addFlowLineBtn = QtGui.QPushButton( 'Add' )
        QtCore.QObject.connect( self.addFlowLineBtn, QtCore.SIGNAL('clicked()'), self.addFlowLineCB )      
        layout.addWidget( self.addFlowLineBtn, 1, 1 )

        # delete button
        self.delFlowLineBtn = QtGui.QPushButton( 'Delete' )
        self.delFlowLineBtn.setEnabled( False )
        QtCore.QObject.connect( self.delFlowLineBtn, QtCore.SIGNAL('clicked()'), self.delFlowLineCB )
        layout.addWidget( self.delFlowLineBtn, 1, 2 )

        # edit button
        self.editFlowLineBtn = QtGui.QPushButton( 'Edit' )
        self.editFlowLineBtn.setCheckable( True )
        self.editFlowLineBtn.setEnabled( False )
        QtCore.QObject.connect( self.editFlowLineBtn, QtCore.SIGNAL('toggled(bool)'), self.editFlowLineCB )
        layout.addWidget( self.editFlowLineBtn, 2, 1 )

        # flip button
        self.flipFlowLineBtn = QtGui.QPushButton( 'Flip' )
        self.flipFlowLineBtn.setEnabled( False )
        QtCore.QObject.connect( self.flipFlowLineBtn, QtCore.SIGNAL('clicked()'), self.flipFlowLineCB )
        layout.addWidget( self.flipFlowLineBtn, 2, 2 )

        # line name
        layout.addWidget( QtGui.QLabel("Line Name"), 3, 0, 1, 1, QtCore.Qt.AlignRight )
        self.flowNameGUI = QtGui.QLineEdit()
        regExp = QtCore.QRegExp( "[^~\\|,]*" )
        validator = QtGui.QRegExpValidator( regExp, self )
        self.flowNameGUI.setValidator( validator )
        QtCore.QObject.connect( self.flowNameGUI, QtCore.SIGNAL('editingFinished()'), self.flowLineNameChangeCB )
        layout.addWidget( self.flowNameGUI, 3, 1, 1, 2 )
        
        return box
    
    def body( self ):
        '''Build the task-specific GUI.  This should be overwritten by subclass'''
        TaskWidget.body( self )
        self.bodyLayout.addWidget( self.createFlowLineBox() )

    def lineChangedCB( self ):
        '''Called when the line number changes'''
        idx = self.linesGUI.currentIndex()
        active = idx > -1
        self.delFlowLineBtn.setEnabled( active )
        self.editFlowLineBtn.setEnabled( active )
        self.flipFlowLineBtn.setEnabled( active )
        self.linesGUI.setEnabled( self.linesGUI.count() > 0 )
        if ( active ):
            self.flowNameGUI.setText( self.context.getName( idx ) )
        self.context.setActive( idx )
        self.rsrc.glWindow.updateGL()
        if ( not active ):
            self.editFlowLineBtn.setChecked( False )

    def addFlowLineCB( self ):
        '''When the add flow line is clicked, we add the flow line and update the GUI appropriately'''
        nextIdx = self.linesGUI.count()
        self.delFlowLineBtn.setEnabled( True )
        self.context.addLine()
        self.linesGUI.addItem( '%d' % nextIdx )
        self.linesGUI.setCurrentIndex( nextIdx )
        self.linesGUI.setEnabled( True )
        self.editFlowLineBtn.setChecked( True ) # this should call the callback and automatically enable the context to draw a line
        self.rsrc.glWindow.updateGL()

    def delFlowLineCB( self ):
        '''Remove the current selected line'''
        idx = self.linesGUI.currentIndex()
        assert( idx > -1 )  # this button shouldn't be enabled if this isn't true
        self.context.deleteLine( idx )
        self.rsrc.glWindow.updateGL()
        self.linesGUI.removeItem( self.linesGUI.count() - 1 )
        self.linesGUI.setCurrentIndex( -1 )
        
    def editFlowLineCB( self, checked ):
        '''Cause the current line to be editable'''
        idx = self.linesGUI.currentIndex()
        if ( checked ):
            assert( idx > -1 )  # this button shouldn't be enabled if this isn't true
            self.context.editLine( idx )
        else:
            self.context.stopEdit()
        self.rsrc.glWindow.updateGL()
        
    def flipFlowLineCB( self ):
        '''Flip the current line'''
        idx = self.linesGUI.currentIndex()
        assert( idx > -1 )  # this button shouldn't be enabled if this isn't true
        self.context.flipLine( idx )
        self.rsrc.glWindow.updateGL()

    def flowLineNameChangeCB( self ):
        '''Called when the name of a flow line is edited.'''
        idx = self.linesGUI.currentIndex()
        if ( idx > -1 ):
            self.context.setLineName( idx, str( self.flowNameGUI.text() ) )
            
    def cancelAddFlowLine( self ):
        '''Called when an add flow line action is canceled'''
        self.linesGUI.removeItem( self.linesGUI.count() - 1 )
        self.linesGUI.setCurrentIndex( -1 )

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return 'FLOW'
    
    def readConfig( self, file ):
        '''Reads the widget state from the given file'''
        self.linesGUI.clear()
        TaskWidget.readConfig( self, file )
        self.context.setFromString( file.readline() )
        if ( self.context.lineCount() ):
            self.linesGUI.addItems( [ '%d' % i for i in xrange( self.context.lineCount() ) ] )
            self.linesGUI.setEnabled( True )
            self.linesGUI.setCurrentIndex( 0 )

    def writeConfig( self, file ):
        '''Writes the widget state to the given file'''
        TaskWidget.writeConfig( self, file )
        lineData = self.context.toConfigString()
        file.write( '%s\n' % lineData )

    def getTask( self ):
        '''Returns a task for this widget.

        @return     An instance of FlowAnalysisTask.
        @raises     ValueError if there is a problem in instantiating the task.addLine
        '''
        LINE_COUNT = self.context.lineCount()
        if ( LINE_COUNT == 0 ):
            print "No flow lines defined for FLOW task %s" % ( self.title() )
            raise ValueError
        
        task = FlowAnalysisTask()
        self.setTaskParameters( task )
        return task

    def copySettings( self, task ):
        '''Copy the settings from the given task into this task'''
        TaskWidget.copySettings( self, task )
        if ( isinstance( task, FlowTaskWidget ) ):
            self.context.copy( task.context )
            self.linesGUI.clear()
            items = [ task.linesGUI.itemText( i ) for i in xrange( task.linesGUI.count() ) ]
            self.linesGUI.addItems( items )
            hasItems = len( items ) > 0
            self.delFlowLineBtn.setEnabled( hasItems )
            self.flipFlowLineBtn.setEnabled( hasItems )
            self.editFlowLineBtn.setEnabled( hasItems )
            if ( hasItems ):
                self.linesGUI.setCurrentIndex( 0 )

    def setTaskParameters( self, task ):
        '''Sets the parameters in the task based on this widget.
        If there is a problem with the parameters, a ValueError exception is raised.

        @raises     ValueError if there is a problem in setting the parameters.
        '''
        TaskWidget.setTaskParameters( self, task )
        LINE_COUNT = self.context.lineCount()
        for i in xrange( LINE_COUNT ):
            task.addFlowLine( self.context.getLine( i ), self.context.getName( i ) )
    
class PopulationTaskWidget( TaskWidget ):
    def __init__( self, name, parent=None, delCB=None, rsrc=None ):
        TaskWidget.__init__( self, name, parent, delCB, rsrc )
        # TODO: This needs a context
        self.context = QTRectContext( self.cancelAddRect )

    def createRectBox( self ):
        '''Creates the GroupBox containing the widgets for controlling rectangular regions'''
        box = QtGui.QGroupBox( "Rectangular Regions" )
        layout = QtGui.QGridLayout( box )
        layout.setColumnStretch( 0, 0 )
        layout.setColumnStretch( 1, 1 )
        layout.setColumnStretch( 2, 1 )

        # Rectangular region selector
        self.rectsGUI = QtGui.QComboBox( box )
        self.rectsGUI.setEnabled( False )
        QtCore.QObject.connect( self.rectsGUI, QtCore.SIGNAL('currentIndexChanged(int)'), self.rectChangedCB )
        layout.addWidget( QtGui.QLabel("Region No."), 0, 1, 1, 1, QtCore.Qt.AlignRight )
        layout.addWidget( self.rectsGUI, 0, 2 )

        tmpLayout = QtGui.QHBoxLayout()

        # add button
        self.addRectBtn = QtGui.QPushButton( 'Add' )
        QtCore.QObject.connect( self.addRectBtn, QtCore.SIGNAL('clicked()'), self.addRectCB )      
        tmpLayout.addWidget( self.addRectBtn )

        # delete button
        self.delRectBtn = QtGui.QPushButton( 'Delete' )
        self.delRectBtn.setEnabled( False )
        QtCore.QObject.connect( self.delRectBtn, QtCore.SIGNAL('clicked()'), self.delRectCB )
        tmpLayout.addWidget( self.delRectBtn )

        # edit button
        self.editRectBtn = QtGui.QPushButton( 'Edit' )
        self.editRectBtn.setCheckable( True )
        self.editRectBtn.setEnabled( False )
        QtCore.QObject.connect( self.editRectBtn, QtCore.SIGNAL('toggled(bool)'), self.editRectCB )
        tmpLayout.addWidget( self.editRectBtn )

        layout.addLayout( tmpLayout, 1, 1, 1, 2 )

       # Region name
        layout.addWidget( QtGui.QLabel("Region Name"), 2, 0, 1, 1, QtCore.Qt.AlignRight )
        self.rectNameGUI = QtGui.QLineEdit()
        regExp = QtCore.QRegExp( "[^~\\|,]*" )
        validator = QtGui.QRegExpValidator( regExp, self )
        self.rectNameGUI.setValidator( validator )
        QtCore.QObject.connect( self.rectNameGUI, QtCore.SIGNAL('editingFinished()'), self.rectNameChangeCB )
        layout.addWidget( self.rectNameGUI, 2, 1, 1, 2 )
        
        return box
    
    def body( self ):
        '''Build the task-specific GUI.  This should be overwritten by subclass'''
        TaskWidget.body( self )
        self.bodyLayout.addWidget( self.createRectBox() )

    def rectChangedCB( self ):
        '''Called when the rect number changes'''
        idx = self.rectsGUI.currentIndex()
        active = idx > -1
        self.delRectBtn.setEnabled( active )
        self.editRectBtn.setEnabled( active )
        self.rectsGUI.setEnabled( self.rectsGUI.count() > 0 )
        if ( active ):
            self.rectNameGUI.setText( self.context.getName( idx ) )
        self.context.setActive( idx )
        self.rsrc.glWindow.updateGL()
        if ( not active ):
            self.editRectBtn.setChecked( False )

    def addRectCB( self ):
        '''When the add rect is clicked, we add the rect and update the GUI appropriately'''
        nextIdx = self.rectsGUI.count()
        self.delRectBtn.setEnabled( True )
        self.context.addRect()
        self.rectsGUI.addItem( '%d' % nextIdx )
        self.rectsGUI.setCurrentIndex( nextIdx )
        self.rectsGUI.setEnabled( True )
        self.editRectBtn.setChecked( True ) # this should call the callback and automatically enable the context to draw a rect
        self.rsrc.glWindow.updateGL()

    def delRectCB( self ):
        '''Remove the current selected rect'''
        idx = self.rectsGUI.currentIndex()
        assert( idx > -1 )  # this button shouldn't be enabled if this isn't true
        self.context.deleteRect( idx )
        self.rsrc.glWindow.updateGL()
        self.rectsGUI.removeItem( self.rectsGUI.count() - 1 )
        self.rectsGUI.setCurrentIndex( -1 )
        
    def editRectCB( self, checked ):
        '''Cause the current rect to be editable'''
        idx = self.rectsGUI.currentIndex()
        if ( checked ):
            assert( idx > -1 )  # this button shouldn't be enabled if this isn't true
            self.context.editRect( idx )
        else:
            self.context.stopEdit()
        self.rsrc.glWindow.updateGL()
        
    def rectNameChangeCB( self ):
        '''Called when the name of a rect is edited.'''
        idx = self.rectsGUI.currentIndex()
        if ( idx > -1 ):
            self.context.setName( idx, str( self.rectNameGUI.text() ) )
            
    def cancelAddRect( self ):
        '''Called when an add rect action is canceled'''
        self.rectsGUI.removeItem( self.rectsGUI.count() - 1 )
        self.rectsGUI.setCurrentIndex( -1 )

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return 'POPULATION'
    
    def readConfig( self, file ):
        '''Reads the widget state from the given file'''
        self.rectsGUI.clear()
        TaskWidget.readConfig( self, file )
        self.context.setFromString( file.readline() )
        if ( self.context.rectCount() ):
            self.rectsGUI.addItems( [ '%d' % i for i in xrange( self.context.rectCount() ) ] )
            self.rectsGUI.setEnabled( True )
            self.rectsGUI.setCurrentIndex( 0 )

    def writeConfig( self, file ):
        '''Writes the widget state to the given file'''
        TaskWidget.writeConfig( self, file )
        rectData = self.context.toConfigString()
        file.write( '%s\n' % rectData )

    def getTask( self ):
        '''Returns a task for this widget.

        @return     An instance of PopulationAnalysisTask.
        @raises     ValueError if there is a problem in instantiating the task.
        '''
        RECT_COUNT = self.context.rectCount()
        if ( RECT_COUNT == 0 ):
            print "No regions defined for POPULATION task %s" % ( self.title() )
            raise ValueError
        
        task = PopulationAnalysisTask()
        self.setTaskParameters( task )
        return task

    def setTaskParameters( self, task ):
        '''Sets the parameters in the task based on this widget.
        If there is a problem with the parameters, a ValueError exception is raised.

        @raises     ValueError if there is a problem in setting the parameters.
        '''
        TaskWidget.setTaskParameters( self, task )
        RECT_COUNT = self.context.rectCount()
        for i in xrange( RECT_COUNT ):
            task.addRectDomain( self.context.getRect( i ), self.context.getName( i ) )

    def copySettings( self, task ):
        '''Copy the settings from the given task into this task'''
        TaskWidget.copySettings( self, task )
        if ( isinstance( task, PopulationTaskWidget ) ):
            self.context.copy( task.context )
            self.rectsGUI.clear()
            items = [ task.rectsGUI.itemText( i ) for i in xrange( task.rectsGUI.count() ) ]
            self.rectsGUI.addItems( items )
            hasItems = len( items ) > 0
            self.delRectBtn.setEnabled( hasItems )
            self.editRectBtn.setEnabled( hasItems )
            if ( hasItems ):
                self.rectsGUI.setCurrentIndex( 0 )
