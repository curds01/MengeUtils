## Contexts control the effect that interaction has in an OpenGL window

class ContextResult:
    """Report of the work the context did"""
    def __init__( self, handled=False, redraw=False, finished=False ):
        self.handled = handled      # reports if the event no longer needs handling, it's been handled
        self.redraw = redraw        # report if the handling requires redraw
        self.finished = finished    # reports if the context should be removed

    def __str__( self ):
        return "Result: %s, %s, %s" % ( self.handled, self.redraw, self.finished )
    
    def setHandled( self, state ):
        self.handled = state

    def isHandled( self ):
        return self.handled

    def isFinished( self ):
        return self.finished

    def setFinished( self, state ):
        self.finished = state
        
    def setNeedsRedraw( self, state ):
        self.redraw = state

    def needsRedraw( self ):
        return self.redraw

    def set( self, handled, redraw, finished=False ):
        self.handled = handled
        self.redraw = redraw
        self.finished = finished

    def combine( self, result ):
        '''Combines this result with the given result in a boolean fashion'''
        self.handled = self.handled or result.handled
        self.redraw = self.redraw or result.redraw
        self.finished = self.finished or result.finished

class Event:
    '''Base event class'''
    # Enumerations for modifiers
    NO_MODS = 0
    SHIFT = 1
    CTRL = 2
    ALT = 4
    
    def __init__( self, evtType, **attributes ):
        '''Constructor.'''
        self.type = evtType
        self.attr = attributes
        assert( self.attr.has_key( 'modifiers' ) )

    @property
    def modifiers( self ):
        return self.attr[ 'modifiers' ]

    def noModifiers( self ):
        '''Reports if there are no modifiers pressed for this event'''
        return self.attr[ 'modifiers' ] == self.NO_MODS

class MouseEvent( Event ):
    '''A generic mouse event'''
    # Enumeration for the type of event
    MOVE = 1
    DOWN = 2
    UP = 3

    # Enumeration for mouse buttons
    NO_BTN = 0
    LEFT = 1
    MIDDLE = 2
    RIGHT = 3

    def __init__( self, evtType, **attributes ):
        '''Constructor.

        @param      evtType     The type of mouse event.
        @param      attributes  A named keyword argument list.  A mouse event requires the following
                                keywords:
                                    modifiers:  A modifier enumeration value 
                                    button:     A button enumeration value
                                    x:          An int - the mouse x-position
                                    y:          An int - the mouse y-position
            
        '''
        Event.__init__( self, evtType, **attributes )
        # validate
        assert( evtType == MouseEvent.MOVE or evtType == MouseEvent.DOWN or evtType == MouseEvent.UP )
        assert( self.attr.has_key( 'button' ) )
        assert( self.attr.has_key( 'x' ) and self.attr.has_key( 'y' ) )

    @property
    def button( self ):
        return self.attr[ 'button' ]

    @property
    def x( self ):
        return self.attr[ 'x' ]

    @property
    def y( self ):
        return self.attr[ 'y' ]    

        
class BaseContext:
    """Basic context"""
    def __init__( self ):
        pass

    def __str__( self ):
        return self.__class__.__name__

    def drawGL( self, view ):
        """This gives the context the chance to draw in the OpenGL view"""
        pass

    def selectGL( self, drawables, camera, selectPoint ):
        """How the context handles selection"""
        pass

    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        return ContextResult()

    def handleKeyboard( self, event, view ):
        """The context handles the keyboard event as it sees fit and reports it's status with a ContextResult"""
        return ContextResult()

    def newGLContext( self ):
        '''Renews the open gl objects for ths context'''
        pass

    def activate( self ):
        '''Called when the context is first activated'''
        pass

    def deactivate( self ):
        '''Called when the context is deactivated.'''
        pass

    def exportDisplay( self ):
        '''Reports if the screen should be exported to an image.  Returns a name to export the display to.
        If the display shouldn't be exported, it returns None.'''
        return None
    