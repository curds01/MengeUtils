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
from Context import GLLine
from flow import *
from primitives import Vector2
from scbData import FrameSet
from trace import renderTraces
import pylab as plt
from ObjSlice import Polygon

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
        self.frameData.append( ( self.agentData.mean(), self.agentData.std(), self.agentData.min(), self.agentData.max() ) )
        self.currAgent = 0

    def write( self, fileName ):
        '''Outputs the data into a text file'''
        f = open( fileName, 'w' )
        for m, s, minVal, maxVal in self.frameData:
            f.write( '{0:>15}{1:>15}{2:>15}{3:>15}\n'.format( m, s, minVal, maxVal ) )
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
        
class RasterReport:
    """Simple class to return the results of rasterization"""
    def __init__( self ):
        self.maxVal = 0.0
        self.count = 0

    def incCount( self ):
        self.count += 1

    def setMax( self, val ):
        if ( val > self.maxVal ):
            self.maxVal = val
            
class BufferGrid:
    """Entry into a buffer for a grid"""
    def __init__( self, id, grid ):
        self.id = id
        self.grid = grid

    def __eq__( self, id ):
        return self.id == id

    def __str__( self ):
        return "BufferGrid %d, %f" % ( self.id, self.grid.maxVal() )
    
# The thread that does the rasterization work
ACTIVE_RASTER_THREADS = 0
def threadRasterize( log, bufferLock, buffer, frameLock, frameSet, minCorner, size, resolution, distFunc, maxRad ):
    # acquire frame
    frameLock.acquire()
    frame, index = frameSet.next()
    frameLock.release()
    
    while ( frame ):
        # create grid and rasterize
        g = Grid( minCorner, size, resolution )
        g.rasterizePosition( frame, distFunc, maxRad )
        # update log
        log.setMax( g.maxVal() )
        log.incCount()
        # put into buffer
        bufferLock.acquire()
        buffer.append( BufferGrid(index, g ) )
        bufferLock.release()
        # acquire next frame
        frameLock.acquire()
        frame, index = frameSet.next()
        frameLock.release()

# the thread that does the file output
def threadOutput( outFile, buffer, bufferLock, startTime ):
    """Reads grids from the buffer and writes them to the output file"""
    nextGrid = 0
    while ( buffer or ACTIVE_RASTER_THREADS ):
        # keep doing the work as long as the buffer has contents or there are active raster threads
        bufferLock.acquire()
        try:
            i = buffer.index( nextGrid )
            bg = buffer.pop( i )
            bufferLock.release()
            print "\t\tWriting buffer %d at time %f s" % ( nextGrid, time.clock() - startTime )
            outFile.write( bg.grid.binaryString() )
            nextGrid += 1
        except ValueError:
            bufferLock.release()
            time.sleep( 1.0 )

class Kernel:
    """Distance function kernel"""
    def __init__( self, radius, dFunc, cSize ):
        """Creates a kernel to add into the grid.normalize
        The kernel is a 2d grid (with odd # of cells in both directions.)
        The cell count is determined by the radius and cell size.x
        The cellsize is a tuple containing the width and height of a cell.
        (it need not be square.)  The values in each cell are determined
        by the distance of each cell from the center cell computed with
        dFunc.  Each cell is given a logical size of cSize"""
        hCount = int( 6 * radius / cSize.x )
        if ( hCount % 2 == 0 ):
            hCount += 1
        o = np.arange( -(hCount/2), hCount/2 + 1) * cSize.x
        X, Y = np.meshgrid( o, o )
        self.data = dFunc( X, Y )


    def max( self ):
        return self.data.max()

    def min( self ):
        return self.data.min()

    def sum( self ):
        return self.data.sum()
    
    def __str__( self ):
        return str( self.data )

class Kernel2:
    """Computes the contribution of an agent to it's surrounding neighborhood"""
    # THE BIG DIFFERENCE between Kernel2 and Kernel:
    #   Kernel assumes that every agent is centered on a cell, so the contribution
    #   is a fixed contribution to the neighborhood
    #   This kernel has fixed size, but the values change because it's computed based
    #   on the actual world position of the agent w.r.t. the world position of the kernel center
    #   So, this creates a generic kernel of the appropriate size, but then given a particular
    #   center value and a particular position, computes the unique kernel (instance method)
    def __init__( self, radius, cSize ):
        # compute size: assume cSize is square
        self.k = int( 6 * radius / cSize.x )
        if ( self.k % 2 == 0 ):
            self.k += 1
        self.data = np.zeros( (self.k, self.k), dtype=np.float32 )
        # world offsets from the center of the kernel
        o = np.arange( -(self.k/2), self.k/2 + 1) * cSize.x
        self.localX, self.localY = np.meshgrid( o, o )
        
    def instance( self, dfunc, center, position ):
        '''Creates an instance of the sized kernel for this center and position'''
        localPos = position - center
        deltaX = ( self.localX - localPos.x ) ** 2
        deltaY = ( self.localY - localPos.y ) ** 2
        distSqd = deltaX + deltaY
        # the distance function must take an array as an argument.
        self.data = dfunc( distSqd )
                
