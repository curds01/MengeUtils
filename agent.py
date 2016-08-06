from xml.sax import make_parser, handler
from OpenGL.GL import *
from math import cos, sin, pi
import os

class Agent:
    """Agent object for drawing"""
    ID = 0

    INACTIVE = 0
    AGENT = 1
    def __init__( self, radius, pos ):
        self.radius = radius
        self.pos = pos
        self.id = Agent.ID
        self.active = Agent.INACTIVE
        Agent.ID += 1

    def __str__( self ):
        return "Agent %d of %d - %s" % ( self.id, Agent.ID, self.pos )

    def xml( self ):
        return '<Agent p_x="{0}" p_y="{1}" />'.format( self.pos[0], self.pos[1] )
    
    def getActivePos( self ):
        if ( self.active == Agent.AGENT ):
            return self.pos
        else:
            raise AttributeError, "Can't get active position for an inactive agent"
        
    def setActivePos( self, p ):
        if ( self.active == Agent.AGENT ):
            self.pos = p
        else:
            raise AttributeError, "Can't set active position for an inactive agent"
        
    def setPosition( self, pos ):
        self.pos = pos

    def activateAgent( self ):
        self.active = Agent.AGENT

    def deactivate( self ):
        self.active = False

    def drawGL( self, select=False, editable=False ):
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
            
    def selectAgent( self, id ):
        """Given the agent id, returns the agent with activity set correctly"""
        agt = self.agents[ id ]
        agt.activateAgent()
        return agt

    def initFromFile( self, file ):
        print "Reading", file
        base, ext = os.path.splitext( file )
        if ( ext == '.xml' ):
            parser = make_parser()
            agtHandler = AgentXMLParser( self )
            parser.setContentHandler( agtHandler )
            parser.parse( file )
        else:
            raise RuntimeError('Only reads xml files')

    def xml( self ):
        '''Returns the xml-formatted agent group'''
        #TODO: I need to partition them based on agent radius
        s = '''<?xml version="1.0"?>
<Experiment version="2.0" >

    <AgentProfile name="group1" >
		<Common max_angle_vel="360" class="1" max_neighbors="10" obstacleSet="1" neighbor_dist="5" r="0.2" pref_speed="1.34" max_speed="2" max_accel="5" >
			<Property name="pref_speed" dist="u" min="0.5" max="1.8" />
		</Common>
		<PedVO factor="1.57" buffer="0.9" tau="3" tauObst="0.1" turningBias="1.0" />
        <Helbing mass="80" />
        <ORCA tau="3.0" tauObst="0.15" />
	</AgentProfile>

	<AgentGroup>
        <ProfileSelector type="const" name="group1" />
		<StateSelector type="const" name="" />
		<Generator type="explicit" >'''
        for a in self.agents:
            s += '\n        	' + a.xml()
        s += '''
		</Generator>
	</AgentGroup>
</Experiment>'''
        return s
    
    def addAgent( self, pos, radius = None ):
        if ( radius is None ):
            radius = self.defRadius
        a = Agent( radius, pos )
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
        self.version = (1,0)
        self.inAgentSet = False

    def startElement( self, name, attrs ):
        if ( name == 'Experiment' ):
            try:
                vStr = attrs[ 'version' ]
            except:
                pass
            else:
                self.version = map( lambda x: int(x), vStr.split('.') )
        elif ( name == 'Agent' ):
            x = float( attrs[ 'p_x' ] )
            y = float( attrs[ 'p_y' ] )
            try:
                r = float( attrs[ 'r' ] )
            except:
                r = self.agentSet.defRadius
            self.agentSet.addAgent( (x, y), r )
        elif ( name == 'AgentSet' ):
            self.inAgentSet = True
            if ( self.version[0] == 1 ):
                self.agentSet.defRadius = float( attrs[ 'r' ] )
        elif ( name == 'Common' ):
            if ( self.inAgentSet ):
                self.agentSet.defRadius = float( attrs[ 'r' ] )

    def endElement( self, name ):
        if ( name == 'AgentSet' ):
            self.inAgentSet = False
            