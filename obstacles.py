from ObjSlice import AABB, Segment, Polygon
from primitives import Vector3, Vector2
# sax parser for obstacles
from xml.sax import make_parser, handler

from OpenGL.GL import *

class GLPoly ( Polygon ):
    def __init__( self ):
        Polygon.__init__( self )
        self.vStart = 0         # the index at which select values for vertices starts
        self.eStart = 0         # the index at which select values for edges starts

    def drawGL( self, select=False, selectEdges=False, editable=False, drawNormals=False ):
        if ( not select ):
            if ( self.winding == Polygon.NO_WINDING ):
                self.setWinding(Vector3(0, 0, 1))

            if ( self.closed == False ):
                if ( editable ):
                    glColor3f( 0.0, 0.8, 0.0 )
                    normColor = ( 0.5, 0.5, 0.1 )
                else:
                    glColor3f( 0.0, 0.4, 0.0 )
                    normColor = ( 0.25, 0.25, 0.05 )
            elif ( self.winding == Polygon.CCW ):
                if ( editable ):
                    glColor3f( 0.8, 0.0, 0.0 )
                    normColor = ( 0.5, 0.5, 0.1 )
                else:
                    glColor3f( 0.4, 0.0, 0.0 )
                    normColor = ( 0.25, 0.25, 0.05 )
            else:
                if ( editable ):
                    glColor3f( 0.3, 0.3, 0.8 )
                    normColor = ( 0.5, 0.5, 0.1 )
                else:
                    glColor3f( 0.15, 0.15, 0.4 )
                    normColor = ( 0.5, 0.25, 0.05 )

        if ( selectEdges or not select ):        
            for i in range( self.vertCount() - 1):
                if ( selectEdges ):
                    glLoadName( self.eStart + i )
                v1 = self.vertices[i]
                v2 = self.vertices[i+1]
                glBegin( GL_LINES )
                glVertex3f( v1.x, v1.y, 0 )
                glVertex3f( v2.x, v2.y, 0 )
                glEnd()
            if ( self.closed ):
                if ( selectEdges ):
                    glLoadName( self.eStart + self.vertCount() - 1 )
                v1 = self.vertices[0]
                v2 = self.vertices[-1]
                glBegin( GL_LINES )
                glVertex3f( v1.x, v1.y, 0 )
                glVertex3f( v2.x, v2.y, 0 )
                glEnd()
        if ( editable or ( select and not selectEdges ) ):            
            glColor3f( 0.9, 0.9, 0.0 )
            for i in range( len( self.vertices ) ):
                if ( select ):
                    glLoadName( self.vStart + i )
                v = self.vertices[ i ]
                glBegin( GL_POINTS )
                glVertex3f( v.x, v.y, 0 )
                glEnd()   
        # normals
        if ( drawNormals and not select ):
            glColor3f( normColor[0], normColor[1], normColor[2] )
            glBegin( GL_LINES )
            for i in range( self.vertCount() - 1):
                v1 = self.vertices[i]
                v2 = self.vertices[i+1]
                mid = ( v1 + v2 ) / 2.0
                dir = v2 - v1
                end = Vector2( dir.y, -dir.x ).normalize() + mid
                glVertex3f( end.x, end.y, 0 )
                glVertex3f( mid.x, mid.y, 0 )

            if ( self.closed ):
                v1 = self.vertices[-1]
                v2 = self.vertices[0]
                mid = ( v1 + v2 ) / 2.0
                dir = v2 - v1
                end = Vector2( dir.y, -dir.x ).normalize() + mid
                glVertex3f( end.x, end.y, 0 )
                glVertex3f( mid.x, mid.y, 0 )
            glEnd()

    def updateWinding( self ):
        '''Updates the winding'''
        self.setWinding( Vector3( 0.0, 1.0, 0.0 ) )
        
    
Obstacle = GLPoly

