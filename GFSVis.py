# Script for visualizing a grid file sequence

from Grid import DataGrid
import numpy as np
import pygame
from primitives import Vector2

def drawSites( sites, surface, grid, radius=3 ):
    '''Draws dots at the site locations onto the provided surface.

    @param      sites       An Nx2 numpy array of locations in world coordinates.
    @param      surface     An instance of a pygame Surface.  The sites will be
                            drawn onto this surface.
    @param      grid        An instance of AbstractGrid (see Grid.py)  Used to map
                            from world to image coordinates.
    @param      radius      A float.  The radius of the sites (in pixels)
    '''
    RADIUS = 3
    for site in sites:
        x, y = grid.getCenter( Vector2( site[0], site[1] ) )
        y = grid.resolution[1] - y
        pygame.draw.circle( surface, (0,0,0), (x,y), radius + 2 )
        pygame.draw.circle( surface, (255, 255, 255), (x,y), radius )
            
def drawObstacles( obstacles, surface, grid ):
    '''Draws an obstacle on the a surface using the grid as the translation from
    world to image coordsinates.

    @param  obstacles       An instance of ObstacleSet (see obstacles.py)
    @param  surface         An instance of a pygame surface.  The obstacles will
                            be drawn on this surface.
    @param  grid            An instance of AbstractGrid (see Grid.py).  Used to map
                            from world to image coordinates.
    '''
    OBST_COLOR = np.array( (128,128,128), dtype=np.uint8 )
    OBST_WIDTH = 1
    for obst in obstacles.polys:
        if ( obst.closed ):
            verts = map( lambda x: grid.getCenter( Vector2( x[0], x[1] ) ), obst.vertices )
            pygame.draw.polygon( surface, OBST_COLOR, verts )
        else:
            for seg in obst.segments:
                p0 = grid.getCenter( Vector2( seg.p1[0], seg.p1[1] ) )
                p1 = grid.getCenter( Vector2( seg.p2[0], seg.p2[1] ) )
                pygame.draw.line( surface, OBST_COLOR, (p0[0],p0[1]), (p1[0], p1[1]), OBST_WIDTH )
    

def visualizeGFS( gfsFile, cMap, outFileBase, imgFormat, mapRange=1.0, sites=None, obstacles=None ):
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
    @param      sites           An Nx2 numpy array of locations in world coordinates.
    @param      obstacles       An instance of ObstacleSet (optional).  If obstacle are provided,
                                Then they will be drawn over the top of the data.
    '''
    pygame.init()
    
    print gfsFile.summary()
    digits = int( np.ceil( np.log10( gfsFile.gridCount() ) ) )
    minVal = gfsFile.range[0]
    maxVal = gfsFile.range[1]
    maxVal = ( maxVal - minVal ) * mapRange + minVal
    
    for grid, gridID in gfsFile:
        try:
            s = grid.surface( cMap, minVal, maxVal )
        except MemoryError:
            print "Error on frame", i
            raise
        if ( sites ):
            frame, frameID = sites.next()
            drawSites( frame, s, grid )
        if ( not obstacles is None ):
            drawObstacles( obstacles, s, grid )
        pygame.image.save( s, '{0}{1:0{2}d}.{3}'.format( outFileBase, gridID, digits, imgFormat ) )
    pygame.image.save( cMap.lastMapBar(7), '%sbar.png' % ( outFileBase ) )
        
        

if __name__ == '__main__':
    def main():
        from GridFileSequence import GridFileSequenceReader
        import optparse
        import ColorMap
        import sys, os
        import obstacles
        import IncludeHeader
        from trajectoryReader import SeyfriedTrajReader
        parser = optparse.OptionParser()
        parser.add_option( '-i', '--input', help='A path to a grid file sequence - the data to visualize',
                           action='store', dest='input', default='' )
        parser.add_option( '-t', '--trajectory', help='(Optional) The path to the pedestrian data which produced the voronoi diagrams.',
                           action='store', dest='trajName', default=None )
        parser.add_option( '-o', '--output', help='The path and base filename for the output images (Default is "vis").',
                           action='store', dest='output', default='./vis' )
        parser.add_option( '-c', '--colorMap', help='Specify the color map to use.  Valid values are: %s.  Defaults to "black_body".' % ColorMap.getValidColorMaps(),
                           action='store', dest='cmapName', default='black_body' )
        parser.add_option( '-e', '--extension', help='Image format: [png, jpg, bmp] (default is png)',
                           action='store', dest='ext', default='png' )
        parser.add_option( '-b', '--obstacles', help='Path to an obstacle xml file',
                           action='store', dest='obstXML', default=None )
        options, args = parser.parse_args()

        if ( options.input == '' ):
            print '\n *** You must specify an input file'
            parser.print_help()
            sys.exit(1)

        try:
            colorMap = ColorMap.getColorMapByName( options.cmapName )
        except KeyError:
            print '\n *** You have selected an invalid color map: %s' % ( options.cmapName )
            parser.print_help()
            sys.exit(1)

        if ( not options.ext.lower() in ( 'png', 'jpg', 'bmp' ) ):
            print '\n *** You have selected an invalid file format: %s' % ( options.ext )
            parser.print_help()
            sys.exit(1)

        trajData = None
        if ( options.trajName ):
            trajData = SeyfriedTrajReader( 1 / 16.0 )
            trajData.readFile( options.trajName )
            trajData.setNext( 0 )

        folder, baseName = os.path.split( options.output )
        if ( folder ):
            if ( not os.path.exists( folder ) ):
                os.makedirs( folder )

        reader = GridFileSequenceReader( options.input )
        reader.setNext( 0 )    

        obstacles = None
        if ( options.obstXML ):
            obstacles, bb = obstacles.readObstacles( options.obstXML )

        visualizeGFS( reader, colorMap, options.output, options.ext, 1.0, trajData, obstacles )
        
    main()    
    