class Grid:
    """Class to discretize scalar field computation"""
    def __init__( self, minCorner, size, resolution, initVal=0.0 ):
        """Initializes the grid to span the space starting at minCorner,
        extending size amount in each direction with resolution cells"""
        self.minCorner = minCorner          # tuple (x, y)  - float
        self.size = size                    # tuple (x, y)  - float
        self.resolution = resolution        # tuple (x, y)  - int
        self.initVal = initVal
        self.clear()
        self.cellSize = Vector2( size.x / float( resolution[0] ), size.y / float( resolution[1] ) )
        
       
    def __str__( self ):
        s = 'Grid'
        for row in range( self.resolution[1] - 1, -1, -1 ):
            s += '\n'
            for col in range( self.resolution[0] ):
                s += '%7.2f' % ( self.cells[ col ][ row ] )
        return s

    def binaryString( self ):
        """Produces a binary string for the data"""
        return self.cells.tostring()

    def setFromBinary( self, binary ):
        """Populates the grid values from a binary string"""
        self.cells = np.fromstring( binary, np.float32 )
        self.cells = self.cells.reshape( self.resolution )

    def __idiv__( self, scalar ):
        self.cells /= scalar
        return self

    def __imul__( self, scalar ):
        self.cells *= scalar
        return self

    def maxVal( self ):
        """Returns the maximum value of the grid"""
        return self.cells.max()

    def minVal( self ):
        """Returns the maximum value of the grid"""
        return self.cells.min()

    def clear( self ):
        # Cells are a 2D array accessible with (x, y) values
        #   x = column, y = row
        if ( self.initVal == 0 ):
            self.cells = np.zeros( ( self.resolution[0], self.resolution[1] ), dtype=np.float32 )
        else:
            self.cells = np.zeros( ( self.resolution[0], self.resolution[1] ), dtype=np.float32 ) + self.initVal

    def getCenter( self, position ):
        """Returns the closest cell center to this position"""
        # offset in euclidian space
        offset = position - self.minCorner
        # offset in cell sizes
        ofX = offset.x / self.cellSize.x
        ofY = offset.y / self.cellSize.y
        x = int( ofX )
        y = int( ofY )
        return x, y
      

    def rasterizePosition( self, frame, distFunc, maxRad ):
        """Given a frame of agents, rasterizes the whole frame"""
        kernel = Kernel( maxRad, distFunc, self.cellSize )

        # This assumes the kernel dimensions are ODD-sized        
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        for agt in frame.agents:
            center = self.getCenter( agt.pos )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            self.cells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ]

    def rasterizePosition2( self, frame, distFunc, maxRad ):
        """Given a frame of agents, rasterizes the whole frame"""
        kernel = Kernel2( maxRad, self.cellSize )
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        for agt in frame.agents:
            center = self.getCenter( agt.pos )
            centerWorld = Vector2( center[0] * self.cellSize.x + self.minCorner.x,
                                   center[1] * self.cellSize.y + self.minCorner.y )
            kernel.instance( distFunc, centerWorld, agt.pos )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            self.cells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ]            

    def rasterizeValue( self, frame, distFunc, maxRad ):
        """Given a frame of agents, rasterizes the whole frame"""
        kernel = Kernel( maxRad, distFunc, self.cellSize )
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        for agt in frame.agents:
            center = self.getCenter( agt.pos )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            self.cells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ] * agt.value        

    

    def rasterizeContribSpeed( self, kernel, f2, f1, distFunc, maxRad, timeStep ):
        """Given two frames of agents, computes per-agent displacement and rasterizes the whole frame"""
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        invDT = 1.0 / timeStep
        countCells = np.zeros_like( self.cells )
        maxSpd = 0
        for i in range( len ( f2.agents ) ):
            ag2 = f2.agents[ i ]
            ag1 = f1.agents[ i ]
            disp = ( ag2.pos - ag1.pos ).magnitude()
            disp *= invDT
            if ( disp > maxSpd ): maxSpd = disp
            center = self.getCenter( ag2.pos )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            self.cells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ] * disp
            countCells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ]
        countMask = countCells == 0
        countCells[ countMask ] = 1
        print "Counts: max", countCells.max(), "min:", countCells.min(),
        print "Accum max:", self.cells.max(), 
        self.cells /= countCells
        print "Max speed:", maxSpd, "max cell", self.cells.max()

    def rasterizeProgress( self, f2, initFrame, prevProgress, callBack=None ):
        '''Given the current frame and the initial frame, computes the fraction of the circle that
        each agent has travelled around the kaabah.'''
        # TODO: don't let this be periodic.
        TWO_PI = 2.0 * np.pi
        for i in range( len( f2.agents ) ):
            # first compute progress based on angle between start and current position
            ag2 = f2.agents[ i ]
            ag1 = initFrame.agents[ i ]
            dir2 = ag2.pos.normalize()
            dir1 = ag1.pos.normalize()
            angle = np.arccos( dir2.dot( dir1 ) )
            cross = dir1.det( dir2 )
            if ( cross < 0 ):
                angle = TWO_PI - angle
            progress = angle / TWO_PI

            # now determine direction from best progress so far
            
            if ( progress > prevProgress[i,2] ):
                best = Vector2( prevProgress[i,0], prevProgress[i,1] )
                cross = best.det( dir2 )
                if ( cross < 0 ):
                    # if I'm moving backwards from best progress BUT I'm apparently improving progress
                    #   I've backed over the 100% line.
                    progress = 0.0
                else:
                    prevProgress[ i, 2 ] = progress
                    prevProgress[ i, 0 ] = dir2.x
                    prevProgress[ i, 1 ] = dir2.y

            center = self.getCenter( ag2.pos )
            INFLATE = True # causes the agents to inflate more than a single cell
            if ( INFLATE ):
                l = center[0] - 1
                r = l + 3
                b = center[1] - 1
                t = b + 3
            else:
                l = center[0]
                r = l + 1
                b = center[1]
                t = b + 1
            
            if ( l < 0 ):
                l = 0
            if ( b < 0 ):
                b = 0
            if ( r >= self.resolution[0] ):
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                t = self.resolution[1]
            self.cells[ l:r, b:t ] =  progress
            if ( callBack ):
                callBack( progress )            

    def rasterizeSpeedBlit( self, kernel, f2, f1, distFunc, maxRad, timeStep, callBack=None ):
        """Given two frames of agents, computes per-agent displacement and rasterizes the whole frame"""
        invDT = 1.0 / timeStep
        for i in range( len ( f2.agents ) ):
            ag2 = f2.agents[ i ]
            ag1 = f1.agents[ i ]
            disp = ( ag2.pos - ag1.pos ).magnitude()
            disp *= invDT
            if ( disp > 3.0 ): continue
            center = self.getCenter( ag2.pos )

            INFLATE = True # causes the agents to inflate more than a single cell
            if ( INFLATE ):
                l = center[0] - 1
                r = l + 3
                b = center[1] - 1
                t = b + 3
            else:
                l = center[0]
                r = l + 1
                b = center[1]
                t = b + 1
            
            if ( l < 0 ):
                l = 0
            if ( b < 0 ):
                b = 0
            if ( r >= self.resolution[0] ):
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                t = self.resolution[1]
            self.cells[ l:r, b:t ] =  disp
            if ( callBack ):
                callBack( disp )

    def rasterizeOmegaBlit( self, kernel, f2, f1, distFunc, maxRad, timeStep, callBack=None ):
        """Given two frames of agents, computes per-agent angular speed and rasterizes the whole frame"""
        invDT = 1.0 / timeStep
        RAD_TO_ANGLE = 180.0 / np.pi * invDT
        for i in range( len ( f2.agents ) ):
            # compute the angle around the origin
            ag2 = f2.agents[ i ]
            ag1 = f1.agents[ i ]
            dir2 = ag2.pos.normalize()
            dir1 = ag1.pos.normalize()
            angle = np.arccos( dir2.dot( dir1 ) ) * RAD_TO_ANGLE
            cross = dir1.det( dir2 )
            if ( cross < 0 ):
                angle = -angle
                
            center = self.getCenter( ag2.pos )
            INFLATE = True # causes the agents to inflate more than a single cell
            if ( INFLATE ):
                l = center[0] - 1
                r = l + 3
                b = center[1] - 1
                t = b + 3
            else:
                l = center[0]
                r = l + 1
                b = center[1]
                t = b + 1
            
            if ( l < 0 ):
                l = 0
            if ( b < 0 ):
                b = 0
            if ( r >= self.resolution[0] ):
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                t = self.resolution[1]
            self.cells[ l:r, b:t ] =  angle
            if ( callBack ):
                callBack( angle )


    def rasterizeDenseSpeed( self, denseFile, kernel, f2, f1, distFunc, maxRad, timeStep ):
        '''GIven two frames of agents, computes per-agent speed and rasterizes the whole frame.agents
        Divides the rasterized speeds by density from the denseFile'''
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        invDT = 1.0 / timeStep
        countCells = np.zeros_like( self.cells )
        maxSpd = 0
        for i in range( len ( f2.agents ) ):
            ag2 = f2.agents[ i ]
            ag1 = f1.agents[ i ]
            disp = ( ag2.pos - ag1.pos ).magnitude()
            disp *= invDT
            if ( disp > maxSpd ): maxSpd = disp
            center = self.getCenter( ag2.pos )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            self.cells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ] * disp
        dataStr = denseFile.read( self.resolution[0] * self.resolution[1] * 4 ) # total floats X 4 bytes per float
        density = np.fromstring( dataStr, dtype=np.float32 )
