# a bit of hacked code to support contexts for the roadmap builder

from Context import BaseContext, ContextResult
import pygame
from fieldTools import *
import numpy as np
from OpenGL.GL import *

# This is here instead of Context.py because this is pygame dependent and that is QT dependent.
#   I need to unify those.

LEFT = 1
MIDDLE = 2
RIGHT = 3
WHEEL_UP = 4
WHEEL_DOWN = 5

class ContextSwitcher( BaseContext ):
    '''A context for switching contexts'''
    def __init__( self ):
        BaseContext.__init__( self )
        self.contexts = {}
        self.activeContext = None

    def handleKeyboard( self, event, view ):
        """The context handles the keyboard event as it sees fit and reports it's status with a ContextResult"""
        result = ContextResult()
        mods = pygame.key.get_mods()
        hasShift = mods & pygame.KMOD_SHIFT
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        noMods = not( hasShift or hasCtrl or hasAlt )
        if ( event.type == pygame.KEYDOWN ):
            if ( event.key == pygame.K_ESCAPE and noMods ):
                changed = self.activeContext != None
                self.switchContexts( None )
                result.set( True, changed )
            if ( not result.isHandled() ):
                if ( self.activeContext ):
                    result = self.activeContext.handleKeyboard( event, view )
                else:
                    if ( self.contexts.has_key( event.key ) ):
                        ctx = self.contexts[ event.key ]
                        changed = ctx != self.activeContext
                        self.switchContexts( ctx )
                        result.set( True, changed )
        elif ( event.type == pygame.KEYUP ):
            if ( self.activeContext ):
                result = self.activeContext.handleKeyboard( event, view )
        return result

    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        if ( self.activeContext ):
            return self.activeContext.handleMouse( event, view )
        else:
            return ContextResult()

    def addContext( self, context, key ):
        '''Adds a context to the switcher, keyed by the given key.

        @param context: an instance of a context.
        @param key: a pygame key.  The key which will trigger the given context.

        If the key is already mapped to another context, the key is remapped.        
        '''
        if ( self.contexts.has_key( key ) ):
            print "Key {0} is already mapped to the context {1}.  It will be remapped".format( key, self.contexts[ key ].__class__.__name__ )
        self.contexts[ key ] = context
        print "Adding context {0} to key {1}".format( context, key )

    def switchContexts( self, context ):
        '''Switch the active context to this context.

        @param context: an instance of a context'''
        if ( context != self.activeContext ):
            if ( self.activeContext ):
                self.activeContext.deactivate()
            self.activeContext = context
            if ( self.activeContext ):
                self.activeContext.activate()

    def newGLContext( self ):
        '''Renews the open gl objects for ths context'''
        for ctx in self.contexts.values():
            ctx.newGLContext()

    def drawGL( self, view ):
        '''Draws the context into the view'''
        if ( self.activeContext ):
            self.activeContext.drawGL( view )

    def selectGL( self ):
        """How the context handles selection"""
        if ( self.activeContext ):
            self.activeContext.selectGL()

class MouseEnabled:
    '''A set of functionality for context which use the mouse'''
    def __init__( self ):
        self.downX = 0
        self.downY = 0
        self.dragging = False
        
class AgentContext( BaseContext, MouseEnabled ):
    '''A context for adding agents-goal pairs and editing existing pairs'''
    def __init__( self, agentSet ):
        BaseContext.__init__( self )
        MouseEnabled.__init__( self )
        self.agents = agentSet
        self.downPos = None     # the position of the active agent when the mouse was pressed

    def activate( self ):
        '''Enables the agent set for editing'''
        self.agents.editable = True

    def deactivate( self ):
        '''Turns off the editable state for the agents'''
        self.agents.editable = False
        self.dragging = False
        if ( self.agents.activeAgent ):
            self.agents.activeAgent.deactivate()
        
    def drawGL( self, view ):
        '''Draws the agent context into the view'''
        title = "Edit agents: %d" % self.agents.count()
        view.printText( title,  (10,10) )

    def handleKeyboard( self, event, view ):
        """The context handles the keyboard event as it sees fit and reports it's status with a ContextResult"""
        result = ContextResult()
        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        if ( event.type == pygame.KEYDOWN ):
            if ( event.key == pygame.K_s and noMods ):
                f = open('positions.txt', 'w' )
                f.write( '%s' % self.agents.sjguy() )
                f.close()
                result.set( True, False )
            elif ( event.key == pygame.K_DELETE and noMods ):
                result.set( True, self.agents.deleteActiveAgent() )
        return result

    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = ContextResult()
        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        if (event.type == pygame.MOUSEMOTION ):
            if ( self.dragging ):
                if ( self.agents.activeAgent ):
                    dX, dY = view.screenToWorld( ( self.downX, self.downY ) )
                    pX, pY = view.screenToWorld( event.pos )
                    newX = self.downPos[0] + ( pX - dX )
                    newY = self.downPos[1] + ( pY - dY )
                    self.agents.activeAgent.setActivePos( (newX, newY ) )
                    result.set( True, True )
            else:
                pX, pY = event.pos
                selected = view.select( pX, pY, self.agents, hasShift )
                if ( selected == -1 ):
                    if ( self.agents.activeAgent ):
                        self.agents.activeAgent.deactivate()
                        result.set( True, True )
                        self.agents.activeAgent = None                    
                else:
                    selAgt = self.agents.selectAgent( selected )
                    if ( selAgt != self.agents.activeAgent ):
                        if ( self.agents.activeAgent ):
                            self.agents.activeAgent.deactivate()
                        result.set( True, True )
                        self.agents.activeAgent = selAgt                        
        elif ( event.type == pygame.MOUSEBUTTONUP ):
            if ( event.button == LEFT ):
                self.dragging = False
        elif ( event.type == pygame.MOUSEBUTTONDOWN ):
            if ( event.button == LEFT and noMods ):
                self.downX, self.downY = event.pos
                if ( self.agents.activeAgent ):
                    self.downPos = self.agents.activeAgent.getActivePos()
                else:
                    p = view.screenToWorld( event.pos )
                    self.downPos = p
                    self.agents.addAgent( p, p )
                    self.agents.selectLastGoal()
                    result.setNeedsRedraw( True )
                self.dragging = True
        
        return result

