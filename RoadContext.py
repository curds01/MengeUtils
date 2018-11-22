# a bit of hacked code to support contexts for the roadmap builder

from Context import BaseContext, ContextResult
import pygame
from fieldTools import *
import numpy as np
from OpenGL.GL import *
import trajectory.scbData as scbData
from primitives import Vector2
from obstacles import GLPoly
import paths
try:
    import cairo
    HAS_CAIRO = True
except ImportError:
    print "pycairo is not available.  You will not be able to output a pdf of the scene"
    HAS_CAIRO = False

# This is here instead of Context.py because this is pygame dependent and that is QT dependent.
#   I need to unify those.

class PGMouse:
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

    def exportDisplay( self ):
        '''Reports if the screen should be exported to an image'''
        if ( self.activeContext ):
            return self.activeContext.exportDisplay()
        return None        

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
                changed = self.activeContext is not None
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
        self.downX = 0      # the screen space coordinates where the mouse was pressed (x)
        self.downY = 0      # the screen space coordinates where the mouse was pressed (x)
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
                '\n\t\t* Each adds a factor of 10 to the playback' + \
                '\n\tCtrl-o - toggle whether or not the frames are output'
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
    def __init__( self, scbFileName, obstacles, agentRadius=0.13 ):
        PGContext.__init__( self )
        if ( HAS_CAIRO ):
            self.HELP_TEXT += '\n\tCtrl-p - output the current frame as a pdf file.'
        self.obstacles = obstacles
        print "***\nOBSTACLES"
        print obstacles
        self.scbData = None
        self.currFrame = None
        self.loadSCBData( scbFileName )
        self.radius=agentRadius    # assumes uniform radius
        self.selected = -1
        self.visState = False   # causes the agents to be colored according to state instead of class
        self.view = None
        # data for saving images
        self.saveDisplay = False
        self.lastSaved = -1
        if ( self.scbData ):
            print "SCBContext"
            print "\tFrame shape:", self.currFrame.shape
            print "Found agents with the following ids:", self.classes.keys()

    def exportDisplay( self ):
        '''Reports if the screen should be exported to an image'''
        if ( self.saveDisplay ):
            if ( self.currFrameID != self.lastSaved ):
                self.lastSaved = self.currFrameID
                return paths.getPath( 'scb%05d.png' % ( self.lastSaved ), False )
        return None
        
    def loadSCBData( self, fileName ):
        if ( fileName ):
            self.scbData = scbData.NPFrameSet( fileName )
            self.currFrame, self.currFrameID = self.scbData.next()
            self.classes = self.scbData.getClasses()
            self.is3D = self.scbData.is3D

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
        
        if ( self.is3D ):
            pos = self.currFrame[ :, :3:2 ]
        else:
            pos = self.currFrame[ :, :2 ]

        for i, idClass in enumerate( keys ):
            color = self.COLORS[ ( i * COLOR_STRIDE ) % self.COLOR_COUNT ]
            glColor3f( color[0], color[1], color[2] )
            glBegin( GL_POINTS )
            for idx in self.classes[ idClass ]:
                x, y = pos[ idx, : ]
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
        self.view = view
        self.drawAgents( view )
        PGContext.drawGL( self, view )
        title = "Play SCB -- "
        if ( self.scbData ):
            title += "frame %d (%d agents)" % (self.currFrameID, self.scbData.agtCount )
        else:
            title += "no scb file loaded"
        if ( self.selected != -1 ):
            title += " (Agent %d selected: <%.2f, %.2f>)" % ( self.selected, self.currFrame[ self.selected, 0 ], self.currFrame[ self.selected, 1 ] )
        if ( self.visState ):
            title += ", color shows state"
        else:
            title += ", color shows class"
        if ( self.saveDisplay ):
            title += "    - saving display"
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
                            try:
                                self.currFrame, self.currFrameID = self.scbData.next()
                                result.set( True, True )
                            except StopIteration:
                                pass
                    else:
                        if ( self.scbData ):
                            AMT = 0
                            if ( hasCtrl ): AMT += 10
                            if ( hasAlt ): AMT += 10
                            if ( hasShift ): AMT += 10
                            try:
                                self.currFrame, self.currFrameID = self.scbData.next( AMT )
                            except StopIteration:
                                pass
                            else:
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
                    result.setHandled( True )
                elif ( event.key == pygame.K_c and noMods ):
                    if ( self.hasStateData() ):
                        self.visState = not self.visState
                        result.set( True, True )
                    else:
                        print "No state data!"
                elif ( event.key == pygame.K_o and hasCtrl ):
                    self.saveDisplay = not self.saveDisplay
                    if ( not self.saveDisplay ):
                        self.lastSaved = -1
                    result.set( True, True )
                elif ( HAS_CAIRO and event.key == pygame.K_p and hasCtrl ):
                    if ( self.scbData ):
                        self.saveFramePDF()
                    result.setHandled( True )
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
            if ( noMods and event.button == PGMouse.LEFT ):
                pX, pY = view.screenToWorld( event.pos )        
                result.setNeedsRedraw( self.findAgent( pX, pY ) )
        return result
    
    def saveFrameXML( self ):
        '''Save the current frame as an xml file for running a simulation'''
        # HARD-CODED FILE NAME
        f = open( paths.getPath( 'scene.xml', False ), 'w' )
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

    def saveFramePDF( self ):
        '''Save the current frame as a pdf file for visualization'''
        # assumes this is only called if cairo has been successfully installed
        assert( self.view is not None )
        fName = paths.getPath( 'scb%05d' % ( self.currFrameID ), False )
        surface = cairo.SVGSurface( fName + '.svg', self.view.wWidth, self.view.wHeight )
        cr = cairo.Context( surface )
        # draw stuff here
        # set up basic transform so image coords match sim coords
        cr.scale( self.view.wWidth / self.view.vWidth, self.view.wHeight / self.view.vHeight )
        cr.translate( 0, self.view.vHeight)
        cr.scale( 1.0, -1.0 )
        cr.translate( -self.view.vLeft, -self.view.vBottom )
        cr.set_line_width(max(cr.device_to_user_distance(3,3)))
        
        # draw obstacles
        for o in self.obstacles.polys:
            if ( len( o.vertices ) <= 1 ): continue
            v = o.vertices[0]
            cr.move_to( v.x, v.y )
            for v in o.vertices[1:]:
                cr.line_to( v.x, v.y )
            if ( o.closed ):
                cr.close_path()
            if ( o.closed ):
                cr.set_source_rgb( 0.5, 0.5, 0.5 )
                cr.fill_preserve()
                cr.set_source_rgb( 0.0, 0.0, 0.0 )
                cr.stroke()                
            else:
                cr.stroke()

        cr.set_line_width(max(cr.device_to_user_distance(1.5, 1.5)))
        # draw agents
        keys = self.classes.keys()
        keys.sort()
        CLASS_COUNT = len( self.classes.keys() )
        COLOR_STRIDE = self.COLOR_COUNT / CLASS_COUNT
        MAX_COLOR = 1/0.7
        for i, idClass in enumerate( keys ):
            for idx in self.classes[ idClass ]:
                x, y = self.currFrame[ idx, :2 ]
                if ( x + self.radius < self.view.vLeft or
                     x - self.radius > self.view.vLeft + self.view.vWidth or
                     y + self.radius < self.view.vBottom or
                     y - self.radius > self.view.vBottom + self.view.vHeight ):
                    continue
                cr.arc( x, y, self.radius, 0, 2 * np.pi )
                if ( self.visState ):
                    color = self.COLORS[ int( self.currFrame[ idx, 3 ] ) % self.COLOR_COUNT ]
                else:
                    color = self.COLORS[ ( i * COLOR_STRIDE ) % self.COLOR_COUNT ]
                cr.set_source_rgb( color[0] * MAX_COLOR, color[1] * MAX_COLOR, color[2] * MAX_COLOR )
                cr.fill_preserve()
                cr.set_source_rgb( 0, 0, 0 )
                cr.stroke()
        
        # finalize
        surface.write_to_png( fName + '.png' )
        cr.show_page()
        surface.finish()

