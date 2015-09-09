import Goals
from OpenGL.GL import *
import numpy as np
import operator

# unit circle centered on radius
CIRCLE = np.column_stack( (np.cos( np.linspace( 0, np.pi * 2.0, 24, endpoint=False ) ),
                           np.sin( np.linspace( 0, np.pi * 2.0, 24, endpoint=False ) ) ) )

# square box with size 1, bottom-left corner positioned on origin
SQUARE = np.array( ( (0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0) ), dtype=np.float32 )

class GoalEditor:
    '''A class for managing multiple goal sets and drawing them.'''
    def __init__( self, goalSets ):
        '''Constructor.

        @param      goalSets        A list of Goals.GoalSet instances.
        '''
        self.goalSets = goalSets
        # The index of the goal set currently displayed for editing
        self.editSet = -1
        self.activeGoal = -1

    def __getitem__( self, i ):
        '''Returns the ith goalset'''
        return self.goalSets[ i ]
    
    def setCount( self ):
        '''Reports the total number of goal sets'''
        return len( self.goalSets )

    def goalCount( self ):
        '''Reports the total number of goals'''
        return reduce( operator.add, map( lambda x: len(x), self.goalSets ), 0 )

    def newSet( self ):
        '''Creates a new goal set, returns its index.

        @returns        The index of the new goal set.
        '''
        id = len( self.goalSets )

        badIDs = map( lambda x: x.id, self.goalSets )
        badIDs.sort()
        newID = badIDs[-1] + 1
        gs = Goals.GoalSet()
        gs.id = newID
        self.goalSets.append( gs )
        return id

    def deleteSet( self, index ):
        '''Deletes the goal indicated by index.  This is not the same as the GoalSet.id, it is
        the index in the list of goal sets.

        @param      index       The index into the list of goal sets to delete.
        '''
        assert( index >= -len(self.goalSets) and index < len( self.goalSets ) )
        self.goalSets.pop( index )

    def deleteGoal( self, setIndex, goalIndex ):
        '''Deletes the indicated goal from the indicated set.

        @param      setIndex        The logical index of the goal set (i.e., it's position in
                                    the list of goal sets -- not it's FSM id.
        @param      goalIndex       The logical index of the goal inside the goal set.  Not
                                    the FSM id.
        '''
        assert( setIndex >= -len(self.goalSets) and setIndex < len( self.goalSets ) )
        assert( goalIndex >= -len( self.goalSets[ setIndex ] ) and goalIndex < len( self.goalSets[ setIndex ] ) )
        self.goalSets[ setIndex ].pop( goalIndex )

    def addGoal( self, setIndex, goal ):
        '''Adds the given goal to the indicated set.  Acquires a goal id from the goal set.

        @param      setIndex        The logical index of the goal set (i.e., it's position in
                                    the list of goal sets -- not it's FSM id.
        @param      goal            The goal to add.
        @returns    The local index of the goal in the set.
        '''
        assert( setIndex >= -len(self.goalSets) and setIndex < len( self.goalSets ) )
        id = self.goalSets[ setIndex ].getFreeID()
        goal.id = id
        return self.goalSets[ setIndex ].addGoal( goal )

    def getGoal( self, setIndex, goalIndex ):
        '''Returns the indicated goal from the indicated set.

        @param      setIndex        The logical index of the goal set (i.e., it's position in
                                    the list of goal sets -- not it's FSM id.
        @param      goalIndex       The logical index of the goal inside the goal set.  Not
                                    the FSM id.
        '''
        assert( setIndex >= -len(self.goalSets) and setIndex < len( self.goalSets ) )
        assert( goalIndex >= -len( self.goalSets[ setIndex ] ) and goalIndex < len( self.goalSets[ setIndex ] ) )
        return self.goalSets[ setIndex ][ goalIndex ]

        
    def drawGL( self, select=False, junk=None ):
        '''Draws the list of goal sets to the OpenGL context.

        @param      select          Determines if the goals are being drawn for selection
                                    purposes.
        @param      junk            A garbage argument to make it compatible with the
                                    view selection paradigm.
        '''
        glPushAttrib( GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT | GL_POINT_BIT | GL_LINE_BIT | GL_POLYGON_BIT )
        glBlendFunc( GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA )
        glPolygonMode( GL_FRONT, GL_LINE )
        glDisable( GL_DEPTH_TEST )
        glPointSize( 5 )
        glLineWidth( 2 )
        glID = 0
        for i, gs in enumerate( self.goalSets ):
            editable = i == self.editSet
            if ( editable ):
                c = ( 0.7, 0.3, 0.9, 0.25 )
                glColor4fv( c )
            else:
                if ( select ):  # don't draw goals in the uneditable set
                    continue
                glColor3f( 0.35, 0.15, 0.45 )
            for i, g in enumerate( gs ):
                if ( select ):
                    glLoadName( glID )
                    glID += 1
                elif ( editable and i == self.activeGoal ):
                    continue
                drawGoal( g, select, editable )
                
        if ( not select and self.activeGoal > -1 ):
            glColor4f( 0.7, 0.7, 0.1, 0.25 )
            drawGoal( self.goalSets[ self.editSet ][ self.activeGoal ], select, True )
        glPopAttrib()

