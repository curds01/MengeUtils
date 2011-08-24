from xml.sax import make_parser, handler
from OpenGL.GL import *
from math import cos, sin, pi
import os

class Agent:
    """Agent object for drawing"""
    ID = 0

    INACTIVE = 0
    AGENT = 1
    GOAL = 2
    def __init__( self, radius, pos, goal ):        
        self.radius = radius
        self.pos = pos
        self.goal = goal
        self.id = Agent.ID
        self.active = Agent.INACTIVE
        Agent.ID += 2

    def __str__( self ):
        return "Agent %d of %d - %s" % ( self.id, Agent.ID, self.pos )

    def sjguy( self ):
        return '%f %f %f %f' % ( self.pos[0], self.pos[1], self.goal[0], self.goal[1] )

    def xml( self, defRadius ):
        s = '\n\t<Agent p_x="{0}" p_y="{1}" '.format( self.pos[0], self.pos[1] )
        if ( self.radius != defRadius ):
            s += 'r="{0}" '.format( self.radius )
        s += '/>'
        return s
    
    def printActive( self ):
        if ( self.active == Agent.GOAL ):
            print "GOAL active"
        elif ( self.active == Agent.AGENT ):
            print "AGENT active"
        else:
            raise AttributeError, "Can't get active position for an inactive agent"
        
    def getActivePos( self ):
        if ( self.active == Agent.GOAL ):
            return self.goal
        elif ( self.active == Agent.AGENT ):
            return self.pos
        else:
            raise AttributeError, "Can't get active position for an inactive agent"
        
    def setActivePos( self, p ):
        if ( self.active == Agent.GOAL ):
            self.goal = p
        elif ( self.active == Agent.AGENT ):
            self.pos = p
        else:
            raise AttributeError, "Can't get active position for an inactive agent"
        
    def setPosition( self, pos ):
        self.pos = pos

    def setGoalPosition( self, pos ):
        self.goal = pos

    def activateAgent( self ):
        self.active = Agent.AGENT

    def activateGoal( self ):
        self.active = Agent.GOAL        

    def deactivate( self ):
        self.active = False

    def drawGL( self, select=False, editable=False ):
        if ( self.active and not select ):
            glColor3f( 0, 0, 1 )
            glBegin( GL_LINES )
            glVertex3f( self.pos[0], self.pos[1], 0 )
            glVertex3f( self.goal[0], self.goal[1], 0 )
            glEnd()

        # draw the agent
        if ( editable ):
            glColor3f( 0, 0, 0.95 )
        else:
            glColor3f( 0, 0, 0.4 )

        scale = self.radius
        if ( self.active == Agent.AGENT ):
            scale *= 1.5
        glPushMatrix()            
        glTranslate( self.pos[0], self.pos[1], 0 )
        glScale( scale, scale, scale )
        SEGMENTS = 10
        dTheta = 2 * pi / SEGMENTS
        if ( select ):
            glLoadName( self.id )
        glBegin( GL_TRIANGLE_FAN )
        glVertex3f( 0, 0, 0 )
        for i in range( SEGMENTS + 1 ):
            theta = dTheta * i
            c = cos( theta )
            s = sin( theta )
            glVertex3f( c, s, 0 )
        glEnd()
        glPopMatrix()
        # draw the goal                    
        if ( editable ):
            glColor3f( 0.9, 0.45, 0.0 )
        else:
            glColor3f( 0.45, 0.225, 0 )

        glPushMatrix()            
        glTranslate( self.goal[0], self.goal[1], 0 )
        scale = self.radius
        if ( self.active == Agent.GOAL ):
            scale *= 1.5
        glScale( scale, scale, scale )
        SEGMENTS = 10
        if ( select ):
            glLoadName( self.id + 1)
        glBegin( GL_TRIANGLE_FAN )
        glVertex3f( 0, 0, 0 )
        for i in range( SEGMENTS + 1 ):
            theta = dTheta * i
            c = cos( theta )
            s = sin( theta )
            glVertex3f( c, s, 0 )
        glEnd()
        glPopMatrix()