##        density[ density == 0 ] = 1
        density = density.reshape( self.cells.shape )
##        density[ density == 0 ] = 1
        print "Density: max", density.max(), "min:", density.min(),
        print "Accum max:", self.cells.max(), 
##        self.cells /= density
        print "Max speed:", maxSpd, "max cell", self.cells.max()
        
    def rasterizeSpeedGauss( self, kernel, f2, f1, distFunc, maxRad, timeStep ):
        """Given two frames of agents, computes per-agent displacement and rasterizes the whole frame"""
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        invDT = 1.0 / timeStep
        for i in range( len ( f2.agents ) ):
            ag2 = f2.agents[ i ]
            ag1 = f1.agents[ i ]
            disp = ( ag2.pos - ag1.pos ).magnitude()
            disp *= invDT
            center = self.getCenter( ag2.pos )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            self.cells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ] * disp

    def rasterizeVelocity( self, X, Y, kernel, f2, f1, distFunc, maxRad, timeStep ):
        """Given two frames of agents, computes per-agent displacement and rasterizes the whole frame"""
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        invDT = 1.0 / timeStep
        X.fill( 0.0 )
        Y.fill( 0.0 )
        for i in range( len ( f2.agents ) ):
            ag2 = f2.agents[ i ]
            ag1 = f1.agents[ i ]
            disp = ag2.pos - ag1.pos
            disp *= invDT
            center = self.getCenter( ag2.pos )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            X[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ] * disp.x
            Y[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ] * disp.y
        self.cells = X + Y
        #self.cells = np.sqrt( X * X + Y * Y )

    def surface( self, map, minVal, maxVal ):
        """Creates a pygame surface"""
        return map.colorOnSurface( (minVal, maxVal ), self.cells )

    def swapValues( self, oldVal, newVal ):
        """Replaces all cells with the value oldVal with newVal"""
        self.cells[ self.cells == oldVal ] = newVal


##          HELPER FUNCTION FOR REGION TESTS
def findCurrentRegion( frame, polygons ):
    '''Given a frame, determines which region each agent is in.
    Performs a brute-force search across all regions'''
    regions = np.zeros( len( frame.agents ), dtype=np.int )
    for a, agt in enumerate( frame.agents ):
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

