# a bit of hacked code to support contexts for the roadmap builder

from Context import BaseContext, ContextResult
import pygame
from fieldTools import *
import numpy as np
from OpenGL.GL import *
import scbData

# This is here instead of Context.py because this is pygame dependent and that is QT dependent.
#   I need to unify those.

LEFT = 1
MIDDLE = 2
RIGHT = 3
WHEEL_UP = 4
WHEEL_DOWN = 5

class PGContext( BaseContext ):
    '''A pygame-based context'''
    HELP_TEXT = 'No help defined'
    def __init__( self ):
        BaseContext.__init__( self )
        self.displayHelp = False

    def drawHelp( self, view ):
        '''Displays this context's instructions to the display'''
        if ( self.displayHelp ):
            hCenter = view.wWidth / 2
            vCenter = view.wHeight / 2
            t = self.HELP_TEXT + '\n\t---\n' + view.HELP_TEXT
            size = view.textSize( t )
            vCenter += size[1] / 2
            hCenter -= size[0] / 2
            view.printText( t, (hCenter, vCenter) )

    def drawGL( self, view ):
        '''Responsible for drawing help'''
        self.drawHelp( view )
        
    def handleKeyboard( self, event, view ):
        """The context handles the keyboard event as it sees fit and reports it's status with a ContextResult"""
        result = ContextResult()
        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        if ( noMods and event.type == pygame.KEYDOWN ):
            if ( event.key == pygame.K_h ):
                result.set( True, not self.displayHelp )
                self.displayHelp = True
        elif ( event.type == pygame.KEYUP ):
            if ( event.key == pygame.K_h and self.displayHelp ):
                self.displayHelp = False
                result.set( True, True )
        return result

    def deactivate( self ):
        '''When deactivating, the help can no longer be displayed'''
        self.displayHelp = False

class ContextSwitcher( PGContext ):
    '''A context for switching contexts'''
    HELP_BASE = 'Hit the following keys to activate a context (hit ESC to back out)'
    HELP_TEXT = HELP_BASE
    def __init__( self ):
        PGContext.__init__( self )
        self.contexts = {}
        self.activeContext = None

    def handleKeyboard( self, event, view ):
        """The context handles the keyboard event as it sees fit and reports it's status with a ContextResult"""
        result = ContextResult()#PGContext.handleKeyboard( self, event, view )
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
                    result = PGContext.handleKeyboard( self, event, view )
                    if ( not result.isHandled() and self.contexts.has_key( event.key ) ):
                        print 'changing contexts'
                        ctx = self.contexts[ event.key ]
                        changed = ctx != self.activeContext
                        self.switchContexts( ctx )
                        result.set( True, changed )
        elif ( event.type == pygame.KEYUP ):
            if ( self.activeContext ):
                result = self.activeContext.handleKeyboard( event, view )
            else:
                result = PGContext.handleKeyboard( self, event, view )
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
        keys = self.contexts.keys()
        keys.sort()
        self.HELP_TEXT = self.HELP_BASE
        for k in keys:
            self.HELP_TEXT += '\n\t%s: %s' % ( pygame.key.name( k ), self.contexts[ k ] )
        print "Adding context {0} to key {1}".format( context, pygame.key.name( key ) )

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
        else:
            PGContext.drawGL( self, view )

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

