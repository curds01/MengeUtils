# Parses an OBJ file and outputs an NavMesh file definition
#   - see navMesh.py for the definition of that file format

from ObjReader import ObjFile
from navMesh import Node, Edge, NavMesh
import numpy as np

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
    edgeMap = {}
    nodes = []
    for face in objFile.getFaceIterator():
        vCount = len( face.verts )
        # create node
        node = Node()
        # compute plane
        node.poly = face
        A = B = C = 0.0
        M = []
        b = []
        X = Z = 0.0
        for v in xrange( len( face.verts ) ):
            vIdx = face.verts[ v ]
            vert = V[ vIdx - 1 ]
            X += vert.x
            Z += vert.z
            M.append( ( vert.x, vert.z, 1 ) )
            b.append( vert.y )
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