class PositionContext( PGContext, MouseEnabled ):
    '''A context for determining positions in the scene'''
    HELP_TEXT = 'Position Context' + \
                '\n\tAllows the user to query world space coordinates' + \
                '\n\tSimply click on the window, the world space coordinates' + \
                '\n\twill be printed to the console'
    
    def __init__( self ):
        PGContext.__init__( self )
        MouseEnabled.__init__( self )
        self.worldPos = [0,0]

    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = ContextResult()
        self.downX, self.downY = event.pos
        self.worldPos = view.screenToWorld( ( self.downX, self.downY ) )
        if ( event.type == pygame.MOUSEBUTTONDOWN ):
            if ( event.button == PGMouse.LEFT ):
                print "World position: %f %f" % ( self.worldPos[0], self.worldPos[1] )
        elif ( event.type == pygame.MOUSEMOTION ):
            result.set( False, True )
        return result

    def drawGL( self, view ):
        '''Draws the current rectangle to the open gl context'''
        PGContext.drawGL( self, view )
        posStr = '(%.3f, %.3f)' % ( self.worldPos[0], self.worldPos[1] )
        view.printText( '%s' % posStr,  (self.downX, view.wHeight - self.downY) )

# Ideas
#   1) Load a reference obj that can be drawn on top
#   2) Create multiple obstacle sets (using one as reference to the other)
#   3) Display grid, snap to grid
#
# Plan
#
#   Create polygons/polylines
#       polygons are, defacto closed
#       switch modes between polygons/lines
#       Start polygon, left-click, left-click, right to end
#
#   Edit obstacles
#       - delete vertex
#       - delete edge (connection)
#       - connect vertices (make edge)
#       - create vertex
#       - create and connect
class ObstacleContext( PGContext, MouseEnabled ):
    '''A context for creating and editing obstacles'''
    BASE_TEXT = 'Obstacle Context' + \
                '\n\tAllows the creation and editing of obstacles\n' + \
                '\n\tn            Toggle normal drawing' + \
                '\n\t0            Do nothing' + \
                '\n\t1            Create polygons' + \
                '\n\t2            Edit polygons' + \
                '\n\tCtrl+s       Save the obstacle file to "obstacles.xml"' + \
                '\n\tShift+s      Save the obstacle file to "obstacles.obj"'

    NO_ACTION = 0
    NEW_POLY = 1
    NEW_LINE = 2
    EDIT_POLY = 3
    
    def __init__( self, obstacleSet ):
        '''Constructor.

        @param obstacleSet          An instance of an ObstacleSet.  
        '''        
        PGContext.__init__( self )
        MouseEnabled.__init__( self )
        self.obstacleSet = obstacleSet
        self.state = self.NEW_POLY
        self.contexts = { self.NO_ACTION:ObstacleNullContext(),
                          self.NEW_POLY:DrawPolygonContext(),
                          self.EDIT_POLY:EditPolygonContext( obstacleSet )
                          }
        self.drawNormal = False     # determines if normals are drawn on the obstacles

    def activate( self ):
        '''Called when the context is first activated'''
        self.setState( self.state, True )

    def deactivate( self ):
        '''Called when the context is deactivated'''
        self.contexts[ self.state ].deactivate()
        
    def drawGL( self, view ):
        '''Draws the current rectangle to the open gl context'''
        # assumes obstacles are already being drawn by the scene -
        #   merely needs to draw current obstacle and decorations
        PGContext.drawGL( self, view )
        self.contexts[ self.state ].drawGL( view, self.drawNormal )

    def setState( self, newState, force=False ):
        '''Sets the contexts new activity state'''
        if ( self.state != newState or force ):
            self.contexts[ self.state ].deactivate()
            self.state = newState
            self.contexts[ self.state ].activate()
            self.HELP_TEXT = self.BASE_TEXT + '\n\n' + self.contexts[ self.state ].HELP_TEXT
            
        
    def handleKeyboard( self, event, view ):
        """The context handles the keyboard event as it sees fit and reports it's status with a ContextResult"""
        result = PGContext.handleKeyboard( self, event, view )
        
        if ( not result.isHandled() ):
            result = self.contexts[ self.state ].handleKeyboard( event, view )
            if ( not result.isHandled() ):
                mods = pygame.key.get_mods()
                hasCtrl = mods & pygame.KMOD_CTRL
                hasAlt = mods & pygame.KMOD_ALT
                hasShift = mods & pygame.KMOD_SHIFT
                noMods = not( hasShift or hasCtrl or hasAlt )

                if ( event.type == pygame.KEYDOWN ):
                    if ( event.key == pygame.K_0 and noMods ):
                        result.set( True, self.state != self.NO_ACTION )
                        self.setState( self.NO_ACTION )
                    elif ( event.key == pygame.K_1 and noMods ):
                        result.set( True, self.state != self.NEW_POLY )
                        self.setState( self.NEW_POLY )
                    elif ( event.key == pygame.K_2 and noMods ):
                        result.set( True, self.state != self.EDIT_POLY )
                        self.setState( self.EDIT_POLY )
                    elif ( event.key == pygame.K_n and noMods ):
                        self.drawNormal = not self.drawNormal
                        self.obstacleSet.visibleNormals = self.drawNormal
                        result.set( True, True )
                    elif ( self.obstacleSet and event.key == pygame.K_s ):
                        if hasCtrl and not hasShift and not hasAlt:
                            path = paths.getPath( 'obstacles.xml', False )
                            print "Writing obstacles to:", path
                            f = open( path, 'w' )
                            f.write ('''<?xml version="1.0"?>
    <Experiment version="2.0">

        <ObstacleSet type="explicit" class="1"> ''')
                            f.write( '%s' % self.obstacleSet.xml() )
                            f.write( '\n\t</ObstacleSet>\n\n</Experiment>' )
                            f.close()
                            result.set( True, False )
                        elif hasShift and not hasCtrl and not hasAlt:
                            path = paths.getPath('obstacles.obj', False)
                            print "Writing obj from obstacles to {}".format(path)
                            with open(path, 'w') as f:
                                f.write(self.obstacleSet.obj())
                            result.set(True, False)

        return result    

    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = PGContext.handleMouse( self, event, view )

        if ( not result.isHandled() ):
            result = self.contexts[ self.state ].handleMouse( event, view )
            if ( result.isFinished() ):
                if ( self.state == self.NEW_POLY ):
                    self.obstacleSet.append( self.contexts[ self.state ].polygon )
                    
        return result
