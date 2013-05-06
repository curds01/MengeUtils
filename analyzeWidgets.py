# I'm trying to construct an app with a big window on the right and a scrollable window of widgets
#    on the left.

from PyQt4 import QtGui, QtCore
import os
from obstacles import readObstacles
from ColorMap import *
from qtcontext import *


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
    
class CollapsableWidget( QtGui.QGroupBox ):
    '''A Qt GroupBox that allows collapsing'''
    def __init__( self, title, parent=None ):
        QtGui.QGroupBox.__init__( self, title, parent )
        self.setCheckable( True )
        layout = QtGui.QVBoxLayout( self )
        self.bodyFrame = QtGui.QFrame( self )
        layout.addWidget( self.bodyFrame, 0 )
        QtCore.QObject.connect( self, QtCore.SIGNAL('toggled(bool)'), self.toggleState )

    def toggleState( self, state ):
        '''Hides/shows the body of the collapsable widget based on the checked
        state of the group box.

        @param      state       A boolean.  The state of the group box check box.
        '''
        self.bodyFrame.setHidden( not state )

    def setLayout( self, layout ):
        '''Sets the layout of the body'''
        self.bodyFrame.setLayout( layout )

    def addWidget( self, widget ):
        '''Adds the child widget to the body of the widget'''
        widget.setParent( self.bodyFrame )

class DynamicItem( QtGui.QWidgetItem ):
    '''A layout item that expects the underlying widget to change shape.  As such, it doesn't
    cache size hints or minimum size.'''
    def __init__( self, widget=None ):
        QtGui.QWidgetItem.__init__( self, widget )
        self.widget = widget
    
    def minimumSize( self ):
        return self.widget.minimumSize()

    def sizeHint( self ):
        return self.widget.sizeHint()    

class VFlowLayout( QtGui.QLayout ):
    '''A layout for flowing child widgets from top to bottom'''
    def __init__( self, parent=None, margin=0, spacing=-1 ):
        QtGui.QLayout.__init__( self )
        self.setMargin( margin )
        self.setSpacing( spacing )
        self.items = []

    def addItem( self, layoutItem ):
        '''Add a layout item to the layout'''
        self.items.append( layoutItem )

    def addWidget( self, widget ):
        '''Add a widget to the layout'''
        self.addItem( DynamicItem( widget ) )

    def expandingDirections( self ):
        '''Returns the expanding directions of the layout'''
        return 0

    def hasHeightForWidth( self ):
        '''Reports if the height depends on width'''
        return False

    def count( self ):
        '''Returns the number of elements in the layout'''
        return len( self.items )

    def itemAt( self, index):
        '''Returns the layout item with the given index'''
        try:
            return self.items[ index ]
        except IndexError:
            return None

    def minimumSize( self ):
        '''Returns the minimimu size (QSize) for the contents'''
        size = QtCore.QSize()
        space = self.spacing()
        w = 0
        h = 0
        for item in self.items:
            s = item.minimumSize()
            w = max( w, s.width() )
            h += s.height() + space
        size = QtCore.QSize( 2 * self.margin() + w, 2 * self.margin() + h )
        return size

    def setGeometry( self, rect ):
        '''Sets the geometry of the layout from a QRect'''
        QtGui.QLayout.setGeometry( self, rect )
        self.doLayout( rect )

    def sizeHint( self ):
        '''Returns the size hint for the layout'''
        size = QtCore.QSize()
        space = self.spacing()
        w = 0
        h = 0
        for item in self.items:
            s = item.sizeHint()
            w = max( w, s.width() )
            h += s.height() + space
            
        size = QtCore.QSize( 2 * self.margin() + w, 2 * self.margin() + h )
        return size

    def takeAt( self, index ):
        '''Remove and returns the layout item at the given index'''
        try:
            self.items.pop( index )
        except IndexError:
            return 0

    def doLayout( self, rect ):
        '''Performs the layout in the given rectangle.  Returns the final y value'''
        x = rect.x()
        w = rect.width() - 20
        y = rect.y()
        space = self.spacing()

        for item in self.items:
            size = item.sizeHint()
            fitSize = QtCore.QSize( w, size.height() )
            item.setGeometry( QtCore.QRect( QtCore.QPoint(x, y), fitSize ) )
            y += space + size.height()
        return y 

