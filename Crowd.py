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
from Grid import *
import Signals
import Kernels
from GridFileSequence import *
from flow import *
from primitives import Vector2, Segment
from trajectory.scbData import FrameSet
from trace import renderTraces
import pylab as plt
from ObjSlice import Polygon
from obstacles import *
import pylab as plt
from GFSVis import visualizeGFS
from stats import StatRecord

        
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
    dFile = open( dataFile, 'r' )
    nameLine = dFile.readline()[2:]
    if ( legendStr is None ):
        legendStr = nameLine.split('~')
    
    data = np.loadtxt( dFile )
    data[:,0] *= timeStep
    smoothFlows = np.empty_like( data[:, 1:] )
    for col in xrange( data.shape[1] - 1 ):
        smoothFlows[:, col] = np.convolve( data[:, col+1], kernel, 'same' )
    ax = fig.add_subplot(2,1,1)
    ax.set_title( '%s - Flow' % titlePrefix )
##    plt.plot( data[:,0], data[:, 1:], linewidth=0.25 )
    plt.plot( data[:,0], smoothFlows )
    if ( legendStr == None or len( legendStr ) != data.shape[1] - 1 ):
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

def plotPopulation( outFileName, timeStep, titlePrefix='', legendStr=None, newFig=False, xlimits=None, ylimits=None ):
    '''Given the data in outFileName and the given timestep, creates plots'''
    # SMOOTH IT
    SIGMA = 8.0
    kernel = gaussKernel1D( 1.0, SIGMA )

    if ( newFig ):
        fig = plt.figure()
    else:
        plt.clf()
        fig = plt.gcf()
    
    dataFile = outFileName + ".pop"
    dFile = open( dataFile, 'r' )
    nameLine = dFile.readline()[2:]
    if ( legendStr is None ):
        legendStr = nameLine.split('~')
    
    data = np.loadtxt( dFile )
    data[:,0] *= timeStep
    smoothFlows = np.empty_like( data[:, 1:] )
    for col in xrange( data.shape[1] - 1 ):
        smoothFlows[:, col] = np.convolve( data[:, col+1], kernel, 'same' )
    ax = fig.add_subplot(1,1,1)
    ax.set_title( '%s - Population' % titlePrefix )
    plt.plot( data[:,0], smoothFlows )
    if ( legendStr == None or len( legendStr ) != data.shape[1] - 1 ):
        legendStr = [ 'Region %d' % i for i in range( data.shape[1] - 1 ) ]
    plt.legend( legendStr, loc='upper right' )
    plt.ylabel( 'Agents in Region' )
##    ax = fig.add_subplot(2,1,2)
##    plt.plot( data[:,0], np.clip( firstDeriv( smoothFlows, timeStep, 4 * 16 ), 0.0, 1e6 ) )
    plt.xlabel( 'Simulation time (s)' )
##    plt.ylabel( 'Flow (agents/s)' )
    if ( xlimits != None ):
        plt.xlim( xlimits )
    if ( ylimits != None ):
        plt.ylim( ylimits )
    
    plt.savefig( outFileName + ".pop.png" )
    plt.savefig( outFileName + ".pop.eps" )

def computeFlow( frameSet, segments, outFileName, names=None ):
    '''Compute the flow of agents past the indicated line segments.
    Output is an NxM array where there are N time steps and M segments.
    Each segment has direction and every agent will only be counted at most once w.r.t.
    each segment.

    @param  frameSet        An instance of trajectory data (currently scb data)
    @param  segments        A list of Segment instances.
    @param  outFileName     The name of the file to write the flow results to.
    @param  names           An optional list of strings.  If provided, there must be
                            one string for each Segment (in segments).  If none are
                            provided, line names will be generated.
    '''
    if ( names is None ):
        names = [ 'Line %d' % i for i in xrange( len( segments ) ) ]
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

    # write names
    outFile.write( '# %s\n' % '~'.join( names ) )
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
    if ( frameSet.is3D ):
        pY = frame[:, 2:3 ]
    else:
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
        if ( frameSet.is3D ):
            pY = frame[:, 2:3 ]
        else:
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
    