class ObstacleNullContext( PGContext ):
    '''A simple context for indicating no action is being taken'''
    HELP_TEXT = 'No action'

    def drawGL( self, view, visNormals ):
        '''Draws the agent context into the view'''
        PGContext.drawGL( self, view )
        view.printText( "No action",  (10,30) )

# Actions
#   Vertices
#       1) Move
#       2) Delete (aka clear)
#   Edges
#       1) Move
#       2) Collapse
#       3) Insert vertex
#   Polygon
#       1) Delete (aka clear)
#       2) Move
#       3) Reverse winding

class EditPolygonContext( PGContext, MouseEnabled ):
    '''A context for editing obstacles'''
    HELP_TEXT = 'Edit polygon' + \
                '\n\tEdit the properties of a polygonal shape\n' + \
                '\n\tv      Edit vertices' + \
                '\n\t\tLeft-click and drag          Move highlighted vertex' +\
                '\n\t\tRight-click while dragging   Cancel move' + \
                '\n\t\tc                            Clear highlighted vertex' + \
                '\n\t\t                             Removes polygons with < 3 vertices' + \
                '\n\te      Edit edges' + \
                '\n\t\tMiddle-click and drag        Insert vertex into highlighted edge' + \
                '\n\t\tRight-click while draggin    Cancel insertion' + \
                '\n\t\tc                            Collapse the highlighted edge' + \
                '\n\t\t                             Removes polygon when it has < 3 vertices' + \
                '\n\tp      Edit polygons' + \
                '\n\t\tLeft-click and drag          Move highlighted polygon' + \
                '\n\t\tRight-click while dragging   Cancel move' + \
                '\n\t\tc                            Clears the highlighted polygon' + \
                '\n\t\tr                            Reverse winding of highlighted polygon' + \
                ''
    #states for editing
    NO_EDIT = 0
    VERTEX = 1
    EDGE = 2
    POLY = 3
    
    def __init__( self, obstacles ):
        '''Constructor.

        @param      obstacles       An instance of ObstacleSet
        '''        
        PGContext.__init__( self )
        MouseEnabled.__init__( self )
        self.obstacles = obstacles
        self.state = self.NO_EDIT
        self.edgeDir = None
        self.activeID = -1
        self.activePoly = None
        
    def activate( self ):
        '''Called when the context is first activated'''
        self.obstacles.activeEdit = True
        self.obstacles.activeEdge = None
        self.obstacles.activeVert = None
        self.activePoly = None
        self.activeID = -1

    def deactivate( self ):
        '''Called when the context is deactivated'''
        self.obstacles.activeEdit = False
        self.obstacles.activeEdge = None
        self.obstacles.activeVert = None
        self.activePoly = None
        self.activeID = -1

    def setState( self, newState ):
        '''Changes the edit state of the context.

        @param      newState        A valid state enumeration.
        '''
        if ( self.state != newState ):
            self.state = newState
            self.obstacles.activeEdge = None
            self.obstacles.activeVert = None
            self.activePoly = None
            self.activeID = -1

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
                if ( event.key == pygame.K_v and noMods ):
                    result.set( True, self.state != self.VERTEX )
                    self.setState( self.VERTEX )
                elif ( event.key == pygame.K_e and noMods ):
                    result.set( True, self.state != self.EDGE )
                    self.setState( self.EDGE )
                elif ( event.key == pygame.K_p and noMods ):
                    result.set( True, self.state != self.POLY )
                    self.setState( self.POLY )
                elif ( event.key == pygame.K_r and noMods and self.activePoly ):
                    self.activePoly.reverseWinding()
                    result.set( True, True )
                elif ( event.key == pygame.K_c and noMods ):
                    if ( self.activePoly is not None ):
                        self.obstacles.removePoly( self.activePoly )
                        self.activePoly = None
                        result.set( True, True )
                    elif ( self.obstacles.activeVert is not None ):
                        self.obstacles.removeVertex( self.activeID )
                        self.activeID = -1
                        self.obstacles.activeVert = None
                        result.set( True, True )
                    elif ( self.obstacles.activeEdge is not None ):
                        self.obstacles.collapseEdge( self.activeID )
                        self.obstacles.activeEdge = None
                        result.set( True, True )
                    
        return result

    def modeLabel( self ):
        '''Returns a string reporting on the editing mode'''
        if ( self.state == self.VERTEX ):
            return "Edit vertex"
        elif ( self.state == self.EDGE ):
            return "Edit edge"
        elif ( self.state == self.POLY ):
            return "Edit polygon"
        else:
            return "Hit v, e, or p to edit vertices, edges, or polygons"

    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = PGContext.handleMouse( self, event, view )

        if ( not result.isHandled() ):
            mods = pygame.key.get_mods()
            hasCtrl = mods & pygame.KMOD_CTRL
            hasAlt = mods & pygame.KMOD_ALT
            hasShift = mods & pygame.KMOD_SHIFT
            noMods = not( hasShift or hasCtrl or hasAlt )

            if ( noMods ):
                if ( event.type == pygame.MOUSEBUTTONDOWN ):
                    if ( event.button == PGMouse.LEFT ):
                        self.downX, self.downY = view.screenToWorld( event.pos )
                        if ( self.activePoly is not None ):
                            origin = self.activePoly.vertices[ 0 ]
                            self.origin = ( origin.x, origin.y )
                            self.displace = []
                            for i in xrange( 1, len( self.activePoly.vertices ) ):
                                delta = self.activePoly.vertices[i] - origin
                                self.displace.append( ( delta.x, delta.y ) )
                            self.dragging = True
                        elif ( self.obstacles.activeVert is not None ):
                            self.origin = ( self.obstacles.activeVert.x, self.obstacles.activeVert.y )
                            self.dragging = True
                        elif ( self.obstacles.activeEdge is not None ):
                            v1, v2 = self.obstacles.activeEdge
                            self.origin = ( v1.x, v1.y )
                            self.edgeDir = ( v2.x - v1.x, v2.y - v1.y )
                            self.dragging = True
                    elif ( event.button == PGMouse.RIGHT and self.dragging ):
                        if ( self.obstacles.activeVert is not None ):
                            self.obstacles.activeVert.x = self.origin[0]
                            self.obstacles.activeVert.y = self.origin[1]
                        elif ( self.obstacles.activeEdge is not None ):
                            v1, v2 = self.obstacles.activeEdge
                            v1.x = self.origin[0]
                            v1.y = self.origin[1]
                            v2.x = v1.x + self.edgeDir[0]
                            v2.y = v1.y + self.edgeDir[1]
                        elif ( self.activePoly is not None ):
                            self.activePoly.vertices[ 0 ].x = self.origin[0]
                            self.activePoly.vertices[ 0 ].y = self.origin[1]
                            for i in xrange( 1, len( self.activePoly.vertices ) ):
                                self.activePoly.vertices[ i ].x = self.origin[0] + self.displace[i-1][0]
                                self.activePoly.vertices[ i ].y = self.origin[1] + self.displace[i-1][1]
                        self.dragging = False
                        result.set( True, True )
                    elif ( event.button == PGMouse.MIDDLE and self.state == self.EDGE ):
                        if ( self.obstacles.activeEdge is not None ):
                            self.downX, self.downY = view.screenToWorld( event.pos )
                            # insert vertex
                            self.obstacles.activeVert = Vector2( self.downX, self.downY )
                            self.activeID = self.obstacles.insertVertex( self.obstacles.activeVert, self.activeID )
                            self.origin = ( self.obstacles.activeVert.x, self.obstacles.activeVert.y )
                            # temporarily change to dragging vertex
                            self.obstacles.activeEdge = None
                            self.dragging = True
                            result.set( True, True )
                elif ( event.type == pygame.MOUSEBUTTONUP ):
                    if ( event.button == PGMouse.LEFT or event.button == PGMouse.MIDDLE):
                        self.dragging = False
                elif ( event.type == pygame.MOUSEMOTION ):
                    if ( self.dragging ):
                        pX, pY = view.screenToWorld( event.pos )
                        newX = self.origin[0] + ( pX - self.downX )
                        newY = self.origin[1] + ( pY - self.downY )
                        if ( self.obstacles.activeVert ):
                            self.obstacles.activeVert.x = newX
                            self.obstacles.activeVert.y = newY
                        elif ( self.obstacles.activeEdge ):
                            v1, v2 = self.obstacles.activeEdge
                            v1.x = newX
                            v1.y = newY
                            v2.x = v1.x + self.edgeDir[0]
                            v2.y = v1.y + self.edgeDir[1]
                        elif ( self.activePoly ):
                            self.activePoly.vertices[ 0 ].x = newX
                            self.activePoly.vertices[ 0 ].y = newY
                            for i in xrange( 1, len( self.activePoly.vertices ) ):
                                self.activePoly.vertices[ i ].x = newX + self.displace[i-1][0]
                                self.activePoly.vertices[ i ].y = newY + self.displace[i-1][1]
                        result.set( True, True )
                    elif ( self.state != self.NO_EDIT ):
                        result.setHandled( True )
                        pX, pY = event.pos
                        keyEdges = self.state == self.EDGE or self.state == self.POLY
                        
                        selID = view.select( pX, pY, self.obstacles, keyEdges )
                        if ( selID != self.activeID ):
                            self.activeID = selID
                            if ( self.activeID == -1 ):
                                # This can only happen if it just CHANGED to -1
                                result.setNeedsRedraw( True )
                                self.obstacles.activeEdge = None
                                self.obstacles.activeVert = None
                                self.activePoly = None
                            else:
                                if ( keyEdges ):
                                    selEdge = self.obstacles.selectEdge( self.activeID )
                                    self.obstacles.activeVert = None
                                    if ( self.state == self.EDGE ):
                                        self.obstacles.activeEdge = selEdge
                                    elif ( self.state == self.POLY ):
                                        self.activePoly = self.obstacles.polyFromEdge( self.activeID )
                                        self.obstacles.activeEdge = None
                                    result.setNeedsRedraw( True )
                                else:
                                    self.obstacles.activeEdge = None
                                    selVert = self.obstacles.selectVertex( self.activeID )
                                    if ( selVert != self.obstacles.activeVert ):
                                        self.obstacles.activeVert = selVert
                                        result.setNeedsRedraw( True )
        return result

    def drawGL( self, view, visNormals=False ):
        '''Draws the current rectangle to the open gl context'''
        PGContext.drawGL( self, view )
        view.printText( 'Edit polygon\n\t%s' % self.modeLabel(),  (10,30) )
        if ( self.activePoly ):
            glPushAttrib( GL_COLOR_BUFFER_BIT | GL_LINE_BIT | GL_ENABLE_BIT )
            glColor3f( 0.9, 0.9, 0.0 )
            glDisable( GL_DEPTH_TEST )
            glLineWidth( 3.0 )
            glBegin( GL_LINE_LOOP )
            for v in self.activePoly.vertices:
                glVertex3f( v.x, v.y, 0 )
            glEnd()
            glPopAttrib()
    
        
