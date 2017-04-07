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
        # A logger for printing messages to the system
        self.logger = None

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
    FUND_DIAG = 4
    
    TECHNIQUES = ( 'Density', 'Flow', 'Speed', 'Population', 'Fundamental Diagram' )
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
            self.rsrc.logger.error( "No tasks to run" )
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
            self.rsrc.logger.info( "Starting task execution..." )
            self.workThread.start()
        else:
            self.rsrc.logger.error( "Already running" )

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
        elif ( index == self.FUND_DIAG ):
            TaskClass = FundDiagTaskWidget
        
        task = TaskClass( name, rsrc=self.rsrc, delCB=self.deleteTask )
        self.addTask( task, TaskClass.typeStr() )

    def addTask( self, task, tabLabel ):
        '''Adds a task to the widget'''
        self.taskGUIs.addTab( task, tabLabel )
        self.goBtn.setEnabled( True )
        QtCore.QObject.connect( task.goBtn, QtCore.SIGNAL('clicked(bool)'), self.runCurrent )
        self.tasks.append( task )
        self.taskGUIs.setCurrentWidget( task )
        
    def getTasks( self, testValid=True ):
        '''Returns a list of AnalysisTasks for the active task widgets.  If there are any
        errors (incomplete data, etc.) a ValueError is raised.

        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        @returns        A list of AnalysisTasks.
        @raises         ValueError if there are data problems with ANY task.
        '''
        aTasks = []
        for task in self.tasks:
            if ( task.isChecked() ):
                t = task.getTask( testValid )               
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

    def readConfig( self, fileName ):
        '''Configures the analysis widget based on configuraiton file.

        @param      fileName    A string.  The name of the file which contains the
                                configuration information.
        '''
        tasks = readAnalysisProject( fileName )
        for task in tasks:
            taskType = task.typeStr()
            TaskClass = getTaskWidgetClass( taskType )
            widget = TaskClass( '', rsrc=self.rsrc, delCB=self.deleteTask )
            widget.setFromTask( task )
            self.addTask( widget, taskType )

    def writeConfig( self, fileName ):
        '''Writes the configuration file based on task widget state.

        @param      fileName    A string.  The name of the file which contains the
                                configuration information.
        '''
        tasks = self.getTasks( False )
        writeAnalysisProject( tasks, fileName )        
            
