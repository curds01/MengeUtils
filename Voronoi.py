import IncludeHeader

import math
from Grid import AbstractGrid
from primitives import Vector2, Segment
import pylab as plt
import drawVoronoi

MAX_DIST = 1000.0

class Voronoi:
    """ A class to partition world space into Voronoi region with agent's radius constraint """
    def __init__( self, minCorner, size, resolution, obstacles=None  ):
        """ frame is a list of agent in the world at that point in time; worldGrid
        @param minCorner is the bottom left corner of the world
        @param size is the size of world grid
        @param resolution is the resolution of the world grid
        @param obstacles is an object of class obstacle handler which provides interace to find intersection with obstacles"""
        self.minCorner = minCorner
        self.size = size
        self.resolution = resolution
        self.domain = AbstractGrid( minCorner, size, resolution )
        # Store shortest distance initally every cells has infinitely far away from agents
        self.distGrid = self.domain.getDataGrid( MAX_DIST )
        # Store index indicating who own the grid initially all the cells don't have any owner
        self.ownerGrid = self.domain.getDataGrid( -1, np.int32 ) 
        self.obstacles = obstacles
    
    def distField( self, points, startPt, l, r, b, t ):
        '''computes the distance to testPoint of all the positions defined in points.

        @param points:  an NxNx2 numpy array such that [i,j,:] is the x & y positions of the
                    cell at (i, j)
        @param testPoint: an 2x1 numpy array of the test point.
        @returns an NxNx1 numpy array of the distances to testPoint.
        '''
        testPoint = startPt.reshape(1, 1, 2)
        # Create a grid to store distance from cell (i,j) center to the agent position
        # by default every cells are "infinitely" far away
        if self.obstacles is not None:
            h = t-b
            w = r-l
            if h < 0:
                h = 0
            if w < 0:
                w = 0
            dist = np.ones( (w,h) ) * MAX_DIST
            for x in xrange( l,r ):
                for y in xrange( b,t ):
                    endPt = points[ x,y ]
                    segment = Segment(Vector2( startPt[1], startPt[0] ), Vector2( endPt[1], endPt[0] ) )
                    intersection = self.obstacles.findIntersectObject( segment )
                    if intersection is None:
                        disp = endPt - testPoint
##                        length = np.sum( disp * disp, axis=2)
                        dist[ x-l, y-b ] = 1