class InputWidget( QtGui.QGroupBox ):
    '''The group box which contains the input data for the work'''
    def __init__( self, rsrc, parent=None ):
        '''Constructor.

        @param      rsrc        An instance of SystemResource.  Used to coordinate
                                system-wide data.
        '''
        QtGui.QGroupBox.__init__( self, 'Input', parent )
        self.rsrc = rsrc
        self.build()

    def build( self ):
        '''Populate the widget with the input elements'''
        fLayout = QtGui.QGridLayout( self )
        fLayout.setColumnStretch( 0, 0 )
        fLayout.setColumnStretch( 1, 1 )
        fLayout.setColumnStretch( 2, 0 )
        # scb file
        fLayout.addWidget( QtGui.QLabel( "SCB file" ), 0, 0, 1, 1, QtCore.Qt.AlignRight )
        self.scbFilePathGUI = QtGui.QPushButton( '', self )
        QtCore.QObject.connect( self.scbFilePathGUI, QtCore.SIGNAL('clicked(bool)'), self.selectSCBDlg )
        fLayout.addWidget( self.scbFilePathGUI, 0, 1, 1, 2 )

        # domain
        fLayout.addWidget( QtGui.QLabel( "Min. Point" ), 1, 0, 1, 1, QtCore.Qt.AlignRight )
        self.domainMinXGUI = QtGui.QDoubleSpinBox( self )
        self.domainMinXGUI.setRange( -1e6, 1e6 )
        fLayout.addWidget( self.domainMinXGUI, 1, 1, 1, 1 )
        self.domainMinYGUI = QtGui.QDoubleSpinBox( self )
        self.domainMinYGUI.setRange( -1e6, 1e6 )
        fLayout.addWidget( self.domainMinYGUI, 1, 2, 1, 1 )

        fLayout.addWidget( QtGui.QLabel( "Domain Size" ), 2, 0, 1, 1, QtCore.Qt.AlignRight )
        self.domainSizeXGUI = QtGui.QDoubleSpinBox( self )
        self.domainSizeXGUI.setRange( -1e6, 1e6 )
        fLayout.addWidget( self.domainSizeXGUI, 2, 1, 1, 1 )
        self.domainSizeYGUI = QtGui.QDoubleSpinBox( self )
        self.domainSizeYGUI.setRange( -1e6, 1e6 )
        fLayout.addWidget( self.domainSizeYGUI, 2, 2, 1, 1 )        

        # timestep
        fLayout.addWidget( QtGui.QLabel( "Time step" ), 3, 0, 1, 1, QtCore.Qt.AlignRight )
        self.timeStepGui = QtGui.QDoubleSpinBox( self )
        self.timeStepGui.setDecimals( 4 )
        fLayout.addWidget( self.timeStepGui, 3, 1, 1, 2 )

        # obstacle file
        fLayout.addWidget( QtGui.QLabel( "Obstacle file" ), 4, 0, 1, 1, QtCore.Qt.AlignRight )
        self.obstFilePathGUI = QtGui.QPushButton( '', self )
        QtCore.QObject.connect( self.obstFilePathGUI, QtCore.SIGNAL('clicked(bool)'), self.selectObstDlg )
        fLayout.addWidget( self.obstFilePathGUI, 4, 1, 1, 1 )
        self.loadObstBtn = QtGui.QPushButton( "Load", self )
        QtCore.QObject.connect( self.loadObstBtn, QtCore.SIGNAL('clicked(bool)'), self.loadObstacle )
        fLayout.addWidget( self.loadObstBtn, 4, 2, 1, 1 )

    def selectSCBDlg( self ):
        """Spawns a dialog to select an scb file"""
        fileName = QtGui.QFileDialog.getOpenFileName( self, "Open SCB file", self.rsrc.lastFolder, "SCB Files (*.scb)")
        if ( fileName ):
            self.scbFilePathGUI.setText( fileName )
            path, fName = os.path.split( str( fileName ) )
            self.rsrc.lastFolder = path


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

    def setFromConfig( self, cfg ):
        '''Sets the various fields from a configuration'''
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

    def setConfig( self, cfg ):
        '''Sets the various fields into the given cfg file'''
        cfg[ 'SCB' ] = str( self.scbFilePathGUI.text() )
        cfg[ 'minPtX' ] = self.domainMinXGUI.value()
        cfg[ 'minPtY' ] = self.domainMinYGUI.value()
        cfg[ 'sizeX' ] = self.domainSizeXGUI.value()
        cfg[ 'sizeY' ] = self.domainSizeYGUI.value()
        cfg[ 'timeStep' ] = self.timeStepGui.value()
        cfg[ 'obstacle' ] = str( self.obstFilePathGUI.text() )


