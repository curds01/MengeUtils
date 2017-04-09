# This is the OpenGL context for creating vector field domains

from Context import *
from vField import GLVectorField
from OpenGL.GL import *

class GridContext( BaseContext ):
    '''A context for working with a vector field'''
    def __init__( self, minPt, size, cellSize, editCB=None ):
        '''Constructor.

        @param      minPt           A 2-tuple-like object of floats: the minimum x- and y-
                                    position of the grid.
        @param      size            A 2-tuple-like object of floats: the dimsions of the
                                    grid (width, height).
        @param      cellSize        A float; the length of the side of the square grid
                                    cells.
        @param      editCB          A callable. An optional callback object for when grid
                                    is edited. It's argument is: a 2-tuple of 2-tuples:
                                    (minPoint, size).
        '''
        BaseContext.__init__( self )
        self.editCB = editCB
        self.vField = GLVectorField( minPt, size, cellSize )
        self.vField.gridChanged()

    def activate( self ):
        '''Enables the agent set for editing'''
        self.vField.editable = True

    def deactivate( self ):
        '''Turns off the editable state for the agents'''
        self.vField.editable = False
        self.dragging = False
        # TODO: all other clean-up

    def drawGL( self ):
        pass

class FieldDomainContext( GridContext ):
    '''A context for editing the boundaries and resolution of a field'''
    HELP_TEXT = 'Edit field domain properties' + \
                '\n\tIncrease cell size - right arrow' + \
                '\n\tDecrease cell size - left arrow' + \
                '\n\t\t* holding Ctrl/Alt/Shift changes the cell size change rate'

    NO_EDIT = 0
    EDIT_HORZ = 1
    EDIT_VERT = 2
    def __init__( self, minPt, size, cellSize, editCB=None ):
        GridContext.__init__( self, minPt, size, cellSize, editCB )
        self.corners = [ [x, y] for (x, y) in self.vField.getCorners() ]
        self.size = self.vField.size # the size is (height, width)
        self.activeEdge = None
        self.modifyFunc = None
        self.downX = 0
        self.downY = 0
        self.dragging = self.NO_EDIT
        self.drawCells = True

    def activate( self  ):
        '''Begin boundary edit'''
        pass

    def deactivate( self ):
        '''End boundary edit'''
        # todo: if in the middle of an edit, cancel it
        self.activeEdge = None

    def setCellDraw( self, state ):
        self.drawCells = state
        
    def setMinX( self, value ):
        '''Sets the minimum x-value'''
        self.vField.setMinX( value )
        self.vField.gridChanged()
        delta = value - self.corners[0][0]
        self.corners[0][0] = value
        self.corners[1][0] += delta
        self.corners[2][0] += delta
        self.corners[3][0] += delta

    def setMinY( self, value ):
        '''Sets the mininum y-value'''
        self.vField.setMinY( value )
        self.vField.gridChanged()
        delta = value - self.corners[0][1]
        self.corners[0][1] = value
        self.corners[1][1] += delta
        self.corners[2][1] += delta
        self.corners[3][1] += delta

    def setWidth( self, value ):
        '''Sets the width value'''
        self.vField.setWidth( value )
        self.vField.gridChanged()
        delta = value - self.corners[2][0] + self.corners[0][0]
        self.corners[1][0] += delta
        self.corners[2][0] += delta

    def setHeight( self, value ):
        '''Sets the height value'''
        self.vField.setHeight( value )
        self.vField.gridChanged()
        delta = value - self.corners[2][1] + self.corners[0][1]
        self.corners[2][1] += delta
        self.corners[3][1] += delta

    def setCellSize( self, value ):
        '''Sets the height value'''
        self.vField.setCellSize( value, self.visSize() )
        self.vField.gridChanged()
    
