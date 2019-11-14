# Parses an OBJ file and outputs an NavMesh file definition
#   - see navMesh.py for the definition of that file format

import sys

from ObjReader import ObjFile
from navMesh import Node, Edge, Obstacle, NavMesh
import numpy as np
from primitives import Vector2

def analyze_obj(obj_file, vertex_tolerance=1e-4):
    '''Analyzes the obj. It assess various aspects of the OBJ to determine if it is
    sufficiently "clean" to have a navigation mesh. Some failed tests lead to warnings,
    others lead to exit errors.
    "Clean" means the following:

    Error conditions:
      - Adjacent faces must have consistent winding.
      - There should be at *most* two faces adjacent to a single edge.
      - T.B.D.

    Warning conditions:
      - Find out if there are any vertices within a user-given threshold
        (This indicates the possibility of un-merged vertices).
      - T.B.D.

    @param obj_file           The parsed OBJ file to analyze.
    @param vertex_tolerance   The minimum distance required between vertices.
    '''
    warnings = []
    errors = []

    ## This determines if adjacent faces have reversed winding. We do this by looking at
    ## how the edges are implicitly defined. The face (v0, v1, v2, v3) has edges
    ## (v0, v1), (v1, v2), (v2, v3), and (v3, v0). Given the first edge, (v0, v1), if it
    ## is shared by another face, that face should have it ordered as (v1, v0). This
    ## represents consistent winding. If two faces refer to the same edge in the same
    ## order, then they have inconsistent winding.
    # A map from edge edge (v0, v1) to the face that referenced it.
    edge_to_face = {}
    # A map from each unique edge identifier (a, b) to the faces that reference it.
    # In this case, it is guaranteed that a < b.
    unique_edges = {}
    for face, _ in obj_file.getFaceIterator():
        v_count = len(face.verts)
        for v_idx in xrange(-1, v_count - 1):
            edge = (face.verts[v_idx], face.verts[v_idx + 1])
            if edge in edge_to_face:
                errors.append("The faces on lines {} and {} have inconsistent winding"
                              .format(obj_file.object_line_numbers[face],
                                      obj_file.object_line_numbers[edge_to_face[edge]]))
            edge_to_face[edge] = face
            unique_edge = (min(edge), max(edge))
            unique_edges[unique_edge] = unique_edges.get(unique_edge, []) + [face]

    bad_faces = filter(lambda face_list: len(face_list) > 2, unique_edges.values())
    for face_list in bad_faces:
        errors.append("More than two faces reference the same edge. The faces on lines {}"
                      .format(', '.join([str(obj_file.object_line_numbers[f])
                                         for f in face_list])))

    # Test for vertex distance against the given distance tolerance. Note: this is an
    # O(N^2) operation. In the future, this *could* be accelerated as necessary.
    for i in xrange(len(obj_file.vertSet) - 1):
        v_i = obj_file.vertSet[i]
        for j in xrange(i + 1, len(obj_file.vertSet)):
            v_j = obj_file.vertSet[j]
            delta = (v_i - v_j).length()
            if delta <= vertex_tolerance:
                warnings.append("Vertices on lines {} and {} are closer ({} units) than "
                                "the given tolerance {}"
                                .format(obj_file.object_line_numbers[v_i],
                                        obj_file.object_line_numbers[v_j],
                                        delta,
                                        vertex_tolerance))

    if warnings:
        print("The following issues were encountered which may indicate a problem:\n  {}"
              .format("\n  ".join(warnings)))

    if errors:
        print("The following issues were encountered which prevent a navigation mesh "
              "from being made from the given obj file:\n  {}"
              .format("\n  ".join(errors)))
        return False
    return True

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


