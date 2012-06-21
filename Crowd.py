# Basic framework/structures for perfomring analysis of crowds
#   Agent positions are rasterized onto a grid

# TODO:
#   - Stream processing
#       - Each unnormalized grid should get output to a file
#       - the file can then be re-processed to normalize across all grids
#       - this normalization can be extended to normalize multiple files
#   - multi-threaded
#       - Process multiple frames at a time (one frame on each processor)
#           - each finished grid gets dumped into a queue
#           - additional thread streams to the file from the queue (making sure they get
#             written in an ordered fashion.
#   - dump out legend
#       - bar showing the color map with units and amounts and description labeled.
#   - speed seems flawed
#   - Draw in obstacles (lowest priority)

from math import sqrt, ceil
import struct
import pygame
import numpy as np
import threading
import time
from ColorMap import *
from Kernels import Kernel
from Grid import *
from GridFileSequence import *
from qtcontext import GLLine
from flow import *
from primitives import Vector2
from scbData import FrameSet
from trace import renderTraces
import pylab as plt
from ObjSlice import Polygon
from obstacles import *
import pylab as plt

class StatRecord:
    '''A simple, callable object for accumulating statistical information about the
    quanity being computed and rasterized'''
    def __init__( self, agentCount ):
        # frame data is an N x 2 array.  N = number of times it is called.
        # It contains the following data:
        #   mean, std deviation, min, max
        self.frameData = []
        # agent data is the data for all of the agents in a single frame
        self.agentData = np.zeros( agentCount, dtype=np.float32 )
        self.currAgent = 0

    def __call__( self, value ):
        '''Assign the current value to the current agent'''
        self.agentData[ self.currAgent ] = value
        self.currAgent += 1

    def nextFrame( self ):
        '''Prepares the data for the next frame'''
        self.frameData.append( ( self.agentData[:self.currAgent].mean(), self.agentData[:self.currAgent].std(), self.agentData[:self.currAgent].min(), self.agentData[:self.currAgent].max(), self.currAgent ) )
        self.currAgent = 0

    def write( self, fileName ):
        '''Outputs the data into a text file'''
        f = open( fileName, 'w' )
        for m, s, minVal, maxVal, agtCount in self.frameData:
            f.write( '{0:>15}{1:>15}{2:>15}{3:>15}{4:>15}\n'.format( m, s, minVal, maxVal, agtCount ) )
        f.close()

    def savePlot( self, fileName, title ):
        '''Saves a plot of the data to the specified filename'''
        plt.figure()
        data = np.array( self.frameData )
        x = np.arange( data.shape[0] ) + 1
        plt.errorbar( x, data[:,0], data[:,1] )
        plt.ylim( ( data[:,2].min(), data[:,3].max() ) )
        plt.title( title )
        plt.savefig( fileName )
        
##class RasterReport:
##    """Simple class to return the results of rasterization"""
##    def __init__( self ):
##        self.maxVal = 0.0
##        self.count = 0
##
##    def incCount( self ):
##        self.count += 1
##
##    def setMax( self, val ):
##        if ( val > self.maxVal ):
##            self.maxVal = val
            
class BufferGrid:
    """Entry into a buffer for a grid"""
    def __init__( self, id, grid ):
        self.id = id
        self.grid = grid

    def __eq__( self, id ):
        return self.id == id

    def __str__( self ):
        return "BufferGrid %d, %f" % ( self.id, self.grid.maxVal() )
    
