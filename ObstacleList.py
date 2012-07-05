# The file contains data structure which is in form of the list of obstacles
import IncludeHeader
from ObstacleStructure import ObstacleStructure

class ObstacleList( ObstacleStructure ):
    def __init__( self, segmentList ):
        # List of all line segments of all obstacles
        self.data = segmentList

    def findIntersectObject( self, line2 ):
        for line in self.data:
            intersectPts = self.lineIntersectionTest( line, line2 )
            if len(intersectPts) > 0:
                return intersectPts
        return []

    def __len__( self ):
        return len( self.data )