def computePopulation( frameSet, rectDomains, outFileName, names=None ):
    '''Computes the time-dependent population for a set of rectangular domains.
    Output is an NxM array where there are N time steps and M rectangular regions.

    @param  frameSet        An instance of trajectory data (currently scb data)
    @param  rectDomains     A list of Segment instances.
    @param  outFileName     The name of the file to write the flow results to.
    @param  names           An optional list of strings.  If provided, there must be
                            one string for each Segment (in segments).  If none are
                            provided, line names will be generated.
    '''
    if ( names is None ):
        names = [ 'Region %d' % i for i in xrange( len( rectDomains ) ) ]
    # In this scenario, there are N agents and M segments

    outFile = open( outFileName + '.pop', 'w' )
    rectCount = len( rectDomains )

    # write names
    outFile.write( '# %s\n' % '~'.join( names ) )
    frameSet.setNext( 0 )
    X_COL_LIMIT = 1
    Y_COL = 1
    if ( frameSet.is3D ):
        Y_COL = 2
    
    # pre-compute max corner to facilitate the test    
    for i, rect in enumerate( rectDomains ):
        rect.maxCorner = ( rect.minCorner[0] + rect.size[0], rect.minCorner[1] + rect.size[1] )

    for i, rect in enumerate( rectDomains ):
    
     while ( True ):
        try:
            frame, idx = frameSet.next()
        except StopIteration:
            break
        else:
            ids = frameSet.getFrameIds()   # mapping from frame IDs to global IDs
            frameIDs = map( lambda x: ids[ x ], xrange( frame.shape[0] ) )
        # compute crossability for the current frame
        
        pX = frame[:, :X_COL_LIMIT ]
        pY = frame[:, Y_COL:Y_COL+1 ]

        # the number of agents in each rect
        population = np.zeros( rectCount, dtype=np.int )
        
        for i, rect in enumerate( rectDomains ):
            inside = ( pX >= rect.minCorner[0] ) & ( pX <= rect.maxCorner[0] ) & ( pY >= rect.minCorner[1] ) & ( pY <= rect.maxCorner[1] )
            population[ i ] = np.sum( inside )

        outFile.write('{0:10d}'.format( idx ) )
        for val in population:
            outFile.write('{0:10d}'.format( val ) )
        outFile.write('\n')

    outFile.close()
    

def framesInRegion( region, data ):
    '''For each agent in data, computes the largest interval of time during which
    the agent is in the region

    @param      region      An instance of RectDomain.
    @param      data        An instance of trajectory data with N agents.
    @returns    A 2-tuple of numpy arrays: ( intervals, speeds )
                    intervals: A numpy array of ints of shape (N, 2).
                        The first column represents the frame time the agent enters the region.
                        The second colum represents the number of frames the agent is
                            inside the region.
                    distances: The distances traveled by the agent from entry to exit over the
                        interval.
                    if the interval duration is zero, the distance value will be meaningless.
    '''
    data.setNext( 0 )
    # The entrance and duration times of each agent
    agtTime = np.zeros( ( data.agentCount(), 2 ), dtype=np.int )
    inRegion = {}   # map from the agent id to the time it entered

    enterPt = np.empty( ( data.agentCount(), 2 ), dtype=np.float32 )
    distance = np.empty( data.agentCount(), dtype=np.float32 )
    
    while ( True ):
        try:
            frame, idx = data.next()
        except StopIteration:
            break
        IDs = data.getFrameIds()  # a mapping from frame ID to data ID
        posData = frame[:, :2 ]
        if ( data.is3D ):
            posData = frame[:, :3:2 ]
        isInside = region.pointsInside( posData )
        for fID, state in enumerate( isInside ):
            simID = IDs[ fID ]
            if ( state ):
                if ( not inRegion.has_key( simID ) ):
                    inRegion[ simID ] = idx
                    enterPt[ simID, : ] = posData[ fID, : ]
            else:
                if ( inRegion.has_key( simID ) ):
                    enter = inRegion.pop( simID )
                    elapsed = idx - enter
                    if ( elapsed > agtTime[ simID, 1 ] ):
                        agtTime[ simID, : ] = ( enter, elapsed )
                        exit = posData[ fID, : ]
                        delta = exit - enterPt[ simID, : ]
                        distSq = np.dot( delta, delta )
                        distance[ simID ] = distSq
    distance = np.sqrt( distance )
    
    return agtTime, distance

