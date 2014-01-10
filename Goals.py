# handles the definition of agent goals and goal sets

from primitives import Vector2
from xml.sax import make_parser, handler

class GoalSet:
    '''A set of goals.  Maps integer identifiers to instances of goals.'''
    def __init__( self, id=-1 ):
        '''Constructor

        @param      id      The id of the goal set.
        '''
        self.id = id
        self.goals = {}

    def setFromXML( self, attrs ):
        '''Sets the GoalSet parameters from a dictionary of xml attributes.

        @param      attrs       A dictionary mapping attribute names to string attribute values.
        @raises     Raises ValueError if there is a problem in parsing the xml.
        '''
        if ( attrs.has_key( 'id' ) ):
            self.id = int( id )
        else:
            raise ValueError, 'GoalSet missing "id" attribute'
    
    def addGoal( self, id, goal ):
        '''Adds a goal to the goal set.

        @param      id      The unique id associated with the goal.
        @param      goal    An instance of Goal.
        @raises     KeyError        If the id is not unique
        '''
        if ( self.goals.has_key( id ) ):
            raise KeyError, "GoalSet already contains a goal with id %d" % ( id )
        self.goals[ id ] = goal

    def __len__( self ):
        '''Returns the number of goals'''
        return len( self.goals )

    def xml( self, indent=0 ):
        '''Returns an xml specification of the goal set.

        @param      indent      The number of indentations for the definition.
        '''
        INDENT = '\t' * indent
        s = '%s<GoalSet id="%d">\n' % ( INDENT, self.id )
        ids = self.goals.keys()
        ids.sort()
        for id in ids:
            s += '%s\n' % ( self.goals[ id ].xml( indent + 1 ) )
        s += '%s</GoalSet>' % ( INDENT )
        return s
    
class Goal:
    '''The goal base class'''
    TYPE = 'undefined'
    def __init__( self ):
        '''Constructor.
        '''
        self.weight = 1.0
        self.capacity = 1000000
        self.id = -1

    def xmlAttr( self ):
        '''Returns a string of the unique xml attributes of this goal'''
        return ''
    
    def setFromXML( self, attrs ):
        '''Sets the GoalSet parameters from a dictionary of xml attributes.

        This function should be explicitly called by child classes and its value should be
        returned.

        @param      attrs       A dictionary mapping attribute names to string attribute values.
        @returns    The goals id. 
        @raises     Raises ValueError if there is a problem in parsing the xml.
        '''
        if ( attrs.has_key( 'id' ) ):
            try:
                id = int( attrs[ 'id' ] )
            except ValueError:
                print "Goal is missing \"id\" attribute"
                raise            
        if ( attrs.has_key( 'weight' ) ):
            try:
                self.weight = float( attrs[ 'weight' ] )
            except ValueError:
                print "Goal has a \"weight\" attribute which isn't a float.  Using default value of 1.0"
        else:
            print "Goal is missing \"weight\" attribute.  Using default value 1.0"

        if ( attrs.has_key( 'capacity' ) ):
            try:
                self.capacity = int( attrs[ 'capacity' ] )
            except ValueError:
                print "Goal has a \"capacity\" attribute which isn't a float.  Using default value of %d" % self.capacity
        else:
            print "Goal is missing \"capacity\" attribute.  Using default value %d" % self.capacity
    
    def xml( self, indent=0 ):
        '''Returns an xml specification of this goal.

        @param      indent      The number of indentations for the definition.
        '''
        INDENT = '\t' * indent
        s = '%s<Goal type="%s" id="%d" %s weight="%f" capacity="%d" />' % ( INDENT, self.TYPE, self.id, self.xmlAttr(), self.weight, self.capacity )
        return s

class PointGoal( Goal ):
    '''A simple point goal.  The agent's goal position is this point.'''
    # The goal type for xml
    TYPE = 'point'
    def __init__( self, x, y, weight=1.0, capacity=1 ):
        '''Constructor

        @param      x               The x-position of the goal
        @param      y               The y-position of the goal.
        @param      weight          The relative probability of selecting this goal.
        @param      capacity        The goal's capacity.
        '''
        Goal.__init__( self, weight, capacity )
        self.p = Vector2( x, y )

    def xmlAttr( self ):
        '''Returns a string of the unique xml attributes of this goal'''
        return 'x="%f" y="%f"' % ( self.p.x, self.p.y )

    def setFromXML( self, attrs ):
        '''Sets the GoalSet parameters from a dictionary of xml attributes.

        @param      attrs       A dictionary mapping attribute names to string attribute values.
        @raises     Raises ValueError if there is a problem in parsing the xml.
        '''
        Goal.setFromXML( self, attrs )
    
