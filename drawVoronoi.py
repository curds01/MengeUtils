import pygame as pg
import numpy as np
from primitives import Vector2
from GFSVis import drawObstacles, drawSites
import os

def drawVoronoi( dataGrid, fileName, sites=None, obstacles=None ):
    '''Creates an image of the voronoi diagram, optionally drawing sites
    and obstacles as provided.

    @param      dataGrid    An instance of GridData.  Contains the integer data
                            for the voronoi diagram.
    @param      fileName    A string. The name to save the image as.
    @param      sites       An instance of pedestrian data (simulated or actual).
                            An Nx2 numpy array of x-/y-positions of the agents that
                            produced the Voronoi diagram.
                            If provided, dots are drawn, otherwise, no sites.
    @param      obstacles   An instance of ObstacleSet.  If provided, obstacles
                            will be drawn over the top of the voronoi diagram.
    '''
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
    cells = dataGrid.cells
    color = np.zeros( ( cells.shape[0], cells.shape[1], 3 ), dtype=np.uint8 )
    bg = cells == -1
    indices = cells % COLOR_COUNT
    color[~bg, : ] = COLORS[ indices[~bg] ]
    color[ bg, : ] = BG_COLOR

    surf = pg.surfarray.make_surface( color[:, ::-1, : ] )
    if ( not sites is None ):
        drawSites( sites, surf, dataGrid )
            
    if ( not obstacles is None ):
        for obst in obstacles.polys:
                drawObstacle( obst, surf, dataGrid )
    pg.image.save( surf, fileName )

def drawVoronoiSeries( gfsData, outBaseName, trajData=None, obstacles=None, ext='png' ):
    '''Given a GridFileSequence of voronoi diagrams, draws the sequence.

    @param      gfsData         An instance of GridFileSequenceReader.
    @param      outBaseName     A string.  The path (including file name base) to which the
                                images should be written.
    @param      trajData        An instance of a quasi-iterable trajectory data (scbData or
                                SeyfriedTrajectoryReader) The trajectory data which produced the
                                voronoi diagram. If provided, the agent positions will be drawn
                                as dots over the voronoi diagram.
    @param      obstacles       An instance of ObstacleSet.  If provided, obstacles will be
                                drawn over the top of the voronoi diagram and sites.
    @param      ext             A string.  The file type to save the files as.
    '''
    pg.init()

    # make sure the path exists
    path, name = os.path.split( outBaseName )
    if ( not os.path.exists( path ) ):
        os.makedirs( path )    

    print gfsData.summary()
    digits = int( np.ceil( np.log10( gfsData.gridCount() ) ) )

    for grid, gridID in gfsData:
        
        frame = None
        if ( trajData ):
            try:
                frame, frameID = trajData.next()
            except StopIteration:
                break
        fileName = '{0}{1:0{2}d}.{3}'.format( outBaseName, gridID, digits, ext )
        try:
            drawVoronoi( grid, fileName, frame, obstacles )
        except MemoryError:
            print "Error on frame", i
            raise

if __name__ == '__main__':
    def main():
        from GridFileSequence import GridFileSequenceReader
        import optparse
        import sys, os
        import obstacles
        from trajectory import loadTrajectory
        parser = optparse.OptionParser()
        parser.set_description( 'Visualize a sequence of voronoi diagrams in a GridFileSequence' )
        parser.add_option( '-i', '--input', help='A path to a grid file sequence - the data to visualize',
                           action='store', dest='gfsName', default='' )
        parser.add_option( '-t', '--trajectory', help='(Optional) The path to the pedestrian data which produced the voronoi diagrams.',
                           action='store', dest='trajName', default=None )
        parser.add_option( '-o', '--output', help='The path and base filename for the output images (Default is "vis").',
                           action='store', dest='output', default='./vis' )
        parser.add_option( '-e', '--extension', help='Image format: [png, jpg, bmp] (default is png)',
                           action='store', dest='ext', default='png' )
        parser.add_option( '-b', '--obstacles', help='(Optional) Path to an obstacle xml file.  If provided, they will be drawn on top of the voronoi.',
                           action='store', dest='obstXML', default=None )
        options, args = parser.parse_args()

        if ( options.gfsName == '' ):
            print '\n *** You must specify an input GridFileSequence file'
            parser.print_help()
            sys.exit(1)

        if ( not options.ext.lower() in ( 'png', 'jpg', 'bmp' ) ):
            print '\n *** You have selected an invalid file format: %s' % ( options.ext )
            parser.print_help()
            sys.exit(1)

        folder, baseName = os.path.split( options.output )
        if ( folder ):
            if ( not os.path.exists( folder ) ):
                os.makedirs( folder )

        trajData = None
        if ( not options.trajName is None ):
            try:
                trajData = loadTrajectory( options.trajName )
            except ValueError:
                print "Unable to recognize the data in the file: %s" % ( options.trajName )

        reader = GridFileSequenceReader( options.gfsName )
        reader.setNext( 0 )    

        obstacles = None
        if ( options.obstXML ):
            obstacles, bb = obstacles.readObstacles( options.obstXML )

        drawVoronoiSeries( reader, options.output, trajData, obstacles )
        
    main()    
    