def calcSpeeds( intervals, distances, timeStep ):
    '''Compute the average speed for each agent crossing the rectangular region.

    @param      intervals       A numpy array of ints of shape (N, 2).
                                The first column is the frame during which the corresponding agent
                                    enters the rectangular region.
                                The second column is the duration of time spent in the region.
    @param      distances       A numpy array of floats of shape (N, ).  The distance that each
                                agent traveled during its interval
    @param      rect            An instance of RectDomain.
    @param      timeStep        A float. The duration of a single frame in the data.
    @returns    A 2-tuple of numpy arrays: ( speeds, valid ).
                    speeds: A numpy array of floats of shape (N, ).  The average speed for each agent.
                    valid:  A numpy array of bool of shape (N, ).  True if the corresponding speed is
                        meaningful, False otherwise.  This will happen if there is not a well-defined
                        interval for the agent.
    '''
    elapsedTime = intervals[ :, 1 ] * timeStep
    valid = elapsedTime > 0
    speed = np.empty_like( elapsedTime )
    speed[ valid ] = distances[ valid ] / elapsedTime[ valid ]
    
    return speed, valid

def calcIntervalDensityRegion( intervals, density ):
    '''Computes the average density for each interval based on the average density in the region.

    @param      intervals       A numpy array of ints of shape (N, 2).
                                The first column is the frame during which the corresponding agent
                                    enters the rectangular region.
                                The second column is the duration of time spent in the region.
    @param      density         A numpy array of floats of shape (T, )
                                The average density of the region over the time [0, T).
                                The interval values in intervals should lie in the domain [0, T).
    @returns    A numpy array of floats with shape (N, 1).  The average density in the region over
                    each non-zero interval.
    '''
    densities = np.empty( intervals.shape[0], dtype=np.float32 )
    for i, iVal in enumerate( intervals ):
        start, length = iVal
        if ( length > 0 ):
            densities[ i ] = np.mean( density[ start:(start+length) ] )
    return densities

def defaultRegionNames( regionCount, forFileName=True ):
    '''Produces a list of default region names.

    @param      regionCount     An int.  The number of region names to generate.
    @param      forFileName     A boolean.  Determines if the names are created for filenames
                                (True) or for display (False).
    '''
    if ( forFileName ):
        return [ 'Region_%d' % i for i in xrange( len( rectDomains ) ) ]
    else:
        [ 'Region %d' % i for i in xrange( len( rectDomains ) ) ]
                                

def computeFundDiag( frameSet, rectDomains, outFileName, names=None ):
    '''Computes the fundamental diagram in one or more regions for the given agent data and
    writes it to files.

    @param      frameSet        An instance of trajectory data.
    @param      rectDomains     A list of RectDomain instances.  Compute the fundamental diagram for
                                each agent who passes through the region.
    @param      outFileName     The base name for the output files - one file per region will be
                                created, with an index number as suffix (starting at 0).
    @param      names           A list of strings.  Names for the rectangular domains.
    '''
    #   TODO: Offer up alternative density computation
    # compute population of region over the time.
    computePopulation( frameSet, rectDomains, outFileName, names )
    # read population data
    dataFile = outFileName + ".pop"
    dFile = open( dataFile, 'r' )
    nameLine = dFile.readline()[2:]
    areas = np.array( [ rect.area for rect in rectDomains ], dtype=np.float32 )
    areas.shape = (1, -1)
    density = np.loadtxt( dFile )[:,1:] / areas

    if ( names is None ):
        names = defaultRegionNames( len( rectDomains ) ) 
    else:
        assert( len( names ) == len( rectDomains ) )
    
    # For each region
    for i, rect in enumerate( rectDomains ):
        # Compute intervals of agents crossing the regions
        intervals, distances = framesInRegion( rect, frameSet )
        # For each interval, determine the agent's average speed and the average density
        speeds, valid = calcSpeeds( intervals, distances, frameSet.simStepSize )
        densities = calcIntervalDensityRegion( intervals, density[ :, i ] )
        data = np.column_stack( ( densities[valid], speeds[valid] ) )
        fdFileName = outFileName + '_%s.npy' % names[ i ] 
        np.save( fdFileName, data )