### The   that does the rasterization work
##ACTIVE_RASTER_THREADS = 0
##def threadRasterize( log, bufferLock, buffer, frameLock, frameSet, minCorner, size, resolution, distFunc, maxRad ):
##    while ( True ):
##        # create grid and rasterize
##        # acquire frame
##        frameLock.acquire()
##        try:
##            frame, index = frameSet.next()
##        except StopIteration:
##            break
##        finally:            
##            frameLock.release()
##        g = Grid( minCorner, size, resolution )
##        g.rasterizePosition( frame, distFunc, maxRad )
##        # update log
##        log.setMax( g.maxVal() )
##        log.incCount()
##        # put into buffer
##        bufferLock.acquire()
##        buffer.append( BufferGrid(index, g ) )
##        bufferLock.release()
####        # acquire next frame
####        frameLock.acquire()
####        frame, index = frameSet.next()
####        frameLock.release()
##
### the thread that does the file output
##def threadOutput( outFile, buffer, bufferLock, startTime ):
##    """Reads grids from the buffer and writes them to the output file"""
##    nextGrid = 0
##    while ( buffer or ACTIVE_RASTER_THREADS ):
##        # keep doing the work as long as the buffer has contents or there are active raster threads
##        bufferLock.acquire()
##        try:
##            i = buffer.index( nextGrid )
##            bg = buffer.pop( i )
##            bufferLock.release()
##            print "\t\tWriting buffer %d at time %f s" % ( nextGrid, time.clock() - startTime )
##            outFile.write( bg.grid.binaryString() )
##            nextGrid += 1
##        except ValueError:
##            bufferLock.release()
##            time.sleep( 1.0 )
                
##          HELPER FUNCTION FOR REGION TESTS
def findCurrentRegion( frame, polygons, excludeStates ):
    '''Given a frame, determines which region each agent is in.
    Performs a brute-force search across all regions'''
    regions = np.zeros( len( frame.agents ), dtype=np.int )
    for a, agt in enumerate( frame.agents ):
        if ( agt.state in excludeStates ): continue
        poly = -1
        for i, p in enumerate( polygons ):
            if ( p.pointInside( agt.pos ) ):
                poly = i
                break
        assert poly != -1
        regions[a] = poly
    return regions

def updateRegion( currRegion, pos, polygons ):
    '''Given a Vector2 (pos) and the expectation of its last known region, provides
    a new region assignment.'''
    if ( polygons[ currRegion ].pointInside( pos ) ):
        return currRegion
    else:
        test = ( currRegion + 1 ) % len( polygons )
        if ( polygons[ test ].pointInside( pos ) ):
            return test
        else:
            return currRegion

def findRegionSpeed( f1, f2, timeStep, polygons, excludeStates, regions=None ):
    '''Given a frame of data, and a set of polygons computes the average region speed for
    each region.  If regions is a Nx1 array (for N agents in frame) then it uses a smart
    mechanism for determining which region the agent is in (and updates it accordingly)
    Otherwise, it performs the brute-force search.
    Returns an Mx1 array (for M polygons) and the regions object.'''
    # if regions is defined, it's the location of the region for f1
    #   This region accumulates the speed

    regions = findCurrentRegion( f2, polygons, excludeStates )
    speeds = np.zeros( len(polygons), dtype=np.float32 )
    counts = np.zeros( len(polygons), dtype=np.int )
    for a, ag1 in enumerate( f1.agents ):
        if ( f2.agents[a].state in excludeStates ): continue
        # compute speed
        p1 = ag1.pos
        p2 = f2.agents[ a ].pos
        disp = (p2 - p1).magnitude()
        speed = disp / timeStep
        
        # increment counters and accumulators
        speeds[ regions[a] ] += speed
        counts[ regions[a] ] += 1

    mask = counts != 0
    speeds[ mask ] /= counts[ mask ]
    return speeds, regions
    

def drawPolygonPG( surf, polygon, worldToImg, color, width ):
    '''Given a surface, a polygon, a color and a function mapping polygon coordinates to image coordinates,
    draws the polygon on the pygame surface'''
    points = []
    for v in polygon.vertices:
        points.append( worldToImg( v ) )
    pygame.draw.polygon( surf, color, points, width )

def drawPolygons( surf, polygons, worldToImg, colors ):
    '''Given an ordered list of polygons and an ordered list of colors, draws the polygons to the
        provided surface with boundaries'''
    # draw the filled-in shapes
    for i, p in enumerate( polygons ):
        drawPolygonPG( surf, p, worldToImg, colors[i], 0 )
    # draw the outlines
    for p in polygons:
        drawPolygonPG( surf, p, worldToImg, (0,0,0), 5 )
        
        