class SCBContext( PGContext ):
    '''Plays back an scb file'''
    HELP_TEXT = 'Playback an scbfile' + \
                '\n\tup arrow - go to beginning' + \
                '\n\tCtrl-s - save current configuration in xml file' + \
                '\n\tc - toggle coloring between state and class' + \
                '\n\tright arrow - step frame forward' + \
                '\n\tleft arrow - step frame backward' + \
                '\n\t\t* Holding Ctrl, Alt, Shift will speed up the playback step' + \
                '\n\t\t* Each adds a factor of 10 to the playback'
    COLORS = ( (0.7, 0.0, 0.0 ),  # red
##               (0.7, 0.35, 0.0 ), # orange
               (0.7, 0.7, 0.0 ),  # yellow
##               (0.35, 0.7, 0.0 ), # chartreuse
               (0.0, 0.7, 0.0 ),  # green
##               (0.0, 0.7, 0.35),  # teal
               (0.0, 0.7, 0.7),   # cyan
               (0.0, 0.35, 0.7),  # aqua
               (0.0, 0.0, 0.7),   # blue
               (0.35, 0.0, 0.7),  # purple
               (0.7, 0.0, 0.7),   # magenta
               (0.7, 0.0, 0.35),  # burgandy
               )
    COLOR_COUNT = len( COLORS )
    def __init__( self, scbFileName, agentRadius=0.25 ):
        PGContext.__init__( self )
        self.scbData = None
        self.currFrame = None
        self.loadSCBData( scbFileName )
        self.radius=0.25    # assumes uniform radius
        self.selected = -1
        self.visState = False   # causes the agents to be colored according to state instead of class
        if ( self.scbData ):
            print "SCBContext"
            print "\tFrame shape:", self.currFrame.shape
            print "Found agents with the following ids:", self.classes.keys()
        
    def loadSCBData( self, fileName ):
        if ( fileName ):
            self.scbData = scbData.NPFrameSet( fileName )
            self.currFrame, self.currFrameID = self.scbData.next()
            self.classes = self.scbData.getClasses()

    def drawAgents( self, view ):
        if ( self.scbData ):
            if ( self.visState ):
                self.drawAgentState( view )
            else:
                self.drawAgentClass( view )

    def drawHighlighted( self, view ):
        '''Draws the highlighted agent'''
        if ( self.selected != -1 ):
            glBegin( GL_POINTS );
            glColor3f( 1.0, 1.0, 1.0 )
            x, y = self.currFrame[ self.selected, :2 ]
            glVertex2f( x, y )
            glEnd()
            
    def drawAgentClass( self, view ):
        '''Draws the agents, colored by class'''
        # this draws agents as points
        #   it changes the size of the points according to current view
        #   parameters and rounds the points using point smothing
        glPushAttrib( GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT | GL_POINT_BIT )
        glDisable( GL_DEPTH_TEST )
        glDepthMask( False )
        glPointSize( 2.0 * self.radius / view.pixelSize )
        glEnable( GL_POINT_SMOOTH )
        glEnable( GL_BLEND )
        glAlphaFunc( GL_GEQUAL, 0.5 )
        CLASS_COUNT = len( self.classes.keys() )
        COLOR_STRIDE = self.COLOR_COUNT / CLASS_COUNT
        keys = self.classes.keys()
        keys.sort()
        for i, idClass in enumerate( keys ):
            color = self.COLORS[ ( i * COLOR_STRIDE ) % self.COLOR_COUNT ]
            glColor3f( color[0], color[1], color[2] )
            glBegin( GL_POINTS )
            for idx in self.classes[ idClass ]:
                x, y = self.currFrame[ idx, :2 ]
                glVertex2f( x, y )
            glEnd()
        self.drawHighlighted( view )
        glPopAttrib()

    def drawAgentState( self, view ):
        '''Draws the agents, colored by state'''
        glPushAttrib( GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT | GL_POINT_BIT )
        glDisable( GL_DEPTH_TEST )
        glDepthMask( False )
        glPointSize( 2.0 * self.radius / view.pixelSize )
        glEnable( GL_POINT_SMOOTH )
        glEnable( GL_BLEND )
        glAlphaFunc( GL_GEQUAL, 0.5 )

        glBegin( GL_POINTS )
        for agt in self.currFrame:
            color = self.COLORS[ int( agt[3] ) % self.COLOR_COUNT ]
            glColor3f( color[0], color[1], color[2] )
            x, y = agt[ :2 ]
            glVertex2f( x, y )
        glEnd()
        self.drawHighlighted( view )
        glPopAttrib()

    def hasStateData( self ):
        '''Reports if the scb file contains state data'''
        if ( self.scbData ):
            return self.scbData.hasStateData()
        return False

    def drawGL( self, view ):
        '''Draws the agent context into the view'''
        PGContext.drawGL( self, view )
        self.drawAgents( view )
        title = "Play SCB -- "
        if ( self.scbData ):
            title += "frame %d (%d agents)" % (self.currFrameID, self.scbData.agtCount )
        else:
            title += "no scb file loaded"
        if ( self.selected != -1 ):
            title += " (Agent %d selected)" % ( self.selected )
        if ( self.visState ):
            title += ", color shows state"
        else:
            title += ", color shows class"
        view.printText( title,  (10,10) )            

    def findAgent( self, pX, pY ):
        '''Finds the closest agent to the point'''
        radSqd = self.radius * self.radius
        p = np.array( (pX, pY) )
        disp = self.currFrame[:, :2] - p
        dispSqd = np.sum( disp * disp, axis=1 )
        id = np.argmin( dispSqd )
        changed = False
        if ( dispSqd[ id ] < radSqd ):
            changed = self.selected != id
            self.selected = id
        else:
            changed = self.selected != -1
            self.selected = -1
        return changed
        
    def handleKeyboard( self, event, view ):
        """The context handles the keyboard event as it sees fit and reports it's status with a ContextResult"""
        result = PGContext.handleKeyboard( self, event, view )
        if ( not result.isHandled() ):
            mods = pygame.key.get_mods()
            hasCtrl = mods & pygame.KMOD_CTRL
            hasAlt = mods & pygame.KMOD_ALT
            hasShift = mods & pygame.KMOD_SHIFT
            noMods = not( hasShift or hasCtrl or hasAlt )
            if ( event.type == pygame.KEYDOWN ):
                if ( event.key == pygame.K_RIGHT ):
                    if ( noMods ):
                        if ( self.scbData ):
                            self.currFrame, self.currFrameID = self.scbData.next()
                            result.set( True, True )
                    else:
                        if ( self.scbData ):
                            AMT = 0
                            if ( hasCtrl ): AMT += 10
                            if ( hasAlt ): AMT += 10
                            if ( hasShift ): AMT += 10
                            self.currFrame, self.currFrameID = self.scbData.next( AMT )
                            result.set( True, True )
                elif ( event.key == pygame.K_LEFT ):
                    if ( noMods ):
                        if ( self.scbData ):
                            self.currFrame, self.currFrameID = self.scbData.prev()
                            result.set( True, True )
                    else:
                        if ( self.scbData ):
                            AMT = 0
                            if ( hasCtrl ): AMT += 10
                            if ( hasAlt ): AMT += 10
                            if ( hasShift ): AMT += 10
                            self.currFrame, self.currFrameID = self.scbData.prev( AMT )
                            result.set( True, True )
                elif ( event.key == pygame.K_UP and noMods ):
                    if ( self.scbData ):
                        self.scbData.setNext( 0 )
                        self.currFrame, self.currFrameID = self.scbData.next()
                        result.set( True, True )
                elif ( event.key == pygame.K_s and hasCtrl ):
                    if ( self.scbData ):
                        self.saveFrameXML()
                elif ( event.key == pygame.K_c and noMods ):
                    if ( self.hasStateData() ):
                        self.visState = not self.visState
                        result.set( True, True )
                    else:
                        print "No state data!"
        return result

    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = ContextResult()
        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )
        
        if ( event.type == pygame.MOUSEBUTTONDOWN ):
            if ( noMods and event.button == LEFT ):
                pX, pY = view.screenToWorld( event.pos )        
                result.setNeedsRedraw( self.findAgent( pX, pY ) )
        return result
    
    def saveFrameXML( self ):
        '''Save the current frame as an xml file for running a simulation'''
        # HARD-CODED FILE NAME
        f = open( 'scene.xml', 'w' )
        HEADER = '''<?xml version="1.0"?>

<Experiment time_step="0.05" gridSizeX="82" gridSizeY="82" visualization="1" useProxies="1" neighbor_dist="5">

'''
        f.write( HEADER )
        keys = self.classes.keys()
        keys.sort()
        for idClass in keys:
            f.write( '\t<AgentSet class="%d">\n' % idClass )
            for idx in self.classes[ idClass ]:
                x, y = self.currFrame[ idx, :2 ]
                f.write( '\t\t<Agent p_x="%f" p_y="%f" />\n' % ( x, y ) )
            f.write( '\t</AgentSet>' )
        f.write( '</Experiment>' )
        f.close()
        