def findRegionSpeed( f1, f2, timeStep, polygons, regions=None ):
    '''Given a frame of data, and a set of polygons computes the average region speed for
    each region.  If regions is a Nx1 array (for N agents in frame) then it uses a smart
    mechanism for determining which region the agent is in (and updates it accordingly)
    Otherwise, it performs the brute-force search.
    Returns an Mx1 array (for M polygons) and the regions object.'''
    # if regions is defined, it's the location of the region for f1
    #   This region accumulates the speed
    if ( regions == None ):
        regions = findCurrentRegion( f1, polygons )
    speeds = np.zeros( len(polygons), dtype=np.float32 )
    counts = np.zeros( len(polygons), dtype=np.int )
    for a, ag1 in enumerate( f1.agents ):
        # compute speed
        p1 = ag1.pos
        p2 = f2.agents[ a ].pos
        disp = (p2 - p1).magnitude()
        speed = disp / timeStep
        
        # increment counters and accumulators
        speeds[ regions[a] ] += speed
        counts[ regions[a] ] += 1
        # update region
        regions[ a ] = updateRegion( regions[a], p2, polygons )
    mask = counts != 0
    speeds[ mask ] /= counts[ mask ]
    return speeds, regions
    
def regionSpeedImages( dataFile, imagePath, polygons, colorMap ):
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
    
    
class GridFileSequence:
    """Creates a grid sequence from a frame file and streams the resulting grids to
       a file"""
    HEADER_SIZE = 20        # 20 bytes: resolution, grid count, min/max values
    # different ways of visualizing speed
    BLIT_SPEED = 0      # simply blit the agent to the cell center with his speed
    NORM_SPEED = 1      # distribute speed with a normalized gaussian
    UNNORM_SPEED = 2    # distribute speed with an unnormalized gaussian
    NORM_DENSE_SPEED = 3 # distribute speed with normalized gaussian and then divide by the density
    NORM_CONTRIB_SPEED = 4 # distribute speed with normalized gaussian and then divide by contribution matrix
    LAPLACE_SPEED = 5   # compute the magnitude of the laplacian of the velocity field
    
    def __init__( self, outFileName ):
        self.outFileName = outFileName

    def renderTraces( self, minCorner, size, resolution, frameSet, preWindow, postWindow, fileBase ):
        """Creates a sequence of images of the traces of the agents.

        The trace extends temporally backwards preWindow frames.
        The trace extends temporally forwards postWindow frames.
        The dimensions of the rasterized grid are determined by: minCorner, size, resolution.
        The rendered colors are then output via the colorMap and fileBase name.
        """

        renderTraces( minCorner, size, resolution, frameSet, preWindow, postWindow, fileBase )
        
    def computeDensity( self, minCorner, size, resolution, distFunc, maxRad, frameSet ):
        '''Creates a binary file representing the density scalar fields of each frame'''
        global ACTIVE_RASTER_THREADS

        THREAD_COUNT = 7
        # file output
        outFile = open( self.outFileName + '.density', 'wb' )
        outFile.write( struct.pack( 'ii', resolution[0], resolution[1] ) )  # size of grid
        outFile.write( struct.pack( 'i', 0 ) )                              # grid count
        outFile.write( struct.pack( 'ff', 0.0, 0.0 ) )                      # range of grid values
        buffer = []
        bufferLock = threading.Lock()
        saveThread = threading.Thread( target=threadOutput, args=(outFile, buffer, bufferLock, time.clock() ) )
        ACTIVE_RASTER_THREADS = THREAD_COUNT
        saveThread.start()

        # prepare rasterization        
        frameSet.setNext( 0 )
        frameLock = threading.Lock()
        rasterThreads = []
        rasterLogs = []
        for i in range( THREAD_COUNT ):
            rasterLogs.append( RasterReport() )
            rasterThreads.append( threading.Thread( target=threadRasterize, args=( rasterLogs[-1], bufferLock, buffer, frameLock, frameSet, minCorner, size, resolution, distFunc, maxRad ) )  )
                
        for i in range( THREAD_COUNT ):
            rasterThreads[i].start()
        for i in range( THREAD_COUNT ):
            rasterThreads[i].join()
            ACTIVE_RASTER_THREADS -= 1
