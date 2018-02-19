# Classes required to represent a behavioral finite state machine visually
#
from graph import Vertex, Edge, Graph
import lxml.etree as ET
import os
from OpenGL.GL import *
import numpy as np

class State(Vertex):
    '''Represents the state (equivalent to a vertex in a graph)'''
    def __init__(self, name, pos, is_final=False):
        '''Constructor.
        @param pos      A list of 2 floats: [x, y]
        @param name     A string: the unique name of the state.
        @param is_final A bool. True indicates that this is a "final" state.
        '''
        Vertex.__init__(self, pos)
        self.name = name
        self.is_final = is_final
        self.is_start = False

    def __str__(self):
        return "State{}({}, is_final={})".format(self.is_start * '*',
                                                 self.name,
                                                 self.is_final)

class Transition(Edge):
    '''Represents the state transitions (equivalent ot an edge in
    a graph'''
    def __init__(self, cond_type, from_state, to_state):
        '''Constructor.
        @param cond_type    A string - the type of condition this transition works on.
        @param from_state   A State instance -- the state from which the transition comes.
        @param to_state     A State instance -- the state to which the transition leads.
        '''
        Edge.__init__(self, from_state, to_state)
        self.cond_type = cond_type

    def __str__(self):
        '''String representation of the transition'''
        return '{} to {} by {}'.format(self.start.name, self.end.name, self.cond_type)

