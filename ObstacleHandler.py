# This file contain obstacle handle which provide interface to interact and use underline data structure containing obstacles
import IncludeHeader
from KDTree import*
from ObstacleList import *
from obstacles import *
import primitives

class ObjectHandler():
    def __init__( self, obstacleSet ):
        # Use appropriate data structure based on how complicated the objectSet
        """ Have to call initializeData to create appropriated data structure """
        self.data = self.initializeData( obstacleSet )
        
    def initializeData( self, obstacleSet):
        # Given set of obstacles then parse the obstacles into line segments
        segmentList = []
        for obstacle in obstacleSet.polys:
            for segment in obstacle.segments:
                segmentList.append(segment)
                
        if len(obstacleSet) > 10:
            print "Constructing KDTree"
            return KDTree( segmentList )
        else:
            print "Constructing list"
            return ObstacleList( segmentList )

def main():
    obstName = '\Users\ksuvee\Documents\Density_project\julich\\bottleneck\width\\b140_obstacles.xml'
    if ( obstName ):
        obstacles, bb = readObstacles( obstName )
        handle = ObjectHandler( obstacles )
        intersect = handle.data.findIntersectObject( primitives.Segment(Vector2(-30.0,.0), Vector2(-30.0, -20.0)) )
        print intersect
        
if __name__ == '__main__':
    main()
            