class AnlaysisWidget( QtGui.QGroupBox ):
    '''The widget for controlling the analysis'''
    # Enumerations of the type of analysis
    DENSITY = 0
    POPULATION = 1
    FLOW = 2
    SPEED = 3
    
    TECHNIQUES = ( 'Density', 'Population', 'Flow', 'Speed' )
    def __init__( self, rsrc, parent=None ):
        '''Constructor.

        @param      rsrc        An instance of SystemResource.  Used to coordinate
                                system-wide data.
        '''
        QtGui.QGroupBox.__init__( self, 'Analysis', parent )
        self.rsrc = rsrc
        self.build()
        self.tasks = []

    def build( self ):
        layout = QtGui.QGridLayout()
        layout.setColumnStretch( 0, 0 )
        layout.setColumnStretch( 1, 1 )

        ####################################
        # Control for adding widgets
        addBtn = QtGui.QPushButton( 'Add', self )
        layout.addWidget( addBtn, 0, 0 )
        QtCore.QObject.connect( addBtn, QtCore.SIGNAL('clicked(bool)'), self.addWork )
        # TODO: Connect this
        self.toolGUI = QtGui.QComboBox( self )
        self.toolGUI.addItems( self.TECHNIQUES )
        layout.addWidget( self.toolGUI, 0, 1 )
        layout.addWidget( QtGui.QLabel("Task name"), 1, 0 )
        self.taskNameGUI = QtGui.QLineEdit()
        layout.addWidget( self.taskNameGUI, 1, 1 )

        # This should be greyed out if no actions exist
        self.goBtn = QtGui.QPushButton( 'Go', self )
        self.goBtn.setEnabled( False )
        layout.addWidget( self.goBtn, 2, 0, 1, 2 )
        # TODO: Connect this

        div = QtGui.QFrame( self )
        div.setFrameShape( QtGui.QFrame.HLine )
        div.setFrameShadow( QtGui.QFrame.Sunken )
        layout.addWidget( div, 3, 0, 1, 2 )
        taskLabel = QtGui.QLabel( "Tasks" )
        layout.addWidget( taskLabel, 4, 0, 1, 2 )

        self.taskGUIs = QtGui.QTabWidget()
        QtCore.QObject.connect( self.taskGUIs, QtCore.SIGNAL('currentChanged(int)'), self.changeActiveTask )
        layout.addWidget( self.taskGUIs, 5, 0, 1, 2 )
        
        self.setLayout( layout )

    def changeActiveTask( self, active ):
        '''Called when the tab of a task is selected'''
        self.taskGUIs.currentWidget().activate()
    
    def deleteTask( self, task ):
        '''Deletes the given task from the analysis.

        @param      task        An instance of a WorkWidget (or subclass).  The task to be
                                deleted.
        '''
        assert( task in self.tasks )
        self.tasks.pop( self.tasks.index( task ) )
        idx = self.taskGUIs.indexOf( task )
        self.taskGUIs.removeTab( idx )
        if ( self.taskGUIs.count() == 0 ):
            self.goBtn.setEnabled( False )

    def addWork( self ):
        '''Adds a block of work'''
        name = str( self.taskNameGUI.text() )
        if ( not name ):
            name = 'junk'
        self.taskNameGUI.setText( '' )
        
        index = self.toolGUI.currentIndex()
        if ( index == self.DENSITY ):
            TaskClass = DensityWorkWidget
            s = "DENSITY"
        elif ( index == self.POPULATION ):
            TaskClass = WorkWidget
            s = "POPULATION"
        elif ( index == self.FLOW ):
            TaskClass = FlowWorkWidget
            s = "FLOW"
        elif ( index == self.SPEED ):
            TaskClass = SpeedWorkWidget
            s = "SPEED"

        task = TaskClass( name, rsrc=self.rsrc, delCB=self.deleteTask )
        
        self.taskGUIs.addTab( task, s )
        self.goBtn.setEnabled( True )
        self.tasks.append( task )
        
    def setConfig( self, cfg ):    
        '''Sets the various fields into the given cfg file'''
        pass

    def setFromConfig( self, cfg ):
        '''Sets the various fields from a configuration'''
        pass