##                        dist[ x-l, y-b ] = precomputeDist[ x-l, y-b ]
        else:
            disp = points[l:r, b:t] - testPoint
            dist = np.sqrt( np.sum( disp * disp, axis=2 ) )
        return dist

    def computeVoronoi( self, worldGrid, frame, agentRadius ):
        ''' Compute Voronoi region for particular frame
        @param worldGrid: discrete world in grid form
        @param frame: a NX2 storing agents' position
        @agentRaidus: uniform agenet radius for each one
        @obstacles: an obstacles Handler interface to interact with obstacles data structure
        '''
        # Size agent Radius in the grid space
        hCount = int( 2 * agentRadius/worldGrid.cellSize[0] )
        agentRadius *= agentRadius
        if (hCount % 2 == 0):
            hCount += 1
        # Precomptue distance grid
        o = np.arange( -(hCount/2), hCount/2 + 1) * worldGrid.cellSize[0]
        X, Y = np.meshgrid(o, o)
        def dFunc ( dispX, dispY, radiusSqd ):
            disp = dispX * dispX + dispY * dispY
            mask = disp <= radiusSqd
            result = disp * mask
            result[~mask] = MAX_DIST
            return result
        self.data = dFunc(X, Y, agentRadius)
        
        w, h = self.data.shape
        w /= 2
        h /= 2
        if (frame.shape[0] != 0):
            centers = worldGrid.getCenters()
            # Calculate distance from agent[0] to every cell  in the grid
            pos = frame[0,:]
            # Find the index of the potential Voronoi Region with in the agentRadius away from the agent position
            posCenter = worldGrid.getCenter( Vector2(pos[0], pos[1]) )
            l = posCenter[0] - w 
            r = posCenter[0] + w + 1 
            b = posCenter[1] - h 
            t = posCenter[1] + h + 1 
            rl = 0
            rb = 0
            rr, rt = self.data.shape
            
            if ( l < 0 ):
                rl -= l
                l = 0
            if ( b < 0 ):
                rb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                rr -= r - self.resolution[0]
                r = int( worldGrid.resolution[0] )
            if ( t >= self.resolution[1] ):
                rt -= t - self.resolution[1]
                t = int( worldGrid.resolution[1] )
    

            if ( l < r and b < t and rl < rr and rb < rt ):
                # We have to swap the x,y in the np.array becasue the getcenters return swaping coordinate due to meshgrid function call
                self.distGrid.cells[l:r,b:t] = self.distField( centers, np.array((pos[1],pos[0])), l, r, b, t )
                self.distGrid.cells[ l:r, b:t ] *= self.data[ rl:rr, rb:rt ]

    
            # if the distance is with in agent's radius then the cell belong to agent[0]
            region = self.distGrid.cells <= agentRadius
            # region = self.distGrid.cells[l:r,b:t] <= agentRadius
            # Assign the cell's owner to be agent[0]
            self.ownerGrid.cells[ region ] = 0
            workDist = np.ones(self.distGrid.cells.shape) * MAX_DIST
            for i in range( 1, frame.shape[0] ):
                pos = frame[i, :]
                posCenter = worldGrid.getCenter( Vector2(pos[0], pos[1]) )
                l = posCenter[0] - w 
                r = posCenter[0] + w + 1 
                b = posCenter[1] - h 
                t = posCenter[1] + h + 1 

                rl = 0
                rb = 0
                rr, rt = self.data.shape
                if ( l < 0 ):
                    rl -= l
                    l = 0
                if ( b < 0 ):
                    rb -= b
                    b = 0
                if ( r >= self.resolution[0] ):
                    rr -= r - self.resolution[0]
                    r = int( worldGrid.resolution[0] )
                if ( t >= self.resolution[1] ):
                    rt -= t - self.resolution[1]
                    t = int( worldGrid.resolution[1] )
                if ( l < r and b < t and rl < rr and rb < rt ):
                    workDist[l:r,b:t] = self.distField( centers, np.array((pos[1],pos[0])), l, r, b, t )
                    workDist[l:r,b:t] *= self.data[ rl:rr, rb:rt ]
                    
                region2 = workDist <= agentRadius
                region3 = self.distGrid.cells > workDist
                region = (workDist <= agentRadius) & ( self.distGrid.cells > workDist )
                self.distGrid.cells[ region ] = workDist[region]
                self.ownerGrid.cells[ region ] = i
                workDist[l:r,b:t] = MAX_DIST
                
    def computeVoronoiDensity( self, worldGrid, frame, orgMinCorner, orgSize, orgResolution,
                              orgDomainX, orgDomainY, paddingSize, agentRadius ):
        # Agent Radius may be different from uniform kernel size
        ''' Compute Voronoi region for each agent and then calculate density in that region
        @param orgMinCorner is the bottom left corner before we add padding for Voronoi calculation
        @param orgSize is the size before we add padding for Voronoi calculation
        @param orgResolution is the resolution before we add padding for Voronoi calculation
        @param orgDomainX is the domain in x before we add padding for Voronoi calculation
        @param orgDomainY is the domain in y corner before we add padding for Voronoi calculation
        @param paddingSize is the Vector2 of pad size added for Voronoi calculation
        @return densityGrid contains density values computed from Voronoi'''
        # Compute Voronoi region for current frame
        # Store density in each cell of Voronoi region using 1/A
        densityGrid = Grid( self.minCorner, self.size, self.resolution, initVal=0 )
        self.computeVoronoi( worldGrid, frame, agentRadius )
        for i in xrange( 0, frame.shape[0] ):
            areaMask = self.ownerGrid.cells == i
            area = areaMask.sum()
            densityGrid.cells[areaMask] = (1./area)
        densityGrid.minCorner = orgMinCorner
        densityGrid.size = orgSize
        densityGrid.resolution = orgResolution
        temp = densityGrid.cells
        xStart = paddingSize[0]
        xEnd = xStart + orgResolution[0]
        yStart = paddingSize[1]
        yEnd = yStart + orgResolution[1]
        densityGrid.cells = np.resize(temp,(orgResolution[0],orgResolution[1]))
        densityGrid.cells[0:orgResolution[0],0:orgResolution[1]] = temp[xStart:xEnd,yStart:yEnd]
        return densityGrid

def main():
    import os
    print os.getcwd()
    MIN_CORNER = Vector2(-5.0, -5.0)
    SIZE = Vector2(10.0, 10.0)
    RES = Vector2(101,101)

    worldGrid = Grid( MIN_CORNER, SIZE, RES, Vector2(0,3.2), Vector2(-6,6), MAX_DIST )

    frame = np.array( ( (0, 0) ,
                        (-0.3, 0) ,
                         ( 1, 4 ),
                         ( 2.5, -1 ),
                         (-2, 1),
                         (3,3),
                         (4.5, -4.5)
                     )
                   )

    import obstacles
    obst, bb = obstacles.readObstacles( 'obst.xml' )
    agentRadius = 1.0
    v = Voronoi( MIN_CORNER,SIZE, RES )
    v.computeVoronoiDensity( worldGrid, frame, agentRadius )
    drawVoronoi.drawVoronoi( v.ownerGrid.cells, "Voronoi_test.png", obst, v.ownerGrid ) 

if __name__ == '__main__':
    main()