##            print "ACTIVE_RASTER_THREADS:", ACTIVE_RASTER_THREADS
        saveThread.join()

        gridCount = 0
        maxVal = 0.0
        for log in rasterLogs:
            gridCount += log.count
            if ( log.maxVal > maxVal ):
                maxVal = log.maxVal

        # add the additional information about grid count and maximum values            
        outFile.seek( 8 )
        outFile.write( struct.pack( 'i', gridCount ) )
        outFile.write( struct.pack( 'ff', 0.0, maxVal ) )
        outFile.close()

    def computeRegionSpeed( self, minCorner, size, resolution, frameSet, polygons, timeStep, timeWindow=1 ):
        '''Given an ordered set of polygons, computes the average speed for all agents in each polygon
        per time step.'''
        # NOTE: This only really applies to the tawaf.
        print "Computing regional speed:"
        print "\tminCorner:       ", minCorner
        print "\tsize:            ", size
        print "\tresolution:      ", resolution
        print "\ttime step:       ", timeStep
        print "Number of polygons:", len(polygons)
        gridSize = resolution[0] * resolution[1]
        cellSize = Vector2( size.x / float( resolution[0] ), size.y / float( resolution[1] ) )
        frameSet.setNext( 0 )        
        data = [ frameSet.next() for i in range( timeWindow + 1 ) ]

        regions = None
        speeds = []
        while ( data[ -1 ][0] ):
            f1, i1 = data.pop(0)
            f2, i2 = data[ -1 ]
            frameSpeeds, regions = findRegionSpeed( f1, f2, timeStep * timeWindow, polygons, regions )
            speeds.append( frameSpeeds )
            data.append( frameSet.next() )
        data = np.array( speeds )
        np.savetxt( self.outFileName + ".region", data, fmt='%.5f' )
            
        
    def computeSpeeds( self, minCorner, size, resolution, maxRad, frameSet, timeStep, speedType=NORM_CONTRIB_SPEED, timeWindow=1 ):
        """Computes the displacements from one cell to the next"""
        print "Computing speeds:"
        print "\tminCorner:  ", minCorner
        print "\tsize:       ", size
        print "\tresolution: ", resolution
        print "\tmaxRad:     ", maxRad
        print "\ttime step:  ", timeStep
        print "\ttime window:", timeWindow
        outFile = open( self.outFileName + '.speed', 'wb' )
        outFile.write( struct.pack( 'ii', resolution[0], resolution[1] ) )  # size of grid
        outFile.write( struct.pack( 'i', 0 ) )                              # grid count
        outFile.write( struct.pack( 'ff', 0.0, 0.0 ) )                      # range of grid values
        maxVal = -1e6
        minVal = 1e6
        gridCount = 0
        gridSize = resolution[0] * resolution[1]
        cellSize = Vector2( size.x / float( resolution[0] ), size.y / float( resolution[1] ) )
        frameSet.setNext( 0 )        
        data = [ frameSet.next() for i in range( timeWindow + 1 ) ]
        # continue while the index of the last frame on the queue is greater than the index of the first frame

        distFunc = lambda x, y: np.exp( -( (x * x + y *y) / ( maxRad * maxRad ) ) )
        print "Speedy type:", speedType
        if ( speedType == GridFileSequence.BLIT_SPEED ):
            speedFunc = Grid.rasterizeSpeedBlit
            kernel = None
            gridFunc = lambda: Grid( minCorner, size, resolution, -1.0 )
        elif ( speedType == GridFileSequence.NORM_SPEED ):
            speedFunc = Grid.rasterizeSpeedGauss
            kernel = Kernel( maxRad, distFunc, cellSize )
            gridFunc = lambda: Grid( minCorner, size, resolution )
        elif ( speedType == GridFileSequence.UNNORM_SPEED ):
            speedFunc = Grid.rasterizeSpeedGauss
            kernel = Kernel( maxRad, distFunc, cellSize )
            gridFunc = lambda: Grid( minCorner, size, resolution )
        elif ( speedType == GridFileSequence.NORM_DENSE_SPEED ):
            try:
                denseFile = open( self.outFileName + ".density", "rb" )
            except:
                print "Can't open desnity file: %.density" % ( self.outFileName )
                raise
            else:
                w, h, count, minVal, maxVal = struct.unpack( 'iiiff', denseFile.read( GridFileSequence.HEADER_SIZE ) )
                assert( w == resolution[0] and h == resolution[1] )
            speedFunc = lambda g, k, f2, f1, dist, rad, step: Grid.rasterizeDenseSpeed( g, denseFile, k, f2, f1, dist, rad, step )
            kernel = Kernel( maxRad, distFunc, cellSize )
            gridFunc = lambda: Grid( minCorner, size, resolution )
        elif ( speedType == GridFileSequence.NORM_CONTRIB_SPEED ):
            speedFunc = Grid.rasterizeContribSpeed
            kernel = Kernel( maxRad, distFunc, cellSize )
            gridFunc = lambda: Grid( minCorner, size, resolution )
        elif ( speedType == GridFileSequence.LAPLACE_SPEED ):
            distFunc = lambda x, y: 1.0 / ( np.pi * maxRad * maxRad ) * ((x * x + y * y - maxRad * maxRad) / (0.25 * maxRad ** 4 ) ) * np.exp( -( (x * x + y *y) / ( maxRad * maxRad ) ) )
            gridFunc = lambda: Grid( minCorner, size, resolution )
            X = np.zeros( resolution, dtype=np.float32 )
            Y = np.zeros( resolution, dtype=np.float32 )
            speedFunc = lambda g, k, f2, f1, dist, rad, step: Grid.rasterizeVelocity( g, X, Y, k, f2, f1, dist, rad, step )
            kernel = Kernel( maxRad, distFunc, cellSize )

        # TODO: This will probably break for some other speed vis method
        stats = StatRecord( frameSet.agentCount() )              
        while ( data[ -1 ][0] ): 
            f1, i1 = data.pop(0)
            f2, i2 = data[ -1 ]
            g = gridFunc() 
            speedFunc( g, kernel, f2, f1, distFunc, maxRad, timeStep * timeWindow, stats )
            M = g.maxVal()
            if ( M > maxVal ):
                maxVal = M
            m = g.minVal()
            if ( m < minVal ):
                minVal = m
            outFile.write( g.binaryString() )
            gridCount += 1
            data.append( frameSet.next() )
            stats.nextFrame()

        if ( speedType != GridFileSequence.LAPLACE_SPEED ):
            minVal = 0
        # add the additional information about grid count and maximum values            
        outFile.seek( 8 )
        outFile.write( struct.pack( 'i', gridCount ) )
        outFile.write( struct.pack( 'ff', minVal, maxVal ) )
        outFile.close()
        return stats


    def initProgress( self, frame ):
        '''A helper function for the progress compuation.  Creates an N x 3 array.ArrayType
        Columns 0 & 1 are normalized vectors pointing to the direction of the agents and
        column2 is the best progress.'''
        agtCount = len( frame.agents )
        progress = np.zeros( ( agtCount, 3 ), dtype=np.float32 )
        for i in range( agtCount ):
            agt = frame.agents[ i ]
            dir = agt.pos.normalize()
            progress[ i, 0] = dir.x
            progress[ i, 1] = dir.y
        return progress
    
    def computeProgress( self, minCorner, size, resolution, maxRad, frameSet, timeStep, timeWindow=1 ):
        """Computes the progress from one frame to the next - progress is measured in the fraction
        of the circle traversed from the initial position"""
        print "Computing progress:"
        print "\tminCorner:  ", minCorner
        print "\tsize:       ", size
        print "\tresolution: ", resolution
        print "\tmaxRad:     ", maxRad
        print "\ttime step:  ", timeStep
        print "\ttime window:", timeWindow
        outFile = open( self.outFileName + '.progress', 'wb' )
        outFile.write( struct.pack( 'ii', resolution[0], resolution[1] ) )  # size of grid
        outFile.write( struct.pack( 'i', 0 ) )                              # grid count
        outFile.write( struct.pack( 'ff', 0.0, 0.0 ) )                      # range of grid values
        maxVal = -1e6
        minVal = 1e6
        gridCount = 0
        gridSize = resolution[0] * resolution[1]
        cellSize = Vector2( size.x / float( resolution[0] ), size.y / float( resolution[1] ) )
        frameSet.setNext( 0 )        
        data = [ frameSet.next() for i in range( timeWindow + 1 ) ]

        stats = StatRecord( frameSet.agentCount() )
        initFrame, initIndex = data[0]
        progress = self.initProgress( initFrame )
        while ( data[ -1 ][0] ):
            print '.',
            f1, i1 = data.pop(0)
            f2, i2 = data[ -1 ]
            g = Grid( minCorner, size, resolution, 100.0 ) 
            g.rasterizeProgress( f2, initFrame, progress, stats )

            m = g.minVal()
            if ( m < minVal ):
                minVal = m
            g.swapValues( 100.0, -100.0 )
            M = g.maxVal()
            if ( M > maxVal ):
                maxVal = M            
            
            outFile.write( g.binaryString() )
            gridCount += 1
            data.append( frameSet.next() )
            stats.nextFrame()
        print
        # add the additional information about grid count and maximum values            
        outFile.seek( 8 )
        outFile.write( struct.pack( 'i', gridCount ) )
        outFile.write( struct.pack( 'ff', minVal, maxVal ) )
        outFile.close()
        return stats

    def computeAngularSpeeds( self, minCorner, size, resolution, maxRad, frameSet, timeStep, speedType=BLIT_SPEED, timeWindow=1 ):
        """Computes the displacements from one cell to the next"""
        print "Computing angular speed:"
        print "\tminCorner:  ", minCorner
        print "\tsize:       ", size
        print "\tresolution: ", resolution
        print "\tmaxRad:     ", maxRad
        print "\ttime step:  ", timeStep
        print "\ttime window:", timeWindow
        outFile = open( self.outFileName + '.omega', 'wb' )
        outFile.write( struct.pack( 'ii', resolution[0], resolution[1] ) )  # size of grid
        outFile.write( struct.pack( 'i', 0 ) )                              # grid count
        outFile.write( struct.pack( 'ff', 0.0, 0.0 ) )                      # range of grid values
        maxVal = -1e6
        minVal = 1e6
        gridCount = 0
        gridSize = resolution[0] * resolution[1]
        cellSize = Vector2( size.x / float( resolution[0] ), size.y / float( resolution[1] ) )
        frameSet.setNext( 0 )        
        data = [ frameSet.next() for i in range( timeWindow + 1 ) ]
        # continue while the index of the last frame on the queue is greater than the index of the first frame

        distFunc = lambda x, y: np.exp( -( (x * x + y *y) / ( maxRad * maxRad ) ) )
        print "Speedy type:", speedType
        if ( speedType == GridFileSequence.BLIT_SPEED ):
            speedFunc = Grid.rasterizeOmegaBlit
            kernel = None
            gridFunc = lambda: Grid( minCorner, size, resolution, 720.0 )
        elif ( speedType == GridFileSequence.NORM_SPEED ):
            raise ValueError, "Compute Angular speed doesn't support normalized angular speed"