def getTaskWidgetClass( taskName ):
    '''Returns a class object for the given analysis task name'''
    if ( taskName == DensityAnalysisTask.typeStr() ):
        return DensityTaskWidget
    elif ( taskName == FlowAnalysisTask.typeStr() ):
        return FlowTaskWidget
    elif ( taskName == SpeedAnalysisTask.typeStr() ):
        return SpeedTaskWidget
    elif ( taskName == PopulationAnalysisTask.typeStr() ):
        return PopulationTaskWidget
    elif ( taskName == FundDiagAnalysisTask.typeStr() ):
        return FundDiagTaskWidget
    else:
        self.rsrc.logger.error( "Unrecognized analysis task type: %s" % ( taskName ) )
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
        self.rsrc.logger.info( "Launching %s - %s" % ( self.typeStr(), self.title() ) )
  
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
                    self.rsrc.logger.warning( "SCB data is version %s, you must set the time step explicitly" % frameSet.version )
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
            self.rsrc.logger.info( 'Reading obstacle file: %s' % obstFileName )
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
                self.rsrc.logger.error( 'Error reading obstacle file: %s' % obstFileName )
        else:
            self.rsrc.logger.error( 'No obstacle file to load' )
    
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
    
    def copySettings( self, task ):
        '''Copy the settings from the given task into this task'''
        assert( isinstance( task, TaskWidget ) )
        self.scbFilePathGUI.setText( task.scbFilePathGUI.text() )
        self.timeStepGui.setValue( task.timeStepGui.value() )
        self.obstFilePathGUI.setText( task.obstFilePathGUI.text() )
        self.outPathGUI.setText( task.outPathGUI.text() )
        self.timeStepGui.setEnabled( task.timeStepGui.isEnabled() )
        # don't copy task name, activity or enabled state

    def setFromTask( self, task ):
        '''Sets the task properties from the given AnalysisTask.

        @param      task        An instance of AnalysisTask.
        '''
        self.scbFilePathGUI.setText( task.scbName )
        if ( task.scbName ):
            try:
                frameSet = NPFrameSet( str( task.scbName ) )
            except IOError:
                self.rsrc.logger.error( "Error with scb file - clearing the field" )
                self.scbFilePathGUI.setText( '' )
                self.timeStepGui.setEnabled( False )
            else:
                if ( frameSet.version[0] == '1' ):
                    self.timeStepGui.setEnabled( True )
                    self.timeStepGui.setValue( task.timeStep )
                else:
                    self.timeStepGui.setEnabled( False )
                    self.timeStepGui.setValue( frameSet.simStepSize )
        self.obstFilePathGUI.setText( task.obstName )
        self.outPathGUI.setText( task.workFldr )
        self.setTitle( task.workName )
        self.setEnabled( task.active )
        self.actionGUI.setCurrentIndex( task.work - 1 )

    def getTask( self, testValid=True ):
        '''Returns an AnalysisTask instance appropriate for this type of widget.

        This widget should be considered abstract and doesn't support an analysis task.
        
        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        '''
        raise NotImplementedError
        
    def setToTask( self, task, testValid=True ):
        '''Sets the parameters in the task based on this widget.
        If there is a problem with the parameters, a ValueError exception is raised.

        @param      task        Given an AnalysisTask, sets the widget's properties to
                                the task.
        
        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        @raises     ValueError if there is a problem in setting the parameters.
        '''
        # input scb file
        task.setTaskName( str( self.title() ) )
        # action
        actIndex = self.actionGUI.currentIndex()
        active = True
        if ( actIndex == 0 ):
            task.setWork( AnalysisTask.COMPUTE )
        elif ( actIndex == 1 ):
            task.setWork( AnalysisTask.VIS )
        elif ( actIndex == 2 ):
            task.setWork( AnalysisTask.COMPUTE_VIS )
        else:
            if ( testValid ):
                self.rsrc.logger.error( "Unrecognized value for task action %s for %s" % ( self.actionGUI.currentText(), self.title() ) )
                raise ValueError
            else:
                self.rsrc.logger.warning( "Unrecognized value for task action %s for %s -- setting the task inactive" % ( self.actionGUI.currentText(), self.title() ) )
                active = False
        # scb file
        scbFile = str( self.scbFilePathGUI.text() ).strip()
        if ( not scbFile ):
            if ( testValid ):
                self.rsrc.logger.error( "No scb file specified for analysis" )
                raise ValueError
            else:
                self.rsrc.logger.warning( "No scb file specified for analysis" )
        task.setSCBFile( scbFile )
        dt = self.timeStepGui.value()
        if ( dt == 0.0 ):
            if ( testValid ):
                self.rsrc.logger.error( "No time step specified!" )
                raise ValueError
            else:
                self.rsrc.logger.warning( "No time step specified! - setting 0.0" )
                dt = 0.0
        # time step
        task.setTimeStep( dt )
        # output folder
        outFldr = str( self.outPathGUI.text() )
        if ( not outFldr ):
            if ( testValid ):
                self.rsrc.logger.error( "No output folder specified for %s - %s" % ( self.typeStr(), self.title() ) )
                raise ValueError
            else:
                self.rsrc.logger.warning( "No output folder specified for %s - %s -- setting to execution folder" % ( self.typeStr(), self.title() ) )
                outFldr = '.'
        task.setWorkFolder( outFldr )
        task.setActiveState( self.isChecked() and active )
        task.setObstFile( str( self.obstFilePathGUI.text() ) )

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
                self.rsrc.logger.warning( 'There is a memory leak for png format!' )
        QtCore.QObject.connect( self.imgFormatGUI, QtCore.SIGNAL('currentIndexChanged(int)'), formatIdxChanged )
        fLayout.addWidget( self.imgFormatGUI, 3, 1, 1, 1 )        

        return box
        
    def body( self ):
        TaskWidget.body( self )
        self.bodyLayout.addWidget( self.domainBox() )
        self.bodyLayout.addWidget( self.rasterBox() )

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

    def setFromTask( self, task ):
        '''Sets the task properties from the given AnalysisTask.

        @param      task        An instance of AnalysisTask.
        '''
        assert( isinstance( task, DiscreteAnalysisTask ) )
        TaskWidget.setFromTask( self, task )
        self.domainMinXGUI.setValue( task.domainX[0] )
        self.domainMinYGUI.setValue( task.domainY[0] )
        self.domainSizeXGUI.setValue( task.domainX[1] - task.domainX[0] )
        self.domainSizeYGUI.setValue( task.domainY[1] - task.domainY[0] )
        self.cellSizeGUI.setValue( task.cellSize )
        self.colorMapGUI.setCurrentIndex( self.colorMapGUI.findText( task.colorMapName ) )
        self.imgFormatGUI.setCurrentIndex( self.imgFormatGUI.findText( task.outImgType ) )

    def getTask( self, testValid=True ):
        '''Returns an AnalysisTask instance appropriate for this type of widget.

        This widget should be considered abstract and doesn't support an analysis task.

        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        '''
        raise NotImplementedError
        
    def setToTask( self, task, testValid=True ):
        '''Sets the parameters in the task based on this widget.
        If there is a problem with the parameters, a ValueError exception is raised.

        @param      task        Given an AnalysisTask, sets the widget's properties to
                                the task.
        
        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        @raises     ValueError if there is a problem in setting the parameters.
        '''
        TaskWidget.setToTask( self, task, testValid )
        w = self.domainSizeXGUI.value()
        h = self.domainSizeYGUI.value()
        if ( w <= 0.0 or h <= 0.0 ):
            if ( testValid ):
                self.rsrc.logger.error( "Invalid domain defined for analysis - zero area" )
                raise ValueError
            else:
                self.rsrc.logger.warning( "Invalid domain defined for analysis - zero area" )
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

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return 'DENSITY'

    def copySettings( self, task ):
        '''Copy the settings from the given task into this task'''
        TaskWidget.copySettings( self, task )
        if ( isinstance( task, DensityTaskWidget ) ):
            self.kernelSizeGUI.setValue( task.kernelSizeGUI.value() )

    def setFromTask( self, task ):
        '''Sets the task properties from the given DensityAnalysisTask.

        @param      task        An instance of DensityAnalysisTask.
        '''
        assert( isinstance( task, DensityAnalysisTask ) )
        DomainTaskWidget.setFromTask( self, task )
        self.kernelSizeGUI.setValue( task.smoothParam )
        
    def getTask( self, testValid=True ):
        '''Returns a task for this widget.

        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        @return     An instance of DensityAnalysisTask.
        @raises     ValueError if there is a problem in instantiating the task.addLine
        '''
        task = DensityAnalysisTask()
        self.setToTask( task, testValid )
        return task

    def setToTask( self, task, testValid=True ):
        '''Sets the parameters in the task based on this widget.
        If there is a problem with the parameters, a ValueError exception is raised.

        @param      task        Given an AnalysisTask, sets the widget's properties to
                                the task.
        
        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        @raises     ValueError if there is a problem in setting the parameters.
        '''
        DomainTaskWidget.setToTask( self, task, testValid )
        task.setSmoothParam( self.kernelSizeGUI.value() )

