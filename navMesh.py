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

    def addEdge( self, edgeID ):
        '''Given the index of an internal edge, adds the edge to the definition'''
        self.edges.append( edgeID )

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
            s += ' %d' % ( edge )
        return s

    def binaryString( self ):
        '''Output the node data to a binary string'''
        s = struct.pack( 'i', len( self.poly.verts ) )
        for v in self.poly.verts:
            s += struct.pack( 'i', v - 1 )
        s += struct.pack('fffff', self.A, self.B, self.C, self.center.x, self.center.y )
        s += struct.pack( 'i', len( self.edges ) )
        for edge in self.edges:
            s += struct.pack( 'i', edge )
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

    def asciiString( self ):
        '''Writes out the edge as an ascii string'''
        s = '\n%.5f %.5f' % ( self.point.x, self.point.y )
        s += '\n\t%.5f %.5f' % ( self.disp.x, self.disp.y )
        s += '\n\t%.5f %d %d' % ( self.dist, self.node0, self.node1 )
        return s

    def binaryString( self ):
        '''Writes out a binary string representation of the string'''
        s = struct.pack( 'ff', self.point.x, self.point.y )
        s += struct.pack( 'ff', self.disp.x, self.disp.y )
        s += struct.pack( 'fii', self.dist, self.node0, self.node1 )
        return s

class NavMesh:
    '''A simple navigation mesh'''
    def __init__( self ):
        self.vertices = []  # the set of vertices in the mesh
        self.nodes = []
        self.edges = []
        self.obstacles = []

    def addNode( self, node ):
        '''Adds a node to the mesh and returns the index'''
        idx = len( self.nodes )
        self.nodes.append( node )
        return idx

    def addEdge( self, edge ):
        '''Adds a edge to the mesh and returns the index'''
        idx = len( self.edges )
        self.edges.append( edge )
        return idx

    def addObstacle( self, o ):
        '''Adds an obstacle (a list of vertex indices) to the obstacle list'''
        idx = len( self.obstacles )
        self.obstacles.append( o )
        return idx

    def extendObstacles( self, obstList ):
        '''Extends the obstacles with the list of obstacles'''
        self.obstacles.extend( obstList )
        
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
            f.write( '\n\t%.5f %.5f' % ( x, y ) )
        #edges
        f.write( '\n%d' % len( self.edges ) )
        for e in self.edges:
            f.write( e.asciiString() )
        # nodes
        f.write( '\n%d' % len( self.nodes ) )
        for n in self.nodes:
            f.write( n.asciiString() )            
        # obstacles
        f.write( '\n%d' % len( self.obstacles ) )
        for o in self.obstacles:
            f.write( '\n\t%s' % ' '.join( map( lambda x: str(x), o ) ) )
        f.close()

    def writeNavFileBinary( self, fileName ):
        '''Writes the ascii navigation mesh file'''
        f = open( fileName, 'wb' )
        # vertices
        f.write( struct.pack('i', len( self.vertices ) ) )
        for x,y in self.vertices:
            f.write( struct.pack('ff', x, y ) )
        # edges
        f.write( struct.pack('i', len( self.edges ) ) )
        for e in self.edges:
            f.write( e.binaryString() )
        # nodes
        f.write( struct.pack('i', len( self.nodes ) ) )
        for n in self.nodes:
            f.write( n.binaryString() )            
        # obstacles
        f.write( struct.pack( 'i', len( self.obstacles ) ) )
        for o in self.obstacles:
            f.write( ''.join( map( lambda x: struct.pack( 'i',x ), o ) ) )
        f.close()
        

