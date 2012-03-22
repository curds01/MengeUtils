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
    dist[ mask2 ] =  np.sum( samplesReshape[ mask2, : ] * N, axis=1 ) + C

    dist  = np.reshape( dist, samples.shape[:2] )
    return dist

if __name__ == '__main__':
    from primitives import Segment, Vector2
    import time
    def main():
        '''Test the functionality'''
        p1 = Vector2( -1.0, 0.0 )
        p2 = Vector2( 1.0, 0.0 )
        seg = Segment( p1, p2 )
        samples = np.linspace( -2, 2, 500 )
        X, Y = np.meshgrid( samples, samples )
        grid = np.dstack( (X, Y ) )
        s = time.clock()
        dist = computeSegmentDistance( seg, grid )
        e = time.clock()
        print "Took %f seconds to compute %d distances" % ( e - s, grid.size /2 )

    main()    