class DrawPolygonContext( PGContext, MouseEnabled ):
    '''A context for drawing a closed polygon'''
    HELP_TEXT = 'Draw polygon' + \
                '\n\tAllows the creation of a polygonal shape' + \
                '\n\tLeft-click        Create a vertex' + \
                '\n\t                  It will be connected to previous vertices in a' + \
                '\n\t                  closed polygon' + \
                '\n\tRight click       Finish polygon and add to obstacle set' + \
                '\n\tDelete            Cancel current polygon' + \
                '\n\tCtrl-z            Remove the last vertex added' + \
                '\n\tf                 Flip obstacle sinding' + \
                '\n\n\tYou must define a polygon with at least three vertices'

    # states for drawing
    WAITING = 0
    DRAWING = 1
    
    def __init__( self ):
        '''Constructor. '''        
        PGContext.__init__( self )
        MouseEnabled.__init__( self )
        self.activate()

    def activate( self ):
        '''Called when the context is first activated'''
        self.state = self.WAITING
        self.polygon = None

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
                if ( event.key == pygame.K_z and hasCtrl ):
                    result.setHandled( True )
                    result.setNeedsRedraw( self.popVertex() )
                elif ( event.key == pygame.K_DELETE and noMods ):
                    result.set( True, self.polygon is not None )
                    self.activate()
                elif ( event.key == pygame.K_f and noMods ):
                    result.set( True, self.reverseWinding() )
                    
        return result

    def reverseWinding( self ):
        '''Reverses the winding of the active polygon.

        @returns        True if the polygon reversed, false otherwise.
        '''
        reversed = False
        if ( self.polygon.vertCount() > 1 ):
            self.polygon.reverseWinding()
            reversed = True
        return reversed
    
    def popVertex( self ):
        '''Removes the last vertex from the polygon (essentially undo the last).

        If there are no vertices left, the polygon is cleared and the draw state changes.

        @returns        True if a redraw is necessary, false if not.
        '''
        needsRedraw = self.polygon is not None
        if ( self.polygon ):
            self.polygon.vertices.pop( -1 )
            if ( self.polygon.vertCount() == 0 ):
                self.polygon = None
                self.state = self.WAITING
            else:
                self.polygon.updateWinding()
                        
        return needsRedraw
                    
    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = PGContext.handleMouse( self, event, view )

        if ( not result.isHandled() ):
        
            mods = pygame.key.get_mods()
            hasCtrl = mods & pygame.KMOD_CTRL
            hasAlt = mods & pygame.KMOD_ALT
            hasShift = mods & pygame.KMOD_SHIFT
            noMods = not( hasShift or hasCtrl or hasAlt )

            if ( noMods ):
                if ( event.type == pygame.MOUSEBUTTONDOWN ):
                    if ( event.button == PGMouse.LEFT ):
                        if ( self.state == self.WAITING ):
                            # initialize a polygon
                            self.polygon = GLPoly()
                            self.polygon.closed = True
                            self.state = self.DRAWING
                        self.downX, self.downY = event.pos
                        p = view.screenToWorld( ( self.downX, self.downY ) )
                        self.polygon.vertices.append( Vector2( p[0], p[1] ) )
                        self.polygon.updateWinding()
                        self.dragging = True
                        result.set( True, True )
                    elif ( event.button == PGMouse.RIGHT and self.state == self.DRAWING ):
                        if ( self.polygon.vertCount() < 3 ):
                            self.polygon = None
                        self.dragging = False
                        self.state = self.WAITING
                        result.set( True, True, self.polygon is not None )
                elif ( event.type == pygame.MOUSEBUTTONUP ):
                    if ( event.button == PGMouse.LEFT and self.dragging ):
                        self.dragging = False
                elif ( event.type == pygame.MOUSEMOTION ):
                    if ( self.dragging  ):
                        self.downX, self.downY = event.pos
                        p = view.screenToWorld( ( self.downX, self.downY ) )
                        self.polygon.vertices[ -1 ] = Vector2( p[0], p[1] )
                        result.set( True, True )
                        
                    
        return result

    def drawGL( self, view, visNormals=False ):
        '''Draws the current rectangle to the open gl context'''
        PGContext.drawGL( self, view )
        view.printText( 'New polygon',  (10,30) )
        if ( self.state == self.DRAWING ):
            self.polygon.drawGL( editable=True, drawNormals=visNormals )
     