##            speedFunc = Grid.rasterizeSpeedGauss
##            kernel = Kernel( maxRad, distFunc, cellSize )
##            gridFunc = lambda: Grid( minCorner, size, resolution )
        elif ( speedType == GridFileSequence.UNNORM_SPEED ):
            raise ValueError, "Compute Angular speed doesn't support unnormalized angular speed"
##            speedFunc = Grid.rasterizeSpeedGauss
##            kernel = Kernel( maxRad, distFunc, cellSize )
##            gridFunc = lambda: Grid( minCorner, size, resolution )
        elif ( speedType == GridFileSequence.NORM_DENSE_SPEED ):
            raise ValueError, "Compute Angular speed doesn't support normalized density angular speed"
##            try:
##                denseFile = open( self.outFileName + ".density", "rb" )
##            except:
##                print "Can't open desnity file: %.density" % ( self.outFileName )
##                raise
##            else:
##                w, h, count, minVal, maxVal = struct.unpack( 'iiiff', denseFile.read( GridFileSequence.HEADER_SIZE ) )
##                assert( w == resolution[0] and h == resolution[1] )
##            speedFunc = lambda g, k, f2, f1, dist, rad, step: Grid.rasterizeDenseSpeed( g, denseFile, k, f2, f1, dist, rad, step )
##            kernel = Kernel( maxRad, distFunc, cellSize )
##            gridFunc = lambda: Grid( minCorner, size, resolution )
        elif ( speedType == GridFileSequence.NORM_CONTRIB_SPEED ):
            raise ValueError, "Compute Angular speed doesn't support normalized contribution angular speed"
