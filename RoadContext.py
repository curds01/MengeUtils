# a bit of hacked code to support contexts for the roadmap builder

from Context import BaseContext, ContextResult
import pygame

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

            