class VFieldContext( BaseContext, MouseEnabled ):
    '''A context for working with a vector field'''
    def __init__( self, vfield ):
        BaseContext.__init__( self )
        MouseEnabled.__init__( self )
        self.field = vfield

    def activate( self ):
        '''Enables the agent set for editing'''
        self.field.editable = True

    def deactivate( self ):
        '''Turns off the editable state for the agents'''
        self.field.editable = False
        self.dragging = False
        # TODO: all other clean-up

    def getTitle( self ):
        '''Returns the title generated by this context'''
        return "{0} X {1} vector field (cell size = {2})".format( self.field.resolution[0], self.field.resolution[1], self.field.cellSize )
        
    def drawGL( self, view ):
        view.printText( self.getTitle(), (10,10) )

class FieldEditContext( VFieldContext ):
    '''The context which allows various kinds of edits on a vector field'''
    def __init__( self, vfield ):
        VFieldContext.__init__( self, vfield )
        self.activeContext = FieldStrokeContext( self.field )

    def activate( self ):
        VFieldContext.activate( self )
        if ( self.activeContext ):
            self.activeContext.activate()

    def deactivate( self ):
        VFieldContext.deactivate( self )
        if ( self.activeContext ):
            self.activeContext.deactivate ()

    def handleKeyboard( self, event, view ):
        result = ContextResult()
        if ( self.activeContext ):
            result = self.activeContext.handleKeyboard( event, view)
            if ( result.isHandled() ):
                return result
        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        if ( event.type == pygame.KEYDOWN ):
            if ( event.key == pygame.K_RSHIFT or event.key == pygame.K_LSHIFT ):
                if ( self.activeContext ):
                    self.activeContext.deactivate()
                self.activeContext = FieldBoundaryContext( self.field )
                self.activeContext.activate()
                result.set( True, True )
        elif ( event.type == pygame.KEYUP ):
             if ( event.key == pygame.K_RSHIFT or event.key == pygame.K_LSHIFT ):
                if ( self.activeContext and self.activeContext.__class__ == FieldBoundaryContext ):
                    self.activeContext.deactivate()
                    self.activeContext = None
                    result.set( True, True )
        return result

    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = ContextResult()
        if ( self.activeContext ):
            result = self.activeContext.handleMouse( event, view )
            if ( result.isHandled() ):
                return result
        return result
    
    def drawGL( self, view ):
        if ( self.activeContext ):
            self.activeContext.drawGL( view )
        else:
            view.printText( self.getTitle(), (10,10) )        
    def newGLContext( self ):
        '''Update the OpenGL context'''
        if ( self.activeContext ):
            self.activeContext.newGLContext()
            
class FieldStrokeContext( VFieldContext ):
    '''A context for editing the field by applying "instantaneous" strokes'''
    def __init__( self, vfield ):
        VFieldContext.__init__( self, vfield )
        self.brushID = 0        # opengl brush id
        self.brushPos = (0.0, 0.0)  # position, in world space of the brush
        self.setBrushSize( 2.0 ) # size of brush (in meters)

    def setBrushSize( self, size ):
        '''This sets the size of the brush - the absolute radius of the brush'''
        self.brushSize = size
        self.newGLContext()

    def activate( self ):
        # compute the initial position of the mouse
        px, py = pygame.mouse.get_pos()
        #TODO: This is NOT the world position of the mouse, but the screen position
