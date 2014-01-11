import sys, pygame

from OpenGL.GL import *
from OpenGL.GLU import *
from primitives import Vector3
from view import View
import paths
import os

# editable entities
from agent import *
from graph import *
from obstacles import *
from vField import GLVectorField

# contexts
from RoadContext import ContextSwitcher, AgentContext, FieldEditContext, SCBContext, PositionContext, ObstacleContext
from GoalContext import GoalContext
from GoalEditor import GoalEditor
import Goals
from Context import ContextResult

NO_EDIT = 0
GRAPH_EDIT = 1
EDIT_STATE_COUNT = 2
editState = NO_EDIT

def handleKey( event, context, view, theGraph, obstacles, agents, field ):
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
            print theGraph
        elif ( event.key == pygame.K_s and hasCtrl ):
            if ( editState == GRAPH_EDIT ):
                fileName = paths.getPath( 'graph.txt', False )
                f = open( fileName, 'w' )
                f.write( '%s\n' % theGraph.newAscii() )
                f.close()
                print "Graph saved!", fileName
        elif ( event.key == pygame.K_e ):
            editState = ( editState + 1 ) % EDIT_STATE_COUNT
            result.setNeedsRedraw( True )
        elif ( event.key == pygame.K_DELETE ):
            if ( editState == GRAPH_EDIT ):
                if ( theGraph.fromID != None ):
                    theGraph.deleteVertex( theGraph.fromID )
                    theGraph.fromID = None
                    result.setNeedsRedraw( True )
                elif ( theGraph.activeEdge != None ):
                    theGraph.deleteEdge( theGraph.activeEdge )
                    theGraph.activeEdge = None
                    result.setNeedsRedraw( True )
        elif ( hasAlt and event.key == pygame.K_F4 ):
            raise Exception
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
ZOOM = 5
TEST = 6    # state to test various crap

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
        elif ( dragging == ZOOM ):
            dy = downY - event.pos[1]
            view.zoom( dy )
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
            elif ( hasShift ):
                view.startZoom( event.pos )
                dragging = ZOOM
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
                result.setNeedsRedraw( True )
            elif ( dragging == PAN ):
                view.cancelPan()
                result.setNeedsRedraw( True )
            elif ( dragging == ZOOM ):
                view.cancelZoom()
                result.setNeedsRedraw( True )
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
            if ( editState == GRAPH_EDIT and graph.fromID == None ):
                p = view.screenToWorld( event.pos )
                graph.addVertex( p )
                graph.fromID = graph.lastVertex()
                result.setNeedsRedraw( True )
            graph.testEdge.start = graph.fromID
            dragging = EDGE
    return result