class AgentSet:
    def __init__( self, defRadius ):
        self.defRadius = defRadius
        self.agents = []
        self.activeAgent = None
        self.editable = False

    def setRadius( self, radius ):
        '''Sets the default radius'''
        self.defRadius = radius

    def count( self ):
        '''Returns the number of agents in the set'''
        return len( self.agents )

    def selectLastGoal( self ):
        if ( self.activeAgent ):
            self.activeAgent.deactivate()
            self.activeAgent = None
        if ( self.agents ):
            self.activeAgent = self.agents[-1]
            self.activeAgent.activateGoal()
            
    def selectAgent( self, id ):
        """Given the goal or the Agent id, returns the agent with activity set correctly"""
        agtId = id >> 1
        agt = self.agents[ agtId ]
        if ( id & 0x1 ):
            agt.activateGoal()
        else:
            agt.activateAgent()
        return agt

    def initFromFile( self, file ):
        print "Reading", file
        base, ext = os.path.splitext( file )
        if ( ext == '.txt' ):
            f = open( file, 'r' )
            aCount = int( f.readline() )
            for line in f.xreadlines():
                line = line.strip()
                if ( line ):
                    x1, y1, x2, y2 = map( lambda x: float(x), line.split() )
                    self.agents.append( Agent( self.defRadius, (x1, y1), (x2,y2) ) )
        else:
            
            parser = make_parser()
            agtHandler = AgentXMLParser( self )
            parser.setContentHandler( agtHandler )
            parser.parse( file )

    def sjguy( self ):
        """Returns the stephen guy formatted agent set"""
        s = '%d\n' % ( len( self.agents ) )
        for a in self.agents:
            s += '%s\n' % ( a.sjguy() )
        return s

    def xml( self, obstacles=None ):
        '''Returns the xml-formatted agent set'''
        #assumes everyone has the same goal
        s = '''<?xml version="1.0"?>
<Experiment time_step="0.05" >

  <AgentSet obstacleSet="1" neighbor_dist="1.1" max_neighbors="10" r="{0}" class="0" g_r="3.0" pref_speed="1.04" ttc="0.5" max_speed="2.0" max_accel="2.0" >'''.format( self.defRadius )
        for a in self.agents:
            s += '  ' + a.xml( self.defRadius )
        s += '\n  </AgentSet>'
        if ( obstacles ):
            s += obstacles.xml()
        s += '\n</Experiment>'
        return s
    
    def addAgent( self, pos, goal, radius = None ):
        if ( radius == None ):
            radius = self.defRadius
        a = Agent( radius, pos, goal )
        self.agents.append( a )
        return a

    def drawGL( self, select=False, dummy=None ):
        glPushAttrib( GL_POLYGON_BIT )
        glPolygonMode( GL_FRONT_AND_BACK, GL_FILL )
        for agent in self.agents:
            agent.drawGL( select, self.editable )
        glPopAttrib()

    def deleteActiveAgent( self ):
        """Removes the active agent"""
        if ( self.activeAgent ):
            agt = self.activeAgent
            activeID = agt.id
            Agent.ID -= 2
            i = activeID >> 1
            popped = self.agents.pop( i )
            assert( popped == agt )
            for a in self.agents[ i:]:
                a.id -= 2
            self.activeAgent = None
            return True
        return False
            
    def clear( self ):
        '''Clears all the agents from the set'''
        self.agents = []
        self.activeAgent = None
        self.editable = False
        
class AgentXMLParser( handler.ContentHandler ):
    def __init__( self, agentSet ):
        self.agentSet = agentSet
        self.goal = (0, 0)
        self.readingGoal = False

    def startElement( self, name, attrs ):
        if ( name == 'Agent' ):
            x = float( attrs[ 'p_x' ] )
            y = float( attrs[ 'p_y' ] )
            try:
                r = float( attrs[ 'r' ] )
            except:
                r = self.agentSet.defRadius
            if ( self.readingGoal ):
                self.goal = ( x, y )
            else:
                self.agentSet.addAgent( (x, y), self.goal, r )
        elif ( name == 'AgentSet' ):
            self.agentSet.defRadius = float( attrs[ 'r' ] )
        elif ( name == 'Goal' ):
            self.readingGoal = True

    def endElement( self, name ):
        if ( name == 'Goal' ):
            self.readingGoal = False
            