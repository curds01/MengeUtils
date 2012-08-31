from Grid import AbstractGrid
from primitives import Vector2
import numpy as np

MAX_DIST = 100000.0

#TODO: Actually include obstacles

def computeFiniteVoronoi( domain, sites, ids, voronoiLimit, obstacles=None ):
    '''Computes the DISCRETE constrained voronoi diagram for the given sites over the given
    domain subject to the constraints imparted by the (optiona) obstacles.  

    Areas which belong to no one are given the value -1.  Otherwise, the ownership is
    the same as the id in the data.  The voronoi region is limited in extent by voronoiLimit.
    The area is bounded by a circle with a radius of voronoiLimit.

    @param      domain          An instance of AbstractGrid.  Defines the domain over which
                                The computation is performed.
    @param      sites           An Nx2 numpy array of sites.  The x-/y-position of each site
                                in the 0th and 1st columns, respectively.
    @param      ids             A N-tuple-like instance of ints.  For each row in the sites,
                                this tuple contains an int which is the sites id.
    @param      obstacles       An instance of ObstacleHandler.  The set of obstacles which
                                satisfies visibility queries.
    @param      voronoiLimit    A float.  It defines the maximum extent of
                                any site's voronoi region.  
    @returns    An instance of DataGrid.  The discrete voronoi diagram.
    '''
    assert( voronoiLimit > 0.0 )

    hCount = int( np.ceil( 2 * voronoiLimit / domain.cellSize[0] ) )
    if (hCount % 2 == 0):
        hCount += 1
    # Precomptue distance grid
    o = np.arange( -hCount/2 + 1, hCount/2 + 1 ) * domain.cellSize[0]
    X, Y = np.meshgrid( o, o )
    def dFunc ( dispX, dispY, radiusSqd ):
        disp = dispX * dispX + dispY * dispY
        mask = disp > radiusSqd
        disp[ mask ] = MAX_DIST
        return disp
    distTemplate = dFunc( X, Y, voronoiLimit * voronoiLimit )
    w, h = distTemplate.shape
    w /= 2
    h /= 2
    
    ownerGrid = domain.getDataGrid( -1, np.int32 )
    distGrid = domain.getDataGrid( MAX_DIST )

    centers = domain.getCenters()
    domainW = domain.resolution[0]
    domainH = domain.resolution[1]
    for i, pos in enumerate( sites ):
        # Calculate distance from agent[0] to every cell  in the grid
        # Find the index of the potential Voronoi Region with in the agentRadius away from the agent position
        posCenter = domain.getCenter( Vector2(pos[0], pos[1]) )
        l = posCenter[0] - w 
        r = posCenter[0] + w + 1 
        b = posCenter[1] - h 
        t = posCenter[1] + h + 1 
        rl = 0
        rb = 0
        rr, rt = distTemplate.shape

        if ( l > domainW or r < 0 or b > domainH or t < 0 ):
            continue
        
        if ( l < 0 ):
            rl -= l
            l = 0
        if ( b < 0 ):
            rb -= b
            b = 0
        if ( r >= domainW ):
            rr -= r - domainW
            r = domainW
        if ( t >= domainH ):
            rt -= t - domainH
            t = domainH

        if ( l < r and b < t and rl < rr and rb < rt ):
            mask = distGrid.cells[ l:r, b:t ] > distTemplate[ rl:rr, rb:rt ]
            distGrid.cells[ l:r, b:t ][ mask ] = distTemplate[ rl:rr, rb:rt ][ mask ]
            ownerGrid.cells[ l:r, b:t ][mask] = ids[i]
            
    return ownerGrid

