import sys, pygame
from math import sqrt, cos, sin, pi

from OpenGL.GL import *
from OpenGL.GLU import *
from ObjSlice import AABB, Segment, Polygon
from primitives import Vector3

# sax parser for obstacles
from xml.sax import make_parser, handler

NO_EDIT = 0
GRAPH_EDIT = 1
OBSTACLE_EDIT = 2
AGENT_EDIT = 3
EDIT_STATE_COUNT = 4
editState = AGENT_EDIT

class Agent:
    """Agent object for drawing"""
    ID = 0

    INACTIVE = 0
    AGENT = 1
    GOAL = 2
    def __init__( self, radius, pos, goal ):        
        self.radius = radius
        self.pos = pos
        self.goal = goal
        self.id = Agent.ID
        self.active = Agent.INACTIVE
        Agent.ID += 2

    def __str__( self ):
        return "Agent %d of %d - %s" % ( self.id, Agent.ID, self.pos )

    def sjguy( self ):
        return '%f %f %f %f' % ( self.pos[0], self.pos[1], self.goal[0], self.goal[1] )
    
    def printActive( self ):
        if ( self.active == Agent.GOAL ):
            print "GOAL active"
        elif ( self.active == Agent.AGENT ):
            print "AGENT active"
        else:
            raise AttributeError, "Can't get active position for an inactive agent"
        
    def getActivePos( self ):
        if ( self.active == Agent.GOAL ):
            return self.goal
        elif ( self.active == Agent.AGENT ):
            return self.pos
        else:
            raise AttributeError, "Can't get active position for an inactive agent"
        
    def setActivePos( self, p ):
        if ( self.active == Agent.GOAL ):
            self.goal = p
        elif ( self.active == Agent.AGENT ):
            self.pos = p
        else:
            raise AttributeError, "Can't get active position for an inactive agent"
        
    def setPosition( self, pos ):
        self.pos = pos

    def setGoalPosition( self, pos ):
        self.goal = pos

    def activateAgent( self ):
        self.active = Agent.AGENT

    def activateGoal( self ):
        self.active = Agent.GOAL        

    def deactivate( self ):
        self.active = False

    def drawGL( self, select=False, editable=False ):
        if ( self.active and not select ):
            glColor3f( 0, 0, 1 )
            glBegin( GL_LINES )
            glVertex3f( self.pos[0], self.pos[1], 0 )
            glVertex3f( self.goal[0], self.goal[1], 0 )
            glEnd()

        # draw the agent
        if ( editable ):
            glColor3f( 0, 0, 0.95 )
        else:
            glColor3f( 0, 0, 0.4 )

        scale = self.radius
        if ( self.active == Agent.AGENT ):
            scale *= 1.5
        glPushMatrix()            
        glTranslate( self.pos[0], self.pos[1], 0 )
        glScale( scale, scale, scale )
        SEGMENTS = 10
        dTheta = 2 * pi / SEGMENTS
        if ( select ):
            glLoadName( self.id )
        glBegin( GL_TRIANGLE_FAN )
        glVertex3f( 0, 0, 0 )
        for i in range( SEGMENTS + 1 ):
            theta = dTheta * i
            c = cos( theta )
            s = sin( theta )
            glVertex3f( c, s, 0 )
        glEnd()
        glPopMatrix()
        # draw the goal                    
        if ( editable ):
            glColor3f( 0.9, 0.45, 0.0 )
        else:
            glColor3f( 0.45, 0.225, 0 )

        glPushMatrix()            
        glTranslate( self.goal[0], self.goal[1], 0 )
        scale = self.radius
        if ( self.active == Agent.GOAL ):
            scale *= 1.5
        glScale( scale, scale, scale )
        SEGMENTS = 10
        if ( select ):
            glLoadName( self.id + 1)
        glBegin( GL_TRIANGLE_FAN )
        glVertex3f( 0, 0, 0 )
        for i in range( SEGMENTS + 1 ):
            theta = dTheta * i
            c = cos( theta )
            s = sin( theta )
            glVertex3f( c, s, 0 )
        glEnd()
        glPopMatrix()

class AgentSet():
    def __init__( self, defRadius ):
        self.defRadius = defRadius
        self.agents = []
        self.activeAgent = None

    def count( self ):
        '''Returns the number of agents in the set'''
        return len( self.agents )

    def selectLastGoal( self ):
        if ( self.activeAgent ):
            self.activeAgent.deactivate()
            self.activeAgent = None
        if ( self.agents ):
            self.activeAgent = self.agents[-1]
            self.activeAgent.activateGoal()
            
    def selectAgent( self, id ):
        """Given the goal or the Agent id, returns the agent with activity set correctly"""
        agtId = id >> 1
        agt = self.agents[ agtId ]
        if ( id & 0x1 ):
            agt.activateGoal()
        else:
            agt.activateAgent()
        return agt

    def initFromFile( self, file ):
        f = open( file, 'r' )
        aCount = int( f.readline() )
        for line in f.xreadlines():
            line = line.strip()
            if ( line ):
                x1, y1, x2, y2 = map( lambda x: float(x), line.split() )
                self.agents.append( Agent( self.defRadius, (x1, y1), (x2,y2) ) )

    def sjguy( self ):
        """Returns the stephen guy formatted agent set"""
        s = '%d\n' % ( len( self.agents ) )
        for a in self.agents:
            s += '%s\n' % ( a.sjguy() )
        return s

    def addAgent( self, pos, goal, radius = None ):
        if ( radius == None ):
            radius = self.defRadius
        a = Agent( radius, pos, goal )
        self.agents.append( a )
        return a

    def drawGL( self, select=False, editable=False ):
        glPushAttrib( GL_POLYGON_BIT )
        glPolygonMode( GL_FRONT_AND_BACK, GL_FILL )
        for agent in self.agents:
            agent.drawGL( select, editable )
        glPopAttrib()

    def deleteActiveAgent( self ):
        """Removes the active agent"""
        if ( self.activeAgent ):
            agt = self.activeAgent
            activeID = agt.id
            Agent.ID -= 2
            i = activeID >> 1
            popped = self.agents.pop( i )
            assert( popped == agt )
            for a in self.agents[ i:]:
                a.id -= 2
            self.activeAgent = None
            return True
        return False
            