class AgentContext( PGContext, MouseEnabled ):
    '''A context for adding agents and editing agent positions'''
    HELP_TEXT = 'Agent context' + \
                '\n\tCreate new agent - left-click in space and drag to position' + \
                '\n\tEdit agent position - hover over agent, left-click and drag to move' + \
                '\n\tDelete agent - hover over agent, hit delete' + \
                '\n\tIncrease NEW agent radius - up arrow (with no agent highlighted)' + \
                '\n\tDecrease NEW agent radius - down arrow (with no agent highlighted)' + \
                '\n\tIncrease specific agent radius - highlight agent/goal, up arrow' + \
                '\n\tDecrease specific agent radius - highlight agent/goal, down arrow' + \
                '\n\tSave out agents.xml - Ctrl + S'
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
        data = '\tNew agent radius: %.2f' % self.agtRadius
        if ( self.agents.activeAgent ):
            data += ', current agent radius: %.2f' % ( self.agents.activeAgent.radius )
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
                if ( event.key == pygame.K_s and hasCtrl ):
                    f = open( paths.getPath( 'agents.xml', False ), 'w' )
                    f.write( '%s' % self.agents.xml() )
                    f.close()
                    result.set( True, False )
                elif ( event.key == pygame.K_DELETE and noMods ):
                    result.set( True, self.agents.deleteActiveAgent() )
                elif ( event.key == pygame.K_UP and noMods ):
                    if ( self.agents.activeAgent ):
                        self.agents.activeAgent.radius += 0.01
                    else:
                        self.agtRadius += 0.01
                        self.agents.setRadius( self.agtRadius )
                    result.set( True, True )
                elif ( event.key == pygame.K_DOWN and noMods ):
                    if ( self.agents.activeAgent ):
                        if ( self.agents.activeAgent.radius > 0.01 ):
                            self.agents.activeAgent.radius -= 0.01
                    else:
                        if ( self.agtRadius > 0.01 ):
                            self.agtRadius -= 0.01
                            self.agents.setRadius( self.agtRadius )
                    result.set( True, True )
        return result

    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = PGContext.handleKeyboard( self, event, view )
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
            if ( event.button == PGMouse.LEFT ):
                self.dragging = False
        elif ( event.type == pygame.MOUSEBUTTONDOWN ):
            if ( event.button == PGMouse.LEFT and noMods ):
                self.downX, self.downY = event.pos
                if ( self.agents.activeAgent ):
                    self.downPos = self.agents.activeAgent.getActivePos()
                else:
                    p = view.screenToWorld( event.pos )
                    self.downPos = p
                    self.agents.addAgent( p )
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
        
    def handleKeyboard( self, event, view ):
        result = PGContext.handleKeyboard( self, event, view )
        if ( result.isHandled() ):
            return result

        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        if ( event.type == pygame.KEYDOWN ):
            if ( event.key == pygame.K_s and hasCtrl ):
                self.field.write( paths.getPath( 'field.txt', False ) )
                result.set( True, False )
                
        return result
    
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
        result.combine( VFieldContext.handleKeyboard( self, event, view ) )
        if ( result.isHandled() ):
            return result
        
        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        if ( event.type == pygame.KEYDOWN ):
            if ( noMods ):
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
                elif ( event.key == pygame.K_4 ):
                    if ( self.activeContext.__class__ != FieldDomainContext ):
                        self.activeContext.deactivate()
                        self.activeContext = FieldDomainContext( self.field )
                        self.activeContext.activate()
                        result.set( True, True )
            
        return result

    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = ContextResult()
        if ( self.activeContext ):
            result.combine( self.activeContext.handleMouse( event, view ) )
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
                        self.setBrushSize( max( self.brushSize - 0.5, 0.1 ) )
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
            if ( self.dragging and event.button == PGMouse.LEFT ):
                self.dragging = False
                result.set( True, True )
        elif ( event.type == pygame.MOUSEBUTTONDOWN ):
            if ( event.button == PGMouse.LEFT and noMods ):
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
            if ( self.dragging and event.button == PGMouse.LEFT ):
                self.liveStroke.endPath()
                self.dragging = False
        elif ( event.type == pygame.MOUSEBUTTONDOWN ):
            if ( event.button == PGMouse.LEFT and noMods ):
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
            
