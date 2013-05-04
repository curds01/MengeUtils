from PyQt4 import QtCore, QtGui, QtOpenGL
from primitives import Vector2, Segment
from OpenGL.GL import *
from Context import *
import flowUtils

class GLLine( Segment):
    """Simple line object"""
    def __init__( self, p1, p2 ):
        Segment.__init__( self, p1, p2 )

    def __str__( self ):
        return "GLLine (%s, %s)" % ( self.p1, self.p2 )

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

class GLFlowLine( Segment ):
    '''Flow line object'''
    def __init__( self, p1, p2 ):
        Segment.__init__( self, p1, p2 )

    def __str__( self ):
        return "GLFlowLine (%s, %s)" % ( self.p1, self.p2 )

    def __repr__( self ):
        return str( self )

    def drawGL( self, color=(0.1, 1.0, 0.1) ):
        glPushAttrib( GL_COLOR_BUFFER_BIT )
        glBegin( GL_LINES )
        glColor3fv( color )
        glVertex2f( self.p1.x, self.p1.y )
        glVertex2f( self.p2.x, self.p2.y )
        mp = self.midPoint()
        l = self.magnitude()
        n = self.normal() * (0.25 * l )
        
        end = mp + n
        glVertex2f( mp.x, mp.y )
        glVertex2f( end.x, end.y )
        glEnd()
        glPopAttrib()

class LineContext( BaseContext ):
    '''Context for drawing, creating and editing lines'''
    MIN_LINE_LENGTH = 2 # the minimum drag required to draw a line
    # edit state - used for knowing what to do with the active line and cancellation
    NO_EDIT = 0
    EDIT = 1
    ADD = 2
    def __init__( self, cancelCB, lineClass=None ):
        BaseContext.__init__( self )
        self.lines = []
        self.names = []

        self.activeID = -1  # the line currently affected by modifications
        self.editState = self.NO_EDIT
        self.cancelCB = cancelCB
        
        self.activeLine = None
        self.canDraw = False
        self.dragging = False
        self.downPost = None
        if ( type( lineClass ) == type( GLFlowLine ) ):
            self.Line = lineClass
        else:
            self.Line = GLFlowLine

    def getName( self, id ):
        '''Returns the name associated with the line index, id.

        @param      id      An integer.  The index into the stored set of lines.
        @return     A string.  The stored name.
        '''
        return self.names[ id ]
    
    def addLine( self ):
        '''Causes the context to go into new line mode'''
        self.canDraw = True
        self.editState = self.ADD
        self.activeID = -1
        self.names.append( 'Line %d' % len( self.names ) )

    def editLine( self, idx ):
        '''Edits the indicated line'''
        if ( self.editState == self.ADD): return
        if ( idx < 0 ):
            self.editState = self.NO_EDIT
            self.canDraw = False
            self.activeID = -1
        else:
            self.editState = self.EDIT
            self.canDraw = True
            self.activeID = idx

    def setLineName( self, idx, name ):
        '''Sets the name for the line with the given index'''
        self.names[ idx ] = name

    def deleteLine( self, idx ):
        '''Removes a line from the set'''
        assert( idx >= 0 and idx < len( self.lines ) )
        self.lines.pop( idx )
        self.names.pop( idx )
        self.activeID = -1

    def flipLine( self, idx ):
        '''Flips the direction of the line in the set'''
        assert( idx >= 0 and idx < len( self.lines ) )
        self.lines[ idx ].flip()

    def setActive( self, idx ):
        '''Sets the active line'''
        self.activeID = idx

    def stopEdit( self ):
        '''Stops the ability to edit'''
        self.editState = self.NO_EDIT
        self.canDraw = False
        
    def getLineCount( self ):
        """Returns the number of defined lines"""
        return len( self.lines )

    def toConfigString( self ):
        """Creates a parseable config string so that the context can be reconsituted"""
        s = ''
        # TODO: This is fragile, it assumes that a comma never appears in the names
        #   I should add a validator to the line editor to guarantee no commas are allowed.
        names = self.names
        while ( len( names ) > len( self.lines ) ):
            assert( self.editState == self.ADD )
            names = names[:-1]
        s = ','.join( names ) + "~"
        for i, line in enumerate( self.lines ):
            s += ' %.5f %.5f %.5f %.5f' % ( line.p1.x, line.p1.y, line.p2.x, line.p2.y )
        return s

    def setFromString( self, s ):
        '''Parses the string created by toConfigString into a set of lines'''
        self.lines = []
        self.activeID = -1
        self.editState = self.NO_EDIT
        self.names, self.lines = flowUtils.flowLinesFromString( s, self.Line )

    def handleMouse ( self, event, view ):
        """Detects click, drag, release and creates a line"""
        result = ContextResult()
        if ( not self.canDraw ):
            return result
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
                    self.activeLine = self.Line( p1, p1 )
                    result.set( True, True, False )
                    self.dragging = True
                elif ( btn == QtCore.Qt.RightButton and self.dragging ):
                    # cancel the edit
                    if ( self.editState == self.ADD ):
                        self.editState = self.NO_EDIT
                        self.cancelCB()
                    canceled = self.activeLine != None
                    self.activeLine = None
                    self.dragging = False
                    result.set( canceled, canceled, False )
            elif ( event.type() == QtCore.QEvent.MouseButtonRelease ):
                if ( btn == QtCore.Qt.LeftButton and self.dragging ):
                    endPos = Vector2( event.x(), event.y() )
                    if ( (endPos - self.downPos).magnitude() >= LineContext.MIN_LINE_LENGTH  ):
                        if ( self.editState == self.ADD ):
                            self.lines.append( self.activeLine )
                            self.editState = self.EDIT
                            self.activeID = len( self.lines ) - 1
                        elif ( self.editState == self.EDIT ):
                            assert( self.activeID > -1 )
                            self.lines[ self.activeID ] = self.activeLine
                        self.activeLine = None
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
        '''Basic lines are drawn in default (green), the active line is drawn in yellow,
        and when it is being edited, the original disappears and the new line is drawn in
        cyan.'''
        if ( self.activeLine ):
            self.activeLine.drawGL( ( 0.1, 1.0, 1.0 ) )
        elif ( self.activeID > -1 and self.editState != self.ADD ):
            self.lines[ self.activeID ].drawGL( ( 1.0, 1.0, 0.1 ) )
            
        for i, line in enumerate( self.lines ):
            if ( i == self.activeID ): continue
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
        
