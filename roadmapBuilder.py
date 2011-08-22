import sys, pygame
from math import sqrt, cos, sin, pi

from OpenGL.GL import *
from OpenGL.GLU import *
from primitives import Vector3
from vField import GLVectorField
from obstacles import *
from view import View

# contexts
from RoadContext import ContextSwitcher, AgentContext, FieldEditContext, SCBContext
from Context import ContextResult



NO_EDIT = 0
GRAPH_EDIT = 1
OBSTACLE_EDIT = 2
EDIT_STATE_COUNT = 3
editState = NO_EDIT

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
        self.editable = False

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

    def drawGL( self, select=False, dummy=None ):
        glPushAttrib( GL_POLYGON_BIT )
        glPolygonMode( GL_FRONT_AND_BACK, GL_FILL )
        for agent in self.agents:
            agent.drawGL( select, self.editable )
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


def handleKey( event, context, view, graph, obstacles, agents, field ):
    global editState
    result = ContextResult()
    if ( context ):
        result = context.handleKeyboard( event, view )
        if ( result.isHandled() ):
            return result
        
    mods = pygame.key.get_mods()
    hasShift = mods & pygame.KMOD_SHIFT
    hasCtrl = mods & pygame.KMOD_CTRL
    hasAlt = mods & pygame.KMOD_ALT

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
        elif ( event.key == pygame.K_e ):
            editState = ( editState + 1 ) % EDIT_STATE_COUNT
            result.setNeedsRedraw( True )
        elif ( event.key == pygame.K_DELETE ):
            if ( editState == GRAPH_EDIT ):
                if ( graph.fromID != None ):
                    graph.deleteVertex( graph.fromID )
                    graph.fromID = None
                    result.setNeedsRedraw( True )
                elif ( graph.activeEdge != None ):
                    graph.deleteEdge( graph.activeEdge )
                    graph.activeEdge = None
                    result.setNeedsRedraw( True )
    return result

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

def handleMouse( event, context, view, graph, obstacles, agents, field ):
    """Handles mouse events -- returns a boolean -- whether the view needs to redraw"""
    result = ContextResult()
    if ( context ):
        result = context.handleMouse( event, view )
        if ( result.isHandled() ):
            return result
    global downX, downY, dragging, downPos, edgeDir#, ZOOM_RECT
    mods = pygame.key.get_mods()
    hasCtrl = mods & pygame.KMOD_CTRL
    hasAlt = mods & pygame.KMOD_ALT
    hasShift = mods & pygame.KMOD_SHIFT
    
    if (event.type == pygame.MOUSEMOTION ):
        if ( dragging == RECT):
            pass
        elif ( dragging == PAN ):
            dX, dY = view.screenToWorld( ( downX, downY ) )
            pX, pY = view.screenToWorld( event.pos )
            view.pan( (dX - pX, dY - pY) )
            result.setNeedsRedraw( True )
        elif ( dragging == EDGE ):
            pX, pY = event.pos 
            selected = view.select( pX, pY, graph )
            selVert = graph.vertices[ selected ]
            if ( selected != -1 and selVert != graph.fromID  ):
                graph.toID = selVert
                graph.testEdge.end = selVert
                result.setNeedsRedraw( True )
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
            result.setNeedsRedraw( True )
        else:
            pX, pY = event.pos
            if ( editState == GRAPH_EDIT ):
                selected = view.select( pX, pY, graph, hasShift )
                if ( selected == -1 ):
                    graph.activeEdge = None
                    graph.fromID = graph.toID = None
                    result.setNeedsRedraw( True )
                else:
                    if ( hasShift ):
                        selEdge = graph.edges[ selected ]
                        graph.fromID = graph.toID = None
                        # select edges
                        if ( selEdge != graph.activeEdge ):
                            graph.activeEdge = selEdge
                            result.setNeedsRedraw( True )
                    else:
                        graph.activeEdge = None
                        selVert = graph.vertices[ selected ]
                        if ( graph.fromID != selVert ):
                            result.setNeedsRedraw( True )
                            graph.fromID = selVert
            elif ( editState == OBSTACLE_EDIT ):
                selected = view.select( pX, pY, obstacles, hasShift )
                if ( selected == -1 ):
                    obstacles.activeEdge = None
                    obstacles.activeVert = None
                    result.setNeedsRedraw( True )
                else:
                    if ( hasShift ):
                        selEdge = obstacles.selectEdge( selected )
                        obstacles.activeVert = None
                        # select edges
                        if ( selEdge != obstacles.activeEdge ):
                            obstacles.activeEdge = selEdge
                            result.setNeedsRedraw( True )
                    else:
                        obstacles.activeEdge = None
                        selVert = obstacles.selectVertex( selected )
                        if ( selVert != obstacles.activeVert ):
                            obstacles.activeVert = selVert
                            result.setNeedsRedraw( True )
    elif ( event.type == pygame.MOUSEBUTTONUP ):
        if ( event.button == LEFT ):
            if ( dragging == RECT ):
                pass