def plotFundDiag( outFileName, rectDomains, names=None ):
    '''Creates plots of fundamental diagram analysis.

    @param      outFileName     The base name for the output files - one file per region will be
                                created, with an index number as suffix (starting at 0).
    @param      rectDomains     A list of RectDomain instances.  Compute the fundamental diagram for
                                each agent who passes through the region.
    @param      names           A list of strings.  Names for the rectangular domains.
    '''
    if ( names is None ):
        fileNames = defaultRegionNames( len( rectDomains ) )
        displayNames = defaultRegionNames( len( rectDomains ), False )
    else:
        assert( len( rectDomains ) == len( names ) )
        fileNames = names
        displayNames = names

    regions = []
    legendStr = []
    plt.figure()
    for i, name in enumerate( fileNames ):
        fdFileName = outFileName + '_%s.npy' % names[ i ]
        fdData = np.load( fdFileName )
        regions.append( fdData )
        legendStr.append( displayNames[ i ] )
        
        plt.title( 'Fundamental Diagram - %s' % displayNames[ i ] )
        plt.plot( fdData[:,0], fdData[:,1], 'ob' )
        plt.xlabel( 'Density (people/m$^2$)' )
        plt.ylabel( 'Speed (m/s)' )
        figName, ext = os.path.splitext( fdFileName )
        plt.ylim( (0.0, 2.0) )
        plt.savefig( figName + '.eps' )
        plt.savefig( figName + '.png' )
        plt.clf()

        plt.title( 'Fundamental Diagram - %s' % displayNames[ i ] )
        plt.plot( fdData[:,0], fdData[:,0] * fdData[:,1], 'ob' )
        plt.xlabel( 'Density (people/m$^2$)' )
        plt.ylabel( 'Flow (speed * density)' )
        figName, ext = os.path.splitext( fdFileName )
        plt.savefig( figName + '_flow_.eps' )
        plt.savefig( figName + '_flow_.png' )
        plt.clf()
        
    plt.title( 'Fundamental Diagram - All Regions' )
    plt.xlabel( 'Density (people/m$^2$)' )
    plt.ylabel( 'Speed (m/s)' )
    plt.ylim( (0.0, 2.0) )
    if ( len( rectDomains ) > 0 ):
        for data in regions:
            plt.plot( data[:,0], data[:,1], 'o' )
        plt.legend( legendStr )
        plt.savefig( outFileName + '.eps' )
        plt.savefig( outFileName + '.png' )

    plt.clf()
    plt.title( 'Fundamental Diagram - All Regions' )
    plt.xlabel( 'Density (people/m$^2$)' )
    plt.ylabel( 'Flow (speed * density)' )
##    plt.ylim( (0.0, 2.0) )
    if ( len( rectDomains ) > 0 ):
        for data in regions:
            plt.plot( data[:,0], data[:,0] * data[:,1], 'o' )
        plt.legend( legendStr )
        plt.savefig( outFileName + '_flow_.eps' )
        plt.savefig( outFileName + '_flow_.png' )


    
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
    
    if ( True ):
        # This size doesn't work for 25k