class FieldDomainContext( VFieldContext, MouseEnabled ):
    '''A context for editing the boundaries and resolution of a field'''
    HELP_TEXT = 'Edit field domain properties' + \
                '\n\tIncrease cell size - right arrow' + \
                '\n\tDecrease cell size - left arrow' + \
                '\n\t\t* holding Ctrl/Alt/Shift changes the cell size change rate'

    NO_EDIT = 0
    EDIT_HORZ = 1
    EDIT_VERT = 2
    def __init__( self, vField ):
        VFieldContext.__init__( self, vField )
        MouseEnabled.__init__( self )
        self.corners = vField.getCorners()
        self.size = vField.size # the size is (height, width)
        self.activeEdge = None

    def activate( self  ):
        '''Begin boundary edit'''
        pass

    def deactivate( self ):
        '''End boundary edit'''
        # todo: if in the middle of an edit, cancel it
        self.activeEdge = None
    
    def handleKeyboard( self, event, view ):
        result = VFieldContext.handleKeyboard( self, event, view )
        if ( result.isHandled() ):
            return result        

        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        DELTA = 1.0
        if ( hasCtrl ):
            DELTA *= 0.1
        if ( hasShift ):
            DELTA *= 0.1
        if ( hasAlt ):
            DELTA *= 0.1

        if ( event.key == pygame.K_RSHIFT or
                 event.key == pygame.K_LSHIFT or
                 event.key == pygame.K_RALT or
                 event.key == pygame.K_LALT or
                 event.key == pygame.K_RCTRL or
                 event.key == pygame.K_LCTRL ):
                result.set( False, True )
                return result
            
        if ( event.type == pygame.KEYDOWN ):
            if ( event.key == pygame.K_RIGHT ):
                self.field.setCellSize( self.field.cellSize + DELTA, self.size )
                result.set( True, True )
            elif ( event.key == pygame.K_LEFT ):
                cs = self.field.cellSize
                result.set( True, False )
                if ( cs > DELTA ):
                    self.field.setCellSize( cs - DELTA, self.size )
                    result.set( True, True )
        return result

    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
        result = VFieldContext.handleMouse( self, event, view )
        if ( result.isHandled() ):
            return result
        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        if ( event.type == pygame.MOUSEMOTION ):
            p = view.screenToWorld( event.pos )
            if ( self.dragging ):
                if ( self.dragging == self.EDIT_HORZ ):
                    dX = p[0] - self.downX
                    self.corners[ self.activeEdge ][ 0 ] = self.startVal + dX
                    self.corners[ self.activeEdge + 1][ 0 ] = self.startVal + dX
                else:
                    dY = p[1] - self.downY
                    self.corners[ self.activeEdge ][ 1 ] = self.startVal + dY
                    self.corners[ self.activeEdge + 1][ 1 ] = self.startVal + dY
                result.set( True, True )
                self.field.setDimensions( self.visSize() )
            else:
                # hover behavior
                newIdx = self.selectEdge( p, view )
                if ( newIdx != self.activeEdge ):
                    result.redraw = True
                    self.activeEdge = newIdx
        elif ( event.type == pygame.MOUSEBUTTONDOWN ):
            if ( noMods and event.button == PGMouse.LEFT and self.activeEdge is not None ):
                self.downX, self.downY = view.screenToWorld( event.pos )
                if ( self.activeEdge % 2 ): # vertical line
                    self.startVal = self.corners[ self.activeEdge ][ 0 ]
                    self.dragging = self.EDIT_HORZ
                else:
                    self.startVal = self.corners[ self.activeEdge ][ 1 ]
                    self.dragging = self.EDIT_VERT
            elif ( event.button == PGMouse.RIGHT and self.dragging ):
                if ( self.dragging == self.EDIT_HORZ ):
                    self.corners[ self.activeEdge ][ 0 ] = self.startVal
                    self.corners[ self.activeEdge + 1][ 0 ] = self.startVal
                else:
                    self.corners[ self.activeEdge ][ 1 ] = self.startVal
                    self.corners[ self.activeEdge + 1][ 1 ] = self.startVal
                self.dragging = self.NO_EDIT
                result.set( True, True )
                self.field.setDimensions( self.visSize() )
                
        elif ( event.type == pygame.MOUSEBUTTONUP ):
            if ( self.dragging ):
                self.size = self.visSize()
                self.field.setDimensions( self.size )
                self.dragging = self.NO_EDIT
                result.set( True, True )
        return result

    def visSize( self ):
        '''Based on the current corner values, computes the field size'''
        return ( self.corners[-1][1] - self.corners[0][1], self.corners[1][0] - self.corners[0][0] )

    def selectEdge( self, worldPos, view ):
        '''Given a world position of the mouse, determines if an edge is "under" the mouse and returns its
        index.  Returns None if no edge is sufficiently close.'''
        DIST = view.pixelSize * 10  # 10 pixels away is considered selection

        i = -1 # left-hand vertical edge        
        if ( worldPos[0] >= self.corners[ i ][0] - DIST and worldPos[0] <= self.corners[ i ][0] + DIST and
             worldPos[1] >= self.corners[ i + 1 ][1] - DIST and worldPos[1] <= self.corners[ i ][1] + DIST ):
            return i
        i = 0 # bottom horizontal edge        
        if ( worldPos[1] >= self.corners[ i ][1] - DIST and worldPos[1] <= self.corners[ i ][1] + DIST and
             worldPos[0] >= self.corners[ i ][0] - DIST and worldPos[0] <= self.corners[ i+1 ][0] + DIST ):
            return i
        i = 1 # right-hand vertical edge        
        if ( worldPos[0] >= self.corners[ i ][0] - DIST and worldPos[0] <= self.corners[ i ][0] + DIST and
             worldPos[1] >= self.corners[ i ][1] - DIST and worldPos[1] <= self.corners[ i + 1 ][1] + DIST ):
            return i
        i = 2 # top horizontal edge        
        if ( worldPos[1] >= self.corners[ i ][1] - DIST and worldPos[1] <= self.corners[ i ][1] + DIST and
             worldPos[0] >= self.corners[ i + 1 ][0] - DIST and worldPos[0] <= self.corners[ i ][0] + DIST ):
            return i
        return None

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

    def drawGL( self, view ):
        # TODO: THIS IS FRAGILE
        #   It would be better for the text printer to handle new lines and do smart layout for
        #   a big block of text
        VFieldContext.drawGL( self, view )
        t = 'Edit field domain (change in cell size: {0})'.format( self.cellSizeChange() )
        view.printText( t, (10, 30 ) )
        glPushAttrib( GL_COLOR_BUFFER_BIT | GL_LINE_BIT )
        glColor3f( 0.25, 1.0, 0.25 )
        glBegin( GL_LINES )
        for i in range( -1, 3 ):
            glVertex3f( self.corners[ i ][0], self.corners[ i ][1] , 0 )
            glVertex3f( self.corners[ i+1 ][0], self.corners[ i+1 ][1] , 0 )
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
        
        
            