def regionSpeedImages( dataFile, imagePath, polygons, colorMap, minCorner, size, resolution ):
    data = np.loadtxt( dataFile )
    data = data.mean( axis=0 )
    print data
    minVal = data.min()
    maxVal = data.max()
    print "\tmin:", minVal
    print "\tmax:", maxVal
    for p in xrange( data.size ):
        print "Polygon", p, "has speed:", data[p], "and rgb:", colorMap.getColor( data[p], (minVal, maxVal) )

    pygame.image.save( colorMap.mapBar( (minVal, maxVal), 7), '%sbar.png' % ( imagePath ) )

    # write the polygons to an image
    g = AbstractGrid( minCorner, size, resolution )
    surf = pygame.Surface( resolution )
    surf.fill( (128, 128, 128 ) )
    worldToImg = lambda x: g.getCenter( x )
    colors = [ colorMap.getColor( data[p], (minVal, maxVal) ) for p in range( data.size ) ]
    drawPolygons( surf, polygons, worldToImg, colors )
    obstacles, junk = readObstacles( 'matafFloor.xml' )
##    obstacles, junk = readObstacles( 'allMatafObst.xml' )
    m = pygame.image.load( 'regionMask.png' )
    drawPolygons( surf, obstacles.polys, worldToImg, [(255,255,255) for p in obstacles.polys] )
    surf = pygame.transform.flip( surf, False, True )
##    surf.blit( m, m.get_rect( ) )
    pygame.image.save( surf, '%s.png' % ( imagePath ) )
    
def firstDeriv( data, timeStep, k=1 ):
    '''Computes a 2nd order approximation of the first derivative using
    center-differences and the appropriate, 2nd-order, one-sided stencil at the ends.
    It samples values k elements away with dt equal to timestep for each step'''
    deriv = np.zeros_like( data )
    # center differences
    denom = 1.0 / ( 2 * k * timeStep )
    deriv[ k:-k ] = ( data[ 2 * k: ] - data[ :-2*k ] ) * denom
    # one-sided
    # start
##    deriv[ :k ] = ( data[k:2*k] - data[:k] ) / ( k * timeStep )
##    deriv[ :k ] = ( -3 * data[:k] + 4 * data[k:2*k] - data[2*k:3*k] ) * denom
    #end
##    deriv[ -k: ] = ( -data[-k:] + 4 * data[-2*k:-k] -3 * data[-3*k:-2*k] ) * denom
    return deriv
    
def gaussKernel1D( dx, sigma ):
    '''Create a 1D gaussian kernel with given sigma, sampled every dx values'''
    width = 6 * sigma
    kWidth = int( width / dx + 0.5 )

    if ( kWidth % 2 == 0 ):
        kWidth += 1
    hWidth = kWidth / 2
    x = np.linspace( -hWidth * dx, hWidth * dx, kWidth )
    A = 1.0 / ( sigma * np.sqrt( 2 * np.pi ) )
    kernel = A * np.exp( -( x * x ) / ( 2 * sigma * sigma ) )
    return kernel

def plotFlow( outFileName, timeStep, titlePrefix='', legendStr=None, newFig=False, xlimits=None, ylimits=None ):
    '''Given the data in outFileName and the given timestep, creates plots'''
    # SMOOTH IT
    SIGMA = 8.0
    kernel = gaussKernel1D( 1.0, SIGMA )

    if ( newFig ):
        fig = plt.figure()
    else:
        plt.clf()
        fig = plt.gcf()
    
    dataFile = outFileName + ".flow"
    data = np.loadtxt( dataFile )
    data[:,0] *= timeStep
    smoothFlows = np.empty_like( data[:, 1:] )
    for col in xrange( data.shape[1] - 1 ):
        smoothFlows[:, col] = np.convolve( data[:, col+1], kernel, 'same' )
    ax = fig.add_subplot(2,1,1)
    ax.set_title( '%s - Flow' % titlePrefix )
##    plt.plot( data[:,0], data[:, 1:], linewidth=0.25 )
    plt.plot( data[:,0], smoothFlows )
    if ( legendStr == None ):
        legendStr = [ 'Line %d' % i for i in range( data.shape[1] - 1 ) ]
    plt.legend( legendStr, loc='upper left' )