def processObstacles( obstacles, vertObstMap, vertNodeMap, navMesh ):
    '''Given a list of Obstacle instances, connects the obstacles into sequences such that each obstacle
    points to the appropriate "next" obstacle.  Assigns obstacles to nodes based on vertex.
    Finally, sets the obstacles to the navigation mesh.'''

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
        # The obstacle should be in the set of every node built on this vertex
        for node in vertNodeMap[ vertID ]:
            node.addObstacle( o0 )
            node.addObstacle( o1 )

    # all obstacles now have a "next" obstacle
    assert( len( filter( lambda x: x.next == -1, obstacles ) ) == 0 )

    navMesh.obstacles = obstacles


def projectVertices(vertexList, y_up):
    '''Given 3D vertices, projects them to 2D for the navigation mesh. Specifically,
    projects them to a plane perpendicular to the y-axis (if y_up is True, otherwise uses
    the z-axis).'''
    #TODO: Eventually the navigation mesh will require 3D data when it is no longer topologically planar
    # The index of the 3D axis which maps to the 2d y-axis. Default to y-up (so we keep z.)
    y_2d_axis = 2
    if y_up == False:
        # Z is up, so we keep the y-axis value.
        y_2d_axis = 1
    verts = map(lambda x: (x[0], x[y_2d_axis]), vertexList)
    return verts


def buildNavMesh(objFile, y_up, vertex_distance):
    '''Given an ObjFile object, constructs the navigation mesh.writeNavFile

    The nodes will be grouped according to the obj face groups.
    @param  objFile         The parsed obj file with obj-style, 1-indexed vertex
                            values.
    @param  y_up            If True, <0, 1, 0> is the up vector and the 2D polygon
                            is defined on the xz-plane with elevation as y(x, z). If
                            False, <0, 0, 1> is the up vector and the 2D polygon is on the
                            yz-plane with z(x, y).
    @param vertex_distance  A tolerance communicating a lower bound on the expected
                            distances between all obj mesh vertices. If vertices are
                            found this distance or nearer, a warning will be issued.
    '''
    if not analyze_obj(objFile, vertex_distance):
        sys.exit(1)

    def extract_2d(v):
        if y_up:
            return v.x, v.z
        else:
            return v.x, v.y

    def extract_up(v):
        if y_up:
            return v.y
        else:
            return v.z

    navMesh = NavMesh()
    V = objFile.vertSet
    navMesh.vertices = projectVertices(V, y_up)
    vertNodeMap = {}    # maps a vertex index to all nodes that are incident to it
    edges = []
    # a dicitionary mapping an edge definition to the faces that are incident to it
    #   an "edge definition" is a two tuple of ints (a, b) such that:
    #       a and b are indices to *vertices* AND
    #       a < b
    edgeMap = {}
    nodes = []
    for f, (face, grpName) in enumerate( objFile.getFaceIterator() ):
        vCount = len( face.verts )
        # create node
        node = Node()
        # compute plane
        #   Note, I trust the obj face to have correct winding
        node.poly = face
        A = B = C = 0.0
        M = []
        b = []
        center_2d = Vector2(0, 0)
        vCount = len( face.verts )
        for v in xrange( vCount ):
            # build the matrix for this mesh

            # NOTE: The obj file seems to be storing the obj, 1-indexed vertex value.
            vIdx = face.verts[ v ] - 1
            if ( not vertNodeMap.has_key( vIdx ) ):
                vertNodeMap[ vIdx ] = [ node ]
            else:
                vertNodeMap[ vIdx ].append( node )
            vert = V[ vIdx ]

            x_2d, y_2d = extract_2d(vert)
            center_2d += Vector2(x_2d, y_2d)
            M.append((x_2d, y_2d, 1))
            b.append(extract_up(vert))
            # define the edge
            nextIdx = face.verts[ ( v + 1 ) % vCount ] - 1
            edge = ( min( vIdx, nextIdx ), max( vIdx, nextIdx ) )
            if ( not edgeMap.has_key( edge ) ):
                edgeMap[ edge ] = [ (f,face) ]
            elif ( len( edgeMap[ edge ] ) > 1 ):
                raise AttributeError, "Edge %s has too many incident faces" % ( edge )
            else:
                edgeMap[ edge ].append( (f,face) )
        node.center = center_2d / vCount
        if ( vCount == 3 ):
            # solve explicitly
            try:
                A, B, C = np.linalg.solve( M, b )
            except np.linalg.linalg.LinAlgError:
                raise ValueError("Face defined on line {} is too close to being co-linear"
                                 .format(objFile.object_line_numbers[face]))
        else:
            # least squares
            x, resid, rank, s = np.linalg.lstsq(M, b)
            # TODO: Use rank and resid to confirm quality of answer:
            #  rank will measure linear independence
            #  resid will report planarity.
            A, B, C = x
        # TODO: This isn't necessarily normalized. If b proves to be the zero vector, then
        # I'm looking at the vector that is the nullspace of the matrix and that's true to
        # arbitrary scale. Confirm that this isn't a problem.
        node.A = A
        node.B = B
        node.C = C
        navMesh.addNode(node, grpName)

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
        # TODO: Do these two nodes require a particular relationship vis a vis
        # the vertex ordering? I.e., should a be on the left and b on the right?
        # is that even guaranteed?
        edge.n0 = na
        edge.n1 = nb
        navMesh.addEdge( edge )

    # process the external edges (obstacles)
    # for each external edge, make sure the "winding" is opposite that of the face
    obstacles = []
    vertObstMap = {}    # mapping from vertex to the obstacles that are incident to the vertex
    for i, e in enumerate( external ):
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
             
    processObstacles( obstacles, vertObstMap, vertNodeMap, navMesh )

    print "Found %d obstacles" % len( obstacles )
