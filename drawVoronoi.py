import pygame as pg
import numpy as np
from primitives import Vector2

def drawVoronoi( data, fileName, obstacles=None, grid=None ):
    '''Creates an image of the voronoi diagram specified by the ownerData
    and saves it out as fileName.  If an ObstacleSet is provided, it also
    draws the obstacles - must also provide a grid.'''
    COLORS = np.array( ( (255, 0 ,0),
                         (127, 0, 0 ),
                         (0, 255, 0 ),
                         (0, 127, 0 ),
                         (0, 0, 255 ),
                         ( 0, 0, 127 ),
                         (255, 255, 0 ),
                         (0, 255, 255 ),
                         (255, 0, 255 ),
                         (200, 200, 200),
                         (255, 255, 255) ),
                       dtype=np.uint8 )
    BG_COLOR = np.array( (0,0,0), dtype=np.uint8 )
    OBST_COLOR = np.array( (255,255,255), dtype=np.uint8 )
    OBST_WIDTH = 1
    def imgSpace( point, grid ):
        '''Given a grid and a point in world space, returns the grid cell value.'''
        return grid.getCenter( point )
    
    COLOR_COUNT = COLORS.shape[0]
    color = np.zeros( ( data.shape[0], data.shape[1], 3 ), dtype=np.uint8 )
    bg = data == -1
    indices = data % COLOR_COUNT
    color[~bg, : ] = COLORS[ indices[~bg] ]
    color[ bg, : ] = BG_COLOR

    surf = pg.surfarray.make_surface( color[:, ::-1, : ] )
    if (obstacles and grid):
        for seg in obstacles.structure.data:
            # Have to changet the coordinate between position of agent and obstacles
            # obstacle increase as moving down y-axis position decrease as moving down y-axis
            sta = Vector2(seg.p1[0], -seg.p1[1])
            end = Vector2(seg.p2[0], -seg.p2[1])
            p0 = imgSpace( sta, grid )
            p1 = imgSpace( end, grid )
            pg.draw.line( surf, OBST_COLOR, (p0[0],p0[1]), (p1[0], p1[1]), OBST_WIDTH )
##            Original Implementation
##    if ( obstacles and grid ):
##        for obst in obstacles.polys:
##            for seg in obst.segments:
##                p0 = imgSpace( seg.p1, grid )
##                p1 = imgSpace( seg.p2, grid )
##                pg.draw.line( surf, OBST_COLOR, (p0[0], p0[1]), (p1[0], p1[1]), OBST_WIDTH )
    pg.image.save( surf, fileName )


if __name__ == '__main__':
    data = np.zeros( (200, 200), dtype=np.int )
    for col in xrange( data.shape[1] ):
        data[col, : ] = col / 5
    drawVoronoi( data, 'test.png' )