class SpeedTaskWidget( DomainTaskWidget ):
    def __init__( self, name, parent=None, delCB=None, rsrc=None ):
        DomainTaskWidget.__init__( self, name, parent, delCB, rsrc )

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return 'SPEED'

    def getTask( self, testValid=True ):
        '''Returns a task for this widget.

        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        @return     An instance of SpeedAnalysisTask.
        @raises     ValueError if there is a problem in instantiating the task.addLine
        '''
        task = SpeedAnalysisTask()
        self.setToTask( task, testValid=True )
        return task

class FlowTaskWidget( TaskWidget ):
    X0 = 0
    X1 = 1
    Y0 = 2
    Y1 = 3
    def __init__( self, name, parent=None, delCB=None, rsrc=None ):
        TaskWidget.__init__( self, name, parent, delCB, rsrc )
        # TODO: This needs a context
        self.context = QTFlowLineContext( self.cancelAddFlowLine )
        QtCore.QObject.connect( self.context, QtCore.SIGNAL('lineEdited(PyQt_PyObject)'), self.setLineValues )

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
        self.editFlowLineBtn = QtGui.QPushButton( 'Edit in View' )
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

        # current line values
        layout.addWidget( self.lineEndPointBox(), 4, 0, 1, 3 )
        
        return box

    def lineEndPointBox( self ):
        '''Creates the box containing the values of the current line's end points.'''
        pointBox = QtGui.QGroupBox( "Line Endpoint Values" )
        fLayout = QtGui.QGridLayout( pointBox )
        fLayout.setColumnStretch( 0, 0 )
        fLayout.setColumnStretch( 1, 1 )
        fLayout.setColumnStretch( 2, 1 )

        # labels
        fLayout.addWidget( QtGui.QLabel( "Point 0" ), 0, 1, 1, 1, QtCore.Qt.AlignHCenter )
        fLayout.addWidget( QtGui.QLabel( "Point 1" ), 0, 2, 1, 1, QtCore.Qt.AlignHCenter )
        fLayout.addWidget( QtGui.QLabel( "x" ), 1, 0, 1, 1, QtCore.Qt.AlignRight )
        fLayout.addWidget( QtGui.QLabel( "y" ), 2, 0, 1, 1, QtCore.Qt.AlignRight )

        # numerical fields
        self.x0 = QtGui.QDoubleSpinBox( self )
        self.x0.setValue( 0.0 )
        self.x0.setRange(-1e6, 1e6 )
        self.x0.setEnabled( False )
        QtCore.QObject.connect( self.x0, QtCore.SIGNAL('valueChanged(double)'), lambda x: self.setPoint(self.X0, x) )
        fLayout.addWidget( self.x0, 1, 1, 1, 1 )
        self.x1 = QtGui.QDoubleSpinBox( self )
        self.x1.setValue( 0.0 )
        self.x1.setRange(-1e6, 1e6 )
        self.x1.setEnabled( False )
        QtCore.QObject.connect( self.x1, QtCore.SIGNAL('valueChanged(double)'), lambda x: self.setPoint(self.X1, x) )
        fLayout.addWidget( self.x1, 1, 2, 1, 1 )

        self.y0 = QtGui.QDoubleSpinBox( self )
        self.y0.setValue( 0.0 )
        self.y0.setRange(-1e6, 1e6 )
        self.y0.setEnabled( False )
        QtCore.QObject.connect( self.y0, QtCore.SIGNAL('valueChanged(double)'), lambda x: self.setPoint(self.Y0, x) )
        fLayout.addWidget( self.y0, 2, 1, 1, 1 )
        self.y1 = QtGui.QDoubleSpinBox( self )
        self.y1.setValue( 0.0 )
        self.y1.setRange(-1e6, 1e6 )
        self.y1.setEnabled( False )
        QtCore.QObject.connect( self.y1, QtCore.SIGNAL('valueChanged(double)'), lambda x: self.setPoint(self.Y1, x) )
        fLayout.addWidget( self.y1, 2, 2, 1, 1 )

        return pointBox

    def setPoint( self, valId, value ):
        idx = self.linesGUI.currentIndex()
        assert( idx > -1 )  # this button shouldn't be enabled if this isn't true
        line = self.context.getLine( idx )
        if ( valId == self.X0 ):
            line.p1.x = value
        elif ( valId == self.X1 ):
            line.p2.x = value
        elif ( valId == self.Y0 ):
            line.p1.y = value
        elif ( valId == self.Y1 ):
            line.p2.y = value
        self.rsrc.glWindow.updateGL()
    
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
        self.setEndPoints()

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
        self.setEndPoints()
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

    def setEndPoints( self ):
        '''Sets the end point values based on the current line'''
        idx = self.linesGUI.currentIndex()
        if ( idx > -1 ):
            line = self.context.getLine( idx )
            self.setLineValues( line )
        else:
            self.setLineValues( None )

    def setLineValues( self, line ):
        if ( not line is None ):
            def enable( widget, value ):
                    widget.blockSignals( True )
                    widget.setEnabled( True )
                    widget.setValue( value )
                    widget.blockSignals( False )
            enable( self.x0, line.p1.x )
            enable( self.y0, line.p1.y )
            enable( self.x1, line.p2.x )
            enable( self.y1, line.p2.y )
        else:
            def disable( widget ):
                widget.blockSignals( True )
                widget.setEnabled( False )
                widget.setValue( 0.0 )
                widget.blockSignals( False )
            disable( self.x0 )
            disable( self.x1 )
            disable( self.y0 )
            disable( self.y1 )

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return 'FLOW'
    
    def copySettings( self, task ):
        '''Copy the settings from the given task widget into this task widget'''
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

    def setFromTask( self, task ):
        '''Sets the task properties from the given FlowAnalysisTask.

        @param      task        An instance of FlowAnalysisTask.
        '''
        assert( isinstance( task, FlowAnalysisTask ) )
        TaskWidget.setFromTask( self, task )
        self.context.setMultiLines( task.lineNames, task.lines )
        lines = task.lines
        hasItems = len( lines ) > 0
        if ( hasItems ):            
            items = [ '%d' % i for i in xrange( len( lines ) ) ]
            self.linesGUI.addItems( items )
            self.linesGUI.setCurrentIndex( 0 )
            self.linesGUI.setEnabled( hasItems )
            self.delFlowLineBtn.setEnabled( hasItems )
            self.flipFlowLineBtn.setEnabled( hasItems )
            self.editFlowLineBtn.setEnabled( hasItems )
        
    def getTask( self, testValid=True ):
        '''Returns a task for this widget.

        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        @return     An instance of FlowAnalysisTask.
        @raises     ValueError if there is a problem in instantiating the task.addLine
        '''
        LINE_COUNT = self.context.lineCount()
        if ( LINE_COUNT == 0 ):
            self.rsrc.logger.error( "No flow lines defined for FLOW task %s" % ( self.title() ) )
            raise ValueError
        
        task = FlowAnalysisTask()
        self.setToTask( task, testValid )
        return task

    def setToTask( self, task, testValid=True ):
        '''Sets the parameters in the task based on this widget.
        If there is a problem with the parameters, a ValueError exception is raised.

        @param      task        Given an AnalysisTask, sets the widget's properties to
                                the task.
        
        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        @raises     ValueError if there is a problem in setting the parameters.
        '''
        TaskWidget.setToTask( self, task, testValid )
        LINE_COUNT = self.context.lineCount()
        for i in xrange( LINE_COUNT ):
            task.addFlowLine( self.context.getLine( i ), self.context.getName( i ) )
    
