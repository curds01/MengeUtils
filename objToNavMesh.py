# Parses an OBJ file and outputs an NavMesh file definition
#   - see navMesh.py for the definition of that file format

from ObjReader import ObjFile
from navMesh import Node, Edge, Obstacle, NavMesh
import numpy as np
from primitives import Vector2

def popEdge( e, vertMap, edges ):
    '''Removes the edge, e, from all references in the vertMap'''
    v0, v1 = edges[ e ]
    try:
        vertMap[ v0 ].pop( vertMap[ v0 ].index( e ) )
        if ( not vertMap[ v0 ] ):
            vertMap.pop( v0 )
    except ValueError:
        pass
    
    try:
        vertMap[ v1 ].pop( vertMap[ v1 ].index( e ) )
        if ( not vertMap[ v1 ] ):
            vertMap.pop( v1 )
    except ValueError:
        pass

def pushEdge( e, vertMap, edges ):
    '''Places an edge into the vertex-edge map'''
    v0, v1 = edges[ e ]
    if ( vertMap.has_key( v0 ) ):
        assert( e not in vertMap[ v0 ] )
        vertMap[ v0 ].append( e )
    else:
        vertMap[ v0 ] = [e]
        
    if ( vertMap.has_key( v1 ) ):
        assert( e not in vertMap[ v1 ] )
        vertMap[ v1 ].append( e )
    else:
        vertMap[ v1 ] = [e]

def extendEdge( e, o, edgeLoop, edges, vertMap ):
    '''Extends the obstacle, o, with the given edge, e.  The edgeLoop gets extended
    by the edge and the vertMap is modified to reflect success.

    @return: -1 - path still valid
             0 - invalid cycle created (i.e. e's final vertex in body of o
             1 - valid cycle finished.
    '''
    edgeLoop.append( e )
    popEdge( e, vertMap, edges )
    vPrev, vNext = edges[ e ]
    if ( vPrev != o[-1] ):
        tmp = vPrev
        vPrev = vNext
        vNext = tmp
        assert( vPrev == o[-1] )
    if ( vNext == o[0] ):
        # reached cycle - obstacle grown to loop
        return 1
    elif ( vNext in o ):
        # created a cycle, but not with the first vertex
        edgeLoop.pop( -1 )
        pushEdge( e, vertMap, edges )
        return 0
    else:
        o.append( vNext )
        return -1

def growObstacle( o, edgeLoop, edges, vertMap ):
    '''Given an obstacle (and the corresponding edge loop) grows the obstacle to
    a single, closed loop.

    @param o: the current obstacle (a list of vertex indices)
    @param edgeLoop: a list of edge indices.  The ith index in this list is the
        edge consisting of the ith and i+1st vertices in o.
    @param edges: the edge definitions (to which the edge indices refer)
    @param vertMap: the mapping from vertex index to edges which share it
    @return: boolean, reporting if a closed obstacle was found.        
    '''
    v = o[-1]
    if ( len( vertMap[ v ] ) == 1 ):
        # simple case -- take the only option
        e = vertMap[ v ][ 0 ]
        state = extendEdge( e, o, edgeLoop, edges, vertMap )
        if ( state == 0  ):
            return False
        elif ( state == 1 ):
            return True

        if ( growObstacle( o, edgeLoop, edges, vertMap ) ):
            return True
        else:
            # this path failed to produce a loop
            edgeLoop.pop( -1 )
            pushEdge( e, vertMap )
    else:
        for e in vertMap[ v ]:
            state = extendEdge( e, o, edgeLoop, edges, vertMap )
            if ( state == 0  ):
                return False
            elif ( state == 1 ):
                return True

            if ( growObstacle( o, edgeLoop, edges, vertMap ) ):
                return True
            else:
                # this path failed to produce a loop
                edgeLoop.pop( -1 )
                pushEdge( e, vertMap )
        return False
    
def startObstacle( vertMap, edges, obstacles ):
    '''Starts a new obstacle from the vertex-edge map.  Modifies the vertex
    map in place (by removing used data) and returns the current vertex and
    an obstacle, and, finally, adds that obstacle to the obstacles list.'''
    v = vertMap.keys()[0]
    e = vertMap[ v ][ 0 ] 
    # remove edge from vert mapping
    popEdge( e, vertMap, edges )

    o = list( edges[ e ] )
    obstacles.append( o )
    return o, e

