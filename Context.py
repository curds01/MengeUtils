## Contexts control the effect that interaction has in an OpenGL window

from PyQt4 import QtCore, QtGui, QtOpenGL
from primitives import Vector2
from OpenGL.GL import *

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

    def set( self, handled, redraw, finished ):
        self.handled = handled
        self.redraw = redraw
        
class BaseContext:
    """Basic context"""
    def __init__( self ):
        pass

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

class GLLine:
    """Simple line object"""
    def __init__( self, p1, p2 ):
        self.p1 = p1
        self.p2 = p2

    def __str__( self ):
        return "Line (%s, %s)" % ( self.p1, self.p2 )

    def __repr__( self ):
        return str( self )

    def drawGL( self, color=(0.1, 1.0, 0.1) ):
        glPushAttrib( GL_COLOR_BUFFER_BIT )
        glBegin( GL_LINES )
        glColor3fv( color )
        glVertex2f( self.p1.x, self.p1.y )
        glVertex2f( self.p2.x, self.p2.y )
        glEnd()
        glPopAttrib()

    def magnitude( self ):
        """Returns length of the line"""
        return ( self.p2 - self.p1 ).magnitude()

    def pointDistance( self, p ):
        """Computes the distance between this line segment and a point p"""
        disp = self.p2 - self.p1
        segLen = disp.magnitude()
        norm = disp / segLen
        dispP = p - self.p1
        dp = norm.dot( dispP )
        if ( dp < 0 ):      
            return (p - self.p1).magnitude()
        elif ( dp > segLen ):
            return ( p - self.p2).magnitude()
        else:
            A = -norm.y
            B = norm.x
            C = -( A * self.p1.x + B * self.p1.y )
            return abs( A * p.x + B * p.y + C )
    
class LineContext( BaseContext ):
    """Context which allows for drawing and displaying one or more lines"""
    MIN_LINE_LENGTH = 3 # the minimum line must be at least 3 pixels in length
    def __init__( self, maxLines=100000 ):
        BaseContext.__init__( self )
        self.maxLines = maxLines        # limit to how many lines can be drawn
        self.lines = []
        self.activeLine = None
        self.oldLine = None
        self.dragging = False
        self.downPost = None

    def getLineCount( self ):
        """Returns the number of defined lines"""
        return len( self.lines )

    def getMaxLineCount( self ):
        """Returns the maximum number of lines"""
        return self.maxLines
    
    def toConfigString( self ):
        """Creates a parseable config string so that the context can be reconsituted"""
        s = '%d %d' % ( len( self.lines ), self.maxLines )
        for line in self.lines:
            s += ' %.5f %.5f %.5f %.5f' % ( line.p1.x, line.p1.y, line.p2.x, line.p2.y )
        return s

    def setFromString( self, s ):
        """Reads a string written by "toConfigString" and sets the context"""
        self.lines = []
        tokens = s.split()
        lineCount = int( tokens[0] )
        self.maxLines = int( tokens[1] )
        v = 2
        for i in range( lineCount ):
            x1 = float( tokens[ v ] ); v += 1
            y1 = float( tokens[ v ] ); v += 1
            x2 = float( tokens[ v ] ); v += 1
            y2 = float( tokens[ v ] ); v += 1
            self.lines.append( GLLine( Vector2( x1, y1 ), Vector2( x2, y2 ) ) )

    def setMaximumLineCount( self, count ):
        """Sets the maximum number of lines - reports if lines are lost"""
        # If there are two many lines, it removes the oldest lines
        self.maxLines = count
        linesLost = len( self.lines ) > count
        while ( len( self.lines ) > count ):
            self.lines.pop(0)
        return linesLost

    def handleMouse ( self, event, view ):
        """Detects click, drag, release and creates a line"""
        result = ContextResult()
        mods = event.modifiers()
        noMods = mods == QtCore.Qt.NoModifier
        if ( noMods ):
            try:
                btn = event.button()
            except AttributeError:
                return result
            if ( event.type() == QtCore.QEvent.MouseButtonPress ):
                if ( btn == QtCore.Qt.LeftButton ):
                    self.downPos = Vector2( event.x(), event.y() )
                    x, y = view.screenToWorld( (event.x(), event.y() ) )
                    p1 = Vector2( x, y )
                    self.activeLine = GLLine( p1, p1 )
                    if ( len( self.lines ) >= self.maxLines ):
                        self.oldLine = self.lines.pop(0)
                    result.set( True, True, False )
                    self.dragging = True
                elif ( btn == QtCore.Qt.RightButton and self.dragging ):
                    if ( self.oldLine ):
                        self.lines.insert( 0, self.oldLine )
                    self.oldLine = None
                    self.activeLine = None
                    self.dragging = False
                    self.activeLine = None
                    result.set( True, True, False )
            elif ( event.type() == QtCore.QEvent.MouseButtonRelease ):
                if ( btn == QtCore.Qt.LeftButton and self.dragging ):
                    endPos = Vector2( event.x(), event.y() )
                    if ( (endPos - self.downPos).magnitude() >= LineContext.MIN_LINE_LENGTH  ):
                        self.lines.append( self.activeLine )
                        self.activeLine = None
                    elif ( self.oldLine ):
                        self.lines.insert( 0, self.oldLine )
                    self.oldLine = None
                    self.activeLine = None  
                    self.dragging = False
                    result.set( True, True, False )
            elif ( event.type() == QtCore.QEvent.MouseMove ):
                if ( self.dragging ):
                    x, y = view.screenToWorld( (event.x(), event.y() ) )
                    p2 = Vector2( x, y )
                    self.activeLine.p2 = p2
                    result.set( True, True, False )
        return result

    def drawGL( self ):
        if ( self.activeLine ):
            self.activeLine.drawGL( ( 1.0, 1.0, 0.1 ) )
        for line in self.lines:
            line.drawGL()

if __name__ == '__main__':
    print
    line = GLLine( Vector2( -1.0, -1.0 ), Vector2( 1.0, 1.0 ) )
    p1 = Vector2( 0.0, 0.0 )
    print "Distance should be 0.0:", line.pointDistance( p1 )
    p2 = Vector2( 1.0, 0.0 )
    print "Distance should be sqrt(2)/2:", line.pointDistance( p2 )
    p3 = Vector2( -1.0, 0.0 )
    print "Distance should be sqrt(2)/2:", line.pointDistance( p3 )
    p4 = Vector2( 2.0, 2.0 )
    print "Distance should be sqrt(2):", line.pointDistance( p4 )
    p4 = Vector2( -2.0, -2.0 )
    print "Distance should be sqrt(2):", line.pointDistance( p4 )
    p5 = Vector2( -1.0, -2.0 )
    print "Distance should be 1:", line.pointDistance( p5 )
        
    