class GLPoly ( Polygon ):
    def __init__( self ):
        Polygon.__init__( self )
        self.vStart = 0         # the index at which select values for vertices starts
        self.eStart = 0         # the index at which select values for edges starts

    def drawGL( self, select=False, selectEdges=False, editable=False ):
        if ( editable ):
            glColor3f( 0.8, 0.0, 0.0 )
        else:
            glColor3f( 0.4, 0.0, 0.0 )

        if ( selectEdges or not select or editable ):        
            for i in range( self.vertCount() - 1):
                if ( selectEdges ):
                    glLoadName( self.eStart + i )
                v1 = self.vertices[i]
                v2 = self.vertices[i+1]
                glBegin( GL_LINES )
                glVertex3f( v1.x, v1.y, 0 )
                glVertex3f( v2.x, v2.y, 0 )
                glEnd()
            if ( self.closed ):
                if ( selectEdges ):
                    glLoadName( self.eStart + self.vertCount() - 1 )
                v1 = self.vertices[0]
                v2 = self.vertices[-1]
                glBegin( GL_LINES )
                glVertex3f( v1.x, v1.y, 0 )
                glVertex3f( v2.x, v2.y, 0 )
                glEnd()
        if ( editable or ( select and not selectEdges ) ):            
            glColor3f( 0.9, 0.9, 0.0 )
            for i in range( len( self.vertices ) ):
                if ( select ):
                    glLoadName( self.vStart + i )
                v = self.vertices[ i ]
                glBegin( GL_POINTS )
                glVertex3f( v.x, v.y, 0 )
                glEnd()   
        
class ObstacleSet:
    def __init__( self ):
        self.edgeCount = 0
        self.vertCount = 0
        self.polys = []
        self.activeVert = None
        self.activeEdge = None        

    def sjguy( self ):
        s = '%d\n' % ( self.edgeCount )
        for p in self.polys:
            s += '%s' % ( p.sjguy() )
        return s
    
    def __iter__( self ):
        return self.polys.__iter__()

    def __len__( self ):
        return len( self.polys )

    def selectVertex( self, i ):
        """Selects the ith vertex in the obstacle set"""
        count = 0
        for o in self.polys:
            tempSum = count + o.vertCount()
            if ( tempSum > i ):
                localI = i - count
                return o.vertices[ localI ]
            count = tempSum

    def selectEdge( self, i ):
        """Selects the ith edge in the obstacle set"""
        count = 0
        for o in self.polys:
            tempSum = count + o.edgeCount()
            if ( tempSum > i ):
                localI = i - count
                return ( o.vertices[ localI ], o.vertices[ localI + 1 ] )
            count = tempSum

    def append( self, poly ):
        poly.vStart = self.vertCount
        poly.eStart = self.edgeCount
        self.vertCount += poly.vertCount()
        self.edgeCount += poly.edgeCount()
        self.polys.append( poly )

    def drawGL( self, select=False, selectEdges = False, editable=False ):
        glPushAttrib( GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT )
        glDisable( GL_DEPTH_TEST )
        
        for o in self.polys:
            o.drawGL( select, selectEdges, editable )
        # now highlight selected elements
        if ( self.activeVert or self.activeEdge ):
            if ( self.activeVert ):
                glPointSize( 6.0 )
                glBegin( GL_POINTS )
                glColor3f( 0.9, 0.9, 0.0 )
                glVertex3f( self.activeVert.x, self.activeVert.y, 0 )
                glEnd()
                glPointSize( 3.0 )
            elif ( self.activeEdge ):
                glLineWidth( 3.0 )
                glBegin( GL_LINES )
                v1, v2 = self.activeEdge
                glVertex3f( v1.x, v1.y, 0 )
                glVertex3f( v2.x, v2.y, 0 )
                glEnd()
                glLineWidth( 1.0 )
        glPopAttrib()               

## TODO: Write this parser
##def sjguyObstParser( fileName ):
##    '''Create an obstacle set and bounding box based on the definition of sjguy for obstacles.activeEdge
##
##    definition is simple:
##    line 0:  number of line segments
##    line 1-N: each line segment is four floats: x0, y0, x1, y1
##    '''
##    obstacles = ObstacleSet()
##    bb = AABB()
##    f = open( fileName, 'r' )
##    obstCount = -1
##    for line in f.xreadlines():
##        if ( obstCount == -1 ):
##            obstCount = int( line )
##        else:
##            tokens = line.split()
##            
##                             
##    f.close()
    
