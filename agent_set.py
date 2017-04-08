# A GLWidget drawable that draws a set of agents

from OpenGL.GL import *
from ObjSlice import AABB
from primitives import Vector3

class AgentSet:
    '''A GLWidget drawable that draws a set of agents.'''
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
    
    def __init__( self, view, agent_radius, frame_set ):
        '''Constructor.

        @param  view            An instance of GLWidget.
        @param  agent_radius    A float; the radius of the agents.
        '''
        self.view = view
        self.radius = agent_radius
        self.classes = frame_set.getClasses()
        self.is3D = frame_set.is3D
        self.currFrame = None

    def setFrame( self, frame ):
        self.currFrame = frame

    def getBB( self ):
        '''Returna bounding box spanning the curent frame'''
        bb = AABB()
        if ( not self.currFrame is None ):
            if ( self.is3D ):
                pos = self.currFrame[ :, :3 ]
                verts = [ Vector3(x, y, z) for (x, z, y) in pos ]
            else:
                pos = self.currFrame[ :, :2 ]
                verts = [ Vector3(x, y, 0) for (x, y) in pos ]
            bb.expand( verts )
        return bb

    def drawGL( self ):
        '''Draws the agents to the current context.'''
        # this draws agents as points
        #   it changes the size of the points according to current view
        #   parameters and rounds the points using point smothing
        if ( not self.currFrame is None ):
            glPushAttrib( GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT | GL_POINT_BIT )
            glDisable( GL_DEPTH_TEST )
            glDepthMask( False )
            glPointSize( 2.0 * self.radius / self.view.pixelSize )
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
            glPopAttrib()
    