class FSM(Graph):
    # The radius of the state -- move to context.
    RADIUS = 5
    def __init__(self):
        Graph.__init__(self)
        # Reports if the states have ben positioned (as opposed to randomly loaded).
        self.is_positioned = False

    def __str__(self):
        s = 'FSM:\nStates:'
        for state in self.vertices:
            s += '\n\t{}'.format(state)
        s += '\nTransitions'
        for t in self.edges:
            s += '\n\t{}'.format(t)
        return s

    def drawGL(self, select=False, selectEdges=False, editable=False):
        '''Overrides the parent class to draw an FSM'''
        if selectEdges or not select:
            self.drawTransitions(self.edges, select, editable)
        if not selectEdges:
            self.drawStates(self.vertices, select, editable)

    def drawTransitions(self, transitions, select, editable):
        # Condition types to handle
        #   conjunctions: and, not, or
        colors = {'goal_reached':(1, 0, 0),
                  'timer':(0, 1, 0),
                  'auto':(1, 1, 1),
                  'AABB':(1, 1, 1),
                  }
        glPushAttrib(GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT)
        glDisable(GL_DEPTH_TEST)
        glLineWidth(3)
        glBegin(GL_LINES)
        for i, t in enumerate(transitions):
            color = colors.get(t.cond_type, (0.4, 0.4, 0.4))
            glColor3fv(color)
            p1 = t.start.pos
            p2 = t.end.pos
            glVertex3f(p1[0], p1[1], 0)
            glVertex3f(p2[0], p2[1], 0)
        glEnd()
        glPushMatrix()
        glPolygonMode(GL_FRONT, GL_FILL)
        for t in transitions:
            color = colors.get(t.cond_type, (0.4, 0.4, 0.4))
            glColor3fv(color)
            p1 = np.array(t.start.pos)
            p2 = np.array(t.end.pos)
            dir = p2 - p1
            dir /= np.sqrt(dir.dot(dir))
            p = p2 - self.RADIUS * dir
            glLoadMatrixf((dir[0], dir[1], 0, 0,
                          -dir[1], dir[0], 0, 0,
                          0, 0, 1, 0,
                          p[0], p[1], 0, 1))
            
            glBegin(GL_TRIANGLES)
            glVertex3f(0, 0, 0)
            glVertex3f(-3, 1.5, 0)
            glVertex3f(-3, -1.5, 0)
            glEnd()
        glPopMatrix()
        glPopAttrib()
        glLineWidth(1.0)

    def drawStates(self, states, select, editable):
        theta = np.linspace(0, np.pi * 2, 32)
        cTheta = np.cos(theta)
        sTheta = np.sin(theta)
        glPolygonMode(GL_FRONT, GL_FILL)
        glPushAttrib(GL_COLOR_BUFFER_BIT)
        glColor3f(1, 1, 1)
        
        def circle(pos, scale):
            # TODO: Push this into a display list
            # TODO: This should really be part of the context and *not* the class.
            glPushMatrix()
            glTranslatef(state.pos[0], state.pos[1], 0)
            glScalef(scale, scale, scale)
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(0, 0, 0)
            for c, s in zip(cTheta, sTheta):
                glVertex3f(c, s, 0)
            glEnd()
            glPopMatrix()
            
        for i, state in enumerate(states):
            if select:
                glLoadName(i)
            if state.is_final and not select:
                glColor3f(1, .2, .2)
                circle(state.pos, self.RADIUS + 1)
                glColor3f(1, 1, 1)
            elif state.is_start and not select:
                glColor3f(.2, 0.8, .2)
                circle(state.pos, self.RADIUS + 1)
                glColor3f(1, 1, 1)
            circle(state.pos, self.RADIUS)
        glPopAttrib()

    def initFromFile(self, file_name):
        print "Reading from behavior file:", file_name
        tree = ET.parse(file_name)
        root = tree.getroot()
        if (root.tag != "BFSM"):
            raise RuntimeError("{} is not a recognized behavior file".format(file_name))

        state_lookup = {}  # mapping from state name to state.
        for state_elem in root.iterchildren('State'):
            s = self.make_state(state_elem, state_lookup)
            self.vertices.append(s)
            
        for trans_elem in root.iterchildren('Transition'):
            t = self.make_transition(trans_elem, state_lookup)
            self.edges.extend(t)

        self.update_start_states()

        base, ext = os.path.splitext(file_name)
        graph_file = base + '.graph'
        if os.path.exists(graph_file):
            self.position(graph_file)

    def format_file(self):
        '''A file that writes a file of this FSM's positions for reloading later'''
        state_data = ['{};{};{}'.format(s.name, s.pos[0], s.pos[1]) for s in self.vertices]
        return '\n'.join(state_data)
        
    def position(self, graph_file):
        '''Positions the states according to the graph file indicated. If there is an error
        in reading the graph file, all states will be returned to the zero position'''
        try:
            with open(graph_file, 'r') as f:
                for line in f.xreadlines():
                    if not line: continue
                    tokens = line.split(';')
                    name = tokens[0]
                    x = float(tokens[1])
                    y = float(tokens[2])
                    match = filter(lambda x: x.name == name, self.vertices)
                    match[0].setPosition((x, y))
        except:
            print "Error loading position data: {}".format(graph_file)
            for s in self.vertices:
                s.setPosition((0, 0))
            return
        self.is_positioned = True
                          
                
    def update_start_states(self):
        '''Examines the transitions to determine if there are any obvious start states
        (i.e., a state that only has exiting transitions'''
        all_targets = set()
        for t in self.edges:
            all_targets.add(t.end.name)
        for s in self.vertices:
            s.is_start = s.name not in all_targets

    def make_state(self, state_elem, state_lookup):
        '''Creates a State instance from a "State" tagged tree element.
        Adds the tree to the given look up dictionary (state_lookup).
        @param state_elem   The state element to parse.
        @param state_lookup Store the state in the dictionary with its name as key.
        @returns The newly instantiated State.
        '''
        name = state_elem.attrib.get('name')
        is_final = int(state_elem.attrib.get('final', '0'))
        if (name is None):
            # TODO: Add line number
            raise RuntimeError("State tag on line {} does not have 'name' attribute"
                               .format(state_elem.sourceline))
        s = State(name, [0, 0], is_final != 0)
        state_lookup[name] = s
        return s

    def get_prob_target_states(self, target_elem):
        '''Extracts the names of the states that a probabilstic transition target goes to'''
        # This assumes that all child tags of 'State' type have valid 'name'
        # attributes.
        return [x.attrib['name'] for x in target_elem.iter('State')]

    def get_return_target_state(self, target_elem):
        '''Extracts the name of the state to which a return target transition goes'''
        # We simply extract the from tag from the parent transition
        # Both of these operations must be valid, because we could only have gotten to
        # this state if they are valid.
        trans_elem = target_elem.getparent()
        return [trans_elem.attrib["from"]]

    def find_target(self, trans_elem):
        '''Returns a list of all of the states that this transition can lead to'''
        to_name = trans_elem.attrib.get('to')
        if to_name is None:
            # TODO: Find some way to link these multiple targets as part of the same transition
            # There are currently two types of TransitionTargets in MengeCore:
            #   Probabilistic (prob)
            #   Return (return)
            #   Fail if any other kind found.
            targets = [t for t in trans_elem.iter("Target")]
            if len(targets) != 1:
                raise RuntimeError("Transition tag on line {} has no 'to' attribute and no"
                                   " child <Target> element".format(trans_elem.sourceline))
            target_type = targets[0].attrib.get("type")
            if target_type == "prob":
                return self.get_prob_target_states(targets[0])
            elif target_type == "return":
                return self.get_return_target_state(targets[0])
            elif target_type is None:
                raise RuntimeError("Target tag on line {} is missing name type"
                                   .format(targets[0].sourceline))
            else:
                raise RuntimeError("Unrecognized Target tag ({}) on line {}"
                                   .format(target_type, targets[0].sourceline))
            # Find the target tag
            #   Extract one or more states from the target -- what are the semantics of target?
            raise RuntimeError("Transition tag on line {} has no 'to' tag".format(trans_elem.sourceline))
        else:
            return [to_name]

    def find_source(self, trans_elem):
        '''Returns a list of all of the states from which this transition applies'''
        # NOTE: For convenience, we support the XML syntax of a comma-delimited list of
        # state names. What it *means* is copy the transition once for each from-to
        # pair.
        from_name = trans_elem.attrib.get('from')
        if from_name is None:
            raise RuntimeError("Transition tag is missing 'from' attribute on line {}"
                               .format(trans_elem.sourceline))
        return from_name.split(',')

    def make_transition(self, trans_elem, state_lookup):
        '''Creates a Transition instance from a "Transition"-tagged tree element.
        Looks up state names from the state-lookup.
        @param trans_elem   The transition element to parse.
        @param state_lookup The dictionary containing instantiated State instances.
        @returns The newly instantiated Transition.
        '''
        from_names = self.find_source(trans_elem)
        to_names = self.find_target(trans_elem)
        
        condition_elem = filter(lambda x: x.tag == "Condition", trans_elem)
        if len(condition_elem) != 1:
            raise RuntimeError("Transition tag on line {} should have a single",
                               "'Condition' tag as a child".format(trans_elem.sourceline))
        condition_type = condition_elem[0].attrib.get('type')

        transitions = []
        for from_name in from_names:
            for to_name in to_names:
                transitions.append(Transition(condition_type, state_lookup[from_name], state_lookup[to_name]))
        return transitions
    
