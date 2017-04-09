# This is the OpenGL context for drawing flow calculation lines
from Context import *
from primitives import Vector2, Segment
from OpenGL.GL import *
from copy import deepcopy

class GLFlowSegment( Segment ):
    '''The OpenGL representation of a flow line.  Basically a segment
    with a direciton indicator.  The direction indicator shows which
    way flow is expected to cross the line.  The flow direction is to
    the RIGHT of the segment.  The forward direction is the direction
    from p1 to p2.'''
    
    def __init__( self, p1, p2 ):
        '''Constructor.

        @param      p1      An instance of Vector2. The start point of the segment.
        @param      p2      An instance of Vector2.  The end point of the segment.
        '''
        Segment.__init__( self, p1, p2 )

    def __str__( self ):
        return "GLFlowSegment (%s, %s)" % ( self.p1, self.p2 )

    def __repr__( self ):
        return str( self )

    def drawGL( self, color=(0.1, 1.0, 0.1) ):
        '''Draw the flow segment into a GL context.

        @param      A 3-tuple of floats.  The color of the line.
                    All values should lie in the range [0, 1], to be
                    interpreted as r, g, b color values.
        '''
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

class FlowLineContext( BaseContext ):
    '''Context for drawing, creating and editing lines'''
    MIN_LINE_LENGTH = 2 # the minimum drag required to draw a line
    # edit state - used for knowing what to do with the active line and cancellation
    NO_EDIT = 0
    EDIT = 1
    ADD = 2
    def __init__( self, cancelCB=None, editCB=None ):
        '''Constructor.

        @param      cancelCB        A callable.  An optional callback object
                                    for when flow line drawing is canceled.
        @param      editCB          A callable. An optional callback object
                                    for when a flow line values are edited.
        '''
        BaseContext.__init__( self )
        self.lines = []
        self.names = []

        self.activeID = -1  # the line currently affected by modifications
        self.editState = self.NO_EDIT
        self.cancelCB = cancelCB
        self.editCB = editCB
        
        self.activeLine = None
        self.canDraw = False
        self.dragging = False
        self.downPost = None

    def copy( self, context ):
        '''Copy the state of the given FlowLineContext into this'''
        assert( isinstance( context, FlowLineContext ) )
        self.clear()
        self.names = [ a for a in context.names ]
        self.lines = deepcopy( context.lines )
        
    def clear( self ):
        '''Clears out all of the lines'''
        self.lines = []
        self.names = []
        self.activeID = -1
        self.editState = self.NO_EDIT
        self.activeLine = None
        self.canDraw = False
        self.dragging = False
        self.downPost = None

    def lineCount( self ):
        return len( self.lines )
    
    def getName( self, id ):
        '''Returns the name associated with the line index, id.

        @param      id      An integer.  The index into the stored set of lines.
        @return     A string.  The stored name.
        '''
        return self.names[ id ]
    
    def getLine( self, id ):
        '''Returns the name associated with the line index, id.

        @param      id      An integer.  The index into the stored set of lines.
        @return     An instance of a FlowLine.
        '''
        return self.lines[ id ]
    
    def addLine( self ):
        '''Causes the context to go into new line mode.  Returning the new name.'''
        self.canDraw = True
        self.editState = self.ADD
        self.activeID = -1
        self.names.append( 'Line %d' % len( self.names ) )
        self.lines.append( GLFlowSegment( Vector2(0, 0), Vector2(0, 0) ) )
        self.activeLine = self.lines[-1]
        return self.names[-1]

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

    def setMultiLines( self, names, lines ):
        '''Sets the lines in the context with the given names and lines.
        It is asserted that len( names ) == len( lines ).

        @param      names       A list of strings.  One name per line.
        @param      lines       A list of Segment instaces.  One line per name.
        '''
        self.lines = map( lambda x: GLFlowSegment( x.p1, x.p2 ), lines )
        self.names = names
        self.activeID = -1
        self.editState = self.NO_EDIT

    def handleMouse ( self, evt, view ):
        """Detects click, drag, release and creates a line"""
        result = ContextResult()
        try:
            event = self.canonicalEvent( evt )
        except ValueError as e:
            return result
            
        if ( not self.canDraw ):
            return result
        if ( event.noModifiers() ):
            btn = event.button
            eX = event.x
            eY = event.y
            if ( event.type == MouseEvent.DOWN ): #QtCore.QEvent.MouseButtonPress ):
                if ( btn == MouseEvent.LEFT ):
                    self.downPos = Vector2( eX, eY )
                    x, y = view.screenToWorld( ( eX, eY ) )
                    p1 = Vector2( x, y )
                    self.activeLine = GLFlowSegment( p1, p1 )
                    result.set( True, True, False )
                    self.dragging = True
                    self.notifyEdit( self.activeLine )
                elif ( btn == MouseEvent.RIGHT and self.dragging ):
                    # cancel the edit
                    if ( self.editState == self.ADD ):
                        self.editState = self.NO_EDIT
                        self.lines.pop(-1)
                        self.names.pop(-1)
                        if ( not self.cancelCB is None ):
                            self.cancelCB()
                        self.notifyEdit( None )
                    canceled = self.activeLine != None
                    self.activeLine = None
                    self.dragging = False
                    result.set( canceled, canceled, False )
            elif ( event.type == MouseEvent.UP ):
                if ( btn == MouseEvent.LEFT and self.dragging ):
                    endPos = Vector2( eX, eY )
                    if ( (endPos - self.downPos).magnitude() >= self.MIN_LINE_LENGTH  ):
                        if ( self.editState == self.ADD ):
                            self.activeID = len( self.lines ) - 1
                            self.lines[self.activeID] = self.activeLine
                            self.editState = self.EDIT
                            self.notifyEdit( self.activeLine )
                        elif ( self.editState == self.EDIT ):
                            assert( self.activeID > -1 )
                            self.lines[ self.activeID ] = self.activeLine
                            self.notifyEdit( self.activeLine )
                        self.activeLine = None
                    self.activeLine = None  
                    self.dragging = False
                    result.set( True, True, False )
            elif ( event.type == MouseEvent.MOVE ):
                if ( self.dragging ):
                    x, y = view.screenToWorld( ( eX, eY ) )
                    p2 = Vector2( x, y )
                    self.activeLine.p2 = p2
                    result.set( True, True, False )
                    self.notifyEdit( self.activeLine )
        return result

    def notifyEdit( self, line ):
        '''Notifies call back of a line that has changed'''
        if ( not self.editCB is None ):
            self.editCB( line )
    
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