def computeInfiniteVoronoi( domain, sites, ids, obstacles=None ):
    '''Computes the DISCRETE constrained voronoi diagram for the given sites over the given
    domain subject to the constraints imparted by the (optiona) obstacles.

    Areas which belong to no one are given the value -1.  Otherwise, the ownership is
    the same as the id in the data.

    @param      domain          An instance of AbstractGrid.  Defines the domain over which
                                The computation is performed.
    @param      sites           An Nx2 numpy array of sites.  The x-/y-position of each site
                                in the 0th and 1st columns, respectively.
    @param      ids             A N-tuple-like instance of ints.  For each row in the sites,
                                this tuple contains an int which is the sites id.
    @param      obstacles       An instance of ObstacleHandler.  The set of obstacles which
                                satisfies visibility queries.
    @returns    An instance of DataGrid.  The discrete voronoi diagram.
    '''
    ownerGrid = domain.getDataGrid( -1, np.int32 )
    distGrid = domain.getDataGrid( MAX_DIST )

    centers = domain.getCenters()
    for i, p in enumerate( sites ):
        pos = np.array( ( p[1], p[0] ) )
        pos.shape = (1, 1, 2)
        delta = centers - pos
        distSq = np.sum( delta * delta, axis=2 )

        # skip the obstacles for now
##        if ( not obstacles is None ):
##            for obst in obstacles:
##                for seg in obst.segments:
##                    A, B, C = seg.implicitEquation()
##                    p, d, L = seg.originDirLen()
##                    posDist = A * pos[0] + B * pos[1] + C
##                    signedDist = A * centers[:,:,0] + B * centers[:,:,1] + C
##                    if ( posDist >= 0 ):
##                        # True is where the distance needs to be increased
##                        signedMask = signedDist < 0
##                    else:
##                        signedMask = signedDist >= 0
        closest = distGrid.cells > distSq
        distGrid.cells[ closest ] = distSq[ closest ]
        ownerGrid.cells[ closest ] = ids[ i ]

    return ownerGrid  

def computeVoronoi( domain, sites, ids, obstacles=None, voronoiLimit=-1 ):
    '''Computes the DISCRETE constrained voronoi diagram for the given sites over the given
    domain subject to the constraints imparted by the (optiona) obstacles.

    Areas which belong to no one are given the value -1.  Otherwise, the ownership is
    the same as the id in the data.

    @param      domain          An instance of AbstractGrid.  Defines the domain over which
                                The computation is performed.
    @param      sites           An Nx2 numpy array of sites.  The x-/y-position of each site
                                in the 0th and 1st columns, respectively.
    @param      ids             A N-tuple-like instance of ints.  For each row in the sites,
                                this tuple contains an int which is the sites id.
    @param      obstacles       An instance of ObstacleHandler.  The set of obstacles which
                                satisfies visibility queries.
    @param      voronoiLimit    A float.  If non-negative, it defines the maximum extent of
                                any site's voronoi region.  If negative, a site's region is
                                unbounded.
    @returns    An instance of DataGrid.  The discrete voronoi diagram.
    '''
    if ( voronoiLimit > 0.0 ):
        return computeFiniteVoronoi( domain, sites, ids, voronoiLimit, obstacles )
    else:
        return computeInfiniteVoronoi( domain, sites, ids, obstacles )

def computeVoronoiDensity( domain, sites, ids, obstacles=None, voronoiLimit=-1 ):
    '''Computes the density of each site based on the inverse area of the voronoi region
    for that site.

    Areas which belong to no one are given the value -1.  Otherwise, the ownership is
    the same as the id in the data.

    @param      domain          An instance of AbstractGrid.  Defines the domain over which
                                The computation is performed.
    @param      sites           An Nx2 numpy array of sites.  The x-/y-position of each site
                                in the 0th and 1st columns, respectively.
    @param      ids             A N-tuple-like instance of ints.  For each row in the sites,
                                this tuple contains an int which is the sites id.
    @param      obstacles       An instance of ObstacleHandler.  The set of obstacles which
                                satisfies visibility queries.
    @param      voronoiLimit    A float.  If non-negative, it defines the maximum extent of
                                any site's voronoi region.  If negative, a site's region is
                                unbounded.
    @returns    An instance of DataGrid.  The discrete voronoi diagram.
    '''
    cellArea = domain.cellArea()
    ownerGrid = computeVoronoi( domain, sites, ids, obstacles, voronoiLimit )
    ownData = ownerGrid.cells
    # now compute density
    densityGrid = domain.getDataGrid( 0.0, np.float32 )
    rhoData = densityGrid.cells
    for id in ids:
        mask = ownData == id
        area = np.sum( mask ) * cellArea
        if ( area > 0.0001 ):
            rhoData[ mask ] = 1.0 / area
        else:
            rhoData[ mask ] = 0.0
    return densityGrid