class ObstXMLParser(handler.ContentHandler):
    def __init__(self):
        self.bb = AABB()
        self.obstacles = ObstacleSet()
        self.currObst = None        

    def startElement(self, name, attrs):
        if ( name == 'Obstacle' ):
            # assume all obstacles have a closed attribute
            self.currObst = GLPoly()
            if ( int( attrs[ 'closed' ] ) != 0 ):
                self.currObst.closed = True
        elif ( name == 'Vertex' ):
            x = float( attrs['p_x'] )
            y = float( attrs['p_y'] )
            self.currObst.vertices.append( Vector3( x, y, 0 ) )
            
    def endElement( self, name ):
        if ( name == "Obstacle" ):
            self.obstacles.append( self.currObst )
            self.bb.expand( self.currObst.vertices )
            
    def endDocument(self):
        print "Found %d obstacles" % ( len( self.obstacles ) )
        print "BB:", self.bb

            
def readObstacles( fileName, yFlip=False ):
    print "READ OBSTACLES: ", fileName
    if ( fileName[-3:] == 'xml' ):
        parser = make_parser()
        obstHandler = ObstXMLParser()
        parser.setContentHandler( obstHandler )
        parser.parse( fileName )
        if ( yFlip ):
            for o in obstHandler.obstacles:
                o.flipY()
            obstHandler.bb.flipY()
    elif ( fileName[ -3: ] == 'txt' ):
        raise Exception, "Invalid obstacle extension: %s" % ( fileName )
    else:
        raise Exception, "Invalid obstacle extension: %s" % ( fileName )
    return obstHandler.obstacles, obstHandler.bb


class Vertex:
    """Graph vertex"""
    COUNT = 0
    def __init__( self, pos ):
        self.pos = pos
        self.neighbors = []
        self.id = Vertex.COUNT
        Vertex.COUNT += 1

    def __str__( self ):
        return "%d %f %f" % ( len( self.neighbors ), self.pos[0], self.pos[1] )

    def setPosition( self, pos ):
        self.pos = ( pos[0], pos[1] )

    def removeEdge( self, edge ):
        i = self.neighbors.index( edge )
        self.neighbors.pop( i )

class Edge:
    """Graph edge"""
    def __init__( self, start=None, end=None ):
        self.start = start
        self.end = end

    def __str__( self ):
        return "%d to %d" % ( self.start.id, self.end.id )
    
    def isValid( self ):
        return self.start != None and self.end != None

    def clear( self ):
        self.start = self.end = None

    def copy( self ):
        return Edge( self.start, self.end )
    