##        size = Vector2( 175.0, 120.0 )
##        minPt = Vector2( -75.0, -60.0 )
        # this size DOES work for 25k
        size = Vector2( 215.0, 160.0 )
        minPt = Vector2( -95.0, -80.0 )
        res = (int( size.x / CELL_SIZE ), int( size.y / CELL_SIZE ) )
        size = Vector2( res[0] * CELL_SIZE, res[1] * CELL_SIZE )
        timeStep = 0.05
        outPath = os.path.join( '/projects','tawaf','sim','jul2011','results' )
        path = os.path.join( outPath, '{0}.scb'.format( srcFile ) )
        print "Reading", path
        outPath = os.path.join( outPath, srcFile )
        if ( not options.includeAll ):
            EXCLUDE_STATES = (1, 2, 3, 4, 5, 6, 7, 8, 9)

    domain = AbstractGrid( minPt, size, res )
    print "Size:", size
    print "minPt:", minPt
    print "res:", res
    timeStep *= FRAME_STEP
    frameSet = FrameSet( path, START_FRAME, MAX_FRAMES, MAX_AGENTS, FRAME_STEP )
    print "Total frames:", frameSet.totalFrames()

    grids = GridFileSequence( os.path.join( outPath, 'junk' ), Vector2(0,3.2), Vector2(-6., 6.))
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
        kernel = Kernels.GaussianKernel( R, CELL_SIZE, False )
        signal = Signals.PedestrianSignal( domain ) # signal domain is the same as convolution domain
        grids.convolveSignal( domain, kernel, signal, frameSet )
        print "\t\tTotal computation time: ", (time.clock() - s), "seconds"
        print "\tComputing density images",
        s = time.clock()
        imageName = os.path.join( outPath, 'dense', 'dense' )
        reader = GridFileSequenceReader( grids.outFileName + ".density"  )
        visualizeGFS( reader, colorMap, imageName, 'png', 1.0, grids.obstacles )
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
        reader = GridFileSequenceReader( grids.outFileName + ".speed"  )
        visualizeGFS( reader, colorMap, imageName, 'png', 0.75, grids.obstacles )
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
        
        reader = GridFileSequenceReader( grids.outFileName + ".omega"  )
        visualizeGFS( reader, colorMap, imageName, 'png', 1.0, grids.obstacles )

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
        reader = GridFileSequenceReader( grids.outFileName + ".progress"  )
        visualizeGFS( reader, colorMap, imageName, 'png', 1.0, grids.obstacles )
        print "Took", (time.clock() - s), "seconds"

    if ( False ):
        if ( not os.path.exists( os.path.join( outPath, 'advec' ) ) ):
            os.makedirs( os.path.join( outPath, 'advec' ) )
    
        lines = [ Segment( Vector2(0.81592, 5.12050), Vector2( 0.96233, -5.27461) ) ]
        print "\tComputing advection",
        s = time.clock()
        grids.computeAdvecFlow( minPt, size, res, dfunc, 3.0, R, frameSet, lines )
        print "Took", (time.clock() - s), "seconds"
        print "\tComputing advection images",
        s = time.clock()
        imageName = os.path.join( outPath, 'advec', 'advec' )
        reader = GridFileSequenceReader( grids.outFileName + ".advec"  )
        visualizeGFS( reader, colorMap, imageName, 'png', 1.0, grids.obstacles )
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
                 
        lines = ( Segment( Vector2( 4.56230, -7.71608 ), Vector2( 81.49586, -4.55443  ) ),
                  Segment( Vector2( 5.08924, 5.72094 ), Vector2( 82.28628, 8.61913  ) ),
                  Segment( Vector2( 3.50842, 8.09218 ), Vector2( 2.71800, 51.30145  ) ),
                  Segment( Vector2( -5.97654, 5.72094 ), Vector2( -8.87472, 51.56492  ) ),
                  Segment( Vector2( -6.50348, -7.18914 ), Vector2(  -40.75473, -53.56005 ) ),
                  Segment( Vector2( -1.23406, -6.92567 ), Vector2( 1.13718, -51.18881  ) ),
                  Segment( Vector2( 3.50842, -7.45261 ), Vector2( 44.08297, -45.65592 ) ) )
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
    