class ObstacleSet:
    def __init__( self ):
        self.edgeCount = 0
        self.vertCount = 0
        self.polys = []
        self.activeVert = None
        self.activeEdge = None
        self.visibleNormals = False
        self.activeEdit = False

    def sjguy( self ):
        s = '%d\n' % ( self.edgeCount )
        for p in self.polys:
            s += '%s' % ( p.sjguy() )
        return s

    def xml( self ):
        '''Returns a string representing the xml representation of this xml set'''
        s = ''
        for p in self.polys:
            s += '\n{0}'.format( p.xml(2) )
        return s

    def obj(self):
        '''Returns an obj representation of the obstacle set'''
        s = '# Computed by MengeUtils from xml specification' # TODO: Add date
        vertices = []
        for p in self.polys:
            vertices += p.vertices
        for v in vertices:
            s += '\nv {} {} {}'.format(v.x, v.y, 0)
        i = 1
        for p in self.polys:
            v_count = len(p.vertices)
            v_indices = ' '.join(map(lambda x: str(x), xrange(i, i + v_count)))
            s += '\nf {}'.format(v_indices)
            i += v_count
        s += '\n'
        return s
    
    def __iter__( self ):
        return self.polys.__iter__()

    def __len__( self ):
        return len( self.polys )

    def removePoly( self, poly ):
        '''Remove the given poly from the obstacle set.

        @param      poly        An instance of Polygon.
        '''
        loss = 0
        for i in xrange( len( self.polys ) ):
            if ( self.polys[i] == poly ):
                # this assumes that the polygon is closed
                loss = len( self.polys[i].vertices )
                self.polys.pop( i )
                break
        self.vertCount -= loss
        self.edgeCount -= loss
        for id in xrange( i, len( self.polys ) ):
            self.polys[ id ].vStart -= loss
            self.polys[ id ].eStart -= loss
        if ( loss == 0 ):
            print "Inexplicably tried to remove a polygon that doesn't belong to the set!"
        
    def polyFromEdge( self, edgeID ):
        '''Returns the polygon which uses the indicated edge.

        @param      edgeID          The global identifier for the edge.
        '''
        count = 0
        for o in self.polys:
            tempSum = count + o.edgeCount()
            if ( tempSum > edgeID ):
                return o
            count = tempSum

    
    def selectVertex( self, i ):
        """Selects the ith vertex in the obstacle set"""
        count = 0
        for o in self.polys:
            tempSum = count + o.vertCount()
            if ( tempSum > i ):
                localI = i - count
                return o.vertices[ localI ]
            count = tempSum

    def selectEdge( self, i ):
        """Selects the ith edge in the obstacle set"""
        count = 0
        for o in self.polys:
            tempSum = count + o.edgeCount()
            if ( tempSum > i ):
                localI = i - count
                return o.getEdgeVertices( localI )
            count = tempSum

    def collapseEdge( self, index ):
        '''Collapse the edge indicated by the given index.  If the polygon only has
        two vertices left, it is deleted.

        @param      index       The global index of the targeted edge.
        '''
        count = 0
        loss = 0
        for oIdx, o in enumerate( self.polys ):
            tempSum = count + o.edgeCount()
            if ( tempSum > index ):
                if ( o.vertCount() == 3 ):
                    self.polys.pop( oIdx )
                    oIdx -= 1
                    loss = 3
                else:
                    loss = 1
                    localI = index - count
                    v1, v2 = o.getEdgeVertices( localI )
                    newVert = ( v2 + v1 ) * 0.5
                    v2.x = newVert.x
                    v2.y = newVert.y
                    o.vertices.pop( localI )
                break
            count = tempSum
        self.vertCount -= loss
        self.edgeCount -= loss
        for i in xrange( oIdx + 1, len( self.polys ) ):
            p = self.polys[ i ]
            p.vStart -= loss
            p.eStart -= loss

    def insertVertex( self, vert, edgeID ):
        '''Inserts the given vertex into the edge indicated by edge id.

        @param      vert        A 2-tuple of values.  The vertex position.
        @param      edgeID      The globally unique identifier for the obstacle edge
                                into which the vertex is inserted.
        @returns    The global index of the vertex.
        '''
        # find the vertex
        count = 0
        vertID = -1
        for oIdx, o in enumerate( self.polys ):
            tempSum = count + o.edgeCount()
            if ( tempSum > edgeID ):
                localI = edgeID - count + 1
                o.vertices.insert( localI, vert )
                vertID = count + localI 
                self.vertCount += 1
                self.edgeCount += 1
                break
            count = tempSum
            
        for i in xrange( oIdx + 1, len( self.polys ) ):
            p = self.polys[ i ]
            p.vStart += 1
            p.eStart += 1
            
        return vertID
    
    def removeVertex( self, index ):
        '''Removes the vertex with the given global index from the obstacle set.add
        This may cause an obstacle to disappear completely (if it drops to less than three
        vertices).

        @param      index       A non-negative integer.  A valid index into the set of vertices.
        '''
        # first find the obstacle and the local index
        count = 0
        loss = 0
        for oIdx, o in enumerate( self.polys ):
            tempSum = count + o.vertCount()
            if ( tempSum > index ):
                localI = index - count
                o.vertices.pop( localI )
                self.vertCount -= 1
                self.edgeCount -= 1
                loss = 1
                if ( o.vertCount() < 3 ):
                    self.polys.pop( oIdx )
                    self.vertCount -= 2
                    self.edgeCount -= 2
                    loss = 3
                    oIdx -= 1
                break
            count = tempSum

        for i in xrange( oIdx + 1, len( self.polys ) ):
            p = self.polys[ i ]
            p.vStart -= loss
            p.eStart -= loss

    def append( self, poly ):
        poly.vStart = self.vertCount
        poly.eStart = self.edgeCount
        self.vertCount += poly.vertCount()
        self.edgeCount += poly.edgeCount()
        self.polys.append( poly )

    def drawGL( self, select=False, selectEdges=False ):
        glPushAttrib( GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT )
        glDisable( GL_DEPTH_TEST )
        
        for o in self.polys:
            o.drawGL( select, selectEdges, self.activeEdit, self.visibleNormals )
        # now highlight selected elements
        if ( self.activeVert or self.activeEdge ):
            if ( self.activeVert ):
                glPointSize( 6.0 )
                glBegin( GL_POINTS )
                glColor3f( 0.9, 0.9, 0.0 )
                glVertex3f( self.activeVert.x, self.activeVert.y, 0 )
                glEnd()
                glPointSize( 3.0 )
            elif ( self.activeEdge ):
                glLineWidth( 3.0 )
                glBegin( GL_LINES )
                v1, v2 = self.activeEdge
                glVertex3f( v1.x, v1.y, 0 )
                glVertex3f( v2.x, v2.y, 0 )
                glEnd()
                glLineWidth( 1.0 )
        glPopAttrib()               