##        self.brushPos = ( px, py )
        
    def newGLContext( self ):
        '''Update gl context'''
        SAMPLES = 30
        self.brushID = glGenLists( 1 )
        points = np.arange( 0, SAMPLES, dtype=np.float32 ) * ( np.pi * 2 / SAMPLES )
        c = np.cos( points ) * self.brushSize
        s = np.sin( points ) * self.brushSize
        glNewList( self.brushID, GL_COMPILE )
        glBegin( GL_LINE_STRIP )
        for i in xrange( SAMPLES ):
            glVertex3f( c[i], s[i], 0 )
        glVertex3f( c[0], s[0], 0 )
        glEnd()
        glEndList()

    def handleKeyboard( self, event, view ):
        result = ContextResult()

        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        if ( noMods ):
            if ( event.key == pygame.K_UP ):
                self.setBrushSize( self.brushSize + 0.5 )
                result.set( True, True )
            elif ( event.key == pygame.K_DOWN ):
                if ( self.brushSize > 1.0 ):
                    self.setBrushSize( self.brushSize - 0.5 )
                    result.set( True, True )
        return result

    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = ContextResult()
        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        pX, pY = view.screenToWorld( event.pos )
        self.brushPos = ( pX, pY )
        result.set( False, True )  # this should be conditional
        if (event.type == pygame.MOUSEMOTION ):
            if ( self.dragging ):
                pX, pY = view.screenToWorld( event.pos )
                dX = pX - self.downX
                dY = pY - self.downY
                # now apply the direction implied by ( dX, dY ) with the brush centered
                # at ( self.downX, self.downY ) to the field
                blendDirection( self.field, ( dX, dY ), self.brushPos, self.brushSize )
                # TODO: instead of instantaneous values, filter this by skipping events                
                self.downX = pX
                self.downY = pY
                result.set( True, True )
        elif ( event.type == pygame.MOUSEBUTTONUP ):
            if ( self.dragging and event.button == LEFT ):
##                self.field.fieldChanged()
                self.dragging = False
                result.set( True, True )
        elif ( event.type == pygame.MOUSEBUTTONDOWN ):
            if ( event.button == LEFT and noMods ):
                self.downX, self.downY = view.screenToWorld( event.pos )
                self.dragging = True
                result.set( True, True )
                
        return result

    def drawGL( self, view ):
        # TODO: THIS IS FRAGILE
        #   It would be better for the text printer to handle new lines and do smart layout for
        #   a big block of text
        t = VFieldContext.getTitle( self )
        view.printText( t, (10,10) )
        view.printText( 'Brush direction', (10, 30 ) )
        glPushAttrib( GL_POLYGON_BIT | GL_COLOR_BUFFER_BIT )
        glPushMatrix()
        if ( self.dragging ):
            glColor3f( 0.0, 1.0, 0.0 )
        else:
            glColor3f( 1.0, 1.0, 1.0 )
        glTranslatef( self.brushPos[0], self.brushPos[1], 0 )
        glCallList( self.brushID )
        glPopMatrix()
        glPopAttrib()

class FieldPathContext( VFieldContext ):
    '''A context for editing the field by applying paths'''
    def __init__( self, vfield ):
        VFieldContext.__init__( self, vfield )
        self.strokes = []
        self.liveStroke = None

    def bake( self ):
        '''Bake the strokes into the field'''
        pass

    def clear( self ):
        '''Clear the strokes'''
        pass

    def activate( self  ):
        '''Begin boundary edit'''
        pass

    def deactivate( self ):
        '''End boundary edit'''
        # todo: if in the middle of an edit, cancel it
        pass
    
    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = ContextResult()
        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        if (event.type == pygame.MOUSEMOTION ):
            if ( self.dragging ):
                pX, pY = view.screenToWorld( event.pos )
                self.liveStroke.addPoint( pX, pY )
                result.set( True, True )
        elif ( event.type == pygame.MOUSEBUTTONUP ):
            if ( self.dragging and event.button == LEFT ):
                self.liveStroke.endPath()
                self.dragging = False
        elif ( event.type == pygame.MOUSEBUTTONDOWN ):
            if ( event.button == LEFT and noMods ):
                pX, pY = view.screenToWorld( event.pos )
                self.liveStroke = Path()
                self.liveStroke.beginPath( pX, pY )
                self.dragging = True
                
        return result

    def drawGL( self, view ):
        # TODO: THIS IS FRAGILE
        #   It would be better for the text printer to handle new lines and do smart layout for
        #   a big block of text
        t = VFieldContext.getTitle( self )
        view.printText( t, (10,10) )
        view.printText( 'Draw stroke', (10, 30 ) )
        if ( self.liveStroke ):
            glColor3f( 0.1, 1.0, 0.1 )
            self.liveStroke.drawGL()            
            
class FieldBoundaryContext( VFieldContext ):
    '''A context for editing the boundaries of the field'''

    def __init__( self, vfield ):
        VFieldContext.__init__( self, vfield )
        self.editLine = None    # a 2-tuple of 2-tuples( (x0, y0), (x1, y1) ) of the line segment

    def activate( self  ):
        '''Begin boundary edit'''
        pass

    def deactivate( self ):
        '''End boundary edit'''
        # todo: if in the middle of an edit, cancel it
        pass
    
    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = ContextResult()
        return result

    def drawGL( self, view ):
        # TODO: THIS IS FRAGILE
        #   It would be better for the text printer to handle new lines and do smart layout for
        #   a big block of text
        t = VFieldContext.getTitle( self )
        view.printText( t, (10,10) )
        view.printText( 'Edit boundaries', (10, 30 ) )
        
        
            