def processObstacles( obstacles, vertObstMap, navMesh ):
    '''Given a list of Obstacle instances, connects the obstacles into sequences such that each obstacle
    points to the appropriate "next" obstacle.  Finally, sets the obstacles to the navigation mesh.'''
##    # The obstacle is simply an ordered list of vertex indices
##    #   The order depends on which side of the obstacle is free space
##    #   Counter-clockwise --> outside is freespace, clockwise --> inside is freespace
##    #   It is assumed that all obstacles are closed
##    vertMap = {}
##    for i, edge in enumerate( edges ):
##        v0, v1 = edge
##        if ( vertMap.has_key( v0 ) ):
##            vertMap[ v0 ].append( i )
##        else:
##            vertMap[ v0 ] = [ i ]
##        if ( vertMap.has_key( v1 ) ):
##            vertMap[ v1 ].append( i )
##        else:
##            vertMap[ v1 ] = [ i ]
##    # furthermore, every vertex should have an EVEN number of incident edges
##    #   Each obstacle boundary is a unique loop.  An edge in requires a unique
##    #   edge out.  The only way out of that is if a single edge was used in two
##    #   loops, which is impossible as that would require an edge connected to NO
##    #   faces (or badly constructed geometry)
##    #
##    # This implicitly catches the case where there is an open vertex (i.e.
##    #   degree == 1 --> degree is odd
##    # And I'm not testing for the case where degree is zero, because that is
##    #   impossible.  A vertex wouldn't be entered into the list if it wasn't part
##    #   of an edge
##    degrees = map( lambda x: len( x ), vertMap.values() )
##    assert( sum( map( lambda x: x % 2, degrees ) ) == 0 )
##
##    obstacles = []
##
##    while ( vertMap ):
##        o, e = startObstacle( vertMap, edges, obstacles )
##        assert( growObstacle( o, [e], edges, vertMap ) )
##
##    return obstacles
    # I'm assuming that the external edges form perfect, closed loops
    #   That means if a vertex is incident to an obstacle, then it must be incident to two and only
    #   two obstacles.  This tests that assumption
    degrees = map( lambda x: len( x ), vertObstMap.values() )
    assert( sum( map( lambda x: x % 2, degrees ) ) == 0 )

    # now connect them up
    #   - this assumes that they are all wound properly
    for vertID in vertObstMap.keys():
        o0, o1 = vertObstMap[ vertID ]
        obst0 = obstacles[ o0 ]
        obst1 = obstacles[ o1 ]
        if ( obst0.v0 == vertID ):
            obst1.next = o0
        else:
            obst0.next = o1

    # all obstacles now have a "next" obstacle
    assert( len( filter( lambda x: x.next == -1, obstacles ) ) == 0 )            
        
    navMesh.obstacles = obstacles
    

def projectVertices( vertexList ):
    '''Given 3D vertices, projects them to 2D for the navigation mesh.'''
    #TODO: Eventually the navigation mesh will require 3D data when it is no longer topologically planar
    verts = map( lambda x: (x[0], x[2]), vertexList )
    return verts

