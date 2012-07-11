# The file contains data structure which is in form of the list of obstacles
import IncludeHeader
import numpy as np
from ObstacleStructure import ObstacleStructure

class ObstacleList( ObstacleStructure ):
    def __init__( self, segmentList ):
        # List of all line segments of all obstacles
        self.data = segmentList

    def findIntersectObject( self, line2 ):
        for line in self.data:
            intersectPts = self.lineIntersectionTest( line, line2 )
            if intersectPts is not None:
                return intersectPts
        return None

    def findClosestObject( self, point ):
        minDist = 10000
        for line in self.data:
            dist = self.shortestDistancePointLine( line, point )
            if (dist < minDist):
                minDist = dist
        return minDist
                 
    def __len__( self ):
        return len( self.data )
    