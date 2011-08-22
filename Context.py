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
        
class BaseContext:
    """Basic context"""
    def __init__( self ):
        pass

    def __str__( self ):
        return self.__class__.__name__

    def drawGL( self ):
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

    