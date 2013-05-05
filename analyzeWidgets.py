# I'm trying to construct an app with a big window on the right and a scrollable window of widgets
#    on the left.

from PyQt4 import QtGui, QtCore

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
