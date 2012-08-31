# A simple test of the kernel and signal functionality

# python modules
import numpy as np
import pygame
import os

# objreader modules
import Grid
import Kernels
import Signals
from primitives import Vector2
from ColorMap import BlackBodyMap
import obstacles 
import ObstacleHandler
from Voronoi import *
from trajectory import loadTrajectory

# GLOBALS

PATH = 'ktest'
if ( not os.path.exists( PATH ) ):
    os.makedirs( PATH )

cMap = BlackBodyMap()
CELL_SIZE = 0.03125 #0.05
smoothParam = 1.5

REFLECT = True
obst, bb = obstacles.readObstacles( '/projects/crowd/fund_diag/paper/pre_density/experiment/Inputs/Corridor_onewayDB/c240_obstacles.xml')
obstSet = ObstacleHandler.ObjectHandler( obst )
##kernel = Kernels.UniformKernel( smoothParam, CELL_SIZE, REFLECT )
##kernel = Kernels.TriangleKernel( smoothParam / 1.1, CELL_SIZE, REFLECT )
##kernel = Kernels.BiweightKernel( smoothParam / 1.2, CELL_SIZE, REFLECT )
kernel = Kernels.GaussianKernel( smoothParam / 3.0, CELL_SIZE, REFLECT )
##kernel = Kernels.Plaue11Kernel( smoothParam, CELL_SIZE, REFLECT, obstSet )
      
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
    # pedestrian domain
    minCorner = Vector2( 0.0, -6 )
    domainSize = Vector2( 2.4, 12 )
    pedDomain = Grid.RectDomain( minCorner, domainSize )
    # grid domain
    minCorner = Vector2( 0.0, -2 )
    domainSize = Vector2( 2.4, 4 )
    resolution = Vector2( domainSize.x / CELL_SIZE, domainSize.y / CELL_SIZE)
    gridDomain = Grid.AbstractGrid( minCorner, domainSize, resolution )

    # load pedestrian data
    pedFile = '/projects/crowd/fund_diag/paper/pre_density/experiment/Inputs/Corridor_onewayDB/uo-065-240-240_combined_MB.txt'
    try:
        data = loadTrajectory ( pedFile )
    except ValueError:
        print "Unable to recognize the data in the file: %s" % ( pedFile )
        return
    grids = []

    sig = Signals.PedestrianSignal( pedDomain )
    print gridDomain
    
    while ( True ):
        try:
            sig.setData( data )
        except StopIteration:
            break
        grid = gridDomain.getDataGrid() 
        kernel.convolve( sig, grid )
##        grid.cells /= ( CELL_SIZE * CELL_SIZE )

        print "Frame %d has min/max values: %f, %f" % ( sig.index, grid.minVal(), grid.maxVal() )        
        grids.append( grid )
##        break

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

    pedDomain = Grid.RectDomain( minCorner, domainSize )    
    sig = Signals.DiracSignal( pedDomain )
    
    for i in xrange( STEP_COUNT ):
        sig.setData( traj[:, :, i] )
        grid = Grid.DataGrid( minCorner, domainSize, resolution )
        kernel.convolve( sig, grid )
##        grid.cells /= ( CELL_SIZE * CELL_SIZE )
        grids.append( grid )
    
    visGrids( grids )
    
def debugFieldConvolve():
    '''Test field convolution with a simple'''
    global CELL_SIZE
    if ( False ):       # synthetic
        SCALE = 10#30
        K_SIZE = 1.5
        R = False
##        kernel = Kernels.UniformKernel(  K_SIZE * SCALE * CELL_SIZE, CELL_SIZE, R )
        kernel = Kernels.TriangleKernel( K_SIZE * SCALE * CELL_SIZE / 1.1, CELL_SIZE, R )
##        kernel = Kernels.BiweightKernel( K_SIZE / 1.2 * SCALE * CELL_SIZE, CELL_SIZE, R )
##        kernel = Kernels.GaussianKernel( K_SIZE / 3.0 * SCALE * CELL_SIZE, CELL_SIZE, R )
        
        # synthetic data
        # define the domain
        W = 8 * SCALE
        H = 10 * SCALE
        minCorner = Vector2( -W / 2.0, -H / 2.0 )
        domainSize = Vector2( W * CELL_SIZE, H * CELL_SIZE )
        resolution = ( W, H )
    
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
        kernel = Kernels.UniformKernel( K_SIZE, CELL_SIZE, R )
##        kernel = Kernels.TriangleKernel( K_SIZE / 1.1, CELL_SIZE, R )
##        kernel = Kernels.BiweightKernel( K_SIZE / 1.2, CELL_SIZE, R )
##        kernel = Kernels.GaussianKernel( K_SIZE / 3.0, CELL_SIZE, R )
        minCorner = Vector2( 0.0, -4.0 )
        width = 2.4
        height = 8.0
        resolution = ( int( np.ceil( width / CELL_SIZE ) ), int( np.ceil( height / CELL_SIZE ) ) )
        domainSize = Vector2( resolution[0] * CELL_SIZE, resolution[1] * CELL_SIZE )
        sigGrid = Grid.DataGrid( minCorner, domainSize, resolution )
        computeVornoiField( sigGrid )
        signal = Signals.FieldSignal( sigGrid )
        # set up convolution grid
        corner = Vector2( 0.0, -3 )
        height = 6.0
        resolution = ( int( np.ceil( width / CELL_SIZE ) ), int( np.ceil( height / CELL_SIZE ) ) )
        domainSize = Vector2( resolution[0] * CELL_SIZE, resolution[1] * CELL_SIZE )
        grid = Grid.DataGrid( corner, domainSize, resolution )

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
    '''Computes a voronoi field and caches it to the folder.  If already cached, it simply loads it.
    It places the voronoi field INTO the given grid.'''
    VORONOI_FILE = os.path.join( PATH, 'testVoronoi.npy' )
    def makeVoronoi( grid ):
        print 'COMPUTING VORONOI!'
        pedFile = '/projects/crowd/fund_diag/paper/pre_density/experiment/Inputs/Corridor_onewayDB/dummy.txt'
        try:
            data = loadTrajectory( pedFile )
        except ValueError:
            print "Unable to recognize the data in the file: %s" % ( pedFile )
        frame, frameId = data.next()
        density = computeVoronoiDensity( grid, frame, data.getFrameIds() )
        grid.cells[ :, : ] = density.cells
        
    if ( not os.path.exists( VORONOI_FILE ) ):
        makeVoronoi( grid )
    else:
        data = np.load( VORONOI_FILE )
        if ( data.shape != grid.resolution ):
            makeVoronoi( grid )
        else:
            grid.cells[:,:] = data
    
        
if __name__ == '__main__':
##    testSynthetic()
    testPedestrian()
##    testSyntheticField()
##    debugFieldConvolve()
