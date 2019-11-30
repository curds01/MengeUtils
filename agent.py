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

class AgentProfile:
    '''A simple approximatino of the Menge profile.  Currently only supports varying
    agent radii.'''
    
    def __init__( self, name, radius, parent=None ):
        '''Constructor

        @param  name        A string.  The name of this profile group.
        @param  radius      A number. The radius for all agents in this group.
        @param  parent      An AgentProfile reference -- the group that this group
                            inherits from.
        '''
        self.name = name
        self.radius = radius
        self.parent = parent

    def xml( self, indent=0 ):
        '''Creates the xml for this group.

        @param  indent      The white space to inject before the xml.
        @returns    A string.  The indented XML for this group.
        '''
        if ( self.parent is None ):
            return self.fullXml( indent )
        else:
            return self.inheritXml( indent )

    def fullXml( self, indent ):
        '''Creates the xml for a "fully" specified agent profile.

        @param  indent      The white space to inject before the xml.
        @returns    A string.  The indented XML for this group.
        '''
        return '''{0}<AgentProfile name="{1}" >
{0}	<Common max_angle_vel="360" class="1" max_neighbors="10" obstacleSet="1" neighbor_dist="5" r="{2}" pref_speed="1.34" max_speed="2" max_accel="5" />'.format(indent, self.radius)
{0}	<PedVO factor="1.57" buffer="0.9" tau="3" tauObst="0.1" turningBias="1.0" />
{0}	<Helbing mass="80" />
{0}	<ORCA tau="3.0" tauObst="0.15" />
{0}</AgentProfile>'''.format( indent, self.name, self.radius )

    def inheritXml( self, indent ):
        '''Creates the xml for an inherited agent profile.

        @param  indent      The white space to inject before the xml.
        @returns    A string.  The indented XML for this group.
        '''
        return '''{0}<AgentProfile name="{1}" inherits="{3}" >
{0}		<Common r="{2}" />
{0}	</AgentProfile>'''.format(indent, self.name, self.radius, self.parent.name )

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

    def groupAgents( self ):
        '''Partitions the agents into distinct agent groups by radius size.

        @returns    A list of tuples: (AgentGroup, list of agents) such that each
                    list belongs to its corresponding agent group.
        '''
        groupSet = {}
        defProfile = None
        for agent in self.agents:
            if ( not groupSet.has_key( agent.radius ) ):
                if ( defProfile is None ):
                    profile = AgentProfile( 'group1', agent.radius )
                    groupSet[ agent.radius ] = (profile, [])
                    defProfile = profile
                else:
                    profile = AgentProfile( 'group%d' % (len(groupSet) + 1), agent.radius, defProfile )
                    groupSet[ agent.radius ] = (profile, [] )
            else:
                profile = groupSet[ agent.radius ]
            groupSet[ agent.radius ][1].append( agent )
        profiles = groupSet.values()
        def compare( a, b ):
            if ( a[0].parent is None ):
                return -1
            elif ( b[0].parent is None ):
                return 1
            else:
                return cmp(a[0].name, b[0].name)
        profiles.sort(compare)
        return profiles

    def xml( self ):
        '''Returns the xml-formatted agent group'''
        #TODO: I need to partition them based on agent radius
        profiles = self.groupAgents()
        s = '''<?xml version="1.0"?>
<Experiment version="2.0" >'''
        for profile, agentList in profiles:
            s += '\n\n' + profile.xml('\t')

        for profile, agentList in profiles:
            s += '''
            
	<AgentGroup>
        <ProfileSelector type="const" name="{0}" />
		<StateSelector type="const" name="???" />
		<Generator type="explicit" >'''.format(profile.name)
            for a in agentList:
                s += '\n        	' + a.xml()
            s += '''
		</Generator>
	</AgentGroup>'''
        s += '''
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
        if self.activeAgent is not None:
            agt = self.activeAgent
            activeID = agt.id
            Agent.ID -= 1
            popped = self.agents.pop(activeID)
            assert(popped == agt)
            # Decrement the ids of all agents following the active agent.
            for a in self.agents[activeID:]:
                a.id -= 1
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
        self.inAgentGroup = False
        self.currRadius = 1.0
        self.profileRadii = {}
        self.currProfile = None

    def startElement( self, name, attrs ):
        if ( name == 'Experiment' ):
            try:
                vStr = attrs[ 'version' ]
            except:
                pass
            else:
                self.version = map( lambda x: int(x), vStr.split('.') )
        elif ( name == 'AgentProfile' ):
            try:
                self.currProfile = attrs[ 'name' ]
                self.profileRadii[ self.currProfile ] = 1.0
            except:
                raise RuntimeError("Found <AgentProfile> without a name")
            try:
                parentName = attrs['inherits']
                self.profileRadii[ self.currProfile ] = self.profileRadii[ parentName ]
            except:
                pass
        elif ( name == 'Common' ):
            if ( self.currProfile is not None ):
                try:
                    r = attrs['r']
                    self.profileRadii[ self.currProfile ] = float( attrs['r'] )
                except:
                    pass
        elif ( name == 'Property' ):
            if ( self.currProfile is not None ):
                try:
                    name = attrs['name']
                    if ( name == 'r' ):
                        dist = attrs['dist']
                        if ( dist == 'u' ):
                            print 'Uniform radius distribution not supported.  Using mid-point value'
                            self.profileRadii[ self.currProfile ] = ( float(attrs['min']) + float(attrs['max']) ) * 0.5
                        elif ( dist == 'c' ):
                            self.profileRadii[ self.currProfile ] = float(attrs['value'])
                        elif ( dist == 'n' ):
                            print 'Normal radius distributino not supported.  Using mean value'
                            self.profileRadii[ self.currProfile ] = float(attrs['mean'])
                except:
                    pass
        elif ( name == 'Agent' ):
            if ( not self.inAgentGroup ):
                raise RuntimeError( "Found Agent definition outside of AgentGroup" )
            x = float( attrs[ 'p_x' ] )
            y = float( attrs[ 'p_y' ] )
            self.agentSet.addAgent( (x, y), self.profileRadii[ self.currProfile ] )
        elif ( name == 'AgentGroup' ):
            self.inAgentGroup = True
        elif ( name == 'ProfileSelector' ):
            try:
                self.currProfile = attrs[ 'name' ]
            except:
                raise RuntimeError("Profile selector doesn't have a profile name reference")
        elif ( name == 'Generator' ):
            try:
                type = attrs['type']
                if ( type != 'explicit' ):
                    print 'Agent group of unsupported type found: %s.  These agents will *not* be instantiated' % type
            except:
                pass

    def endElement( self, name ):
        if ( name == 'AgentGroup' ):
            self.inAgentGroup = False
        elif ( name == 'AgentProfile' ):
            self.currProfile = None
            