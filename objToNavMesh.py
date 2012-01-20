# Parses an OBJ file and outputs an NavMesh file definition
#   - see navMesh.py for the definition of that file format

from ObjReader import ObjFile
from navMesh import Node, Edge, NavMesh
import numpy as np
from primitives import Vector2

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
                edgeMap[ edge ] = [ f ]
            elif ( len( edgeMap[ edge ] ) > 1 ):
                raise AttributeError, "Edge %s has too many incident faces" % ( edge )
            else:
                edgeMap[ edge ].append( f )
            
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
        a, b = edgeMap[ e ]
        na = navMesh.nodes[ a ]
        na.addEdge( i )
        nb = navMesh.nodes[ b ]
        nb.addEdge( i )
        edge = Edge()
        edge.node0 = a
        edge.node1 = b
        edge.dist = (na.center - nb.center).magnitude()
        # I need the geometry of the edge (the vertices)
        v0 = navMesh.vertices[ v0 ]
        v0 = Vector2( v0[0], v0[1] )
        edge.point = v0
        v1 = navMesh.vertices[ v1 ]
        v1 = Vector2( v1[0], v1[1] )
        edge.disp = v1 - v0
        navMesh.addEdge( edge )

    # process the external edges
    #   TODO: I need to do this
    #   At its simplest I can dump out each external edge as a single obstacle.
    #   Better yet, I should string them back up.
    #   WINDING: I need to string them up in such a way that the navigation mesh is on the "inside"
    #       of the obstacle
        
    return navMesh

def main():
    import sys, os, optparse
    parser = optparse.OptionParser()
    parser.set_description( 'Given an obj which defines a navigation mesh, this outputs the corresponding navigation mesh file.' )
    parser.add_option( "-i", "--input", help="Name of obj file to convert",
                       action="store", dest="objFileName", default='' )
    parser.add_option( "-o", "--output", help="The name of the output file. The extension will automatically be added (.nav for ascii, .nbv for binary).",
                       action="store", dest="navFileName", default='output' )
    parser.add_option( "-b", "--binary", help="Determines if the navigation mesh file is saved as a binary (by default, it saves an ascii file.",
                       action="store_false", dest="outAscii", default=True )
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
    mesh.writeNavFile( outName, options.outAscii )
        

if __name__ == '__main__':
    main()