##    plt.xlabel( 'Simulation time (s)' )
    plt.ylabel( 'Agents past marker' )
    ax = fig.add_subplot(2,1,2)
    #plt.plot( data[:,0], np.clip( firstDeriv( data[:,1:], timeStep, 6 * 16 ), 0.0, 1e6 ) )
    plt.plot( data[:,0], np.clip( firstDeriv( smoothFlows, timeStep, 4 * 16 ), 0.0, 1e6 ) )
    plt.xlabel( 'Simulation time (s)' )
    plt.ylabel( 'Flow (agents/s)' )
    if ( xlimits != None ):
        plt.xlim( xlimits )
    if ( ylimits != None ):
        plt.ylim( ylimits )
    
    plt.savefig( outFileName + ".flow.png" )
    plt.savefig( outFileName + ".flow.eps" )

def computeFlow( frameSet, segments, outFileName ):
    '''Compute the flow of agents past the indicated line segments.
    Output is an NxM array where there are N time steps and M segments.
    Each segment has direction and every agent will only be counted at most once w.r.t.
    each segment.'''
    # In this scenario, there are N agents and M segments

    # compute parameters for each segment
    segCount = len( segments )
    agtCount = frameSet.agentCount()
    # these are the x and y values of each segment's 0th and 1st points
    S0X = np.zeros( (1, segCount ) )
    S0Y = np.zeros( (1, segCount ) )
    S1X = np.zeros( (1, segCount ) )
    S1Y = np.zeros( (1, segCount ) )
    for i, seg in enumerate( segments ):
        S0X[ 0, i ] = seg.p1.x
        S0Y[ 0, i ] = seg.p1.y
        S1X[ 0, i ] = seg.p2.x
        S1Y[ 0, i ] = seg.p2.y
    dX = S1X - S0X
    dY = S1Y - S0Y
    L = np.sqrt( dX * dX + dY * dY )
    # this (plus S0X/S0Y) used to determine if position lies between
    dX /= L
    dY /= L
    # this computes signed distance to LINE on which segment lies
    A = -dY
    B = dX
    C = dY * S0X - dX * S0Y
        
    outFile = open( outFileName + '.flow', 'w' )

    frameSet.setNext( 0 )
    # the number of agents who have crossed each segment
    crossed = np.zeros( segCount, dtype=np.int )
    # An NxM array indicating which segment each agent has already crossed
    alreadyCrossed = np.zeros( ( agtCount, segCount ), dtype=np.bool )
    
    outFile.write('{0:10d}'.format( 0 ) )
    for val in crossed:
        outFile.write('{0:10d}'.format( val ) )
    outFile.write('\n')

    # prime the set by computing the data for the first frame
    frame, idx = frameSet.next()
    ids = frameSet.getFrameIds()   # mapping from frame IDs to global IDs
    frameIDs = map( lambda x: ids[ x ], xrange( frame.shape[0] ) )
    
    # note: I'm doing this strange syntax so that they are Nx1 arrays (instead of just N arrays)
    #   this makes the broadcasting work better.
    pX = frame[:, :1 ]
    pY = frame[:, 1:2 ]

    # SDIST: an N x M array.  The cell[i, j] reports if agent i is on the right side of
    #   segment j to cross it (according to indicated flow direction)
    PREV_SDIST = ( A * pX + B * pY + C ) < 0 
    T = (pX - S0X) * dX + (pY - S0Y) * dY
    # BETWEEN: an N x M array.  The cell[i, j] reports if the agent i lies between the endpoints
    #   of segment j.
    BETWEEN = ( T >= 0 ) & ( T <= L )
    # COULD_CROSS: an N x M array.  The cell[i, j] reports if the agent i is in a position to
    #   cross segment j.  (i.e., it lies between the endpoints and is on the negative side.)
    COULD_CROSS = np.zeros( ( agtCount, segCount ), dtype=np.bool )
    
    # Only process the agents that are in the frame
    COULD_CROSS[ frameIDs, : ] = PREV_SDIST & BETWEEN
##    COULD_CROSS = PREV_SDIST & BETWEEN
    
    while ( True ):
        try:
            frame, idx = frameSet.next()
        except StopIteration:
            break
        else:
            ids = frameSet.getFrameIds()   # mapping from frame IDs to global IDs
            frameIDs = map( lambda x: ids[ x ], xrange( frame.shape[0] ) )
        # compute crossability for the current frame
        pX = frame[:, :1 ]
        pY = frame[:, 1:2 ]