class Graph:
    """Simple graph class"""
    def __init__( self ):
        self.vertices = []
        self.edges = []
        self.activeEdge = None
        self.fromID = None
        self.toID = None
        self.testEdge = Edge()

    def initFromFile( self, fileName ):
        print "Roadmap initfromFile", fileName
        f = open( fileName, 'r' )
        vertCount = int( f.readline() )
        for i in range( vertCount ):
            line = f.readline()
            tokens = line.strip().split()
            x = float( tokens[2] )
            y = float( tokens[3] )
            self.addVertex( (x, y ) )
        edgeCount = int( f.readline() )
        for i in range( edgeCount ):
            line = f.readline()
            tokens = line.strip().split()
            v1 = int( tokens[0] )
            v2 = int( tokens[1] )
            self.addEdgeByVert( v1, v2 )
            
    def __str__( self ):
        s = "%d\n" % ( len (self.vertices ) )
        for i, v in enumerate( self.vertices ):
            s += '%d %s\n' % ( i, v )
        s += '%d\n' % ( len( self.edges ) )
        for i, e in enumerate( self.edges ):
            p1 = e.start.pos
            p2 = e.end.pos
            dx = p1[0] - p2[0]
            dy = p1[1] - p2[1]
            dist = sqrt( dx * dx + dy * dy )
            s += '%d %d %f\n' % ( e.start.id, e.end.id, dist )
        return s

    def lastVertex( self ):
        """Returns the index of the last vertex"""
        return self.vertices[-1]
    
    def addVertex( self, pos ):
        self.vertices.append( Vertex( pos ) )

    def deleteVertex( self, vertex ):
        '''delete the given vertex and all edges attached to it'''
        # first remove the vertex from the list
        startIndex = self.vertices.index( vertex )
        v = self.vertices.pop( startIndex )
        # re-enumerate the following vertices
        Vertex.COUNT -= 1
        for i in range( startIndex, len( self.vertices ) ):
            self.vertices[i].id = i

        # remove edges            
        for e in v.neighbors:
            n = e.start
            if ( n == vertex ):
                n = e.end
            n.removeEdge( e )
            self.edges.pop( self.edges.index( e ) )

        v.neighbors = []
        
    def addEdge( self, e ):
        edge = e.copy()
        edge.start.neighbors.append( edge )
        edge.end.neighbors.append( edge )
        self.edges.append( edge )
    
    def deleteEdge( self, edge ):
        # delete the edge
        edge.start.removeEdge( edge )
        edge.end.removeEdge( edge )
        self.edges.pop( self.edges.index( edge ) )
        
    def addEdgeByVert( self, v1, v2 ):
        self.addEdge( Edge( self.vertices[ v1 ], self.vertices[ v2] ) )

    def drawGL( self, select=False, selectEdges = False, editable=False ):
        if ( selectEdges or not select ):
            self.drawEdges( self.edges, select, editable )
        glPointSize( 3.0 )
        if ( not selectEdges ):
            self.drawVertices( self.vertices, select, editable )
        if ( self.fromID != None ):
            glPointSize( 6.0 )
            self.drawVertices( ( self.fromID, ), False, editable )
        if ( self.toID != None ):
            glPointSize( 6.0 )
            self.drawVertices( ( self.toID, ), False, editable )
        if ( self.activeEdge != None ):
            glLineWidth( 3.0 )
            self.drawEdges( ( self.activeEdge, ), False, editable )
        
    def drawEdges( self, edges, select=False, editable=False ):
        if ( edges or self.testEdge.isValid() ):
            glPushAttrib( GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT )
            glDisable( GL_DEPTH_TEST )
            if ( editable ):
                glColor3f( 0.0, 0.75, 0.0 )
            else:
                glColor3f( 0.0, 0.375, 0.0 )
            for i, e in enumerate( edges ):
                if ( select ):
                    glLoadName( i )
                glBegin( GL_LINES )
                p1 = e.start.pos
                p2 = e.end.pos
                glVertex3f( p1[0], p1[1], 0 )
                glVertex3f( p2[0], p2[1], 0 )
                glEnd()
            if ( self.testEdge.isValid() ):
                glLineWidth( 3.0 )
                glColor3f( 0.0, 1.0, 0.5 )
                glBegin( GL_LINES )
                p1 = self.testEdge.start.pos
                p2 = self.testEdge.end.pos
                glVertex3f( p1[0], p1[1], 0 )
                glVertex3f( p2[0], p2[1], 0 )
                glEnd()
            glPopAttrib()
            glLineWidth( 1.0 )            
            
    def drawVertices( self, vertices, select=False, editable=False ):
        if ( vertices ):
            glPushAttrib( GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT )
            glDisable( GL_DEPTH_TEST )
            if ( editable ):
                glColor3f( 0.9, 0.9, 0.0 )
            else:
                glColor3f( 0.45, 0.45, 0.0 )
            
            for i, v in enumerate( vertices ):
                if ( select ):
                    glLoadName( i )
                glBegin( GL_POINTS )
                p = v.pos
                glVertex3f( p[0], p[1], 0 )
                glEnd()
            glPopAttrib()    