##            speedFunc = Grid.rasterizeContribSpeed
##            kernel = Kernel( maxRad, distFunc, cellSize )
##            gridFunc = lambda: Grid( minCorner, size, resolution )
        elif ( speedType == GridFileSequence.LAPLACE_SPEED ):
            raise ValueError, "Compute Angular speed doesn't support laplacian angular speed"
##            distFunc = lambda x, y: 1.0 / ( np.pi * maxRad * maxRad ) * ((x * x + y * y - maxRad * maxRad) / (0.25 * maxRad ** 4 ) ) * np.exp( -( (x * x + y *y) / ( maxRad * maxRad ) ) )
##            gridFunc = lambda: Grid( minCorner, size, resolution )
##            X = np.zeros( resolution, dtype=np.float32 )
##            Y = np.zeros( resolution, dtype=np.float32 )
##            speedFunc = lambda g, k, f2, f1, dist, rad, step: Grid.rasterizeVelocity( g, X, Y, k, f2, f1, dist, rad, step )
##            kernel = Kernel( maxRad, distFunc, cellSize )

        stats = StatRecord( frameSet.agentCount() )            
        while ( data[ -1 ][0] ): 
            f1, i1 = data.pop(0)
            f2, i2 = data[ -1 ]
            g = gridFunc() 
            speedFunc( g, kernel, f2, f1, distFunc, maxRad, timeStep * timeWindow, stats )
            m = g.minVal()
            if ( m < minVal ):
                minVal = m
            # swap out 720.0 value for -720
            g.swapValues( 720.0, -720.0 )
            M = g.maxVal()
            if ( M > maxVal ):
                maxVal = M
            outFile.write( g.binaryString() )
            gridCount += 1
            data.append( frameSet.next() )
            stats.nextFrame()

##        if ( speedType != GridFileSequence.LAPLACE_SPEED ):
##            minVal = 0
        # add the additional information about grid count and maximum values            
        outFile.seek( 8 )
        outFile.write( struct.pack( 'i', gridCount ) )
        outFile.write( struct.pack( 'ff', minVal, maxVal ) )
        outFile.close()
        return stats

    def readGrid( self, g, file, gridSize, index ):
        """Returns the index grid from the given file"""
        gridSize = resolution[0] * resolution[1]
        file.seek( GridFileSequence.HEADER_SIZE + index * gridSize )
        data = file.read( gridSize )
        g.setFromBinary( data )

    def densityImages( self, colorMap, fileBase ):
        """Outputs the density images"""
        try:
            f = open( self.outFileName + ".density", "rb" )
        except:
            print "Can't open desnity file: %.density" % ( self.outFileName )
        else:
            w, h, count, minVal, maxVal = struct.unpack( 'iiiff', f.read( GridFileSequence.HEADER_SIZE ) )
            print "Density images in range:", minVal, maxVal
            gridSize = w * h * 4
            g = Grid( Vector2(0.0, 0.0), Vector2(10.0, 10.0), (w, h) )
            for i in range( count ):
                data = f.read( gridSize )
                g.setFromBinary( data )
                s = g.surface( colorMap, minVal, maxVal )
                pygame.image.save( s, '%s%03d.png' % ( fileBase, i ) )
            f.close()

    def speedImages( self, colorMap, fileBase, limit, maxFrames=-1 ):
        """Outputs the density images"""
        try:
            f = open( self.outFileName + ".speed", "rb" )
        except:
            print "Can't open desnity file: %.speed" % ( self.outFileName )
        else:
            w, h, count, minVal, maxVal = struct.unpack( 'iiiff', f.read( GridFileSequence.HEADER_SIZE ) )
            print "Speed images:"
            print "\tFull range:          ", minVal, maxVal
            maxVal = minVal + (maxVal - minVal) * limit
            print "\tClamped visual range:", minVal, maxVal
            gridSize = w * h * 4
            g = Grid( Vector2(0.0, 0.0), Vector2(10.0, 10.0), (w, h) )
            if ( maxFrames > -1 ):
                if ( maxFrames < count ):
                    count = maxFrames
            for i in range( count ):
##                g.cells = np.loadtxt( 'junk%d.speed' % i )

                data = f.read( gridSize )
                g.setFromBinary( data )
                s = g.surface( colorMap, minVal, maxVal )
                pygame.image.save( s, '%s%03d.png' % ( fileBase, i ) )
            f.close()

    def makeImages( self, colorMap, fileBase, ext ):
        """Outputs the density images"""
        try:
            f = open( self.outFileName + ".%s" % ( ext ), "rb" )
        except:
            print "Can't open file: %.%s" % ( ext ) % ( self.outFileName )
        else:
            w, h, count, minVal, maxVal = struct.unpack( 'iiiff', f.read( GridFileSequence.HEADER_SIZE ) )
            print "%s images in range:" % ( ext ), minVal, maxVal
            gridSize = w * h * 4
            digits = int( np.ceil( np.log10( count ) ) )
            g = Grid( Vector2(0.0, 0.0), Vector2(10.0, 10.0), (w, h) )
            for i in range( count ):
                data = f.read( gridSize )
                g.setFromBinary( data )
                try:
                    s = g.surface( colorMap, minVal, maxVal )
                except MemoryError:
                    print "Error on frame", i
                    raise
                pygame.image.save( s, '{0}{1:0{2}d}.png'.format( fileBase, i, digits ) )