class AgentContext( PGContext, MouseEnabled ):
    '''A context for adding agents-goal pairs and editing existing pairs'''
    HELP_TEXT = 'Agent context' + \
                '\n\tCreate new agent and goal - left-click in space and drag the goal' + \
                '\n\tEdit agent position - hover over agent, left-click and drag to move' + \
                '\n\tEdit goal position - hover over goal, left-click and drag to move' + \
                '\n\tDelete agent - hover over agent or goal, hit delete' + \
                '\n\tIncrease NEW agent radius - up arrow' + \
                '\n\tDecrease NEW agent radius - down arrow'
    def __init__( self, agentSet ):
        PGContext.__init__( self )
        MouseEnabled.__init__( self )
        self.agents = agentSet
        self.agtRadius = self.agents.defRadius
        self.downPos = None     # the position of the active agent when the mouse was pressed

    def activate( self ):
        '''Enables the agent set for editing'''
        self.agents.editable = True

    def deactivate( self ):
        '''Turns off the editable state for the agents'''
        PGContext.deactivate( self )
        self.agents.editable = False
        self.dragging = False
        if ( self.agents.activeAgent ):
            self.agents.activeAgent.deactivate()
        
    def drawGL( self, view ):
        '''Draws the agent context into the view'''
        PGContext.drawGL( self, view )
        title = "Edit agents: %d" % self.agents.count()
        view.printText( title,  (10,30) )
        data = '\tAgent radius: %.2f' % self.agtRadius
        view.printText( data, (10, 10) )

    def handleKeyboard( self, event, view ):
        """The context handles the keyboard event as it sees fit and reports it's status with a ContextResult"""
        result = PGContext.handleKeyboard( self, event, view )
        if ( not result.isHandled() ):
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
                elif ( event.key == pygame.K_UP and noMods ):
                    self.agtRadius += 0.01
                    result.set( True, True )
                    self.agents.setRadius( self.agtRadius )
                elif ( event.key == pygame.K_DOWN and noMods ):
                    if ( self.agtRadius > 0.01 ):
                        self.agtRadius -= 0.01
                        self.agents.setRadius( self.agtRadius )
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

