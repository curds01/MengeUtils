# The definitino of a navigation mesh

import struct

from ObjSlice import AABB
from primitives import Vector2, Vector3, Face

class Node:
    '''The node of a navigation mesh'''
    def __init__( self ):
        # polygon
        self.poly = None    # the obj face for this polygon
        # the explicit definition of the normal to the 3D plane for this polygon
        self.A = 0.0
        self.B = 0.0
        self.C = 0.0

        self.center = Vector2(0.0, 0.0)  # centroid of this polygon
        # Vector comprising of edge indices
        # TODO: Document what these edges mean.
        self.edges = []
        # Vector comprising of obstacle indices.
        self.obstacles = []

    def addEdge( self, edgeID ):
        '''Given the index of an internal edge, adds the edge to the definition'''
        self.edges.append( edgeID )

    def addObstacle( self, obstID ):
        '''Given the index of an obstacle edge, adds the obstacle to the definition'''
        if ( obstID not in self.obstacles ):
            self.obstacles.append( obstID )

    def getElevation(self, p):
        '''Computes the elevation of point p based on its projection onto this nodes plane'''
        return self.A * p.x + self.B * p.y + self.C
        
    def toString( self, ascii=True ):
        '''Output the node data to a string'''
        if ( ascii ):
            return self.asciiString()
        else:
            return self.binaryString()

    def asciiString( self, indent='' ):
        '''Output the node data to an ascii string'''
        s = '%s%.5f %.5f' % ( indent, self.center.x, self.center.y )
        s += '\n%s%d' % ( indent, len( self.poly.verts ) )
        for v in self.poly.verts:
            s += ' %d' % ( v - 1 )
        s += '\n%s%.5f %.5f %.5f' % ( indent, self.A, self.B, self.C )
        s += '\n%s%d' % ( indent, len( self.edges ) )
        for edge in self.edges:
            s += ' %d' % ( edge )
        s += '\n%s%d' % ( indent, len( self.obstacles ) )
        for obst in self.obstacles:
            s += ' %d' % ( obst )
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
    '''The edge of a navigation mesh - an edge that is shared by two polygons'''
    def __init__(self, v0=-1, v1=-1, n0=None, n1=None):
        self.v0 = v0        # index of the first vertex
        self.v1 = v1        # index of the second vertex
        self.n0 = n0        # the first adjacent node
        self.n1 = n1        # the second adjacent node

    def asciiString( self, nodeMap ):
        '''Writes out the edge as an ascii string.

        @param  nodeMap     A mapping from a node instance to its file index'''
        return '%d %d %d %d' % ( self.v0, self.v1, nodeMap[ self.n0 ], nodeMap[ self.n1 ] )

    def binaryString( self, nodeMap ):
        '''Writes out the edge as a binary string

        @param  nodeMap     A mapping from a node instance to its file index'''
        #TODO: Enforce fixed endianness
        return struct.pack( 'iiii', self.v0, self.v1, nodeMap[ self.n0 ], nodeMap[ self.n1 ] )

class Obstacle:
    '''The obstacle of a navigation mesh -- otherwise known as an edge with only a single adjacent polygon'''
    def __init__(self, v0=-1, v1=-1, n0=None, next=-1):
        self.v0 = v0    # index of the first vertex
        self.v1 = v1    # index of the second vertex
        self.n0 = n0    # The adjacent node
        self.next = next    # index of the next obstacle in sequence
        
    def asciiString( self, nodeMap ):
        '''Writes out the edge as an ascii string

        @param  nodeMap     A mapping from a node instance to its file index'''
        return '%d %d %d %d' % ( self.v0, self.v1, nodeMap[ self.n0 ], self.next )

    def binaryString( self, nodeMap ):
        '''Writes out the edge as a binary string

        @param  nodeMap     A mapping from a node instance to its file index'''
        #TODO: Enforce fixed endianness
        return struct.pack( 'iiii', self.v0, self.v1, nodeMap[ self.n0 ], self.next )
    