##                pygame.image.save( s, '%s%03d.png' % ( fileBase, i ) )
            f.close()

    def computeAdvecFlow( self, minCorner, size, resolution, distFunc, maxDist, kernelSize, frameSet, lines ):
        """Performs a visualization of marking agents according to their intial position w.r.t. a line"""
        # initialization
        #   Iterate through the agents on the first frame
        frameSet.setNext( 0 )
        f, i = frameSet.next()
        for agt in f.agents:
            pos = agt.pos
            minDist = 1e6
            for line in lines:
                dist = line.pointDistance( pos )
                if ( dist < minDist ):
                    minDist = dist
            agt.value = max( maxDist - minDist, 0 )

        # now iterate through each frame and rasterize it
        outFile = open( self.outFileName + '.advec', 'wb' )
        outFile.write( struct.pack( 'ii', resolution[0], resolution[1] ) )  # size of grid
        outFile.write( struct.pack( 'i', 0 ) )                              # grid count
        outFile.write( struct.pack( 'ff', 0.0, 0.0 ) )                      # range of grid values
        maxVal = 0        
        gridCount = 0
        gridSize = resolution[0] * resolution[1]
        while ( f ):
            g = Grid( minCorner, size, resolution )
            g.rasterizeValue( f, distFunc, kernelSize )
            M = g.maxVal()
            if ( M > maxVal ):
                maxVal = M
            outFile.write( g.binaryString() )
            gridCount += 1
            f, i = frameSet.next( True )

        # add the additional information about grid count and maximum values            
        outFile.seek( 8 )
        outFile.write( struct.pack( 'i', gridCount ) )
        outFile.write( struct.pack( 'ff', 0.0, maxVal ) )
        outFile.close()               
            
def computeFlowLines( center, lines, frameSet ):
    """Computes the flow of agents past the various lines"""
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
    while( f ):
        flowRegion.step()
        f, i = frameSet.next( True )
    return flowRegion
    
def main():
    """Test the functionality"""
    from math import pi, exp
    import os
    pygame.init()
    CELL_SIZE = 0.2
    MAX_AGENTS = -1
    MAX_FRAMES = -1
    FRAME_STEP = 1
    FRAME_WINDOW = 1
    
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
    elif ( True ):
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
##        srcFile = 'denseTest'
        timeStep = 0.1
        FRAME_STEP = 10
        outPath = os.path.join( '/projects','tawaf','sim','jun2011' )
        path = os.path.join( outPath, '{0}.scb'.format( srcFile ) )
        outPath = os.path.join( outPath, srcFile )
        
##        MAX_AGENTS = 50
        MAX_FRAMES = 420
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
    frameSet = FrameSet( path, MAX_FRAMES, MAX_AGENTS, FRAME_STEP )
    print "Total frames:", frameSet.totalFrames()

    grids = GridFileSequence( os.path.join( outPath, 'junk' ) )
    colorMap = FlameMap()

    # output the parameters used to create the data
    # todo:    

    R = 2.0
    
    def distFunc( dispX, dispY, radiusSqd ):
        """Constant distance function"""
        # This is the local density function provided by Helbing
        return np.exp( -(dispX * dispX + dispY * dispY) / (2.0 * radiusSqd ) ) / ( 2.0 * np.pi * radiusSqd )       

    dfunc = lambda x, y: distFunc( x, y, R * R )

    if ( False ):
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

    if ( False ):
        if ( not os.path.exists( os.path.join( outPath, 'speed' ) ) ):
            os.makedirs( os.path.join( outPath, 'speed' ) )
    
        print "\tComputing speeds",
        s = time.clock()
        stats = grids.computeSpeeds( minPt, size, res, R, frameSet, timeStep, GridFileSequence.BLIT_SPEED )
        stats.write( os.path.join( outPath, 'speed', 'stat.txt' ) )
        stats.savePlot( os.path.join( outPath, 'speed', 'stat.png' ), 'Average speed per step' )
        print "Took", (time.clock() - s), "seconds"
        print "\tComputing displacement images",
        s = time.clock()
        imageName = os.path.join( outPath, 'speed', 'speed' )
        # the limit: 0.5 means the color map is saturated from from minVal to 50% of the range
        grids.speedImages( colorMap, imageName, 0.5, MAX_FRAMES )
        pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
        print "Took", (time.clock() - s), "seconds"

    if ( False ):
        if ( not os.path.exists( os.path.join( outPath, 'omega' ) ) ):
            os.makedirs( os.path.join( outPath, 'omega' ) )
    
        print "\tComputing omega",
        s = time.clock()
        stats = grids.computeAngularSpeeds( minPt, size, res, R, frameSet, timeStep, GridFileSequence.BLIT_SPEED, FRAME_WINDOW )
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

    if ( False ):
        if ( not os.path.exists( os.path.join( outPath, 'progress' ) ) ):
            os.makedirs( os.path.join( outPath, 'progress' ) )

        print "\tComputing progress",
        s = time.clock()
        stats = grids.computeProgress( minPt, size, res, R, frameSet, timeStep, FRAME_WINDOW )
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

    if ( True ):
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
        grids.computeRegionSpeed( minPt, size, res, frameSet, polygons, timeStep )
        print "Took", (time.clock() - s), "seconds"
        # output image
        imagePath = os.path.join( outPath, 'regionSpeed', 'region' )
        colorMap = FlameMap()
        regionSpeedImages( grids.outFileName + ".region", imagePath, polygons, colorMap )
        
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
    