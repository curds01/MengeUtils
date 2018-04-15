# All of the data structures for the road map (basically, a graph structure
from OpenGL.GL import *
from math import sqrt

# global variable to facilitate parsing error messages
line_num = 1

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
        self.clear()
        
    def clear( self ):
        self.vertices = []
        self.edges = []
        self.activeEdge = None
        self.fromID = None
        self.toID = None
        self.testEdge = Edge()
        
    def initFromFile( self, fileName ):
        global line_num
        line_num = 1
        
        def readline():
            '''Reads a single line, returning its stripped contents;
            also increments line number'''
            global line_num
            line_num += 1
            return f.readline().strip()

        def read_int(msg):
            '''Tries to convert the next non-empty line into an int.
            If it fails, it prints error information.'''
            s = ''
            while not s:
                s = readline()
            try:
                return int(s)
            except ValueError:
                raise ValueError, "Error reading int from line {} - read '{}' for {}".format(line_num, s, msg)
        
        print "Roadmap initfromFile", fileName
        f = open( fileName, 'r' )
        vertCount = read_int("vertex count")
        for i in range( vertCount ):
            line = readline()
            tokens = line.strip().split()
            if ( len( tokens ) == 3 ):
                x = float( tokens[1] )
                y = float( tokens[2] )
            elif ( len( tokens ) == 4 ):
                x = float( tokens[2] )
                y = float( tokens[3] )
            else:
                self.clear()
                print "Error reading input file:", fileName
                return
            self.addVertex( (x, y ) )
        edgeCount = read_int("edge count")
        for i in range( edgeCount ):
            line = readline()
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

    def newAscii( self ):
        '''Writes the graph to the new ascii file format.  Returns the string.'''
        s = "%d\n" % ( len (self.vertices ) )
        for i, v in enumerate( self.vertices ):
            s += '%s\n' % ( v )
        s += '%d\n' % ( len( self.edges ) )
        for i, e in enumerate( self.edges ):
            s += '%d %d\n' % ( e.start.id, e.end.id )
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