def buildNavMesh( objFile ):
    '''Given an ObjFile object, constructs the navigation mesh'''
    navMesh = NavMesh()
    V = objFile.vertSet
    navMesh.vertices = projectVertices( V )
    edges = []
    # a dicitionary mapping an edge definition to the faces that are incident to it
    #   an "edge definition" is a two tuple of ints (a, b) such that:
    #       a and b are indices to faces (qua nodes) AND
    #       a < b
    edgeMap = {}
    nodes = []
    for f, face in enumerate( objFile.getFaceIterator() ):
        vCount = len( face.verts )
        # create node
        node = Node()
        # compute plane
        #   Note, I trust the obj face to have correct winding
        node.poly = face
        A = B = C = 0.0
        M = []
        b = []
        X = Z = 0.0
        vCount = len( face.verts )
        for v in xrange( vCount ):
            # build the matrix for this mesh
            vIdx = face.verts[ v ] - 1
            vert = V[ vIdx ]
            X += vert.x
            Z += vert.z
            M.append( ( vert.x, vert.z, 1 ) )
            b.append( vert.y )
            # define the edge
            nextIdx = face.verts[ ( v + 1 ) % vCount ] - 1
            edge = ( min( vIdx, nextIdx ), max( vIdx, nextIdx ) )
            if ( not edgeMap.has_key( edge ) ):
                edgeMap[ edge ] = [ (f,face) ]
            elif ( len( edgeMap[ edge ] ) > 1 ):
                raise AttributeError, "Edge %s has too many incident faces" % ( edge )
            else:
                edgeMap[ edge ].append( (f,face) )
            
        node.center.x = X / vCount
        node.center.y = Z / vCount
        if ( vCount == 3 ):
            # solve explicitly
            A, B, C = np.linalg.solve( M, b )
        else:
            # least squares
            x, resid, rank, s = np.linalg.lstsq( M, b )
            A, B, C = x
        node.A = A
        node.B = B
        node.C = C
        navMesh.addNode( node )
    print "Found %d edges" % ( len( edgeMap ) )
    edges = edgeMap.keys()
    internal = filter( lambda x: len( edgeMap[ x ] ) > 1, edges )
    external = filter( lambda x: len( edgeMap[ x ] ) == 1, edges )
    print "\tFound %d internal edges" % len( internal )
    print "\tFound %d external edges" % len( external )

    # process the internal edges
    for i, e in enumerate( internal ):
        v0, v1 = e
        A, B = edgeMap[ e ]
        a, aFace = A
        b, bFace = B
        na = navMesh.nodes[ a ]
        na.addEdge( i )
        nb = navMesh.nodes[ b ]
        nb.addEdge( i )
        edge = Edge()
        edge.v0 = v0
        edge.v1 = v1
        edge.n0 = na
        edge.n1 = nb
        navMesh.addEdge( edge )

    # process the external edges (obstacles)
    # for each external edge, make sure the "winding" is opposite that of the face
    obstacles = []
    vertObstMap = {}    # mapping from vertex to the obstacles that are incident to the vertex
    for e in external:
        f, face = edgeMap[ e ][0]
        v0, v1 = e

        oID = len( obstacles )
        o = Obstacle()
        o.n0 = navMesh.nodes[ f ]
        if ( vertObstMap.has_key( v0 ) ):
            vertObstMap[ v0 ].append( oID )
        else:
            vertObstMap[ v0 ] = [ oID ]
        if ( vertObstMap.has_key( v1 ) ):
            vertObstMap[ v1 ].append( oID )
        else:
            vertObstMap[ v1 ] = [ oID ]

        i0 = face.verts.index( v0 + 1 )
        vCount = len( face.verts )
        if ( face.verts[ ( i0 + 1 ) % vCount ] == (v1+1) ):
            o.v0 = v0
            o.v1 = v1
        else:
            o.v0 = v1
            o.v1 = v0
        obstacles.append( o )
             
    processObstacles( obstacles, vertObstMap, navMesh )

    print "Found %d obstacles" % len( obstacles )
##    for o in obstacles:
##        print '\t', ' '.join( map( lambda x: str(x), o ) )
    
        
    return navMesh

def main():
    import sys, os, optparse
    parser = optparse.OptionParser()
    parser.set_description( 'Given an obj which defines a navigation mesh, this outputs the corresponding navigation mesh file.' )
    parser.add_option( "-i", "--input", help="Name of obj file to convert",
                       action="store", dest="objFileName", default='' )
    parser.add_option( "-o", "--output", help="The name of the output file. The extension will automatically be added (.nav for ascii, .nbv for binary).",
                       action="store", dest="navFileName", default='output' )
##    parser.add_option( "-b", "--binary", help="Determines if the navigation mesh file is saved as a binary (by default, it saves an ascii file.",
##                       action="store_false", dest="outAscii", default=True )
    options, args = parser.parse_args()

    objFileName = options.objFileName

    if ( objFileName == '' ):
        parser.print_help()
        sys.exit(1)

    print "Parsing", objFileName
    obj = ObjFile( objFileName )
    gCount, fCount = obj.faceStats()
    print "\tFile has %d faces" % fCount

    mesh = buildNavMesh( obj )

    outName = options.navFileName
##    ascii = options.outAscii
    ascii = True
    mesh.writeNavFile( outName, ascii )
        

if __name__ == '__main__':
    main()