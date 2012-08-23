# A simple test of the kernel and signal functionality

import Grid
import Kernels
import Signals
from primitives import Vector2
import numpy as np
from ColorMap import BlackBodyMap
import pygame
import os
import IncludeHeader
from trajectoryReader import SeyfriedTrajReader
import obstacles 
import ObstacleHandler
from Voronoi import Voronoi
# GLOBALS

PATH = 'ktest'
if ( not os.path.exists( PATH ) ):
    os.makedirs( PATH )

cMap = BlackBodyMap()
CELL_SIZE = 0.05
smoothParam = 1.0

REFLECT = True
obst, bb = obstacles.readObstacles( '/projects/crowd/fund_diag/paper/pre_density/experiment/Inputs/Corridor_onewayDB/c240_obstacles.xml')
obstSet = ObstacleHandler.ObjectHandler( obst )
kernel = Kernels.Plaue11Kernel( smoothParam, CELL_SIZE, REFLECT, obstSet )
##kernel = Kernels.GaussianKernel( smoothParam, CELL_SIZE, REFLECT )
##kernel = Kernels.UniformKernel( smoothParam, CELL_SIZE, REFLECT )
      
def syntheticPedestrians( SIZE ):
    '''Produce a set of fake pedestrian trajectories.

    @param      SIZE        The size of the origin-centered simulation domain.
    @returns    An Nx2xM numpy array with N pedestrians over M frames and
                    The number of steps in the trajectory.
    '''
    STEP_COUNT = 15
    traj = np.empty( (3, 2, STEP_COUNT ), dtype=np.float32 )
    # ped 1 - moves bottom left to top center
    start = -SIZE * 0.5 + 0.1
    end = 0
    x = np.linspace( start, end, STEP_COUNT )
    y = np.linspace( start, -start, STEP_COUNT )
    traj[ 0, 0, : ] = x
    traj[ 0, 1, : ] = y
    # ped 2 - moves from bottom right to top left
    x = np.linspace( -start, start, STEP_COUNT )
    y = np.linspace( start, -start, STEP_COUNT )
    traj[ 1, 0, : ] = x
    traj[ 1, 1, : ] = y
    # ped 3 - moves from left to right
    x = np.linspace( start, -start, STEP_COUNT )
    y = np.zeros_like( x ) + 0.25
    traj[ 2, 0, : ] = x
    traj[ 2, 1, : ] = y
    return traj, STEP_COUNT

def visGrids( grids, frames=None ):
    '''Given a set of grids, visualizes the grids'''
    # define limits of grid
    pygame.init()
    minVal = 0
    maxVal = 0
    for g in grids:
        M = g.maxVal()
        if ( M > maxVal ):
            maxVal = M
    print "Vis grids"
    print "\t(min, max):", minVal, maxVal

    RADIUS = int( np.ceil( 0.19 / CELL_SIZE ) )
    for i, grid in enumerate( grids ):
        s = grid.surface( cMap, minVal, maxVal )
        # memory leak in writing png.
        if ( frames ):
            try:
                frame, frameID = frames.next()
            except StopIteration:
                break
            for impulse in frame:
                x, y = grid.getCenter( Vector2( impulse[0], impulse[1] ) )
                y = int( grid.resolution[1] ) - y
                pygame.draw.circle( s, ( 50, 50, 255 ), (x,y), RADIUS )
        pygame.image.save( s, os.path.join( PATH, '%03d.png' % i ) )
    pygame.image.save( cMap.lastMapBar(7),
                       os.path.join( PATH, 'bar.png' ) )

def testPedestrian():
    '''Test against legitimate pedestrian data'''
    minCorner = Vector2( 0.0, -4.0 )
    domainSize = Vector2( 2.4, 8 )
    resolution = Vector2( domainSize.x / CELL_SIZE, domainSize.y / CELL_SIZE)

    # load pedestrian data
    data = SeyfriedTrajReader( 1 / 16.0 )
    data.readFile( '/projects/crowd/fund_diag/paper/pre_density/experiment/Inputs/Corridor_onewayDB/uo-065-240-240_combined_MB.txt' )
##    data.readFile( '/projects/crowd/fund_diag/paper/pre_density/experiment/Inputs/Corridor_onewayDB/dummy.txt' )
    data.setNext( 0 )
    grids = []
    while ( True ):
        try:
            sig = Signals.PedestrianSignal( data )
        except StopIteration:
            break
        grid = Grid.DataGrid( minCorner, domainSize, resolution )
        kernel.convolve( sig, grid )
        grid.cells /= ( CELL_SIZE * CELL_SIZE )
        
        grids.append( grid )

    data.setNext( 0 )    
    visGrids( grids, data )

def testSynthetic():
    '''Test against a synthetic set of pedestrians'''
    SIZE = 10.0
    # define the domain
    minCorner = Vector2( -SIZE / 2.0, -SIZE / 2.0 )
    domainSize = Vector2( SIZE, SIZE )
    RES = int( SIZE / CELL_SIZE )
    resolution = Vector2( RES, RES )
   
    # define the signal ( a single point, moving from the origin to the corner
    traj, STEP_COUNT = syntheticPedestrians( SIZE )

    print "Maximum kernel value:", kernel.data.max()
    print "Kernel sum:          ", kernel.data.sum()
    grids = []
    
    for i in xrange( STEP_COUNT ):
        sig = Signals.DiracSignal( traj[:, :, i] )
        grid = Grid.DataGrid( minCorner, domainSize, resolution )
        kernel.convolve( sig, grid )
        grid.cells /= ( CELL_SIZE * CELL_SIZE )
        grids.append( grid )
    
    visGrids( grids )
    
