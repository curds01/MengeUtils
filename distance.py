# functionality for computing a distance field

import numpy as np

def computeSegmentDistance( segment, samples ):
    '''Given grid of sample points, computes the distance from the segment to each point.

    @param segment: a Segment object (from primitives.py)
    @param samples: an MxNx2 numpy array of x,y values

    @return: an MxN numpy array of distance values
    '''
    disp = segment.p2 - segment.p1
    segLen = disp.magnitude()
    dir = disp / segLen

    P = np.array( ( (segment.p1.x, segment.p1.y ), ) )
    D = np.array( ( (dir.x, dir.y ), ) )
    # reshape the input into a Qx2 array where Q = M*N
    samplesReshape = np.reshape( samples, (-1, 2 ) )
    disp = samplesReshape - P
    dotProd = np.sum( disp * D, axis=1 )
    dist = np.empty_like( dotProd )

    # distance to those nearest p0
    mask0 = dotProd < 0
    disp = samplesReshape[ mask0, : ] - P
    dist[ mask0 ] = np.sqrt( np.sum( disp * disp, axis=1 ) )
    # distance for those nearest p1
    mask1 = dotProd > segLen
    disp = samplesReshape[ mask1, : ] - np.array( ( (segment.p2.x, segment.p2.y ), ) )
    dist[ mask1 ] = np.sqrt( np.sum( disp * disp, axis=1 ) )
    # distance to those in the middle
    A = -dir.y
    B = dir.x
    C = -( A * segment.p1.x + B * segment.p1.y )
    N = np.array( ( ( -dir.y, dir.x ), ) )
    mask2 = (~mask0) & (~mask1)
    dist[ mask2 ] =  np.abs( np.sum( samplesReshape[ mask2, : ] * N, axis=1 ) + C )

    dist = np.reshape( dist, samples.shape[:2] )
    return dist

def computeObstacleDistance( obstacle, samples ):
    '''Given grid of sample points, computes the minimum distance from the obstacle to each point.

    @param obstacle: an Obstacle object (from obstacles.py)
    @param samples: an MxNx2 numpy array of x,y values

    @return: an MxN numpy array of distance values
    '''
    segItr = obstacle.segments
    distances = []
    for seg in obstacle.segments:
        distances.append( computeSegmentDistance( seg, samples ) )
    distances = np.array( distances ).min( axis=0 )
    return distances

def imgSpaceSegment( segment, xRange, yRange, xCount, yCount ):
    '''Given the segment defined in world space, and the definition of the image space
    (specified by the xrange of values, the yrange of values and the number of cells in each
    direction)  Computes the equivalent segment in that image space.'''
    xMin = xRange[0]
    xScale = xRange[1] - xRange[0]
    yMin = yRange[0]
    yScale = yRange[1] - yRange[0]
    col0 = int( ( segment.p1.x - xMin ) / xScale * xCount )
    row0 = int( ( segment.p1.y - yMin ) / yScale * yCount )
    col1 = int( ( segment.p2.x - xMin ) / xScale * xCount )
    row1 = int( ( segment.p2.y - yMin ) / yScale * yCount )
    return Segment( Vector2( col0, row0 ), Vector2( col1, row1 ) )

if __name__ == '__main__':
    from primitives import Segment, Vector2, Vector3 
    from obstacles import Obstacle
    from ColorMap import FlameMap
    import time
    import pygame
    def main():
        '''Test the functionality'''
        pygame.init()
        map = FlameMap()

        SAMPLES = 300        
        samples = np.linspace( -5, 5, SAMPLES )
        X, Y = np.meshgrid( samples, samples )
        grid = np.dstack( (X, Y ) )
        
        if ( True ):
            print "Single segment"
            p1 = Vector2( -1.0, 1.0 )
            p2 = Vector2( 1.0, 0.0 )
            seg = Segment( p1, p2 )
            
            s = time.clock()
            dist = computeSegmentDistance( seg, grid )
            e = time.clock()
            print "\tTook %f seconds to compute %d distances" % ( e - s, grid.size /2 )
            surface = map.colorOnSurface( ( dist.min(), dist.max() ), dist.T[:,::-1] )
            imgSeg = imgSpaceSegment( seg, (-5.0, 5.0), (-5.0, 5.0), SAMPLES, SAMPLES )
            pygame.draw.line( surface, (255, 255, 255), (imgSeg.p1.x, imgSeg.p1.y), (imgSeg.p2.x, imgSeg.p2.y) )
            pygame.image.save( surface, 'distFieldSeg.png' )

        if ( True ):        
            print "Obstacle"
            o = Obstacle()
            o.closed = True
            # create a hexagonal obstacle
            RADIUS = 2.0
            RAD_SAMPLE = 12
            for i in xrange( RAD_SAMPLE ):
                theta = 2.0 * np.pi / RAD_SAMPLE * i
                x = np.cos( theta ) * RADIUS
                y = np.sin( theta ) * RADIUS
                o.vertices.append( Vector3( x, y, 0 ) )

            s = time.clock()
            dist = computeObstacleDistance( o, grid )
            e = time.clock()
            print "\tTook %f seconds to compute %d distances" % ( e - s, grid.size /2 )
    ##        print dist

            surface = map.colorOnSurface( ( dist.min(), dist.max() ), dist.T[:, ::-1] )
            for seg in o.segments:
                imgSeg = imgSpaceSegment( seg, (-5.0, 5.0), (-5.0, 5.0), SAMPLES, SAMPLES )
                pygame.draw.line( surface, (255, 255, 255), (imgSeg.p1.x, imgSeg.p1.y), (imgSeg.p2.x, imgSeg.p2.y) )
            
            pygame.image.save( surface, 'distFieldObst.png' )

    main()    