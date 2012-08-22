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
    PATH = 'ktest'
    if ( not os.path.exists( PATH ) ):
        os.makedirs( PATH )

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
    
def testSyntheticField():
    '''Test field convolution with a simple'''
    PATH = 'ktest'
    if ( not os.path.exists( PATH ) ):
        os.makedirs( PATH )
        
    SIZE = 10.0
    # define the domain
    minCorner = Vector2( -SIZE / 2.0, -SIZE / 2.0 )
    domainSize = Vector2( SIZE, SIZE )
    RES = int( SIZE / CELL_SIZE )
    resolution = Vector2( RES, RES )
    
    data = np.zeros( ( RES, RES ), dtype=np.float32 )
    print data.shape
    inset = RES / 2 - SIZE * 0.25 / CELL_SIZE
##    data[0,0] = 1.0
    data[ inset:-inset, inset:-inset ] = 1.0
    print data.min(),data.max()
    signal = Signals.FieldSignal( data )
    grid = Grid.DataGrid( minCorner, domainSize, resolution )
    grid.cells[:,:] = data
    print grid.cells.min(), grid.cells.max()
    s = grid.surface( cMap, grid.cells.min(), grid.cells.max() )
    pygame.image.save( s, os.path.join( PATH, 'fieldBefore.png' ) )
    grid.clear()
##    kernel = Kernels.GaussianKernel( smoothParam, CELL_SIZE, REFLECT )
    kernel = Kernels.UniformKernel( smoothParam, CELL_SIZE, REFLECT )
    kernel.convolve( signal, grid )
    s = grid.surface( cMap, grid.cells.min(), grid.cells.max() )
    pygame.image.save( s, os.path.join( PATH, 'fieldAfter.png' ) )

def testVoronoiField():
    PATH = 'ktest'
    if ( not os.path.exists( PATH ) ):
        os.makedirs( PATH )
        
    SIZE = 10.0
    # define the domain
    minCorner = Vector2( -SIZE / 2.0, -SIZE / 2.0 )
    domainSize = Vector2( SIZE, SIZE )
    RES = int( SIZE / CELL_SIZE )
    resolution = Vector2( RES, RES )
    grid = Grid.DataGrid( minCorner, domainSize, resolution )
    voronoi = Voronoi( minCorner, domainSize, resolution, obstSet)
    data = SeyfriedTrajReader( 1 / 16.0 )
    data.readFile( '/projects/crowd/fund_diag/paper/pre_density/experiment/Inputs/Corridor_onewayDB/dummy.txt' )
    data.setNext( 0 )
    frame, frameId = data.next()
    voronoi.computeVoronoi( grid, frame, 3.0 )
    signal = Signals.FieldSignal( voronoi.ownerGrid.cells )

    grid = Grid.DataGrid( minCorner, domainSize, resolution )
    print "VORONOI min/max", voronoi.ownerGrid.cells.min(), voronoi.ownerGrid.cells.max()
    grid.cells[:,:] = voronoi.ownerGrid.cells
    print "GRID cells", grid.cells.min(), grid.cells.max()
    s = grid.surface( cMap, grid.cells.min(), grid.cells.max() )
    RADIUS = int( np.ceil( 0.19 / CELL_SIZE ) )
    for impulse in frame:
            x, y = grid.getCenter( Vector2( impulse[0], impulse[1] ) )
            y = int( grid.resolution[1] ) - y
            pygame.draw.circle( s, ( 50, 50, 255 ), (x,y), RADIUS )
    pygame.image.save( s, os.path.join( PATH, 'vfieldBefore.png' ) )
    grid.clear()
    kernel = Kernels.GaussianKernel( smoothParam, CELL_SIZE, REFLECT )
##    kernel = Kernels.UniformKernel( smoothParam, CELL_SIZE, REFLECT )
    kernel.convolve( signal, grid )
    s = grid.surface( cMap, grid.cells.min(), grid.cells.max() )
    pygame.image.save( s, os.path.join( PATH, 'vfieldAfter.png' ) )
    
        
if __name__ == '__main__':
##    testSynthetic()
##    testPedestrian()
##    testSyntheticField()
    testVoronoiField()
    