##        if ( idx > 30 and idx < 40 ):
##            print "Frame:", idx
##            print "\tAgents in frame: ", frameIDs
##            print "\tx:", pX.T
##            print "\ty:", pY.T
        SDIST = ( A * pX + B * pY + C ) < 0 
        T = (pX - S0X) * dX + (pY - S0Y) * dY
        BETWEEN = ( T >= 0 ) & ( T <= L )
##        if ( idx > 30 and idx < 40 ):
##            print "\tSDIST:", SDIST
##            print "\tBETWEEN:", BETWEEN
##            print "\tCOULD_CROSS:", COULD_CROSS[ frameIDs,: ]
        # in order to cross, in the previous time step, I had to be in a position to cross
        #   and in this frame, my sign has to reversed AND I have to not already crossed it.
        CROSSED = COULD_CROSS[ frameIDs, : ] & ~SDIST & ~alreadyCrossed[ frameIDs, : ]
        alreadyCrossed[ frameIDs, : ] |= CROSSED
        crossed += CROSSED.sum( axis=0 )
        outFile.write('{0:10d}'.format( idx ) )
        for val in crossed:
            outFile.write('{0:10d}'.format( val ) )
        outFile.write('\n')
        COULD_CROSS[ frameIDs, : ] = SDIST & BETWEEN
##        prevIdx = idx
##        frame, idx = frameSet.next()

    outFile.close()

    crossings = alreadyCrossed.sum( axis=1 )
    print "The following agents never crossed:", np.where( crossings == 0 )
    
def computeFlowLines( center, lines, frameSet ):
    """Computes the flow of agents past the various lines"""
    # THIS VERSION IS HEAVILY TAWAF-CENTRIC - the simple computeFlow is far more generic
    # initialize
    flowRegion = FlowLineRegion()
    for line in lines:
        flowRegion.addLine( line.p1, line.p2 )
    flowRegion.sortLines( center )
    print flowRegion

    frameSet.setNext( 0 )
    f, i = frameSet.next()
    flowRegion.sortAgents( f.agents )

    f, i = frameSet.next( True )
    while( True ):
        flowRegion.step()
        try:
            f, i = frameSet.next( True )
        except StopIteration:
            break
    return flowRegion
    
def main():
    """Test the functionality"""
    from math import pi, exp
    import os, sys
    import optparse
    parser = optparse.OptionParser()
    # analysis to perform
    parser.add_option( "-d", "--density", help="Evaluate density.",
                       action="store_true", dest='density', default=False )
    parser.add_option( "-s", "--speed", help="Evaluate speed.",
                       action="store_true", dest='speed', default=False )
    parser.add_option( "-o", "--omega", help="Evaluate omega.",
                       action="store_true", dest='omega', default=False )
    parser.add_option( "-p", "--progress", help="Evaluate progress.",
                       action="store_true", dest='progress', default=False )
    parser.add_option( "-k", "--koshak", help="Evaluate koshak regions.",
                       action="store_true", dest='koshak', default=False )
    parser.add_option( "-i", "--include", help="Include all states",
                       action="store_true", dest='includeAll', default=False )
    # analysis domain - start, frame count, frame step
    parser.add_option( "-r", "--range", help="A triple of numbers: start frame, max frame count, frame step",
                       nargs=3, action="store", dest='domain', type="int", default=(0, -1, 1) )
    options, args = parser.parse_args()

    # input source file
    srcFile = sys.argv[1]
    pygame.init()
    CELL_SIZE = 0.2
    MAX_AGENTS = -1
    MAX_FRAMES = -1
    FRAME_STEP = 1
    FRAME_WINDOW = 1
    START_FRAME = 0
    EXCLUDE_STATES = ()

    START_FRAME, MAX_FRAMES, FRAME_STEP = options.domain
    print "Command line:", START_FRAME, MAX_FRAMES, FRAME_STEP

    if ( True ):
        #increase the color bar specifications
        ColorMap.BAR_HEIGHT = 300
        ColorMap.BAR_WIDTH = 30
        ColorMap.FONT_SIZE = 20
    
    timeStep = 1.0
    outPath = '.'
    if ( False ):
        size = Vector2(12.0, 12.0 )
        minPt = Vector2( size.x / -2.0, size.y / -2.0 )
        res = (int( size.x / CELL_SIZE ), int( size.y / CELL_SIZE ) )
        path = 'data/Circle10/playbackPLE.scb'
    elif ( False ):
        size = Vector2(60.0, 60.0 )
        minPt = Vector2( size.x / -2.0, size.y / -2.0 )
        res = (int( size.x / CELL_SIZE ), int( size.y / CELL_SIZE ) )
        path = '/projects/SG10/CrowdViewer/Exe/Win32/2circle/playback.scb'        
