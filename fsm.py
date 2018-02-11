# Classes required to represent a behavioral finite state machine visually
#
from graph import Vertex, Edge, Graph
import lxml.etree as ET

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

    def __str__(self):
        return "State({}, is_final={})".format(self.name, self.is_final)

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
    def __init__(self):
        Graph.__init__(self)

    def __str__(self):
        s = 'FSM:\nStates:'
        for state in self.vertices:
            s += '\n\t{}'.format(state)
        s += '\nTransitions'
        for t in self.edges:
            s += '\n\t{}'.format(t)
        return s

    def initFromFile(self, file_name):
        print "Reading from behavior file:", file_name
        tree = ET.parse(file_name)
        root = tree.getroot()
        if (root.tag != "BFSM"):
            raise RuntimeError("{} is not a recognized behavior file".format(file_name))

        state_lookup = {}  # mapping from state name to state.
        for state_elem in root.iter('State'):
            s = self.make_state(state_elem, state_lookup)
            self.vertices.append(s)
            
        for trans_elem in root.iter('Transition'):
            t = self.make_transition(trans_elem, state_lookup)
            self.edges.extend(t)

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
##        r"E:\work\projects\menge_release\examples\core\boolean\booleanB.xml",
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
        print fsm
    #fsm.initFromFile(r'E:\work\projects\menge_release\examples\core\boolean\booleanB.xml')