##class Voronoi:
##    """ A class to partition world space into Voronoi region with agent's radius constraint """
##    def __init__( self, domain, obstacles=None  ):
##        """Constructor
##
##        Defines the domain         
##        @param minCorner is the bottom left corner of the world
##        @param size is the size of world grid
##        @param resolution is the resolution of the world grid
##        @param obstacles is an object of class obstacle handler which provides interace to find intersection with obstacles"""
##        self.minCorner = domain.minCorner
##        self.size = domain.size
##        self.resolution = domain.resolution
##        self.domain = domain
##        # Store shortest distance initally every cells has infinitely far away from agents
##        self.distGrid = self.domain.getDataGrid( MAX_DIST )
##        # Store index indicating who own the grid initially all the cells don't have any owner
##        self.ownerGrid = self.domain.getDataGrid( -1, np.int32 ) 
##        self.obstacles = obstacles
##    
##    def distField( self, points, startPt, l, r, b, t ):
##        '''computes the distance to testPoint of all the positions defined in points.
##
##        @param points:  an NxNx2 numpy array such that [i,j,:] is the x & y positions of the
##                    cell at (i, j)
##        @param testPoint: an 2x1 numpy array of the test point.
##        @returns an NxNx1 numpy array of the distances to testPoint.
##        '''
##        testPoint = startPt.reshape(1, 1, 2)
##        # Create a grid to store distance from cell (i,j) center to the agent position
##        # by default every cells are "infinitely" far away
##        if self.obstacles is not None:
##            h = t-b
##            w = r-l
##            if h < 0:
##                h = 0
##            if w < 0:
##                w = 0
##            dist = np.ones( (w,h) ) * MAX_DIST
##            for x in xrange( l,r ):
##                for y in xrange( b,t ):
##                    endPt = points[ x,y ]
##                    segment = Segment(Vector2( startPt[1], startPt[0] ), Vector2( endPt[1], endPt[0] ) )
##                    intersection = self.obstacles.findIntersectObject( segment )
##                    if intersection is None:
##                        disp = endPt - testPoint
####                        length = np.sum( disp * disp, axis=2)
##                        dist[ x-l, y-b ] = 1
####                        dist[ x-l, y-b ] = precomputeDist[ x-l, y-b ]
##        else:
##            disp = points[l:r, b:t] - testPoint
##            dist = np.sqrt( np.sum( disp * disp, axis=2 ) )
##        return dist
##
##    def computeVoronoi( self, worldGrid, frame, agentRadius ):
##        ''' Compute Voronoi region for particular frame
##        @param worldGrid: discrete world in grid form
##        @param frame: a NX2 storing agents' position
##        @agentRaidus: uniform agenet radius for each one
##        @obstacles: an obstacles Handler interface to interact with obstacles data structure
##        '''
##        # Size agent Radius in the grid space
##        hCount = int( 2 * agentRadius/worldGrid.cellSize[0] )
##        agentRadius *= agentRadius
##        if (hCount % 2 == 0):
##            hCount += 1
##        # Precomptue distance grid
##        o = np.arange( -(hCount/2), hCount/2 + 1) * worldGrid.cellSize[0]
##        X, Y = np.meshgrid(o, o)
##        def dFunc ( dispX, dispY, radiusSqd ):
##            disp = dispX * dispX + dispY * dispY
##            mask = disp <= radiusSqd
##            result = disp * mask
##            result[~mask] = MAX_DIST
##            return result
##        self.data = dFunc(X, Y, agentRadius)
##        
##        w, h = self.data.shape
##        w /= 2
##        h /= 2
##        if (frame.shape[0] != 0):
##            centers = worldGrid.getCenters()
##            # Calculate distance from agent[0] to every cell  in the grid
##            pos = frame[0,:]
##            # Find the index of the potential Voronoi Region with in the agentRadius away from the agent position
##            posCenter = worldGrid.getCenter( Vector2(pos[0], pos[1]) )
##            l = posCenter[0] - w 
##            r = posCenter[0] + w + 1 
##            b = posCenter[1] - h 
##            t = posCenter[1] + h + 1 
##            rl = 0
##            rb = 0
##            rr, rt = self.data.shape
##            
##            if ( l < 0 ):
##                rl -= l
##                l = 0
##            if ( b < 0 ):
##                rb -= b
##                b = 0
##            if ( r >= self.resolution[0] ):
##                rr -= r - self.resolution[0]
##                r = int( worldGrid.resolution[0] )
##            if ( t >= self.resolution[1] ):
##                rt -= t - self.resolution[1]
##                t = int( worldGrid.resolution[1] )
##    
##
##            if ( l < r and b < t and rl < rr and rb < rt ):
##                # We have to swap the x,y in the np.array becasue the getcenters return swaping coordinate due to meshgrid function call
##                self.distGrid.cells[l:r,b:t] = self.distField( centers, np.array((pos[0],pos[1])), l, r, b, t )
##                self.distGrid.cells[ l:r, b:t ] *= self.data[ rl:rr, rb:rt ]
##
##    
##            # if the distance is with in agent's radius then the cell belong to agent[0]
##            region = self.distGrid.cells <= agentRadius
##            # region = self.distGrid.cells[l:r,b:t] <= agentRadius
##            # Assign the cell's owner to be agent[0]
##            self.ownerGrid.cells[ region ] = 0
##            workDist = np.ones(self.distGrid.cells.shape) * MAX_DIST
##            for i in range( 1, frame.shape[0] ):
##                pos = frame[i, :]
##                posCenter = worldGrid.getCenter( Vector2(pos[0], pos[1]) )
##                l = posCenter[0] - w 
##                r = posCenter[0] + w + 1 
##                b = posCenter[1] - h 
##                t = posCenter[1] + h + 1 
##
##                rl = 0
##                rb = 0
##                rr, rt = self.data.shape
##                if ( l < 0 ):
##                    rl -= l
##                    l = 0
##                if ( b < 0 ):
##                    rb -= b
##                    b = 0
##                if ( r >= self.resolution[0] ):
##                    rr -= r - self.resolution[0]
##                    r = int( worldGrid.resolution[0] )
##                if ( t >= self.resolution[1] ):
##                    rt -= t - self.resolution[1]
##                    t = int( worldGrid.resolution[1] )
##                if ( l < r and b < t and rl < rr and rb < rt ):
##                    workDist[l:r,b:t] = self.distField( centers, np.array((pos[1],pos[0])), l, r, b, t )
##                    workDist[l:r,b:t] *= self.data[ rl:rr, rb:rt ]
##                    
##                region2 = workDist <= agentRadius
##                region3 = self.distGrid.cells > workDist
##                region = (workDist <= agentRadius) & ( self.distGrid.cells > workDist )
##                self.distGrid.cells[ region ] = workDist[region]
##                self.ownerGrid.cells[ region ] = i
##                workDist[l:r,b:t] = MAX_DIST
##                
##    def computeVoronoiDensity( self, worldGrid, frame, orgMinCorner, orgSize, orgResolution,
##                              orgDomainX, orgDomainY, paddingSize, agentRadius ):
##        # Agent Radius may be different from uniform kernel size
##        ''' Compute Voronoi region for each agent and then calculate density in that region
##        @param orgMinCorner is the bottom left corner before we add padding for Voronoi calculation
##        @param orgSize is the size before we add padding for Voronoi calculation
##        @param orgResolution is the resolution before we add padding for Voronoi calculation
##        @param orgDomainX is the domain in x before we add padding for Voronoi calculation
##        @param orgDomainY is the domain in y corner before we add padding for Voronoi calculation
##        @param paddingSize is the Vector2 of pad size added for Voronoi calculation
##        @return densityGrid contains density values computed from Voronoi'''
##        # Compute Voronoi region for current frame
##        # Store density in each cell of Voronoi region using 1/A
##        densityGrid = Grid( self.minCorner, self.size, self.resolution, initVal=0 )
##        self.computeVoronoi( worldGrid, frame, agentRadius )
##        for i in xrange( 0, frame.shape[0] ):
##            areaMask = self.ownerGrid.cells == i
##            area = areaMask.sum()
##            densityGrid.cells[areaMask] = (1./area)
##        densityGrid.minCorner = orgMinCorner
##        densityGrid.size = orgSize
##        densityGrid.resolution = orgResolution
##        temp = densityGrid.cells
##        xStart = paddingSize[0]
##        xEnd = xStart + orgResolution[0]
##        yStart = paddingSize[1]
##        yEnd = yStart + orgResolution[1]
##        densityGrid.cells = np.resize(temp,(orgResolution[0],orgResolution[1]))
##        densityGrid.cells[0:orgResolution[0],0:orgResolution[1]] = temp[xStart:xEnd,yStart:yEnd]
##        return densityGrid