# OpenGL View
class View:
    """Contains the OpenGL view parameters for the scene"""
    VIDEO_FLAGS = pygame.OPENGL|pygame.DOUBLEBUF|pygame.RESIZABLE
    def __init__( self, imgSize, imgBottomLeft, viewSize, viewBottomLeft, winSize, font ):
        # the size of the displayed background and where it's bottom left-corner should be placed
        self.bgWidth = imgSize[0]
        self.bgHeight = imgSize[1]
        self.bgLeft = imgBottomLeft[0]
        self.bgBottom = imgBottomLeft[1]
        
        # the current view  - this is the LOGICAL size of what I'm viewing -- not the size of the window
        self.vWidth = viewSize[ 0 ]
        self.vHeight = viewSize[ 1 ]
        self.vLeft = viewBottomLeft[ 0 ]
        self.vBottom = viewBottomLeft[ 1 ]

        self.wWidth = winSize[ 0 ]
        self.wHeight = winSize[ 1 ]

        self.pixelSize = self.vWidth / float( self.wWidth )        # this is assuming square pixels

        # create characters
        self.char = [None for i in range( 256 ) ]
        for c in range( 256 ):
            self.char[ c ] = self._charMap( chr(c), font )
        self.char = tuple( self.char )
        self.lw = self.char[ ord('0') ][1]
        self.lh = self.char[ ord('0') ][2]

    def initWindow( self, title ):
        """Initializes the pygame window"""
        pygame.display.set_mode( (self.wWidth, self.wHeight), View.VIDEO_FLAGS )
        pygame.display.set_caption( title )
        self.resizeGL( ( self.wWidth, self.wHeight ) )
        
    def screenToWorld( self, (x, y ) ):
        """Converts a screen-space value into a world-space value"""
        x_GL = x / float( self.wWidth ) * self.vWidth + self.vLeft
        y_GL = (1.0 - y / float( self.wHeight ) ) * self.vHeight + self.vBottom
        return x_GL, y_GL

    def initGL( self ):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClearDepth(1.0)
        glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )
        
    def resizeGL( self, size ):
        self.wWidth, self.wHeight = size
        if self.wHeight == 0:
            self.wHeight = 1

        glViewport(0, 0, self.wWidth, self.wHeight)
        pygame.display.set_mode( (self.wWidth, self.wHeight), View.VIDEO_FLAGS )
        centerX = self.vLeft + 0.5 * self.vWidth
        centerY = self.vBottom + 0.5 * self.vHeight
        self.vWidth =  self.wWidth * self.pixelSize
        self.vHeight = self.wHeight * self.pixelSize
        self.vLeft = centerX - 0.5 * self.vWidth
        self.vBottom = centerY - 0.5 * self.vHeight
        self.initGL()
        self._setOrtho()

    def select( self, x, y, selectable, selectEdges=False ):
        self._setOrtho( True, x, y )
        
        glSelectBuffer( 512L )
        glRenderMode( GL_SELECT )
            
        glInitNames()
        glPushName( 0 )

        selectable.drawGL( True, selectEdges )
        hits = list(glRenderMode( GL_RENDER ) )
        glMatrixMode( GL_PROJECTION )
        glPopMatrix()
        glMatrixMode( GL_MODELVIEW )
        return self._closestHit( hits )

    def _closestHit( self, buffer ):
        closest = -1
        if ( len(buffer) == 1):
            closest = buffer[0][2][0]
        elif ( len( buffer ) > 1 ):
            closestDist = buffer[0][0]
            closest = buffer[0][2][0]
            for hit in buffer[1:]:
                testDist = hit[0]
                if ( testDist < closestDist ):
                    closest = hit[2][0]
        return closest    

    def _setOrtho( self, select=False, x=None, y=None ):
        self.pixelSize = self.vWidth / float( self.wWidth )
        glMatrixMode( GL_PROJECTION )
        if ( select ):
            SEL_WINDOW = 9
            glPushMatrix()        
            glLoadIdentity()
            viewport = glGetIntegerv( GL_VIEWPORT )
            gluPickMatrix( x, viewport[3] - y, SEL_WINDOW, SEL_WINDOW, viewport )
        else:
            glLoadIdentity()
        glOrtho( self.vLeft, self.vLeft + self.vWidth, self.vBottom, self.vBottom + self.vHeight, -1, 1 )
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()        

    # view controls
    def changeViewWidth( self, delta ):
        self.vWidth += delta
        self._setOrtho()

    def zoomIn( self, center, pct = 0.10 ):
        """Zooms the view in around the center (in screen coords)"""
        # "zooming in" means that a pixel should be 1 + pct times larger than before
        x, y = self.screenToWorld( center )
        
        self.pixelSize *= 1.0 + pct
        viewScale = 1.0 - pct
        self.vWidth *= viewScale
        self.vHeight *= viewScale
        self.vLeft = x - ( center[0] / float( self.wWidth) * self.vWidth )
        self.vBottom = y - ( 1.0 - center[1] / float( self.wHeight) ) * self.vHeight
        self._setOrtho()
        x1, y1 = self.screenToWorld( center )

    def zoomOut( self, center, pct = 0.10 ):
        """Zooms the view out around the center (in screen coords)"""
        # "zooming out" means that a pixel should be 1 - pct times the original size
        x, y = self.screenToWorld( center )
        self.pixelSize *= 1.0 - pct
        viewScale = 1.0 + pct
        self.vWidth *= viewScale
        self.vHeight *= viewScale
        self.vLeft = x - ( center[0] / float( self.wWidth) * self.vWidth )
        self.vBottom = y - ( 1.0 - center[1] / float( self.wHeight) ) * self.vHeight
        self._setOrtho()

    def windowAspectRatio( self ):
        """Returns the window's aspect ratio"""
        return float( self.wWidth ) / float( self.wHeight )
    
    def zoomRectangle( self, rect ):
        """Zooms in based on the given rectangle"""
        rAR = rect.aspectRatio()
        wAR = self.windowAspectRatio()
        if ( rAR > wAR ):
            self.vLeft = rect.left
            self.vWidth = rect.width()
            self.vHeight = self.vWidth / wAR
            self.vBottom = rect.bottom - ( self.vHeight - rect.height() ) * 0.5
        elif ( rAR < wAR ):
            self.vBottom = rect.bottom
            self.vHeight = rect.height()
            self.vWidth = self.vHeight * wAR
            self.vLeft = rect.left - ( self.vWidth - rect.width() ) * 0.5
        else:
            self.vLeft = rect.left
            self.vWidth = rect.width()
            self.vBottom = rect.bottom
            self.vHeight = rect.height()
        self._setOrtho()

    def startPan( self ):
        self.vLeftOld = self.vLeft
        self.vBottomOld = self.vBottom

    def pan( self, (dX, dY) ):
        """Pans the view -- the offset is in world space"""
        self.vLeft = self.vLeftOld + dX
        self.vBottom = self.vBottomOld + dY
        self._setOrtho()

    def cancelPan( self ):
        self.vLeft = self.vLeftOld
        self.vBottom = self.vBottomOld
        self._setOrtho()

    def _charMap(self, c, font):
        try:
            letter_render = font.render(c, True, (255,255,255), (0, 0, 0, 64 ))
            letter = pygame.image.tostring(letter_render, 'RGBA', 1)
            letter_w, letter_h = letter_render.get_size()
        except:
            letter = None
            letter_w = 0
            letter_h = 0
        return (letter, letter_w, letter_h)
    
    def printText( self, txt, pos ):
        """Prints text at the given screen coordinates"""
        # set up screen coords
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0.0, self.wWidth - 1.0, 0.0, self.wHeight - 1.0, -1.0, 1.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        length = len( txt )
        x, y = pos
        i = 0
        lx = 0
        while ( i < length ):
            glRasterPos2i( x + lx, y )
            ch = self.char[ ord( txt[ i ] ) ]
            glDrawPixels( ch[1], ch[2], GL_RGBA, GL_UNSIGNED_BYTE, ch[0] )
            lx += ch[1]
            i += 1
               
        glMatrixMode( GL_PROJECTION )
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
##    def drawSubImg( self ):
##        global SUB_IMG
##        if ( SUB_IMG != None ):
##            glMatrixMode(GL_PROJECTION)
##            glPushMatrix()
##            glLoadIdentity()
##            glOrtho(0.0, self.wWidth - 1.0, 0.0, self.wHeight - 1.0, -1.0, 1.0)
##            glMatrixMode(GL_MODELVIEW)
##            glLoadIdentity()
##
##            x, y = ( 10, 10 )
##            glRasterPos2i( x, y )
##            w, h = SUB_IMG.get_size()
##            glDrawPixels( w, h, GL_RGBA, GL_UNSIGNED_BYTE, pygame.image.tostring( SUB_IMG, 'RGBA', 1 ) )
##                   
##            glMatrixMode( GL_PROJECTION )
##            glPopMatrix()
##            glMatrixMode(GL_MODELVIEW)
            