##                view.zoomRectangle( ZOOM_RECT )
##                ZOOM_RECT.hide()
##                result.setNeedsRedraw( True )
        elif ( event.button == MIDDLE and dragging == EDGE ):
            if ( graph.testEdge.isValid() ):
                graph.addEdge( graph.testEdge )
                graph.fromID = graph.toID
                graph.toID = None
                graph.testEdge.clear()
                result.setNeedsRedraw( True )
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
                        result.setNeedsRedraw( True )
                elif( editState == OBSTACLE_EDIT ):
                    if ( obstacles.activeVert != None ):
                        downPos = ( obstacles.activeVert.x, obstacles.activeVert.y )
                        dragging = MOVE
                    elif ( obstacles.activeEdge != None ):
                        v1, v2 = obstacles.activeEdge
                        downPos = ( v1.x, v1.y )
                        edgeDir = ( v2.x - v1.x, v2.y - v1.y )
                        dragging = MOVE
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
                result.setNeedsRedraw( True )
            elif ( dragging == PAN ):
                view.cancelPan()
            elif ( dragging == EDGE ):
                graph.fromID = graph.toID = None
                graph.testEdge.clear()
                result.setNeedsRedraw( True )
            dragging = NO_DRAG
        elif ( event.button == WHEEL_UP ):
            view.zoomIn( event.pos )
            result.setNeedsRedraw( True )
        elif ( event.button == WHEEL_DOWN ):
            view.zoomOut( event.pos )
            result.setNeedsRedraw( True )
        elif ( event.button == MIDDLE ):
            downX, downY = event.pos
            if ( graph.fromID == None ):
                p = view.screenToWorld( event.pos )
                graph.addVertex( p )
                graph.fromID = graph.lastVertex()
                result.setNeedsRedraw( True )
            graph.testEdge.start = graph.fromID
            dragging = EDGE
    return result

def drawGL( view, context=None, obstacles=None, graph=None, agents=None, field=None ):
    glClear( GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT )
    if ( field ):
        field.drawGL()
    if ( obstacles ):
        obstacles.drawGL( editable=(editState == OBSTACLE_EDIT ) )
    if ( graph ):
        graph.drawGL( editable=(editState == GRAPH_EDIT) )
    if ( agents ):
        agents.drawGL()
    if ( context ):
        context.drawGL( view )
        
## BASIC USAGE
def updateMsg( agtCount ):
    if ( editState == NO_EDIT ):
        return "Hit the 'e' key to enter edit mode."
    elif ( editState == GRAPH_EDIT ):
        return "Edit roadmap"
    elif ( editState == OBSTACLE_EDIT ):
        return "Edit obstacle"
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

def main():
    import optparse
    parser = optparse.OptionParser()
    parser.add_option( "-g", "--graph", help="Optional graph file to load",
                       action="store", dest="graphName", default='' )
    parser.add_option( "-o", "--obstacle", help="Optional obstacle file to load.",
                       action="store", dest='obstName', default='' )
    parser.add_option( "-a", "--agent", help="Optional agent position file to load.",
                       action="store", dest='agtName', default='' )
    parser.add_option( "-f", "--field", help="Optional vector field file to load.",
                       action="store", dest='fieldName', default='' )
    parser.add_option( "-s", "--scb", help="Optional scb file to load.",
                       action="store", dest='scbName', default='' )
    options, args = parser.parse_args()

    obstName = options.obstName
    agtName = options.agtName
    graphName = options.graphName
    fieldName = options.fieldName
    scbName = options.scbName
    print "Arguments:"
    print "\tobstacles:", obstName
    print "\tagents:   ", agtName
    print "\tgraph:    ", graphName
    print "\tfield:    ", fieldName
    print "\tscbName:  ", scbName
    if ( obstName ):
        obstacles, bb = readObstacles( obstName )
    else:
        obstacles = ObstacleSet()
        bb = AABB()
        bb.min = Vector3( -100, -100, 0 )
        bb.max = Vector3( 100, 100, 0 )

    agents = AgentSet( 0.25 )
    if ( agtName ):
        agents.initFromFile( sys.argv[2] )

    if ( fieldName ):
        field = GLVectorField( (0,0), (1, 1), 1 )
        field.read( fieldName )
    else:
        print "Instantiate vector field from geometry:", bb
        bbSize = bb.max - bb.min    
        field = GLVectorField( ( bb.min.x, bb.min.y ), ( bbSize.x, bbSize.y ), 2.0 )
    
    graph = Graph()
    if ( graphName ):
        graph.initFromFile( graphName )

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

    field.newGLContext()
##    field = None

    context = ContextSwitcher()
    context.addContext( AgentContext( agents ), pygame.K_a )
    context.addContext( FieldEditContext( field ), pygame.K_f )
    context.addContext( SCBContext( scbName ), pygame.K_s )
    context.newGLContext()

    redraw = True
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            elif (event.type == pygame.MOUSEMOTION or event.type == pygame.MOUSEBUTTONUP or
                  event.type == pygame.MOUSEBUTTONDOWN ):
                result = handleMouse( event, context, view, graph, obstacles, agents, field )
                redraw |= result.needsRedraw()
            elif ( event.type == pygame.KEYDOWN or event.type == pygame.KEYUP ):
                result = handleKey( event, context, view, graph, obstacles, agents, field  )
                redraw |= result.needsRedraw()
            elif ( event.type == pygame.VIDEORESIZE ):
                view.resizeGL( event.size )
                field.newGLContext()
                context.newGLContext()
                redraw |= True
            elif ( event.type == pygame.VIDEOEXPOSE ):
                redraw |= True
        if ( redraw ):
            drawGL( view, context, obstacles, graph, agents, field )
            message( view, updateMsg( agents.count() ) )
            pygame.display.flip()
            redraw = False
    writeRoadmap()    

if __name__ == '__main__':
    main()