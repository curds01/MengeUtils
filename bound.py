# bounding objects

from primitives import Vector2

class AABB2D:
    '''A 2D, axis-aligned bounding box'''
    MIN = -100000000000.0
    MAX = 100000000000.0
    def __init__( self, vertices = [] ):
        self.min = Vector2( self.MAX, self.MAX )
        self.max = Vector2( self.MIN, self.MIN )
        if ( vertices ):
            self.expand( vertices )

    def flipY( self ):
        '''Flips the y-values of the bounding box'''
        temp = -self.min.y
        self.min.y = -self.max.y
        self.max.y = temp
        
    def __repr__( self ):
        return "BB2D: min %s, max %s" % ( self.min, self.max )
    
    def expand( self, vertices ):
        """Expands the bounding volume based on a list of vertices"""
        for v in vertices:
            if ( self.min.x > v.x ):
                self.min.x = v.x
            if ( self.min.y > v.y ):
                self.min.y = v.y
            if ( self.max.x < v.x ):
                self.max.x = v.x
            if ( self.max.y < v.y ):
                self.max.y = v.y
            
    def hitsAABB( self, aabb ):
        """Reports if this AABB overlaps with aabb"""
        if ( self.min.x > aabb.max.x or
             self.min.y > aabb.max.y or
             self.max.x < aabb.min.x or
             self.max.y < aabb.min.y ):
            return False
        return True
    
    def pointInside( self, point ):
        '''Performs an inside test on the AABB with a point.  Only the x,y values are used'''
        return point[0] >= self.min.x and point[0] <= self.max.x and point[1] >= self.min.y and point[1] <= self.max.y

    def width( self ):
        '''Reports the width of the box'''
        return self.max.x - self.min.x

    def height( self ):
        '''Reports the height of the box'''
        return self.max.y - self.min.y
    
    def area( self ):
        '''Computes the area based on the x, y values'''
        size = self.max - self.min
        return size.x * size.y