def drawGL( view, context=None, obstacles=None, graph=None, agents=None, field=None, goalVis=None ):
    glClear( GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT )
    if ( field ):
        field.drawGL()
    if ( goalVis ):
        goalVis.drawGL()
    if ( obstacles ):
        obstacles.drawGL()
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
    parser.add_option( "-r", "--roadmap", help="Optional roadmap file to load",
                       action="store", dest="roadmapName", default='' )
    parser.add_option( "-g", "--goals", help="Optional goal definition file to load",
                       action="store", dest="goalsName", default='' )
    parser.add_option( "-b", "--obstacle", help="Optional obstacle file to load.",
                       action="store", dest='obstName', default='' )
    parser.add_option( "-a", "--agent", help="Optional agent position file to load.",
                       action="store", dest='agtName', default='' )
    parser.add_option( "-f", "--field", help="Optional vector field file to load.",
                       action="store", dest='fieldName', default='' )
    parser.add_option( "-c", "--createField", help='Creates a field based on the domain of the obstacles - ignored if --field(-f) is specified',
                       action='store_true', dest='createField', default=False )
    parser.add_option( "-s", "--scb", help="Optional scb file to load.",
                       action="store", dest='scbName', default='' )
    parser.add_option( "-i", "--inDir", help="Optional directory to find input files - only applied to file names with relative paths",
                       action="store", dest='inDir', default='.' )
    parser.add_option( "-o", "--outDir", help="Optional directory to write output files - only applied to file names with relative paths",
                       action="store", dest='outDir', default='.' )
    parser.add_option( '--region', help='Specify the bounding region of the action.  If provided, it will set the initial camera properties.  Format is minX minY maxX maxY',
                       nargs=4, type='float', dest='boundRegion', default=None )
    options, args = parser.parse_args()

    paths.setInDir( options.inDir )
    paths.setOutDir( options.outDir )
    obstName = paths.getPath( options.obstName )
    agtName = paths.getPath( options.agtName )
    roadmapName = paths.getPath( options.roadmapName )
    fieldName = paths.getPath( options.fieldName )
    scbName = paths.getPath( options.scbName )
    goalsName = paths.getPath( options.goalsName )
    print "Arguments:"
    print "\tInput dir: ", options.inDir
    print "\tOutput dir:", options.outDir
    print "\tobstacles: ", obstName
    print "\tagents:    ", agtName
    print "\troad map:  ", roadmapName
    print "\tfield:     ", fieldName
    print "\tscbName:   ", scbName
    print "\tGoals:     ", goalsName
    if ( obstName ):
        obstacles, bb = readObstacles( obstName )
    else:
        obstacles = ObstacleSet()
        bb = AABB()
        if ( not options.boundRegion is None ):
            bb.min = Vector3( options.boundRegion[0], options.boundRegion[1], 0 )
            bb.max = Vector3( options.boundRegion[2], options.boundRegion[3], 0 )
            print bb
        else:
            bb.min = Vector3( -100, -100, 0 )
            bb.max = Vector3( 100, 100, 0 )

    agents = AgentSet( 0.23 )
    if ( agtName ):
        agents.initFromFile( agtName )
        if ( scbName != '' ):
            # This reads the agent radius from the file, but no longer visualizes the agents
            # This is a bit of a hack.  It would be better to simply disable drawing the
            #   agents when the scb playback context is active.  But I don't have the time
            #   to figure out an elegant solution to this.
            agents.clear()

    if ( fieldName ):
        field = GLVectorField( (0,0), (1, 1), 1 )
        field.read( fieldName )
    elif ( options.createField ):
        print "Instantiate vector field from geometry:", bb
        bbSize = bb.max - bb.min    
        field = GLVectorField( ( bb.min.x, bb.min.y ), ( bbSize.y, bbSize.x ), 2.0 )
    else:
        field = None
    
    graph = Graph()
    if ( roadmapName ):
        graph.initFromFile( roadmapName )

    # create viewer
    pygame.init()
    fontname = pygame.font.get_default_font()
    font = pygame.font.Font( fontname, 12 )

    w = bb.max.x - bb.min.x
    h = bb.max.y - bb.min.y
    view = View( (w,h), (bb.min.x, bb.min.y), (w,h), (bb.min.x, bb.min.y), (800, 600), font )
    view.HELP_TEXT = 'View controls:' + \
                     '\n\tpan - Ctrl + left mouse button' + \
                     '\n\tzoom in - mouse wheel up' + \
                     '\n\tzoom out - mouse wheel down' + \
                     '\n\tzoom - Shift + left mouse button (up and down)'
    view.initWindow( 'Create roadmap' )
    pygame.key.set_repeat( 250, 10 )
    view.initGL()

    if ( field ):
        field.newGLContext()
##    field = None

    # load goals
    if ( goalsName ):
        try:
            goalSets = Goals.readGoals( goalsName )
        except ValueError as e:
            print "Error parsing goals:", str(e)
            print "\tUsing empty GoalSet"
            goalSets = [Goals.GoalSet()]
    else:
        goalSets = [Goals.GoalSet()]
    goalVis = GoalEditor( goalSets )

    context = ContextSwitcher()
    context.addContext( PositionContext(), pygame.K_q )
    context.addContext( GoalContext( goalVis ), pygame.K_g )
    context.addContext( AgentContext( agents, obstacles ), pygame.K_a )
    context.addContext( ObstacleContext( obstacles ), pygame.K_o )
    if ( field ):
        context.addContext( FieldEditContext( field ), pygame.K_f )
    if ( scbName != '' ):
        context.addContext( SCBContext( scbName, obstacles, agents.defRadius ), pygame.K_s )
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
                try:
                    result = handleKey( event, context, view, graph, obstacles, agents, field  )
                    redraw |= result.needsRedraw()
                except Exception as e:
                    print "Error with keyboard event"
                    print "\t", e
                    running = False
            elif ( event.type == pygame.VIDEORESIZE ):
                view.resizeGL( event.size )
                if ( field ):
                    field.newGLContext()
                context.newGLContext()
                redraw |= True
            elif ( event.type == pygame.VIDEOEXPOSE ):
                redraw |= True
        if ( redraw ):
            drawGL( view, context, obstacles, graph, agents, field, goalVis )
            message( view, updateMsg( agents.count() ) )
            pygame.display.flip()
            if ( context ):
                name = context.exportDisplay()
                if ( name ):
                    pygame.image.save( view.surface, name )
            redraw = False
    writeRoadmap()    

if __name__ == '__main__':
    main()