def main():
    from GridFileSequence import GridFileSequence
    import optparse
    import sys, os
    import obstacles
    from trajectory import loadTrajectory
    parser = optparse.OptionParser()
    parser.set_description( 'Compute a sequence of discrete voronoi diagrams for a trajectory file' )
    parser.add_option( '-t', '--trajectory', help='The path to the trajectoroy data.',
                       action='store', dest='trajFileName', default='' )
    parser.add_option( '-x', '--xDomain', help='The extents of the region along x-axis',
                       nargs=2, action='store', type='float', dest='xRange', default=None )
    parser.add_option( '-y', '--yDomain', help='The extents of the region along y-axis',
                       nargs=2, action='store', type='float', dest='yRange', default=None )
    parser.add_option( '-c', '--cellSize', help='The size of the cell size in the discretization. Default is 0.1',
                       action='store', type='float', dest='cellSize', default=0.1 )
    parser.add_option( '-o', '--output', help='The path and base filename for the grid file sequence to be written -- no extension required. (Default is "output.voronoi").',
                       action='store', dest='output', default='./output' )
    parser.add_option( '-b', '--obstacles', help='Path to an obstacle xml file - not currently supported.',
                       action='store', dest='obstXML', default=None )
    parser.add_option( '-d', '--density', help='Indicates that the voronoi density should be computed and not the voronoi diagram',
                       action='store_true', default=False, dest='density' )
    options, args = parser.parse_args()

    if ( options.trajFileName == '' ):
        print '\n *** You must specify an input trajectory file'
        parser.print_help()
        sys.exit(1)

    if ( options.xRange is None ):
        print '\n *** You must specify the x-range'
        parser.print_help()
        sys.exit(1)

    if ( options.yRange is None ):
        print '\n *** You must specify the y-range'
        parser.print_help()
        sys.exit(1)

    folder, baseName = os.path.split( options.output )
    baseName, ext = os.path.splitext( baseName )
    # strip extension
    if ( folder ):
        if ( not os.path.exists( folder ) ):
            os.makedirs( folder )

    obstacles = None
    if ( options.obstXML ):
        obstacles, bb = obstacles.readObstacles( options.obstXML )

    

    minCorner = Vector2( options.xRange[0], options.yRange[0] )
    size = Vector2( options.xRange[1] - minCorner[0], options.yRange[1] - minCorner[1] )
    rX = int( np.ceil( size[0] / options.cellSize ) )
    rY = int( np.ceil( size[1] / options.cellSize ) )
    size = Vector2( rX * options.cellSize, rY * options.cellSize )
    voronoiDomain = AbstractGrid( minCorner, size, (rX, rY) )

    # currently assuming julich data for voronoi
    try:
        pedData = loadTrajectory( options.trajFileName )
    except ValueError:
        print "Unable to recognize the data in the file: %s" % ( options.trajFileName )
        sys.exit(1)

    if ( options.density ):
        print 'Computing density voronoi'
        gfs = GridFileSequence( os.path.join( folder, baseName ), obstacles, arrayType=np.float32 )
        gfs.computeVoronoiDensity( voronoiDomain, pedData, obstacles )
    else:
        print 'Computing normal voronoi'
        gfs = GridFileSequence( os.path.join( folder, baseName ), obstacles, arrayType=np.int32 )
        gfs.computeVoronoi( voronoiDomain, pedData, obstacles )

if __name__ == '__main__':
    main()
    