## TODO: Write this parser
##def sjguyObstParser( fileName ):
##    '''Create an obstacle set and bounding box based on the definition of sjguy for obstacles.activeEdge
##
##    definition is simple:
##    line 0:  number of line segments
##    line 1-N: each line segment is four floats: x0, y0, x1, y1
##    '''
##    obstacles = ObstacleSet()
##    bb = AABB()
##    f = open( fileName, 'r' )
##    obstCount = -1
##    for line in f.xreadlines():
##        if ( obstCount == -1 ):
##            obstCount = int( line )
##        else:
##            tokens = line.split()
##            
##                             
##    f.close()
    def obstacleBB( self ):
        '''Returns a list of 2-tuples: (obstacle, bb)'''
        return map( lambda x: (x, x.getBB()), self.polys )

    def getBB( self ):
        '''Returns a bounding box spanning all of the obstacles'''
        bb = AABB()
        for poly in self.polys:
            bb.extend( poly.getBB() )
        return bb

    def inflate( self, amount ):
        '''Inflates all of the obstacles by the given amount'''
        for p in self.polys:
            p.inflate( amount )
    
class ObstXMLParser(handler.ContentHandler):
    def __init__(self):
        self.bb = AABB()
        self.obstacles = ObstacleSet()
        self.currObst = None        

    def startElement(self, name, attrs):
        if ( name == 'Obstacle' ):
            # assume all obstacles have a closed attribute
            self.currObst = GLPoly()
            if ( int( attrs[ 'closed' ] ) != 0 ):
                self.currObst.closed = True
        elif ( name == 'Vertex' and self.currObst != None ):
            x = float( attrs['p_x'] )
            y = float( attrs['p_y'] )
            self.currObst.vertices.append( Vector3( x, y, 0 ) )
            
    def endElement( self, name ):
        if ( name == "Obstacle" ):
            self.currObst.close()
            self.obstacles.append( self.currObst )
            self.bb.expand( self.currObst.vertices )
            self.currObst = None
            
    def endDocument(self):
        print "Found %d obstacles" % ( len( self.obstacles ) )
        print "Overal BB:", self.bb
        print

            