##    for o in obstacles:
##        print '\t', ' '.join( map( lambda x: str(x), o ) )

    return navMesh

def main():
    import os, optparse
    parser = optparse.OptionParser()
    parser.set_description( 'Given an obj which defines a navigation mesh, this outputs '
                            'the corresponding navigation mesh file. The mesh must be '
                            'defined in a y-up world.' )
    parser.add_option("-i", "--input", action="store", dest="objFileName", default='',
                      help="Name of obj file to convert")
    parser.add_option("-o", "--output", action="store", dest="navFileName",
                      default='output', help="The name of the output file. The extension "
                      "will automatically be added (.nav for ascii, .nbv for binary).")
    parser.add_option('-u', '--up', dest='up', default='Y', action='store',
                      help='The direction of the up vector -- should be either Y or Z')
    parser.add_option('-d', '--distance', dest='vertex_distance', action='store',
                      type=float, default=1e-5,
                      help='Vertices are expected to be farther apart than this value. '
                      'Must be a positive number.')
##    parser.add_option( "-b", "--binary", help="Determines if the navigation mesh file is saved as a binary (by default, it saves an ascii file.",
##                       action="store_false", dest="outAscii", default=True )
    options, args = parser.parse_args()

    y_up = True
    if options.up.upper() in 'ZY':
        y_up = options.up.upper() == 'Y'
    else:
        print("\nError: The up direction should be specified by either 'y' or 'z'. Found "
              "{}\n'".format(options.up))
        parser.print_help()
        sys.exit(1)

    if options.vertex_distance <= 0.0:
        print('\nError: The vertex distance value must be strictly positive. Found {}\n'
              .format(options.vertex_distance))
        parser.print_help()
        sys.exit(1)

    objFileName = options.objFileName

    if ( objFileName == '' ):
        parser.print_help()
        sys.exit(1)

    print "Parsing", objFileName
    obj = ObjFile( objFileName )
    gCount, fCount = obj.faceStats()
    print "\tFile has %d faces" % fCount

    mesh = buildNavMesh(obj, y_up, options.vertex_distance)

    outName = options.navFileName
##    ascii = options.outAscii
    ascii = True
    mesh.writeNavFile( outName, ascii )
        

if __name__ == '__main__':
    main()