def handleKey( event, view, graph, obstacles, agents ):
    global editState
    mods = pygame.key.get_mods()
    hasShift = mods & pygame.KMOD_SHIFT
    hasCtrl = mods & pygame.KMOD_CTRL
    hasAlt = mods & pygame.KMOD_ALT
    redraw = False
    if ( event.type == pygame.KEYDOWN ):
        if ( event.key == pygame.K_p ):
            print graph
        elif ( event.key == pygame.K_s ):
            if ( editState == GRAPH_EDIT ):
                f = open('graph.txt', 'w' )
                f.write( '%s\n' % graph )
                f.close()
            elif ( editState == OBSTACLE_EDIT ):
                f = open('obstacles.txt', 'w' )
                f.write( '%s' % obstacles.sjguy() )
                f.close()
            elif ( editState == AGENT_EDIT ):
                f = open('positions.txt', 'w' )
                f.write( '%s' % agents.sjguy() )
                f.close()
        elif ( event.key == pygame.K_e ):
            editState = ( editState + 1 ) % EDIT_STATE_COUNT
            redraw = True
        elif ( event.key == pygame.K_DELETE ):
            if ( editState == GRAPH_EDIT ):
                if ( graph.fromID != None ):
                    graph.deleteVertex( graph.fromID )
                    graph.fromID = None
                    redraw = True
                elif ( graph.activeEdge != None ):
                    graph.deleteEdge( graph.activeEdge )
                    graph.activeEdge = None
                    redraw = True
            if ( editState == AGENT_EDIT ):
                redraw = agents.deleteActiveAgent()
    return redraw

## data for handling mouse events
downX = 0
downY = 0
dragging = False
downPos = None
edgeDir = None

# dragging parameters
NO_DRAG = 0
RECT = 1
PAN = 2
EDGE = 3
MOVE = 4
TEST = 5    # state to test various crap

# mouse buttons
LEFT = 1
MIDDLE = 2
RIGHT = 3
WHEEL_UP = 4
WHEEL_DOWN = 5