class RectRegionTaskWidget( TaskWidget ):
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
        return 'RectRegion'

    def copySettings( self, task ):
        '''Copy the settings from the given task into this task'''
        TaskWidget.copySettings( self, task )
        if ( isinstance( task, RectRegionTaskWidget ) ):
            self.context.copy( task.context )
            self.rectsGUI.clear()
            items = [ task.rectsGUI.itemText( i ) for i in xrange( task.rectsGUI.count() ) ]
            self.rectsGUI.addItems( items )
            hasItems = len( items ) > 0
            self.delRectBtn.setEnabled( hasItems )
            self.editRectBtn.setEnabled( hasItems )
            if ( hasItems ):
                self.rectsGUI.setCurrentIndex( 0 )
                self.rectsGUI.setEnabled( True )
    
    def setFromTask( self, task ):
        '''Sets the task properties from the given RectRegionAnalysisTask.

        @param      task        An instance of RectRegionAnalysisTask.
        '''
        assert( isinstance( task, RectRegionAnalysisTask ) )
        TaskWidget.setFromTask( self, task )
        self.context.setMultiRects( task.rectNames, task.rects )
        rects = task.rects
        hasItems = len( rects ) > 0
        if ( hasItems ):            
            items = [ '%d' % i for i in xrange( len( rects ) ) ]
            self.rectsGUI.addItems( items )
            self.rectsGUI.setCurrentIndex( 0 )
            self.rectsGUI.setEnabled( hasItems )
            self.delRectBtn.setEnabled( hasItems )
            self.editRectBtn.setEnabled( hasItems )
        
    def getTask( self, testValid=True ):
        '''Returns a task for this widget.

        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        @return     An instance of PopulationAnalysisTask.
        @raises     ValueError if there is a problem in instantiating the task.
        '''
        raise NotImplementedError

    def setToTask( self, task, testValid=True ):
        '''Sets the parameters in the task based on this widget.
        If there is a problem with the parameters, a ValueError exception is raised.

        @param      task        Given an AnalysisTask, sets the widget's properties to
                                the task.
        
        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        @raises     ValueError if there is a problem in setting the parameters.
        '''
        TaskWidget.setToTask( self, task, testValid )
        RECT_COUNT = self.context.rectCount()
        for i in xrange( RECT_COUNT ):
            task.addRectDomain( self.context.getRect( i ), self.context.getName( i ) )