class VFieldContext( PGContext, MouseEnabled ):
    '''A context for working with a vector field'''
    def __init__( self, vfield ):
        PGContext.__init__( self )
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
        PGContext.drawGL( self, view )

class FieldEditContext( VFieldContext ):
    '''The context which allows various kinds of edits on a vector field'''
    def __init__( self, vfield ):
        VFieldContext.__init__( self, vfield )
        self.activeContext = FieldStrokeDirContext( self.field )

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
            if ( event.key == pygame.K_s and hasCtrl ):
                self.field.write( 'field.txt' )
            elif ( noMods ):
                if ( event.key == pygame.K_1 ):
                    if ( self.activeContext.__class__ != FieldStrokeDirContext ):
                        self.activeContext.deactivate()
                        self.activeContext = FieldStrokeDirContext( self.field )
                        self.activeContext.activate()
                        result.set( True, True )
                elif ( event.key == pygame.K_2 ):
                    if ( self.activeContext.__class__ != FieldStrokeLenContext ):
                        self.activeContext.deactivate()
                        self.activeContext = FieldStrokeLenContext( self.field )
                        self.activeContext.activate()
                        result.set( True, True )
                elif ( event.key == pygame.K_3 ):
                    if ( self.activeContext.__class__ != FieldStrokeSmoothContext ):
                        self.activeContext.deactivate()
                        self.activeContext = FieldStrokeSmoothContext( self.field )
                        self.activeContext.activate()
                        result.set( True, True )
                else:
                    result = VFieldContext.handleKeyboard( self, event, view )
        elif ( event.type == pygame.KEYUP ):
            if ( event.key == pygame.K_RSHIFT or event.key == pygame.K_LSHIFT ):
                if ( self.activeContext and self.activeContext.__class__ == FieldBoundaryContext ):
                    self.activeContext.deactivate()
                    self.activeContext = None
                    result.set( True, True )
            else:
                result = VFieldContext.handleKeyboard( self, event, view )
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
            VFieldContext.drawGL( self, view )
            
    def newGLContext( self ):
        '''Update the OpenGL context'''
        if ( self.activeContext ):
            self.activeContext.newGLContext()
            