def debugFieldConvolve():
    '''Test field convolution with a simple'''
    global CELL_SIZE
    if ( False ):       # synthetic
        SCALE = 10#30
        K_SIZE = 7.5
        R = False
##        kernel = Kernels.UniformKernel( K_SIZE * SCALE * CELL_SIZE, CELL_SIZE, R )
        kernel = Kernels.GaussianKernel( K_SIZE / 3.0 * SCALE * CELL_SIZE, CELL_SIZE, R )
##        kernel = Kernels.BiweightKernel( K_SIZE / 1.2 * SCALE * CELL_SIZE, CELL_SIZE, R )
        # synthetic data
        # define the domain
        W = 8 * SCALE
        H = 10 * SCALE
        minCorner = Vector2( -W / 2.0, -H / 2.0 )
        domainSize = Vector2( W * CELL_SIZE, H * CELL_SIZE )
        resolution = Vector2( W, H )
    
        data = np.zeros( ( W, H ), dtype=np.float32 )
        print data.shape
        winset = W / 2 - 2 * SCALE
        hinset = W / 2 - 2 * SCALE
        data[ winset:-winset, hinset:-hinset ] = 1.0
        grid = Grid.DataGrid( minCorner, domainSize, resolution )
        sigGrid = Grid.DataGrid()
        sigGrid.copyDomain( grid )
        sigGrid.cells[ :, : ] = data
        signal = Signals.FieldSignal( sigGrid )
    else:
        # voronoi signal
        CELL_SIZE = 0.025
        K_SIZE = 1.0
        R = True
##        kernel = Kernels.UniformKernel( K_SIZE, CELL_SIZE, R )
##        kernel = Kernels.BiweightKernel( K_SIZE / 1.2, CELL_SIZE, R )
##        kernel = Kernels.GaussianKernel( K_SIZE / 3.0, CELL_SIZE, R )
        kernel = Kernels.TriangleKernel( K_SIZE / 1.1, CELL_SIZE, R )
        minCorner = Vector2( 0.0, -4.0 )
        width = 2.4
        height = 8.0
        resolution = ( int( np.ceil( width / CELL_SIZE ) ), int( np.ceil( height / CELL_SIZE ) ) )
        domainSize = Vector2( resolution[0] * CELL_SIZE, resolution[1] * CELL_SIZE )
        grid = Grid.DataGrid( minCorner, domainSize, resolution )
        data = computeVornoiField( grid )
        signal = Signals.FieldSignal( data )
        sigGrid = Grid.DataGrid()
        sigGrid.copyDomain( grid )
        sigGrid.cells[ :, : ] = data
        signal = Signals.FieldSignal( sigGrid )

    print "Input signal max:", sigGrid.cells.max()
    print "Input signal sum:", sigGrid.cells.sum()
    minVal = 0
    maxVal = sigGrid.cells.max()
    s = sigGrid.surface( cMap, minVal, maxVal )
    pygame.image.save( s, os.path.join( PATH, 'fieldBefore.png' ) )

    kernel.convolve( signal, grid )
    s = grid.surface( cMap, minVal, maxVal )
    print "Convolved signal max:", grid.cells.max()
    print "Convolved signal sum:", grid.cells.sum()
    pygame.image.save( s, os.path.join( PATH, 'fieldAfter.png' ) )

def computeVornoiField( grid ):
    '''Computes a voronoi field and caches it to the folder.  If already cached, it simply loads it.'''
    VORONOI_FILE = os.path.join( PATH, 'testVoronoi.npy' )
    def makeVoronoi( grid ):
        print 'COMPUTING VORONOI!'
        cellArea = grid.cellSize[0] * grid.cellSize[1] 
        voronoi = Voronoi( grid.minCorner, grid.size, grid.resolution, obstSet )
        data = SeyfriedTrajReader( 1 / 16.0 )
        data.readFile( '/projects/crowd/fund_diag/paper/pre_density/experiment/Inputs/Corridor_onewayDB/dummy.txt' )
        data.setNext( 0 )
        frame, frameId = data.next()
        voronoi.computeVoronoi( grid, frame, 3.0 )
        data = voronoi.ownerGrid.cells
        # convert to density
        print frame.shape
        density = np.zeros( data.shape, dtype=np.float32 )
        for id in xrange( -1, frame.shape[0] ):
            mask = data == id
            area = np.sum( mask ) * cellArea
            if ( area > 0.0001 ):
                density[ mask ] = 1 / area
            else:
                density[ mask ] = 0
        
        np.save( VORONOI_FILE, density )
        return density
    if ( not os.path.exists( VORONOI_FILE ) ):
        return makeVoronoi( grid )
    data = np.load( VORONOI_FILE )
    if ( data.shape != grid.resolution ):
        return makeVoronoi( grid )
    return data
    
        
if __name__ == '__main__':
##    testSynthetic()
##    testPedestrian()
##    testSyntheticField()
    debugFieldConvolve()
    