def handleMouse( event, view, graph, obstacles, agents ):
    """Handles mouse events -- returns a boolean -- whether the view needs to redraw"""
    global downX, downY, dragging, downPos, edgeDir#, ZOOM_RECT
    mods = pygame.key.get_mods()
    hasCtrl = mods & pygame.KMOD_CTRL
    hasAlt = mods & pygame.KMOD_ALT
    hasShift = mods & pygame.KMOD_SHIFT
    redraw = False
    if (event.type == pygame.MOUSEMOTION ):
        if ( dragging == RECT):
            pass
        elif ( dragging == PAN ):
            dX, dY = view.screenToWorld( ( downX, downY ) )
            pX, pY = view.screenToWorld( event.pos )
            view.pan( (dX - pX, dY - pY) )
            redraw = True
        elif ( dragging == EDGE ):
            pX, pY = event.pos 
            selected = view.select( pX, pY, graph )
            selVert = graph.vertices[ selected ]
            if ( selected != -1 and selVert != graph.fromID  ):
                graph.toID = selVert
                graph.testEdge.end = selVert
                redraw = True
        elif ( dragging == MOVE ):
            dX, dY = view.screenToWorld( ( downX, downY ) )
            pX, pY = view.screenToWorld( event.pos )
            newX = downPos[0] + ( pX - dX )
            newY = downPos[1] + ( pY - dY )
            if ( editState == GRAPH_EDIT ):
                graph.fromID.setPosition( (newX, newY ) )
            elif ( editState == OBSTACLE_EDIT ):
                if ( obstacles.activeVert ):
                    obstacles.activeVert.x = newX
                    obstacles.activeVert.y = newY
                elif ( obstacles.activeEdge ):
                    v1, v2 = obstacles.activeEdge
                    v1.x = newX
                    v1.y = newY
                    v2.x = v1.x + edgeDir[0]
                    v2.y = v1.y + edgeDir[1]
            elif ( editState == AGENT_EDIT ):
                if ( agents.activeAgent ):
                    agents.activeAgent.setActivePos( (newX, newY ) )
            redraw = True
        else:
            pX, pY = event.pos
            if ( editState == GRAPH_EDIT ):
                selected = view.select( pX, pY, graph, hasShift )
                if ( selected == -1 ):
                    graph.activeEdge = None
                    graph.fromID = graph.toID = None
                    redraw = True
                else:
                    if ( hasShift ):
                        selEdge = graph.edges[ selected ]
                        graph.fromID = graph.toID = None
                        # select edges
                        if ( selEdge != graph.activeEdge ):
                            graph.activeEdge = selEdge
                            redraw = True
                    else:
                        graph.activeEdge = None
                        selVert = graph.vertices[ selected ]
                        if ( graph.fromID != selVert ):
                            redraw = True
                            graph.fromID = selVert
            elif ( editState == OBSTACLE_EDIT ):
                selected = view.select( pX, pY, obstacles, hasShift )
                if ( selected == -1 ):
                    obstacles.activeEdge = None
                    obstacles.activeVert = None
                    redraw = True
                else:
                    if ( hasShift ):
                        selEdge = obstacles.selectEdge( selected )
                        obstacles.activeVert = None
                        # select edges
                        if ( selEdge != obstacles.activeEdge ):
                            obstacles.activeEdge = selEdge
                            redraw = True
                    else:
                        obstacles.activeEdge = None
                        selVert = obstacles.selectVertex( selected )
                        if ( selVert != obstacles.activeVert ):
                            obstacles.activeVert = selVert
                            redraw = True
            elif ( editState == AGENT_EDIT ):
                selected = view.select( pX, pY, agents, hasShift )
                    
                if ( selected == -1 ):
                    if ( agents.activeAgent ):
                        agents.activeAgent.deactivate()
                    agents.activeAgent = None
                    redraw = True
                else:
                    selAgt = agents.selectAgent( selected )
                    if ( selAgt != agents.activeAgent ):
                        if ( agents.activeAgent ):
                            agents.activeAgent.deactivate()
                        agents.activeAgent = selAgt
                        redraw = True
            
    elif ( event.type == pygame.MOUSEBUTTONUP ):
        if ( event.button == LEFT ):
            if ( dragging == RECT ):
                pass
##                view.zoomRectangle( ZOOM_RECT )
##                ZOOM_RECT.hide()
##                redraw = True
        elif ( event.button == MIDDLE and dragging == EDGE ):
            if ( graph.testEdge.isValid() ):
                graph.addEdge( graph.testEdge )
                graph.fromID = graph.toID
                graph.toID = None
                graph.testEdge.clear()
                redraw = True
        dragging = NO_DRAG
    elif ( event.type == pygame.MOUSEBUTTONDOWN ):
        if ( event.button == LEFT ):
            downX, downY = event.pos
            if ( hasCtrl ):
                view.startPan()
                dragging = PAN
            else:
                if ( editState == GRAPH_EDIT ):
                    if ( graph.fromID != None ):
                        downPos = ( graph.fromID.pos[0], graph.fromID.pos[1] )
                        dragging = MOVE
                    else:
                        p = view.screenToWorld( event.pos )
                        graph.addVertex( p )
                        graph.fromID = graph.lastVertex()
                        redraw = True
                elif( editState == OBSTACLE_EDIT ):
                    if ( obstacles.activeVert != None ):
                        downPos = ( obstacles.activeVert.x, obstacles.activeVert.y )
                        dragging = MOVE
                    elif ( obstacles.activeEdge != None ):
                        v1, v2 = obstacles.activeEdge
                        downPos = ( v1.x, v1.y )
                        edgeDir = ( v2.x - v1.x, v2.y - v1.y )
                        dragging = MOVE
                elif ( editState == AGENT_EDIT ):
                    if ( agents.activeAgent ):
                        downPos = agents.activeAgent.getActivePos()
                        dragging = MOVE
                    else:
                        p = view.screenToWorld( event.pos )
                        downPos = p
                        agents.addAgent( p, p )
                        agents.selectLastGoal()
                        dragging = MOVE
                        redraw = True
                
##            elif ( hasAlt ):
##                dragging = RECT
##            else:
##                if ( currMarker != None ):
##                    dragging = MOVE
##                    markers[ currMarker ].startMove()
        elif ( event.button == RIGHT ):
            if ( dragging == RECT ):
                pass