def drawGoal( goal, select, editable ):
    '''Draws a goal instance to the OpenGL context.

    @param      goal            The instance of Goals.Goal subclass to draw.
    '''
    if ( isinstance( goal, Goals.CircleGoal ) ):
        # this ordering is necessary because CircleGoal inherits from PointGoal
        drawCircleGoal( goal, select, editable )
    elif ( isinstance( goal, Goals.PointGoal ) ):
        drawPointGoal( goal )
    elif ( isinstance( goal, Goals.AABBGoal ) ):
        drawAABBGoal( goal, select, editable )
    elif ( isinstance( goal, Goals.OBBGoal ) ):
        drawOBBGoal( goal, select, editable )

def drawPointGoal( goal ):
    '''Draws a point goal instance to the OpenGL context.

    @param      goal            An instace of Goals.PointGoal.
    '''
    glBegin( GL_POINTS )
    glVertex3f( goal.p.x, goal.p.y, 0.0 )
    glEnd()
    
def drawCircleGoal( goal, select=False, editable=False ):
    '''Draws a point goal instance to the OpenGL context.

    @param      goal            An instace of Goals.PointGoal.
    '''
    glPushMatrix()
    glTranslatef( goal.p.x, goal.p.y, 0.0 )
    glScalef( goal.r, goal.r, goal.r )
    if ( editable ):
        glEnable( GL_BLEND )
        glPolygonMode( GL_FRONT, GL_FILL )
        glBegin( GL_POLYGON )
        for x, y in CIRCLE:
            glVertex3f( x, y, 0.0 )
        glEnd()
        glPolygonMode( GL_FRONT, GL_LINE )
        glDisable( GL_BLEND )
    if ( not select ):
        glBegin( GL_POLYGON )
        for x, y in CIRCLE:
            glVertex3f( x, y, 0.0 )
        glEnd()
    glPopMatrix()

def drawAABBGoal( goal, select=False, editable=False ):
    '''Draws a point goal instance to the OpenGL context.

    @param      goal            An instace of Goals.PointGoal.
    '''
    size = goal.maxPt - goal.minPt
    glPushMatrix()
    glTranslatef( goal.minPt.x, goal.minPt.y, 0.0 )
    glScalef( size.x, size.y, 1.0 )
    #
    if ( editable ):
        glEnable( GL_BLEND )
        glPolygonMode( GL_FRONT, GL_FILL )
        glBegin( GL_POLYGON )
        for x, y in SQUARE:
            glVertex3f( x, y, 0.0 )
        glEnd()
        glPolygonMode( GL_FRONT, GL_LINE )
        glDisable( GL_BLEND )
    if ( not select ):
        glBegin( GL_POLYGON )
        for x, y in SQUARE:
            glVertex3f( x, y, 0.0 )
        glEnd()
    glPopMatrix()

def drawOBBGoal( goal, select=False, editable=False ):
    '''Draws a point goal instance to the OpenGL context.

    @param      goal            An instace of Goals.PointGoal.
    '''
    glPushMatrix()
    glTranslatef( goal.pivot.x, goal.pivot.y, 0.0 )
    glRotatef( goal.angle, 0.0, 0.0, 1.0 )
    glScalef( goal.size.x, goal.size.y, 1.0 )
    if ( editable ):
        glEnable( GL_BLEND )
        glPolygonMode( GL_FRONT, GL_FILL )
        glBegin( GL_POLYGON )
        for x, y in SQUARE:
            glVertex3f( x, y, 0.0 )
        glEnd()
        glPolygonMode( GL_FRONT, GL_LINE )
        glDisable( GL_BLEND )
    if ( not select ):
        glBegin( GL_LINE_LOOP )
        for x, y in SQUARE:
            glVertex3f( x, y, 0.0 )
        glEnd()
    glPopMatrix()