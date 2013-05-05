## Functionality for flow analysis in the tawaf

from primitives import Vector3, Vector2, Segment
from math import atan2

class FlowLine ( Segment ):
    """Class for working with flow lines"""
    def __init__( self, p1, p2 ):
        Segment.__init__( self, p1, p2 )
        self.agents = []
        self.coef = Vector3( 0, 0, 0 ) # coefficients to line's equation
                                  # dot it with the point (x, y, 1) to get signed distance
        self.computeCoefficients()
        self.flowCounts = []        # flow counts for each time step
        self.transferedAgents = []    # when an agent crosses previous line it gets added
                                    # to this line's transfer line
        self.nextLine = None

    def __str__( self ):
        s = Segment.__str__( self )
        for agt in self.agents:
            s += '\n\t\t%s' % agt
        return s
    
    def computeCoefficients( self ):
        """Computes the coefficients of the implicit equation"""
        disp = self.p2 - self.p1
        segLen = disp.magnitude()
        norm = disp / segLen
        
        A = -norm.y
        B = norm.x

        self.coef.z = -( A * self.p1.x + B * self.p1.y )
        self.coef.x = A
        self.coef.y = B
        
    def step( self ):
        """Computes the flow for the next step"""
        # transfer agents
        self.agents += self.transferedAgents
        self.transferedAgents = []
        # increment new counter
        self.flowCounts.append( 0 )
        def signedDistance( agt ):
            pos = Vector3( agt.pos.x, agt.pos.y, 1.0 )
            return self.coef.dot( pos )
        distances = map( signedDistance, self.agents )
        data = zip( distances, self.agents )
        inRegion = filter( lambda x: x[0] < 0, data )
        self.agents = [ agt for dist, agt in inRegion ]
        crossed = filter( lambda x: x[0] >= 0, data )
        if ( crossed ):
            self.flowCounts[ -1 ] = len( crossed )
            self.nextLine.transferAgents( [ agt for dist, agt in crossed ] )

    def transferAgents( self, agentList ):
        """Adds a list of agents to this line's transfer list"""
        self.transferedAgents += agentList
        
    def addAgent( self, agt ):
        """Add an agent to the agent list -- only used during initialization.
        Don't use this to transfer an agent from one line to another"""
        self.agents.append( agt )

class FlowLineRegion:
    """A collection of flow lines, radially ordered which divide
    a space into regions"""
    def __init__( self ):
        self.lines = []
        self.sorted = False

    def __str__( self ):
        s = 'Flow Line Region:'
        for line in self.lines:
            s += '\n\t%s' % line
        return s        

    def addLine( self, p1, p2 ):
        """Add's a line to the set"""
        self.lines.append( FlowLine( p1, p2 ) )
        self.sorted = False

    def sortLines( self, center ):
        """Sorts the lines radially so that they are all encountered in order"""
        lines = self.lines
        directions = map( lambda x: (x.midPoint() - center).normalize(), lines )
        angles = map( lambda x: atan2( x.y, x.x ), directions )
        pairs = zip( angles, lines )
        def angleCmp( e1, e2 ):
            return cmp( e1[0], e2[0] )
        pairs.sort( angleCmp )
        self.lines = [ line for angle, line in pairs ]
        lineCount = len( self.lines )
        for i, line in enumerate( self.lines ):
            line.nextLine = self.lines[ (i + 1) % lineCount ]
        assert( self.lines[0] == self.lines[-1].nextLine )
        
        self.sorted = True

    def sortAgents( self, agents ):
        """Sorts the agents into the appropriate line's queue"""
        # for each pair of adjacent lines, compute the four-sided poly bounded by
        #   the lines
        # create magical line segment between agt pos and a line incredibly far away
        #   in the negative x direction
        lineCount = len( self.lines )
        for agt in agents:
            pos = agt.pos
            l1 = self.lines[0]
            for i in range( lineCount ):
                l2 = l1.nextLine
                # assume all radial lines are define inside->outside
                lines = ( (l1.p1, l1.p2 ), (l1.p2, l2.p2), (l2.p2, l2.p1), (l2.p1, l1.p1) )
                hits = 0
                for p1, p2 in lines:
                    # the line lies above or below the horizontal line
                    if ( ( p1.y < pos.y and p2.y < pos.y ) or   # line lies below agent
                         ( p1.y > pos.y and p2.y > pos.y ) or   # line lies above agent
                         ( p1.x > pos.x and p2.x > pos.x )):    # line lies to right of agent
                        continue
                    else:
                        # compute collison
                        #   if pos and (-10000, pos.y) have the same signed distance,
                        #   there's no collision
                        coef = Vector3( p1.y - p2.y, p2.x - p1.x, p1.x * p2.y - p1.y * p2.x )
                        dist1 = coef.dot( Vector3( pos.x, pos.y, 1 ) )
                        dist2 = coef.dot( Vector3( -1000000, 0, 1 ) )
                        if ( ( dist1 > 0 and dist2 < 0 ) or
                             ( dist1 < 0 and dist2 > 0 ) ):
                            hits += 1
                        
                if ( hits % 2 ):
                    sign1 = l1.coef.dot( Vector3( pos.x, pos.y, 1 ) )
                    if ( sign1 > 0 ):
                        l2.addAgent( agt )
                    else:
                        l1.addAgent( agt )                    
                l1 = l2            
            

    def step( self ):
        """Perform next computation time step of flow"""
        if ( not self.sorted ):
            raise AttributeError, "Can't step FlowLines without sorting first"
        for line in self.lines:
            line.step()

    def write( self, file ):
        """Writes the flow into columns of data - one line per column"""
        print "writing flow region with %d lines" % ( len( self.lines ) )
        stepCount = len( self.lines[0].flowCounts )
        for i in range( stepCount ):
            s = ''
            for line in self.lines:
                s += '%d ' % line.flowCounts[ i ]
            file.write( '%s\n' % s )
            

if __name__ == '__main__':
    lines = FlowLineRegion()
    lines.addLine( Vector2( .1, 0 ), Vector2( 2, 0 ) )
    lines.addLine( Vector2( -.1, 0 ), Vector2( -2, 0 ) )
    lines.addLine( Vector2( 0, .1 ), Vector2( 0, 2 ) )
    lines.addLine( Vector2( 0, -.1 ), Vector2( 0, -2 ) )
    print lines
    lines.sortLines( Vector2( 0, 0 ) )
    print lines

    class Agent:
        def __init__( self, p, id ):
            self.pos = p
            self.id = id
        def __str__( self ):
            return "Agt (%d): %s" % ( self.id, self.pos )

    a1 = Agent( Vector2( 0.5, 0.5 ), 1 )
    a2 = Agent( Vector2( 0.2, 0.9 ), 2 )
    a3 = Agent( Vector2( 1.7, 0.1 ), 3 )
    a4 = Agent( Vector2( -0.5, 0.5 ), 4 )
    agts = (a1, a2, a3, a4)
    lines.sortAgents( agts )
    print lines
        