##    def handleKeyboard( self, event, view ):
##        result = GridContext.handleKeyboard( self, event, view )
##        if ( result.isHandled() ):
##            return result        
##
##        mods = pygame.key.get_mods()
##        hasCtrl = mods & pygame.KMOD_CTRL
##        hasAlt = mods & pygame.KMOD_ALT
##        hasShift = mods & pygame.KMOD_SHIFT
##        noMods = not( hasShift or hasCtrl or hasAlt )
##
##        DELTA = 1.0
##        if ( hasCtrl ):
##            DELTA *= 0.1
##        if ( hasShift ):
##            DELTA *= 0.1
##        if ( hasAlt ):
##            DELTA *= 0.1
##
##        if ( event.key == pygame.K_RSHIFT or
##                 event.key == pygame.K_LSHIFT or
##                 event.key == pygame.K_RALT or
##                 event.key == pygame.K_LALT or
##                 event.key == pygame.K_RCTRL or
##                 event.key == pygame.K_LCTRL ):
##                result.set( False, True )
##                return result
##            
##        if ( event.type == pygame.KEYDOWN ):
##            if ( event.key == pygame.K_RIGHT ):
##                self.vField.setCellSize( self.vField.cellSize + DELTA, self.size )
##                result.set( True, True )
##            elif ( event.key == pygame.K_LEFT ):
##                cs = self.vField.cellSize
##                result.set( True, False )
##                if ( cs > DELTA ):
##                    self.vField.setCellSize( cs - DELTA, self.size )
##                    result.set( True, True )
##        return result

    def handleMouse( self, evt, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = GridContext.handleMouse( self, evt, view )
        if ( result.isHandled() ):
            return result
        try:
            event = self.canonicalEvent( evt )
        except ValueError as e:
            return result

        mods = event.modifiers
        hasCtrl = mods & Event.CTRL
        hasAlt = mods & Event.ALT
        hasShift = mods & Event.SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        btn = event.button
        eX = event.x
        eY = event.y

        if ( event.type == MouseEvent.MOVE ):
            p = view.screenToWorld( (eX, eY) )
            if ( self.dragging ):
                if ( self.dragging == self.EDIT_HORZ ):
                    dX = p[0] - self.downX
                    newVal = self.startVal + dX
                    self.corners[ self.activeEdge ][ 0 ] = newVal
                    self.corners[ self.activeEdge + 1][ 0 ] = newVal
                else:
                    dY = p[1] - self.downY
                    newVal = self.startVal + dY
                    self.corners[ self.activeEdge ][ 1 ] = newVal
                    self.corners[ self.activeEdge + 1][ 1 ] = newVal
                self.modifyFunc( newVal )
                result.set( True, True )
                self.vField.setDimensions( self.visSize() )
                self.reportEdit()
            else:
                # hover behavior
                newIdx, newFunc = self.selectEdge( p, view )
                if ( newIdx != self.activeEdge ):
                    result.redraw = True
                    self.activeEdge = newIdx
                    self.modifyFunc = newFunc
        elif ( event.type == MouseEvent.DOWN ):
            if ( event.noModifiers() and btn == MouseEvent.LEFT and self.activeEdge is not None ):
                self.downX, self.downY = view.screenToWorld( (eX, eY) )
                if ( self.activeEdge % 2 ): # vertical line
                    self.startVal = self.corners[ self.activeEdge ][ 0 ]
                    self.dragging = self.EDIT_HORZ
                else:
                    self.startVal = self.corners[ self.activeEdge ][ 1 ]
                    self.dragging = self.EDIT_VERT
            elif ( btn == MouseEvent.RIGHT and self.dragging ):
                if ( self.dragging == self.EDIT_HORZ ):
                    self.corners[ self.activeEdge ][ 0 ] = self.startVal
                    self.corners[ self.activeEdge + 1][ 0 ] = self.startVal
                else:
                    self.corners[ self.activeEdge ][ 1 ] = self.startVal
                    self.corners[ self.activeEdge + 1][ 1 ] = self.startVal
                self.dragging = self.NO_EDIT
                result.set( True, True )
                self.vField.setDimensions( self.visSize() )
                self.reportEdit()
        elif ( event.type == MouseEvent.UP ):
            if ( self.dragging ):
                self.size = self.visSize()
                self.vField.setDimensions( self.size )
                self.dragging = self.NO_EDIT
                result.set( True, True )
        return result

    def reportEdit( self ):
        if ( self.editCB ):
            self.editCB( (self.corners[0], self.visSize()) )

    def visSize( self ):
        '''Based on the current corner values, computes the field size'''
        return ( self.corners[-1][1] - self.corners[0][1], self.corners[1][0] - self.corners[0][0] )

    def selectEdge( self, worldPos, view ):
        '''Given a world position of the mouse, determines if an edge is "under" the mouse.

        If an edge is under the mouse, a 2-tuple is returned: ( edge index, update method).

        The update method should be invoked when the new value is computed.

        Returns None if no edge is sufficiently close.'''
        DIST = view.pixelSize * 10  # 10 pixels away is considered selection

        i = -1 # left-hand vertical edge        
        if ( worldPos[0] >= self.corners[ i ][0] - DIST and worldPos[0] <= self.corners[ i ][0] + DIST and
             worldPos[1] >= self.corners[ i + 1 ][1] - DIST and worldPos[1] <= self.corners[ i ][1] + DIST ):
            return (i, self.vField.setMinX)
        i = 0 # bottom horizontal edge        
        if ( worldPos[1] >= self.corners[ i ][1] - DIST and worldPos[1] <= self.corners[ i ][1] + DIST and
             worldPos[0] >= self.corners[ i ][0] - DIST and worldPos[0] <= self.corners[ i+1 ][0] + DIST ):
            return (i, self.vField.setMinY)
        i = 1 # right-hand vertical edge        
        if ( worldPos[0] >= self.corners[ i ][0] - DIST and worldPos[0] <= self.corners[ i ][0] + DIST and
             worldPos[1] >= self.corners[ i ][1] - DIST and worldPos[1] <= self.corners[ i + 1 ][1] + DIST ):
            return (i, self.vField.setWidth)
        i = 2 # top horizontal edge        
        if ( worldPos[1] >= self.corners[ i ][1] - DIST and worldPos[1] <= self.corners[ i ][1] + DIST and
             worldPos[0] >= self.corners[ i + 1 ][0] - DIST and worldPos[0] <= self.corners[ i ][0] + DIST ):
            return (i, self.vField.setHeight)
        return None, None

    def cellSizeChange( self ):
        '''Computes the cell size change based on keyboard modifiers'''
        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        
        DELTA = 1.0
        if ( hasCtrl ):
            DELTA *= 0.1
        if ( hasShift ):
            DELTA *= 0.1
        if ( hasAlt ):
            DELTA *= 0.1
        return DELTA

    def drawGL( self ):
        GridContext.drawGL( self )
        glPushAttrib( GL_COLOR_BUFFER_BIT | GL_LINE_BIT )
        if ( self.drawCells ):
            glColor3f( 0.25, 0.25, 0.25 )
            self.drawGrid()
        glColor3f( 0.25, 1.0, 0.25 )
        glBegin( GL_LINE_STRIP )
        for i in range( -2, 3 ):
            glVertex3f( self.corners[ i ][0], self.corners[ i ][1] , 0 )
        glEnd()
        if ( self.activeEdge is not None ):
            i = self.activeEdge
            glColor3f( 0.5, 1.0, 0.5 )
            glLineWidth( 2.0 )
            glBegin( GL_LINES )
            glVertex3f( self.corners[ i ][0], self.corners[ i ][1] , 0 )
            glVertex3f( self.corners[ i+1 ][0], self.corners[ i+1 ][1] , 0 )
            glEnd()
        glPopAttrib()

    def drawGrid( self ):
        minX = self.vField.minPoint[0]
        maxX = minX + self.vField.size[1]
        minY = self.vField.minPoint[1]
        maxY = minY + self.vField.size[0]

        glBegin( GL_LINES )
        # horizontal lines
        for i in xrange( self.vField.resolution[0] + 1 ):
            y = minY + i * self.vField.cellSize
            glVertex3f( minX, y, 0.0 )
            glVertex3f( maxX, y, 0.0 )
        # vertical lines
        for i in xrange( self.vField.resolution[1] + 1 ):
            x = minX + i * self.vField.cellSize
            glVertex3f( x, minY, 0.0 )
            glVertex3f( x, maxY, 0.0 )
        glEnd()