class WorkWidget( QtGui.QGroupBox ):
    '''The basic widget for doing work'''
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
        self.name = name
        self.delCB = delCB
        self.context = None
        self.rsrc = rsrc
        assert( not self.rsrc is None )
        
        self.bodyLayout = QtGui.QVBoxLayout( self )
        self.header()
        self.body()
        self.bodyLayout.addStretch( 10 )

    def deleteCB( self ):
        '''Called when the delete button is clicked'''
        if ( self.delCB ):
            self.delCB( self )
            
    def mouseDoubleClickEvent( self, event ):
        # Spawn a dialog to change the task name
        text, ok = QtGui.QInputDialog.getText( self.parent(), 'Change task name', 'Task name' )
        if ( ok ):
            self.setTitle( text )
            self.name = str( text )

    def header( self ):
        '''Builds the header for the work widget'''
        self.bodyLayout.addWidget( self.actionBox() )
        self.bodyLayout.addWidget( self.outputBox() )

    def actionBox( self ):
        '''Create the QGroupBox containing the action widgets'''
        inputBox = QtGui.QGroupBox("Action")
        fLayout = QtGui.QGridLayout( inputBox )

        self.goBtn = QtGui.QPushButton( "Go", self )
        fLayout.addWidget( self.goBtn, 0, 0 )
        # TODO connect this
        
        self.delBtn = QtGui.QPushButton( "Del", self )
        fLayout.addWidget( self.delBtn, 0, 1 )
        QtCore.QObject.connect( self.delBtn, QtCore.SIGNAL('released()'), self.deleteCB )

        # Folder path for output image files
        self.actionGUI = QtGui.QComboBox( self )
        self.actionGUI.addItems( ( "Compute", "Visualize", "Compute and Vis." ) )
        fLayout.addWidget( self.actionGUI, 1, 0, 1, 2 )
        # TODO: Connect this to something
        return inputBox

    def outputBox( self ):
        '''Craete the QGroupBox containing the output widgets'''
        inputBox = QtGui.QGroupBox("Output")
        fLayout = QtGui.QGridLayout( inputBox )
        fLayout.setColumnStretch( 0, 0 )
        fLayout.setColumnStretch( 1, 1 )
        fLayout.addWidget( QtGui.QLabel( "Folder" ), 0, 0, 1, 1, QtCore.Qt.AlignRight )
        self.outPathGUI = QtGui.QPushButton( '', self )
        QtCore.QObject.connect( self.outPathGUI, QtCore.SIGNAL('clicked(bool)'), self.selectOutPathDlg )
        fLayout.addWidget( self.outPathGUI, 0, 1, 1, 1 )
        return inputBox
    
    def body( self ):
        '''Build the task-specific GUI.  This should be overwritten by subclass'''
        pass

    def selectOutPathDlg( self ):
        """Spawns a dialog to select an scb file"""
        fileName = QtGui.QFileDialog.getExistingDirectory( self, "Select Output Folder", self.rsrc.lastFolder )
        if ( fileName ):
            self.outPathGUI.setText( fileName )
            self.rsrc.lastFolder = str( fileName )

    def activate( self ):
        '''Called when the work widget is activated'''
        if ( self.isChecked ):
            self.rsrc.glWindow.setUserContext( self.context )
        else:
            self.rsrc.glWindow.setUserContext( None )
        self.rsrc.glWindow.updateGL()
            