class PopulationTaskWidget( RectRegionTaskWidget ):
    '''Widget for computing the population in rectangular regions'''
    def __init__( self, name, parent=None, delCB=None, rsrc=None ):
        RectRegionTaskWidget.__init__( self, name, parent, delCB, rsrc )

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return 'POPULATION'

    def getTask( self, testValid=True ):
        '''Returns a task for this widget.

        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        @return     An instance of PopulationAnalysisTask.
        @raises     ValueError if there is a problem in instantiating the task.
        '''
        RECT_COUNT = self.context.rectCount()
        if ( RECT_COUNT == 0 ):
            self.rsrc.logger.error( "No regions defined for POPULATION task %s" % ( self.title() ) )
            raise ValueError
        
        task = PopulationAnalysisTask()
        self.setToTask( task, testValid )
        return task
    
class FundDiagTaskWidget( RectRegionTaskWidget ):
    '''Widget for computing the fundamental diagram'''
    def __init__( self, name, parent=None, delCB=None, rsrc=None ):
        RectRegionTaskWidget.__init__( self, name, parent, delCB, rsrc )

    @staticmethod
    def typeStr():
        '''Returns a string representation of this task'''
        return 'FUND DIAG'

    def getTask( self, testValid=True ):
        '''Returns a task for this widget.

        @param          testValid       A boolean.  If True, the function (and those called)
                                        will test the widget state to make sure the task is
                                        valid.  If False, empty fields will be propagated.
        @return     An instance of FundDiagAnalysisTask.
        @raises     ValueError if there is a problem in instantiating the task.
        '''
        RECT_COUNT = self.context.rectCount()
        if ( RECT_COUNT == 0 ):
            self.rsrc.logger.error( "No regions defined for FUND DIAG task %s" % ( self.title() ) )
            raise ValueError
        
        task = FundDiagAnalysisTask()
        self.setToTask( task, testValid )
        return task
    