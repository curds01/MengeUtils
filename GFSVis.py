# Script for visualizing a grid file sequence

from Grid import DataGrid
import numpy as np
import pygame
from primitives import Vector2

def drawObstacle( obstacle, surface, grid ):
    '''Draws an obstacle on the a surface using the grid as the translation from
    world to image coordsinates.

    @param  obstacle        An instance of Obstacle (see obstacles.py)
    @param  surface         An instance of a pygame surface.  The obstacle will
                            be drawn on this surface.
    @param  grid            An instance of AbstractGrid (see Grid.py).
    '''
    OBST_COLOR = np.array( (128,128,128), dtype=np.uint8 )
    OBST_WIDTH = 1
    if ( obstacle.closed ):
        verts = map( lambda x: grid.getCenter( Vector2( x[0], x[1] ) ), obstacle.vertices )
        pygame.draw.polygon( surface, OBST_COLOR, verts )
    else:
        for seg in obstacle.segments:
            p0 = grid.getCenter( Vector2( seg.p1[0], seg.p1[1] ) )
            p1 = grid.getCenter( Vector2( seg.p2[0], seg.p2[1] ) )
            pygame.draw.line( surface, OBST_COLOR, (p0[0],p0[1]), (p1[0], p1[1]), OBST_WIDTH )
    

def visualizeGFS( gfsFile, cMap, outFileBase, imgFormat, mapRange=1.0, obstacles=None ):
    '''Visualizes a grid file sequence with the given color map.

    @param      gfsFile         An instance of a GridFileSequenceReader.  The grids to visualize.
    @param      cMap            An instance of ColorMap.  Indicates how the visualization works.
    @param      outFileBase     A string.  The basic name of the images to be output.
                                For each grid in the sequence, it outputs outFileBase_###.imgFormat.
                                The path must already exist.
    @param      imgFormat       A string.  The output image format (png, jpg, or bmp )
    @param      mapRange        A float.  Determines what fraction of the data range maps to the color
                                range.  For example, if mapRange is 0.75, then the value that is
                                75% of the way between the min and max value achieves the maximum
                                color value.
    @param      obstacles       An instance of ObstacleSet (optional).  If obstacle are provided,
                                Then they will be drawn over the top of the data.
    '''
    pygame.init()
    
    print gfsFile.summary()
    digits = int( np.ceil( np.log10( gfsFile.gridCount() ) ) )
    g = DataGrid( gfsFile.corner, gfsFile.size, ( gfsFile.w, gfsFile.h ) )
    minVal = gfsFile.range[0]
    maxVal = gfsFile.range[1]
    maxVal = ( maxVal - minVal ) * mapRange + minVal
    
    for gridData, gridID in gfsFile:
        g.cells[ :, : ] = gridData
        try:
            s = g.surface( cMap, minVal, maxVal )
        except MemoryError:
            print "Error on frame", i
            raise
        if ( not obstacles is None ):
            for obst in obstacles.polys:
                drawObstacle( obst, s, g )
        pygame.image.save( s, '{0}{1:0{2}d}.{3}'.format( outFileBase, gridID, digits, imgFormat ) )
    pygame.image.save( cMap.lastMapBar(7), '%sbar.png' % ( outFileBase ) )
        
        

if __name__ == '__main__':
    def test():
        from GridFileSequence import GridFileSequenceReader
        import obstacles
        import ColorMap
        import os
        obstPath = r'/projects/crowd/fund_diag/paper/pre_density/experiment/Inputs/Corridor_oneway/c240_obstacles.xml'
        path = r'/projects/crowd/fund_diag/paper/pre_density/experiment/results/density/gaussian_S1.5/uo-065-240-240_combined_MB.density'
        outPath = r'/projects/crowd/fund_diag/paper/pre_density/experiment/results/density/gaussian_S1.5/uo-065-240-240_combined_MB_density/'
        if ( not os.path.exists( outPath ) ):
            os.makedirs( outPath )
##        colorMap = ColorMap.TwoToneHSVMap( (180, 1, 1), (270, 1, 1) )
##        colorMap = ColorMap.GreyScaleMap()
##        colorMap = ColorMap.BlackBodyMap()
##        colorMap = ColorMap.StephenBlackBodyMap()
##        colorMap = ColorMap.LogBlackBodyMap()
        colorMap = ColorMap.BandedBlackBodyMap()
##        colorMap = ColorMap.RedBlueMap()
        reader = GridFileSequenceReader( path )
        reader.setNext( 0 )
        obstacles, bb = obstacles.readObstacles( obstPath )
        mapRange = 1.5
        visualizeGFS( reader, colorMap, outPath, 'png', mapRange, obstacles )

    test()    
    