class NavMesh:
    '''A simple navigation mesh'''
    class NodeIterator:
        '''An iterator for iterating across the nodes of the navigation mesh for output
        strings.  It respects the node groups.'''
        def __init__( self, navMesh ):
            self.groupNames = navMesh.groups.keys()
            assert( len( self.groupNames ) > 0 )
            self.groupNames.sort()
            self.currGroupID = 0   # the current group to operate on
            self.currGroup = navMesh.groups[ self.groupNames[ 0 ] ]
            self.currNode = 0    # the next face in the group to return
            self.groups = navMesh.groups

        def __iter__( self ):
            return self
        
        def next( self ):
            '''Returns a group name and a node'''
            if ( self.currNode >= len( self.currGroup ) ):
                self.currGroupID += 1
                if ( self.currGroupID >= len( self.groups ) ):
                    raise StopIteration
                else:
                    self.currGroup = self.groups[ self.groupNames[ self.currGroupID ] ]
                    self.currNode = 0

            node = self.currGroup[ self.currNode ]
            self.currNode += 1
            return self.groupNames[ self.currGroupID ], node
        
    def __init__( self ):
        self.clear()

    def clear(self):
        self.vertices = []  # the set of vertices in the mesh
        self.groups = {} # a mapping from node group names to its nodes
        self.nodes = []
        self.edges = []
        self.obstacles = []

    def getBB(self):
        '''Reports a bounding box '''
        bb = AABB()
        vertices_3d = [Vector3(v.x, v.y, 0) for v in self.vertices]
        bb.expand(vertices_3d)
        return bb
    
    def getNodeIterator( self ):
        '''Returns an iterator for passing through all of the nodes in a fixed,
        repeatable order'''
        return NavMesh.NodeIterator( self )
    
    def addNode( self, node, nodeGrp='defaultGrp' ):
        '''Adds a node to the mesh and returns the index'''
        idx = len( self.nodes )
        self.nodes.append( node )
        if ( self.groups.has_key( nodeGrp ) ):
            self.groups[ nodeGrp ].append( node )
        else:
            self.groups[ nodeGrp ] = [ node ]
        return idx

    def addEdge( self, edge ):
        '''Adds a edge to the mesh and returns the index'''
        idx = len( self.edges )
        self.edges.append( edge )
        return idx

    def groupOrder( self ):
        '''Returns a dictionary which maps each node to its final
        file output index.  Used to connect edges and obstacles to
        nodes.'''
        count = 0
        nodeMap = {}
        for group, node in self.getNodeIterator():
            nodeMap[ node ] = count
            count += 1
        return nodeMap    

    def readNavFile(self, file_name, ascii=True):
        self.clear()
        if ascii:
            with open(file_name, 'r') as f:
                self.readNavFileAscii(f)
        else:
            raise NotImplementedError("Can't read binary nav mesh files yet")

    def readNavFileAscii(self, file):
        def next_line():
            line = file.readline()
            if line == '':
                return line
            line = line.strip()
            while not line:
                line = file.readline()
                if line == '': return line
                line = line.strip()
            return line

        v_count = int(next_line())
        for v in xrange(v_count):
            values = [float(x) for x in next_line().split()]
            self.vertices.append(Vector2(values[0], values[1]))

        e_count = int(next_line())
        for e in xrange(e_count):
            indices = [int(x) for x in next_line().split()]
            # Note: this places indices into the adjacent node slots -- after I load the
            #  groups, I need to swap indices for nodes.
            v0, v1, n0, n1 = indices
            self.edges.append(Edge(v0=v0, v1=v1, n0=n0, n1=n1))

        o_count = int(next_line())
        for o in xrange(o_count):
            indices = [int(x) for x in next_line().split()]
            # Note: this places indices into the adjacent node slot (n0) -- after I
            #  load the groups, I need to swap index for node.
            v0, v1, n0, next = indices
            self.obstacles.append(Obstacle(v0=v0, v1=v1, n0=n0, next=next))

        while True:
            group_name = next_line()
            # Note: The only valid break is at reading a new group.
            #  Everywhere should and will throw an exception.
            if group_name == '': break
            self.groups[group_name] = []
            f_count = int(next_line())
            for n in xrange(f_count):
                node = Node()
                center = [float(x) for x in next_line().split()]
                node.center = Vector2(center[0], center[1])

                vertices = [int(x) for x in next_line().split()]
                assert(vertices[0] == len(vertices) - 1)
                # Due to the history of reading these in from an OBJ, these
                # vertex values are erroneously 1-indexed.
                node.poly = Face(v=[x + 1 for x in vertices[1:]])

                norm = [float(x) for x in next_line().split()]
                node.A = norm[0]
                node.B = norm[1]
                node.C = norm[2]

                edges = [int(x) for x in next_line().split()]
                assert(edges[0] == len(edges) - 1)
                node.edges = edges[1:]

                obstacles = [int(x) for x in next_line().split()]
                assert(obstacles[0] == len(obstacles) - 1)
                node.obstacles = obstacles[1:]

                self.groups[group_name].append(node)
                self.nodes.append(node)
                
        # Now, remap index values in edges and obstacles to the actual nodes.
        nodes = [n for g_name, n in self.getNodeIterator()]
        for edge in self.edges:
            edge.n0 = nodes[edge.n0]
            edge.n1 = nodes[edge.n1]
        for obstacle in self.obstacles:
            obstacle.n0 = nodes[obstacle.n0]

    def writeNavFile( self, fileName, ascii=True ):
        '''Outputs the navigation mesh into a .nav file'''
        if ( ascii ):
            if ( not fileName.lower().endswith( '.nav' ) ):
                fileName += '.nav'
            with open(fileName, 'w') as f:
                self.writeNavFileAscii(f)
        else:
            if ( not fileName.lower().endswith( '.nbv' ) ):
                fileName += '.nbv'
            self.writeNavFileBinary( fileName )

    def writeNavFileAscii(self, f):
        '''Writes the ascii navigation mesh file'''
        # vertices
        f.write( '%d' % len( self.vertices ) )
        for x, y in self.vertices:
            f.write( '\n\t%.5f %.5f' % ( x, y ) )

        nodeMap = self.groupOrder()
        # edges
        f.write( '\n%d' % len( self.edges ) )
        for e in self.edges:
            f.write( '\n\t%s' % e.asciiString( nodeMap ) )

        # obstacles
        f.write( '\n%d' % len( self.obstacles ) )
        for o in self.obstacles:
            f.write( '\n\t%s' % o.asciiString( nodeMap ) )

        # node groups
        currGrp = ''
        for group, node in self.getNodeIterator():
            if ( group != currGrp ):
                f.write( '\n%s' % group )
                f.write( '\n%d' % ( len( self.groups[ group ] ) ) )
                currGrp = group
            f.write( '\n%s\n' % ( node.asciiString( '\t') ) )

    def writeNavFileBinary( self, file ):
        '''Writes the ascii navigation mesh file'''
        # TODO: Make this valid
        raise NotImplementedError("Can't write binary nav mesh files yet")