##                ZOOM_RECT.hide()
            elif ( dragging == MOVE ):
                if ( editState == GRAPH_EDIT ):
                    graph.fromID.setPosition( downPos )
                elif ( editState == OBSTACLE_EDIT ):
                    if ( obstacles.activeVert ):
                        obstacles.activeVert.x = downPos[0]
                        obstacles.activeVert.y = downPos[1]
                    elif ( obstacles.activeEdge ):
                        v1, v2 = obstacles.activeEdge
                        v1.x = downPos[0]
                        v1.y = downPos[1]
                        v2.x = v1.x + edgeDir[0]
                        v2.y = v1.y + edgeDir[1]
                elif ( editState == AGENT_EDIT ):
                    if ( agents.activeAgent ):
                        agents.activeAgent.setActivePos( downPos )
                redraw = True
            elif ( dragging == PAN ):
                view.cancelPan()
            elif ( dragging == EDGE ):
                graph.fromID = graph.toID = None
                graph.testEdge.clear()
                redraw = True
            dragging = NO_DRAG
        elif ( event.button == WHEEL_UP ):
            view.zoomIn( event.pos )
            redraw = True
        elif ( event.button == WHEEL_DOWN ):
            view.zoomOut( event.pos )
            redraw = True
        elif ( event.button == MIDDLE ):
            downX, downY = event.pos
            if ( graph.fromID == None ):
                p = view.screenToWorld( event.pos )
                graph.addVertex( p )
                graph.fromID = graph.lastVertex()
                redraw = True
            graph.testEdge.start = graph.fromID
            dragging = EDGE
    return redraw

def drawGL( view, obstacles=None, graph=None, agents=None ):
    glClear( GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT )
    if ( obstacles ):
        obstacles.drawGL( editable=(editState == OBSTACLE_EDIT ) )
    if ( graph ):
        graph.drawGL( editable=(editState == GRAPH_EDIT) )
    if ( agents ):
        agents.drawGL( editable=(editState == AGENT_EDIT ) )
        
## BASIC USAGE
def updateMsg( agtCount ):
    if ( editState == NO_EDIT ):
        return "Hit the 'e' key to enter edit mode."
    elif ( editState == GRAPH_EDIT ):
        return "Edit roadmap"
    elif ( editState == OBSTACLE_EDIT ):
        return "Edit obstacle"
    elif ( editState == AGENT_EDIT ):
        return "Edit agents: %d" % agtCount
    else:
        return "Invalid edit state"

##    global currImg, imgCount, currMarker, markerCount
##    msg = "Frame %d of %d" % ( currImg + 1, imgCount )
##    if ( markerCount > 1 ):
##        if ( currMarker != None ):
##            msg += "\nMarker %d of %d" % ( currMarker + 1, markerCount )
##        else:
##            msg += "\nNo marker active"
##    return msg

def message( view, txt ):
    msgs = txt.split( '\n' )
    x = 10
    y = view.wHeight - 10 - view.lh
    for m in msgs:
        view.printText( m, (x, y ) )
        y -= view.lh
        
def writeRoadmap():
    pass

def usage():
    print "roadmapBuilder <-obst obstFile.xml> <-agt agtFile.txt> <-graph graphFile.txt> <-field fieldFile.txt>"
    print "  Edit configuration for crowd simulation"
    print "  Options (all are optional):"
    print "    -obst obstFile.xml     - load the obstacle description from the xml file obstFile.xml"
    print "    -agt agtFile.txt       - load the agent definitions from the agent description file."
    print "    -graph graphFile.txt   - load a roadmap definition from graphFile.txt"
    print "    -field fieldFile.txt   - load a vector field.  If none is given a default vector field is generated"
    

def main():
    from commandline import SimpleParamManager

    try:
        pMan = SimpleParamManager( sys.argv[1:], {'obst':'', 'agt':'', 'graph':'', 'field':'' } )
    except IOError:
        usage()

    obstName = pMan[ 'obst' ]
    agtName = pMan[ 'agt' ]
    graphName = pMan[ 'graph' ]
    fieldName = pMan[ 'field' ]
    if ( obstName ):
        obstacles, bb = readObstacles( sys.argv[1] )
    else:
        obstacles = ObstacleSet()
        bb = AABB()
        bb.min = Vector3( -100, -100, 0 )
        bb.max = Vector3( 100, 100, 0 )

    agents = AgentSet( 0.25 )
    if ( agtName ):
        agents.initFromFile( sys.argv[2] )
    

    graph = Graph()
    if ( graphName ):
        graph.initFromFile( sys.argv[3] )

    # create viewer
    pygame.init()
    fontname = pygame.font.get_default_font()
    font = pygame.font.Font( fontname, 18 )

    w = bb.max.x - bb.min.x
    h = bb.max.y - bb.min.y
    view = View( (w,h), (bb.min.x, bb.min.y), (w,h), (bb.min.x, bb.min.y), (800, 600), font )
    view.initWindow( 'Create roadmap' )
    pygame.key.set_repeat( 250, 10 )
    view.initGL()
    

    redraw = True
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            elif (event.type == pygame.MOUSEMOTION or event.type == pygame.MOUSEBUTTONUP or
                  event.type == pygame.MOUSEBUTTONDOWN ):
                redraw |= handleMouse( event, view, graph, obstacles, agents )
            elif ( event.type == pygame.KEYDOWN or event.type == pygame.KEYUP ):
                redraw |= handleKey( event, view, graph, obstacles, agents  )
            elif ( event.type == pygame.VIDEORESIZE ):
                view.resizeGL( event.size )
                redraw |= True
            elif ( event.type == pygame.VIDEOEXPOSE ):
                redraw |= True
        if ( redraw ):
            drawGL( view, obstacles, graph, agents )
            message( view, updateMsg( agents.count() ) )
            pygame.display.flip()
            redraw = False
    writeRoadmap()    

if __name__ == '__main__':
    main()