class FieldStrokeContext( VFieldContext ):
    '''The basic context for editing fields with instantaneous strokes'''
    HELP_TEXT = '\n\tUp arrow - increase brush size\n\tdown arrow - decrease brush size'
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

    def drawText( self, view ):
        '''Draws the text to be displayed by this context'''
        VFieldContext.drawGL( self, view )
    
    def drawGL( self, view ):
        # TODO: THIS IS FRAGILE
        #   It would be better for the text printer to handle new lines and do smart layout for
        #   a big block of text
        self.drawText( view )
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

    def handleKeyboard( self, event, view ):
        result = VFieldContext.handleKeyboard( self, event, view )
        if ( not result.isHandled() ):

            mods = pygame.key.get_mods()
            hasCtrl = mods & pygame.KMOD_CTRL
            hasAlt = mods & pygame.KMOD_ALT
            hasShift = mods & pygame.KMOD_SHIFT
            noMods = not( hasShift or hasCtrl or hasAlt )

            if ( noMods ):
                if ( event.type == pygame.KEYDOWN ):
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
                dX = pX - self.downX
                dY = pY - self.downY
                # TODO: instead of instantaneous values, filter this by skipping events                
                self.doWork( (dX, dY ) )
                self.downX = pX
                self.downY = pY
                result.set( True, True )
        elif ( event.type == pygame.MOUSEBUTTONUP ):
            if ( self.dragging and event.button == LEFT ):
                self.dragging = False
                result.set( True, True )
        elif ( event.type == pygame.MOUSEBUTTONDOWN ):
            if ( event.button == LEFT and noMods ):
                self.downX, self.downY = view.screenToWorld( event.pos )
                self.dragging = True
                result.set( True, True )
        return result

    def doWork( self, mouseDelta ):
        '''Perofrm the work of the stroke based on the given mouse movement'''
        pass

    def activate( self ):
        '''Called when the context is first activated'''
        VFieldContext.activate( self )
        pygame.mouse.set_visible( False )

    def deactivate( self ):
        '''Called when the context is first activated'''
        VFieldContext.deactivate( self )
        pygame.mouse.set_visible( True )        
        
class FieldStrokeDirContext( FieldStrokeContext ):
    '''A context for editing the DIRECTION field by applying "instantaneous" strokes'''
    HELP_TEXT = 'Edit the direction of the vectors' + FieldStrokeContext.HELP_TEXT
    def __init__( self, vfield ):
        FieldStrokeContext.__init__( self, vfield )

    def doWork( self, mouseDelta ):
        '''Perofrm the work of the stroke based on the given mouse movement'''
        blendDirectionStroke( self.field, mouseDelta, ( self.downX, self.downY ), self.brushPos, self.brushSize )

    def drawText( self, view ):
        '''Draws the text to be displayed by this context'''
        FieldStrokeContext.drawText( self, view )
        view.printText( 'Brush direction', (10, 30 ) )

