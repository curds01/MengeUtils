# The definitino of a navigation mesh

import struct
from primitives import Vector2

class Node:
    '''The node of a navigation mesh'''
    def __init__( self ):
        # polygon
        self.poly = None    # the obj face for this polygon
        # the explicit definition of the 3D plane for this polygon
        self.A = 0.0
        self.B = 0.0
        self.C = 0.0

        self.center = Vector2(0.0, 0.0)
        self.edges = []

    def toString( self, ascii=True ):
        '''Output the node data to a string'''
        if ( ascii ):
            return self.asciiString()
        else:
            return self.binaryString()

    def asciiString( self ):
        '''Output the node data to an ascii string'''
        s = '\n%d' % len( self.poly.verts )
        for v in self.poly.verts:
            s += ' %d' % ( v - 1 )
        s += '\n\t%.5f %.5f %.5f' % ( self.A, self.B, self.C )
        s += '\n\t%.5f %.5f' % ( self.center.x, self.center.y )
        s += '\n\t%d' % len( self.edges )
        for edge in self.edges:
            s += '\n\t\t%s' % ( edge.asciiString() )
        return s

    def binaryString( self ):
        '''Output the node data to a binary string'''
        s = struct.pack( 'i', len( self.poly.verts ) )
        for v in self.poly.verts:
            s += struct.pack( 'i', v - 1 )
        s += struct.pack('fffff', self.A, self.B, self.C, self.center.x, self.center.y )
        s += struct.pack( 'i', len( self.edges ) )
        for edge in self.edges:
            s += edge.binaryString()
        return s
            

class Edge:
    '''The edge of a navigation mesh'''
    def __init__( self ):
        # geometry of the portal
        self.point = Vector2(0.0, 0.0)
        self.disp = Vector2(0.0, 0.0)

        # logical graph
        self.dist = 0.0
        self.node0 = -1
        self.node1 = -1

class NavMesh:
    '''A simple navigation mesh'''
    def __init__( self ):
        self.vertices = []  # the set of vertices in the mesh
        self.nodes = []
        self.edges = []

    def addNode( self, node ):
        '''Adds a node to the mesh and returns the index'''
        idx = len( self.nodes )
        self.nodes.append( node )
        return idx

    def writeNavFile( self, fileName, ascii=True ):
        '''Outputs the navigation mesh into a .nav file'''
        if ( ascii ):
            if ( not fileName.lower().endswith( '.nav' ) ):
                fileName += '.nav'
            self.writeNavFileAscii( fileName )
        else:
            if ( not fileName.lower().endswith( '.nbv' ) ):
                fileName += '.nbv'
            self.writeNavFileBinary( fileName )

    def writeNavFileAscii( self, fileName ):
        '''Writes the ascii navigation mesh file'''
        f = open ( fileName, 'w' )
        # vertices
        f.write( '%d' % len( self.vertices) )
        for x,y in self.vertices:
            f.write( '\n\t%.5f, %.5f' % ( x, y ) )
        # nodes
        f.write( '\n%d' % len( self.nodes ) )
        for n in self.nodes:
            f.write( n.asciiString() )            
        #edges
        f.write( '\n%d' % len( self.edges ) )
        f.close()

    def writeNavFileBinary( self, fileName ):
        '''Writes the ascii navigation mesh file'''
        f = open( fileName, 'wb' )
        # vertices
        f.write( struct.pack('i', len( self.vertices ) ) )
        for x,y in self.vertices:
            f.write( struct.pack('ff', x, y ) )
        # nodes
        f.write( struct.pack('i', len( self.nodes ) ) )
        for n in self.nodes:
            f.write( n.binaryString() )            
        # edges
        f.write( struct.pack('i', len( self.edges ) ) )
        f.close()
        