if __name__ == '__main__':
    for file_name in [
##        r'E:\work\projects\menge_release\examples\core\4square\4squareB.xml',
        r"E:\work\projects\menge_release\examples\core\boolean\booleanB.xml",
##        r"E:\work\projects\menge_release\examples\core\bottleneck\bottleneckB.xml",
##        r"E:\work\projects\menge_release\examples\core\circle\circleB.xml",
##        r"E:\work\projects\menge_release\examples\core\concave\concaveMapB.xml",
##        r"E:\work\projects\menge_release\examples\core\cross\crossB.xml",
##        r"E:\work\projects\menge_release\examples\core\event\eventB.xml",
##        r"E:\work\projects\menge_release\examples\core\globalNavSwap\globalNavSwapBMap.xml",
##        r"E:\work\projects\menge_release\examples\core\goalDistance\goalDistanceB.xml",
##        r"E:\work\projects\menge_release\examples\core\headon\headonB.xml",
##        r"E:\work\projects\menge_release\examples\core\maze\mazeFieldB.xml",
##        r"E:\work\projects\menge_release\examples\core\navMesh\navMeshB.xml",
##        r"E:\work\projects\menge_release\examples\core\navMeshPlacement\navMeshPlacementB.txt",
##        r"E:\work\projects\menge_release\examples\core\obstacleSwitch\obstacleSwitchB.xml",
        r"E:\work\projects\menge_release\examples\core\office\officeB.xml",
##        r"E:\work\projects\menge_release\examples\core\pedModelSwap\pedModelSwapB.xml",
##        r"E:\work\projects\menge_release\examples\core\periodic\periodicB.xml",
##        r"E:\work\projects\menge_release\examples\core\persistGoal\persistGoalB.xml",
##        r"E:\work\projects\menge_release\examples\core\randomGoal\randomGoalB.xml",
##        r"E:\work\projects\menge_release\examples\core\sharedGoal\sharedGoalB.xml",
##        r"E:\work\projects\menge_release\examples\core\soccer\soccerB.xml",
##        r"E:\work\projects\menge_release\examples\core\stadium\stadiumB.xml",
##        r"E:\work\projects\menge_release\examples\core\swap\swapB.xml",
##        r"E:\work\projects\menge_release\examples\core\tradeshow\tradeshowB.xml",
        ]:
        fsm = FSM()
        print
        fsm.initFromFile(file_name)
        print file_name
        print "Is positioned:", fsm.is_positioned
        print fsm
    #fsm.initFromFile(r'E:\work\projects\menge_release\examples\core\boolean\booleanB.xml')