class DensityWorkWidget( WorkWidget ):
    def __init__( self, name, parent=None, delCB=None, rsrc=None ):
        WorkWidget.__init__( self, name, parent, delCB, rsrc )

    def createRasterBox( self ):
        '''Create the widgets for the rasterization settings'''
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
        self.colorMapGUI.setCurrentIndex( 0 )
        fLayout.addWidget( self.colorMapGUI, 2, 1, 1, 1 )
        
        fLayout.addWidget( QtGui.QLabel( "Image format" ), 3, 0, 1, 1, QtCore.Qt.AlignRight )
        self.imgFormatGUI = QtGui.QComboBox( box )
        self.imgFormatGUI.addItems( ( 'jpg', 'bmp', 'png' ) )
        def formatIdxChanged( idx ):
            if ( idx == 2 ):
                self.logMessage( 'There is a memory leak for png format!' )
        QtCore.QObject.connect( self.imgFormatGUI, QtCore.SIGNAL('currentIndexChanged(int)'), formatIdxChanged )
        fLayout.addWidget( self.imgFormatGUI, 3, 1, 1, 1 )        

        return box
        
    def body( self ):
        '''Build the task-specific GUI.  This should be overwritten by subclass'''
        self.bodyLayout.addWidget( self.createRasterBox() )
        
class SpeedWorkWidget( WorkWidget ):
    def __init__( self, name, parent=None, delCB=None, rsrc=None ):
        WorkWidget.__init__( self, name, parent, delCB, rsrc )

    def createRasterBox( self ):
        '''Create the widgets for the rasterization settings'''
        box = QtGui.QGroupBox("Raster Settings")
        fLayout = QtGui.QGridLayout( box )
        fLayout.setColumnStretch( 0, 0 )
        fLayout.setColumnStretch( 1, 1 )

        fLayout.addWidget( QtGui.QLabel( "Cell Size" ), 1, 0, 1, 1, QtCore.Qt.AlignRight )
        self.cellSizeGUI = QtGui.QDoubleSpinBox( box )
        fLayout.addWidget( self.cellSizeGUI, 1, 1, 1, 1 )

        fLayout.addWidget( QtGui.QLabel( "Color Map" ), 2, 0, 1, 1, QtCore.Qt.AlignRight )
        self.colorMapGUI = QtGui.QComboBox( box )
        cmaps = COLOR_MAPS.keys()
        cmaps.sort()
        self.colorMapGUI.addItems( cmaps )
        self.colorMapGUI.setCurrentIndex( 0 )
        fLayout.addWidget( self.colorMapGUI, 2, 1, 1, 1 )
        
        fLayout.addWidget( QtGui.QLabel( "Image format" ), 3, 0, 1, 1, QtCore.Qt.AlignRight )
        self.imgFormatGUI = QtGui.QComboBox( box )
        self.imgFormatGUI.addItems( ( 'jpg', 'bmp', 'png' ) )
        def formatIdxChanged( idx ):
            if ( idx == 2 ):
                self.logMessage( 'There is a memory leak for png format!' )
        QtCore.QObject.connect( self.imgFormatGUI, QtCore.SIGNAL('currentIndexChanged(int)'), formatIdxChanged )
        fLayout.addWidget( self.imgFormatGUI, 3, 1, 1, 1 )        
        
        return box
        
    def body( self ):
        '''Build the task-specific GUI.  This should be overwritten by subclass'''
        self.bodyLayout.addWidget( self.createRasterBox() )

class FlowWorkWidget( WorkWidget ):
    def __init__( self, name, parent=None, delCB=None, rsrc=None ):
        WorkWidget.__init__( self, name, parent, delCB, rsrc )
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
        QtCore.QObject.connect( self.flowNameGUI, QtCore.SIGNAL('editingFinished()'), self.flowLineNameChangeCB )
        layout.addWidget( self.flowNameGUI, 3, 1, 1, 2 )
        
        return box
    
    def body( self ):
        '''Build the task-specific GUI.  This should be overwritten by subclass'''
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

    
    
    