def readObstacles( fileName, yFlip=False ):
    print "READ OBSTACLES: ", fileName
    if ( fileName[-3:] == 'xml' ):
        parser = make_parser()
        obstHandler = ObstXMLParser()
        parser.setContentHandler( obstHandler )
        parser.parse( fileName )
        if ( yFlip ):
            for o in obstHandler.obstacles:
                o.flipY()
            obstHandler.bb.flipY()
    elif ( fileName[ -3: ] == 'txt' ):
		f = open( fileName, 'r' )
		try:
			oCount = int( f.readline() )
		except ValueError:
			raise Exception, "Tried to parse Stephen's file format, but the first line was not edge count"
		bb = AABB()
		obstacles = ObstacleSet()
		for o in xrange( oCount ):
			try:
				x0, y0, x1, y1 = map( lambda x: float(x), f.readline().split() )
			except:
				raise Exception, "Error trying to parse the sjguy obstacle file -- didn't find the specified number of edges"
			obst = GLPoly()
			obst.closed = False
			obst.vertices.append( Vector3( x0, y0, 0 ) )
			obst.vertices.append( Vector3( x1, y1, 0 ) )
			bb.expand( obst.vertices )
			obstacles.append( obst )
		f.close()
		return obstacles, bb
    else:
        raise Exception, "Invalid obstacle extension: %s" % ( fileName )
    return obstHandler.obstacles, obstHandler.bb

def writeObj( obstacles, fileName ):
    '''Given an obstacle set, writes the obstacles out as an obj file'''
    f = open( fileName, 'w' )
    f.write('# converted from obstacle xml file\n' )
    currVertID = 1
    vertDefs = []   # strings of vertex definitions
    faceDefs = []   # strings which define the faces
    for poly in obstacles.polys:
        # Add vertices to the list
        fStr = 'f'
        for i, v in enumerate( poly.vertices ):
            vertDefs.append( 'v %.5f 0.0 %.5f ' % ( -v.x, v.y ) )
            fStr += ' %d' % ( i + currVertID )
        faceDefs.append( fStr )
        currVertID += len( poly.vertices )

    for v in vertDefs:
        f.write( '%s\n' % ( v ) )
    for face in faceDefs:
        f.write( '%s\n' % ( face ) )
        
    f.close()

def main():
    '''Simple operations on obstacles'''

    OBJ_CONVERT = 1 # convert to obj
    ACTIONS = { 'obj':OBJ_CONVERT,
                OBJ_CONVERT:'obj' }
    import optparse, sys, os
    parser = optparse.OptionParser()
    parser.set_description( 'Perform various operations on XML obstacle files' )
    parser.add_option( '-i', '--input', help='The input xml file to read',
                       action='store', dest='inFile', default='' )
    parser.add_option( '-o', '--output', help='The output file to use (defaults to output.___, with the appropriate extension for the operation',
                       action='store', dest='outFile', default='output' )
    parser.add_option( '-a', '--action', help='The action to perform.  Options: 1) OBJ - convert to obj (default), 2) TBA',
                       action='store', dest='actCode', default=ACTIONS[ OBJ_CONVERT ] )

    options, args = parser.parse_args()

    if ( options.inFile == '' ):
        print '\nYou must specify an input file!\n'
        parser.print_help()
        sys.exit(1)

    if ( not ACTIONS.has_key( options.actCode.lower() ) ):
        print "\nInvalid action specified: %s\n" % options.actCode
        parser.print_help()
        sys.exit( 1 )

    obstacles, bb = readObstacles( options.inFile )

    act = ACTIONS[ options.actCode.lower() ]
    if ( act == OBJ_CONVERT ):
        base, ext = os.path.splitext( options.outFile )
        outName = base + '.obj'
        print outName
        writeObj( obstacles, outName )
    
if __name__ == '__main__':
    main()
##    import sys
##    obstacles, bb = readObstacles( sys[1] )
##    for p in obstacles.polys:
##        p.inflate(3.0)
    