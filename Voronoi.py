import IncludeHeader
from Grid import *
from primitives import Vector2, Segment
from ObstacleStructure import *
import pylab as plt
import drawVoronoi
##from ObjectHandler import *
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
        # Store shortest distance initally every cells has infinitely far away from agents
        self.distGrid = DataGrid( self.minCorner, self.size, self.resolution, 10000. )
        # Store index indicating who own the grid initially all the cells don't have any owner
        self.ownerGrid = DataGrid( self.minCorner, self.size, self.resolution, -1, np.int32 )
        self.obstacles = obstacles
    
    def distField( self, points, startPt, l, r, b, t ):
       '''computes the distance to testPoint of all the positions defined in points.

        @param points:  an NxNx2 numpy array such that [i,j,:] is the x & y positions of the
                    cell at (i, j)
        @param testPoint: an 2x1 numpy array of the test point.
        @returns an NxNx1 numpy array of the distances to testPoint.
        '''
       testPoint = startPt.reshape(1, 1, 2)
       if self.obstacles is not None:
           for x in xrange(l, r):
               for y in xrange(b, t):
                   endPt = points[x,y]
                   segment = Segment(Vector2(startPt[1], startPt[0]), Vector2(endPt[1], endPt[0]))
                   intersection = self.obstacles.findIntersectObject( segment )
                   if intersection is not None:
                       points[x,y] = MAX_DIST
##                       print intersection
                   # Do line intersection with every object in the scene
                   # if there is intersection then the point is not part of the voronoi -> assign very large value
                   # else it is in the voronoi
                   
       disp1 = points - testPoint
       disp = points[l:r, b:t] - testPoint
       dist = np.sqrt( np.sum( disp * disp, axis=2 ) )
       return dist
    
    def computeVoronoi( self, worldGrid, frame, agentRadius=1.0 ):
        ''' Compute Voronoi region for particular frame
        @param worldGrid: discrete world in grid form
        @param frame: a NX2 storing agents' position
        @agentRaidus: uniform agenet radius for each one
        @obstacles: an obstacles Handler interface to interact with obstacles data structure
        '''
        # Size agent Radius in the grid space
        radiusW = agentRadius/worldGrid.cellSize[0]
        radiusH = agentRadius/worldGrid.cellSize[1]
##        radiusW = agentRadius/self.cellSize[0]
##        radiusH = agentRadius/self.cellSize[1]
        if (radiusW % 2 == 0):
            radiusW += 1
        if (radiusH % 2 == 0):
            radiusH += 1
        if (frame.shape[0] != 0):
            centers = worldGrid.getCenters()
            # Calculate distance from agent[0] to every cell in the grid
            pos = frame[0,:]
            # Find the index of the potential Voronoi Region
            posCenter = worldGrid.getCenter( Vector2(pos[0], pos[1]) )
            l = int( posCenter[0] - radiusW )
            r = int( posCenter[0] + radiusW + 1 )
            b = int( posCenter[1] - radiusH )
            t = int( posCenter[1] + radiusH + 1 )
            if ( l < 0 ):
                l = 0
            if ( b < 0 ):
                b = 0
            if ( r >= self.resolution[0] ):
                r = int( worldGrid.resolution[0] )
            if ( t >= self.resolution[1] ):
                t = int( worldGrid.resolution[1] )
                
            # Swapping the x,y to map the with the color
##            self.distGrid.cells = self.distField( centers, np.array((pos[1],pos[0])) )
            # we have to swap the x,y in the np.array becasue the getcenters return swaping coordinate due to meshgrid
            self.distGrid.cells[l:r,b:t] = self.distField( centers, np.array((pos[1],pos[0])), l, r, b, t )
            # if the distance is with in agent's radius then the cell belong to agent[0]
            region = self.distGrid.cells <= agentRadius
            # region = self.distGrid.cells[l:r,b:t] <= agentRadius
            # Assign the cell's owner to be agent[0]
            self.ownerGrid.cells[ region ] = 0
            workDist = np.ones(self.distGrid.cells.shape) * MAX_DIST
            for i in xrange( 1, frame.shape[0] ):
                pos = frame[i, :]
                posCenter = worldGrid.getCenter( Vector2(pos[0], pos[1]) )
                l = int( posCenter[0] - radiusW )
                r = int( posCenter[0] + radiusW + 1 )
                b = int( posCenter[1] - radiusH )
                t = int( posCenter[1] + radiusH + 1 )
                if ( l < 0 ):
                    l = 0
                if ( b < 0 ):
                    b = 0
                if ( r >= self.resolution[0] ):
                    r = int( worldGrid.resolution[0] )
                if ( t >= self.resolution[1] ):
                    t = int( worldGrid.resolution[1] )
##                workDist = self.distField( centers, np.array((pos[1],pos[0])) )
                workDist[l:r,b:t] = self.distField( centers, np.array((pos[1],pos[0])), l, r, b, t )
                region = (self.distGrid.cells > workDist) & (workDist <= agentRadius)
##                region = (self.distGrid.cells > workDist) & (workDist <= agentRadius)
                self.distGrid.cells[ region ] = workDist[region]
                self.ownerGrid.cells[ region ] = i
                workDist[l:r,b:t] = MAX_DIST
                
    def computeVoronoiDensity( self, worldGrid, frame, agentRadius=1 ):
        ''' Compute Voronoi region for each agent and then calculate density in that region'''
        # Compute Voronoi region for current frame
        # Store density in each cell of Voronoi region using 1/A
        densityGrid = Grid( self.minCorner, self.size, self.resolution, initVal=0 )
        self.computeVoronoi( worldGrid, frame, agentRadius)
        for i in xrange( 0, frame.shape[0] ):
            areaMask = self.ownerGrid.cells == i
            area = areaMask.sum()
            densityGrid.cells[areaMask] = (1./area)
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
                             
    plt.imshow(  v.ownerGrid.cells[::-1, :] )
    plt.show()

if __name__ == '__main__':
    main()