import IncludeHeader
import math
from primitives import Vector2

class ObstacleStructure:
    """ Interface class for storing obstacles providing common functionality among them """
    def __init__( self, type ):
        self.type = type

    def findIntersectObject( self, lineSegment ):
        raise NotImplementedError( "Not Yet Implement" )

    def findClosestObject( self, point ):
        raise NotImplementedError( "Not Yet Implement" )

    def __len__( self ):
        raise NotImpelementedError( "Not Yet Implement" )


    def lineIntersectionTest( self, line1, line2 ):
        """ A function to perform lin intersection test in 2D
        @ param line1: a list of 2 points: starting and ending points (line1[0] is starting, line1[1] is ending)
        @ param line2: a list of 2 poitns: starting and ending points (line2[0] is starting, line2[1] is ending)
        @ return if there is an intersection between two line segment then
                 return an intersection point which is  a list of Vector2
                 else return an empty list"""        
        x1 = line1.p1[0]
        x2 = line1.p2[0]
        x3 = line2.p1[0]
        x4 = line2.p2[0]

        y1 = line1.p1[1]
        y2 = line1.p2[1]
        y3 = line2.p1[1]
        y4 = line2.p2[1]

        denom = ( y4 - y3 ) *(  x2 - x1 ) - ( x4 - x3 ) * ( y2 - y1 )
        num1 = ( x4 - x3 ) * ( y1 - y3 ) - ( y4 - y3 ) * ( x1 - x3 )
        num2 = ( x2 - x1) * ( y1 - y3 ) - ( y2 - y1 ) * ( x1 - x3 )

        if (denom == 0):
            return []
        
        ua = num1/denom
        ub = num2/denom

        if ( (ua > 0 and ua < 1) and
             (ub > 0 and ub < 1) ):
            intersectX = x1 + ua * ( x2 - x1 )
            intersectY = y1 + ua * ( y2 - y1 )
            intersectPt = Vector2( intersectX, intersectY )
            return intersectPt
        return None

    def shortestDistancePointLine( self, line, point ):
        """ Find the shortest distance between given line and point
        @param line: line segment described by two points
        @param point: Vector of 2 of point in space
        @return if return shortest distance between point and line
            else return -1 if the line and point are coincident"""
        disp = line.p2 - line.p1
        distSqd = disp.lengthSquared()
        if distSqd == 0:
            return -1.0
        numerator = ( point[0] - line.p1[0]) * ( line.p2[0] - line.p1[0] ) + ( point[1] - line.p1[1] ) * ( line.p2[1] - line.p1[1] )
        u = numerator/distSqd
        # compute closest point on the line from the given point
        x = line.p1[0] + u * ( line.p2[0] - line.p1[0] )
        y = line.p1[1] + u * ( line.p2[1] - line.p1[1] )
        disp = ( point[0] - x ) * ( point[0] - x ) + ( point[1] - y ) * ( point[1] - y )
        return math.sqrt(disp)