##        path = '/projects/SG10/CrowdViewer/Exe/Win32/2circle/playbackRVO.scb'
    elif ( False ):
        size = Vector2( 150.0, 110.0 )
        minPt = Vector2( -70.0, -55.0 )
        res = (int( size.x / CELL_SIZE ), int( size.y / CELL_SIZE ) )
##        srcFile = '13KNew'
##        srcFile = '13KNoAgg'
##        srcFile = '25KNew'
##        timeStep = 0.025
##        FRAME_STEP = 40
        
        srcFile = '13KNewObs'
        srcFile = '13KNewObsNoAgg'
        srcFile = '13KSame'
        srcFile = '13KSameNoAgg'
        srcFile = '13KNew0'
        srcFile = '13KNew20'
        srcFile = '13K_custom'
        srcFile = '13K_thingy'
##        srcFile = '25K_thingy'
##        srcFile = '25k_slower'
##        srcFile = '25k_slowest'
        srcFile = '25k_evenSlower'
        srcFile = '5K_40FPS'
##        srcFile = 'denseTest'
        timeStep = 0.1
        timeStep = 0.025    # 5K_40FPS
        FRAME_STEP = 10
        FRAME_STEP = 40     # 5K_40FPS
        outPath = os.path.join( '/projects','tawaf','sim','jun2011' )
        path = os.path.join( outPath, '{0}.scb'.format( srcFile ) )
        outPath = os.path.join( outPath, srcFile )
        