class CircleGoal( Goal ):
    '''A circular goal which assignes positions with uniform probability'''
    # The goal type for xml
    TYPE = 'circle'
    def __init__( self, x, y, r, weight=1.0, capacity=1 ):
        '''Constructor

        @param      x               The x-position of the goal
        @param      y               The y-position of the goal.
        @param      r               The radius of the circle
        @param      weight          The relative probability of selecting this goal.
        @param      capacity        The goal's capacity.
        '''
        Goal.__init__( self, weight, capacity )
        self.p = Vector2( x, y )
        self.r = r

     def xmlAttr( self ):
        '''Returns a string of the unique xml attributes of this goal'''
        return 'x="%f" y="%f" radius="%f"' % ( self.p.x, self.p.y, self.r )   

    def setFromXML( self, attrs ):
        '''Sets the GoalSet parameters from a dictionary of xml attributes.

        @param      attrs       A dictionary mapping attribute names to string attribute values.
        @raises     Raises ValueError if there is a problem in parsing the xml.
        '''
        return Goal.setFromXML( self, attrs )
    
class AABBGoal( Goal ):
    '''A axis-aligned bounding box goal region with uniform probability'''
    # The goal type for xml
    TYPE = 'AABB'
    def __init__( self, xMin, yMin, xMax, yMax, weight=1.0, capacity=1 ):
        '''Constructor

        @param      xMin            The minimum x-position of the goal
        @param      yMin            The minimum y-position of the goal.
        @param      xMax            The maximum x-position of the goal
        @param      yMax            The maximum y-position of the goal.
        @param      weight          The relative probability of selecting this goal.
        @param      capacity        The goal's capacity.
        '''
        Goal.__init__( self, weight, capacity )
        self.minPt = Vector2( xMin, yMin )
        self.maxPt = Vectro2( xMax, yMax )

     def xmlAttr( self ):
        '''Returns a string of the unique xml attributes of this goal'''
        return 'xmin="%f" ymin="%f" xmax="%f" ymax="%f"' % ( self.minPt.x, self.minPt.y, self.maxPt.x, self.maxPt.y )    

    def setFromXML( self, attrs ):
        '''Sets the GoalSet parameters from a dictionary of xml attributes.

        @param      attrs       A dictionary mapping attribute names to string attribute values.
        @raises     Raises ValueError if there is a problem in parsing the xml.
        '''
        return Goal.setFromXML( self, attrs )
    
class OBBGoal( Goal ):
    '''An oriented bounding box goal region with uniform probability'''
    
    # The goal type for xml
    TYPE = 'OBB'
    def __init__( self, x, y, width, height, angle=0.0, weight=1.0, capacity=1 ):
        '''Constructor

        @param      x               The x-position of the goal's pivot point.
        @param      y               The y-position of the goal's pivot point.
        @param      width           The width of the goal (length along local x-axis).
        @param      height          The height of the goal (length along local y-axis).
        @param      angle           The rotation (around the pivot) in degrees.
        @param      weight          The relative probability of selecting this goal.
        @param      capacity        The goal's capacity.
        '''
        Goal.__init__( self, weight, capacity )
        self.pivot = Vector2( xMin, xMax )
        self.size = Vector2( width, height )
        self.angle = angle

     def xmlAttr( self ):
        '''Returns a string of the unique xml attributes of this goal'''
        return 'x="%f" y="%f" width="%f" height="%f" angle="%f"' % ( self.pivot.x, self.pivot.y, self.size.x, self.size.y, self.angle )    

    def setFromXML( self, attrs ):
        '''Sets the GoalSet parameters from a dictionary of xml attributes.

        @param      attrs       A dictionary mapping attribute names to string attribute values.
        @raises     Raises ValueError if there is a problem in parsing the xml.
        '''
        return Goal.setFromXML( self, attrs )


def getGoalFromType( typeStr ):
    '''Given a valid goal type string, returns an instance of the corresponding goal.

    @param      typeStr     A string of the valid goal type.
    @returns    An instance of the corresopnding goal type.
    @raises     ValueError if no goal type matches.
    '''
    GoalTypes = { PointGoal.TYPE:PointGoal,
                  CircleGoal.TYPE:CircleGoal,
                  AABBGoal.TYPE:AABBGoal,
                  OBBGoal.TYPE:OBBGOal
                  }
    try:
        return GoalTypes[ typeStr ]()
    except KeyError:
        raise ValueError, "Unrecognized goal type: %s" % ( typeStr )
    
class GoalXMLParser( handler.ContentHandler ):
    def __init__( self ):
        self.goalSets = []

    def startElement( self, name, attrs ):
        if ( name == 'GoalSet' ):
            self.goalSets.append( GoalSet() )
            try:
                self.goalSets[ -1 ].setFromXML( attrs )
            except ValueError:
                print "Error parsing goal set "
                raise
        elif ( name == 'Goal' ):
            if ( not attrs.has_key( 'type' ) ):
                raise ValueError, "Goal definition does not have a type identifier"
            goal = getGoalFromType( attrs[ 'type' ] )
            try:
                id = goal.setFromXML( self, attrs )
                self.goalSets[ -1 ].addGoal( id, goal )
            except ValueError:
                print "Error parsing goal"
                raise

def getGoalParser():
    '''Returns a goal parser'''
    return parser

def readGoals( fileName ):
    print "Reading goals:", fileName
    parser = make_parser()
    goalHandler = GoalXMLParser()
    parser.setContentHandler( goalHandler )
    parser.parse( fileName )

    print 'Found %d goal sets' % ( len( goalHandler.goalSets ) )
    for i, set in goalHandler.goalSets:
        print '\tgoal set %d has %d goals' % ( i, len( set ) )
    