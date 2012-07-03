# The file contains basic code for KD Tree construction for points
import sys, os
sys.path.insert( 0, r'\Users\ksuvee\Documents\Density_project\objreader' )

from ObstacleStructure import *

from primitives import Vector2

def merge( left, right, axis ):
    """ Merge left and right list together according to specify axis (0 for x-axis and y for y-axis)
    @param left: list of object to be merged
    @param right: list of object to be merged
    @return merged list"""
    if len(left) == 0:
        return right
    if len(right) == 0:
        return left
    merge = []
    while len(left) > 0 and len(right) > 0:
        leftEle = left[0]
        rightEle = right[0]
        if (leftEle[axis] < rightEle[axis]):
            # If left is smaller than right
            # pick left and advance
            merge.append( leftEle )
            left = left[1::]
        else:
            merge.append( rightEle )
            right = right[1::]
    if len(left) > 0:
        merge += left
    if len(right) > 0:
        merge += right
    return merge
        
def sort( obstacles, axis ):
    """ sort the list of obstacle according to the axis specify (0:x-axis and 1:y-axis)
    @param obstacles: list of obstacles in the world
    @return sorted list of obstacle according to x-axis"""
    if not obstacles:
        return []
    if len(obstacles) <= 1 :
        return obstacles
    middle = len(obstacles)/2
    pivot = obstacles[middle]
    leftList = obstacles[0:middle:]
    rightList = obstacles[middle::]
    sortLeft = sort(leftList, axis)
    sortRight = sort(rightList, axis)
    return merge(sortLeft, sortRight, axis)

def constructKDTree( obstacles, domainX=Vector2(0.0,3.2), domainY=Vector2(-6.0,6.0)):
    # TODO : modify to work with line -> check intersection points with boundary
    """ Construct KD Tree from the list of obstacles; domainX and domainY specify size of the world in x-axis and y-axis
    @param obstacles: list of obstacles in the world
    @param domainX: range of the world in x-axis stored in form Vector2
    @param domainY: range of the world in y-axis stored in form Vector2
    @return Node of the Tree or None if we can construct the Tree"""
    if not obstacles:
        # obstacle in the scene
        return None
    if len(obstacles) <= 1:
        return Node(obstacles[0], None, None) 
    sizeX = domainX[1] - domainX[0]
    sizeY = domainY[1] - domainY[0]
    # devide along the longer axis between the two
    midAxis = Vector2(0.0, 0.0)
    sortedList = []
    axis = 0
    if (sizeX > sizeY):
        sortedList = sort( obstacles, 0 )
        axis = 0
        midAxis = Vector2( domainX[0] + sizeX/2.,0.0 )
    else:
        sortedList = sort( obstacles, 1 )
        axis = 1
        midAxis = Vector2( 0.0, domainY[0] + sizeY/2. )
    left = []
    right = []
    for obstacle in sortedList:
        # partition the sortedList according to the axis
        if (obstacle[axis] < midAxis[axis]):
            left.append( obstacle )
        else:
            right.append( obstacle )
    leftNode = None
    rightNode = None
    if (axis == 0 ):
        leftNode = constructKDTree( left, Vector2( domainX[0], midAxis[0] ), domainY )
        rightNode = constructKDTree( right, Vector2( midAxis[0], domainX[1] ), domainY )
    else:
        leftNode = constructKDTree( left, domainX, Vector2( domainY[0], midAxis[1] ) )
        rightNode = constructKDTree( right, domainX, Vector2( midAxis[1], domainY[1] ) )
    return Node(midAxis,leftNode,rightNode)

class Node:
    def __init__( self, value, left=None, right=None):
        self.value = value  # store partition  line
        # Children
        self.left = left  
        self.right = right

    def __str__(self):
        return "{%s %s %s}" % (self.left, self.value, self.right)

class KDTree( ObstacleStructure ):
    def __init__( self, segmentsList ):
        # the data is simply root of the KDTree
        self.data = constructKDTree( segmentList )
        self.type = 'KDTree'

    def findIntersectObject( self, lineSegment ):
        """ Function to check whether the line segment intersect with any objects in the KDTree
        @param: lineSegment is the line to check for intersection
        @return: object in the Tree which the lineSegment intersect or None if it doesn't intersect with any"""
        # TODO : implement
        print "Not yet implement"
        