class FieldStrokeSmoothContext( FieldStrokeContext ):
    '''A context for SMOOTHING the field by applying "instantaneous" strokes'''
    STRENGTH_CHANGE = 0.01
    KERNEL_CHANGE = 0.25
    HELP_TEXT = 'Smooth the vector field' + FieldStrokeContext.HELP_TEXT + \
        '\n\tright arrow - increase smooth strength' + \
        '\n\tleft arrow - decrease smooth strength' + \
        '\n\t[ - decrease kernel size' + \
        '\n\t] - increase kernel size'
    def __init__( self, vfield ):
        FieldStrokeContext.__init__( self, vfield )
        self.smoothStrength = 1.0
        self.kernelSize = 1.0   # in meters
        
    def drawGL( self, view ):
        '''Draws the brush size and the kernel size in the window'''
        FieldStrokeContext.drawGL( self, view )
        glPushAttrib( GL_POLYGON_BIT | GL_COLOR_BUFFER_BIT )
        glPushMatrix()
        glColor3f( 0.25, 0.25, 1.0 )
        glTranslatef( self.brushPos[0], self.brushPos[1], 0 )
        s = self.kernelSize / self.brushSize
        glScalef( s, s, s )
        glCallList( self.brushID )
        glPopMatrix()
        glPopAttrib()

    def handleKeyboard( self, event, view ):
        result = FieldStrokeContext.handleKeyboard( self, event, view )

        if ( result.isHandled() ): return result        

        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        if ( noMods ):
            if ( event.type == pygame.KEYDOWN ):
                if ( event.key == pygame.K_RIGHT ):
                    self.smoothStrength += self.STRENGTH_CHANGE
                    result.set( True, True )
                elif ( event.key == pygame.K_LEFT ):
                    if ( self.smoothStrength > self.STRENGTH_CHANGE ):
                        self.smoothStrength -= self.STRENGTH_CHANGE
                        result.set( True, True )
                elif ( event.key == pygame.K_RIGHTBRACKET ):
                    self.kernelSize += self.KERNEL_CHANGE
                    result.set( True, True )
                elif ( event.key == pygame.K_LEFTBRACKET ):
                    if ( self.kernelSize > self.KERNEL_CHANGE ):
                        self.kernelSize -= self.KERNEL_CHANGE
                        result.set( True, True )
        return result

    def doWork( self, mouseDelta ):
        '''Perofrm the work of the stroke based on the given mouse movement'''
        smoothStroke( self.field, self.smoothStrength, self.kernelSize, ( self.downX, self.downY ), self.brushPos, self.brushSize )

    def drawText( self, view ):
        # TODO: THIS IS FRAGILE
        #   It would be better for the text printer to handle new lines and do smart layout for
        #   a big block of text
        FieldStrokeContext.drawText( self, view )
        view.printText( 'Brush smooth: strength = {0:.2f}, kernelSize = {1:.3f}'.format( self.smoothStrength, self.kernelSize ), (10, 30 ) )        
        
class FieldStrokeLenContext( FieldStrokeContext ):
    '''A context for editing the MAGNITUDE of the field by applying "instantaneous" strokes'''
    HELP_TEXT = 'Edit the length of the vectors' + FieldStrokeContext.HELP_TEXT + \
                '\n\tright arrow - increase length' + \
                '\n\tleft arrow - decrease length'
    def __init__( self, vfield ):
        FieldStrokeContext.__init__( self, vfield )
        self.factor = 1.0

    def handleKeyboard( self, event, view ):
        result = FieldStrokeContext.handleKeyboard( self, event, view )

        if ( result.isHandled() ): return result        

        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        if ( noMods ):
            if ( event.type == pygame.KEYDOWN ):
                if ( event.key == pygame.K_RIGHT ):
                    self.factor += 0.05
                    result.set( True, True )
                elif ( event.key == pygame.K_LEFT ):
                    f = self.factor - 0.05
                    if ( f < 0.0 ): f = 0.0
                    changed = self.factor != f
                    result.set( changed, changed )
                    self.factor = f
        return result

    def doWork( self, mouseDelta ):
        '''Perofrm the work of the stroke based on the given mouse movement'''
        blendLengthStroke( self.field, self.factor, ( self.downX, self.downY ), self.brushPos, self.brushSize )

    def drawText( self, view ):
        # TODO: THIS IS FRAGILE
        #   It would be better for the text printer to handle new lines and do smart layout for
        #   a big block of text
        FieldStrokeContext.drawText( self, view )
        view.printText( 'Brush length: length = {0:.2f}'.format( self.factor ), (10, 30 ) )

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
        
        
            