##        MAX_AGENTS = 50
        MAX_FRAMES = 120
    elif ( True ):
        # This size doesn't work for 25k
        size = Vector2( 175.0, 120.0 )
        minPt = Vector2( -75.0, -60.0 )
        # this size DOES work for 25k
        size = Vector2( 215.0, 160.0 )
        minPt = Vector2( -95.0, -80.0 )
        res = (int( size.x / CELL_SIZE ), int( size.y / CELL_SIZE ) )
        timeStep = 0.05
        outPath = os.path.join( '/projects','tawaf','sim','jul2011','results' )
        path = os.path.join( outPath, '{0}.scb'.format( srcFile ) )
        print "Reading", path
        outPath = os.path.join( outPath, srcFile )
        if ( not options.includeAll ):
            EXCLUDE_STATES = (1, 2, 3, 4, 5, 6, 7, 8, 9)
    elif ( False ):
        size = Vector2( 15, 5 )
        minPt = Vector2( -1.0, -2.5 )
        res = (int( size.x / CELL_SIZE ), int( size.y / CELL_SIZE ) )
        path = 'linear.scb'
    elif ( False ):
        size = Vector2( 30, 5 )
        minPt = Vector2( -1.0, -2.5 )
        res = (int( size.x / CELL_SIZE ), int( size.y / CELL_SIZE ) )
        path = 'quad.scb'
    print "Size:", size
    print "minPt:", minPt
    print "res:", res
    timeStep *= FRAME_STEP
    frameSet = FrameSet( path, START_FRAME, MAX_FRAMES, MAX_AGENTS, FRAME_STEP )
    print "Total frames:", frameSet.totalFrames()

    grids = GridFileSequence( os.path.join( outPath, 'junk' ) )
    colorMap = FlameMap()

    # output the parameters used to create the data
    # todo:    

    R = 2.0
    R = 1.5
    
    def distFunc( dispX, dispY, radiusSqd ):
        """Constant distance function"""
        # This is the local density function provided by Helbing
        # using Gaussian, delta(in the equation) = radiusSqd
        return np.exp( -(dispX * dispX + dispY * dispY) / (2.0 * radiusSqd ) ) / ( 2.0 * np.pi * radiusSqd )       

    dfunc = lambda x, y: distFunc( x, y, R * R )

    if ( options.density ):
        if ( not os.path.exists( os.path.join( outPath, 'dense' ) ) ):
            os.makedirs( os.path.join( outPath, 'dense' ) )
    
        print "\tComputing density with R = %f" % R
        s = time.clock()
        grids.computeDensity( minPt, size, res, dfunc, R, frameSet )
        print "\t\tTotal computation time: ", (time.clock() - s), "seconds"
        print "\tComputing density images",
        s = time.clock()
        imageName = os.path.join( outPath, 'dense', 'dense' )
        grids.densityImages( colorMap, imageName )
        pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
        print "Took", (time.clock() - s), "seconds"

    if ( options.speed ):
        if ( not os.path.exists( os.path.join( outPath, 'speed' ) ) ):
            os.makedirs( os.path.join( outPath, 'speed' ) )
    
        print "\tComputing speeds",
        s = time.clock()
        stats = grids.computeSpeeds( minPt, size, res, R, frameSet, timeStep, EXCLUDE_STATES, GridFileSequence.BLIT_SPEED )
        stats.write( os.path.join( outPath, 'speed', 'stat.txt' ) )
        stats.savePlot( os.path.join( outPath, 'speed', 'stat.png' ), 'Average speed per step' )
        print "Took", (time.clock() - s), "seconds"
        print "\tComputing speed images",
        s = time.clock()
        imageName = os.path.join( outPath, 'speed', 'speed' )
        # the limit: 0.5 means the color map is saturated from from minVal to 50% of the range
        grids.speedImages( colorMap, imageName, 0.75, MAX_FRAMES )
        pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
        print "Took", (time.clock() - s), "seconds"

    if ( options.omega ):
        if ( not os.path.exists( os.path.join( outPath, 'omega' ) ) ):
            os.makedirs( os.path.join( outPath, 'omega' ) )
    
        print "\tComputing omega",
        s = time.clock()
        stats = grids.computeAngularSpeeds( minPt, size, res, R, frameSet, timeStep, EXCLUDE_STATES, GridFileSequence.BLIT_SPEED, FRAME_WINDOW )
        stats.write( os.path.join( outPath, 'omega', 'stat.txt' ) )
        stats.savePlot( os.path.join( outPath, 'omega', 'stat.png'), 'Average radial velocity per step' ) 
        print "Took", (time.clock() - s), "seconds"
        print "\tComputing omega images",
        s = time.clock()
        imageName = os.path.join( outPath, 'omega', 'omega' )
        colorMap = RedBlueMap()
        grids.makeImages( colorMap, imageName, 'omega' )
        pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
        print "Took", (time.clock() - s), "seconds"

    if ( options.progress ):
        if ( not os.path.exists( os.path.join( outPath, 'progress' ) ) ):
            os.makedirs( os.path.join( outPath, 'progress' ) )

        print "\tComputing progress",
        s = time.clock()
        stats = grids.computeProgress( minPt, size, res, R, frameSet, timeStep, EXCLUDE_STATES, FRAME_WINDOW )
        stats.write( os.path.join( outPath, 'progress', 'stat.txt' ) )
        stats.savePlot( os.path.join( outPath, 'progress', 'stat.png'), 'Average progress around Kaabah' ) 
        print "Took", (time.clock() - s), "seconds"
        print "\tComputing progress images",
        s = time.clock()
        imageName = os.path.join( outPath, 'progress', 'progress' )
        colorMap = FlameMap( (0.0, 1.0) )
        grids.makeImages( colorMap, imageName, 'progress' )
        pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
        print "Took", (time.clock() - s), "seconds"

    if ( False ):
        if ( not os.path.exists( os.path.join( outPath, 'advec' ) ) ):
            os.makedirs( os.path.join( outPath, 'advec' ) )
    
        lines = [ GLLine( Vector2(0.81592, 5.12050), Vector2( 0.96233, -5.27461) ) ]
        print "\tComputing advection",
        s = time.clock()
        grids.computeAdvecFlow( minPt, size, res, dfunc, 3.0, R, frameSet, lines )
        print "Took", (time.clock() - s), "seconds"
        print "\tComputing advection images",
        s = time.clock()
        imageName = os.path.join( outPath, 'advec', 'advec' )
        grids.makeImages( colorMap, imageName, 'advec' )
        pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
        print "Took", (time.clock() - s), "seconds"

    if ( options.koshak ):
        if ( not os.path.exists( os.path.join( outPath, 'regionSpeed' ) ) ):
            os.makedirs( os.path.join( outPath, 'regionSpeed' ) )
        print "\tComputing region speeds"
        s = time.clock()
        vertices = ( Vector2( -0.551530, 0.792406 ),
                     Vector2( 3.736435, -58.246524 ),
                     Vector2( 42.376927, -56.160723 ),
                     Vector2( 5.681046, -6.353232 ),
                     Vector2( 92.823337, -4.904953 ),
                     Vector2( 5.376837, 6.823865 ),
                     Vector2( 92.526405, 9.199321 ),
                     Vector2( 88.517822, -48.850902 ),
                     Vector2( 6.416100, 53.293737 ),
                     Vector2( -5.906582, 6.230001 ),
                     Vector2( -6.203514, 53.739135 ),
                     Vector2( 62.833196, 57.896184 ),
                     Vector2( 93.268736, 43.643444 ),
                     Vector2( -41.686899, -61.322050 ),
                     Vector2( -74.794826, -25.838665 ),
                     Vector2( -75.388691, 49.582085 )
                     )
        vIDs = ( (0, 3, 4, 6, 5),
                 (5, 6, 12, 11, 8),
                 (5, 8, 10, 9, 0),
                 (0, 9, 10, 15, 14, 13),
                 (0, 13, 1),
                 (0, 1, 2, 3),
                 (3, 2, 7, 4)
                 )
        polygons = []
        
        for ids in vIDs:
            p = Polygon()
            p.closed = True
            for id in ids:
                p.vertices.append( vertices[id] )
            polygons.append( p )
        grids.computeRegionSpeed( frameSet, polygons, timeStep, EXCLUDE_STATES )
        print "Took", (time.clock() - s), "seconds"
        # output image
        imagePath = os.path.join( outPath, 'regionSpeed', 'region' )
        colorMap = TwoToneHSVMap( (0, 0.63, 0.96), (100, 0.53, 0.75 ) )
        regionSpeedImages( grids.outFileName + ".region", imagePath, polygons, colorMap, minPt, size, res )
        
    if ( False ):
        # flow lines
        if ( not os.path.exists( os.path.join( outPath, 'flow' ) ) ):
            os.makedirs( os.path.join( outPath, 'flow' ) )
                 
        lines = ( GLLine( Vector2( 4.56230, -7.71608 ), Vector2( 81.49586, -4.55443  ) ),
                  GLLine( Vector2( 5.08924, 5.72094 ), Vector2( 82.28628, 8.61913  ) ),
                  GLLine( Vector2( 3.50842, 8.09218 ), Vector2( 2.71800, 51.30145  ) ),
                  GLLine( Vector2( -5.97654, 5.72094 ), Vector2( -8.87472, 51.56492  ) ),
                  GLLine( Vector2( -6.50348, -7.18914 ), Vector2(  -40.75473, -53.56005 ) ),
                  GLLine( Vector2( -1.23406, -6.92567 ), Vector2( 1.13718, -51.18881  ) ),
                  GLLine( Vector2( 3.50842, -7.45261 ), Vector2( 44.08297, -45.65592 ) ) )
        flow = computeFlowLines( Vector2( 0, 0 ), lines, frameSet )
        flowFile = os.path.join( outPath, 'flow', 'flow.txt' )
        file = open( flowFile, 'w' )
        flow.write( file )
        file.close()

    if ( False ):
        # Traces
        print "Rendering traces"
        s = time.clock()
        grids.renderTraces( minPt, size, res, frameSet, 5, 5, 'data/trace11_' )
        print "Took", (time.clock() - s), "seconds"


if __name__ == '__main__':
    main()
    