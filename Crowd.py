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
##        g.rasterizePosition2( frame, distFunc, maxRad )
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
    def __init__( self, radius, dFunc, cSize, normalize=True ):
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
        #self.data = dFunc( X * X + Y * Y )
        self.data = dFunc( X, Y )
        if ( normalize ):
            self.data /= self.data.sum()

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

    def rasterizeSpeedBlit( self, kernel, f2, f1, distFunc, maxRad, timeStep, callBack=None ):
        """Given two frames of agents, computes per-agent displacement and rasterizes the whole frame"""
        invDT = 1.0 / timeStep
        for i in range( len ( f2.agents ) ):
            ag2 = f2.agents[ i ]
            ag1 = f1.agents[ i ]
            disp = ( ag2.pos - ag1.pos ).magnitude()
            disp *= invDT
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
            kernel = Kernel( maxRad, distFunc, cellSize, False )
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
            kernel = Kernel( maxRad, distFunc, cellSize, False )

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

    def speedImages( self, colorMap, fileBase ):
        """Outputs the density images"""
        try:
            f = open( self.outFileName + ".speed", "rb" )
        except:
            print "Can't open desnity file: %.speed" % ( self.outFileName )
        else:
            w, h, count, minVal, maxVal = struct.unpack( 'iiiff', f.read( GridFileSequence.HEADER_SIZE ) )
            print "Speed images in range:", minVal, maxVal
            gridSize = w * h * 4
            g = Grid( Vector2(0.0, 0.0), Vector2(10.0, 10.0), (w, h) )
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
    # I want cell-size to be approximately 0.4 - i.e. a single person
    timeStep = 1.0
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
        if ( True ):
            path = '/projects/tawaf/sim/jun2011/13K_60sec.scb'
            timeStep = 0.1
        elif ( True ):
            path = '/projects/tawaf/sim/jun2011/13K_2min_1Hz.scb'
            timeStep = 1.0
        elif ( False ):
            path = '/projects/tawaf/sim/jun2011/13K_10min_1Hz.scb'
            timeStep = 1.0
##        path = 'data/bigtawaf/playback.scb'
##        MAX_AGENTS = 50
##        FRAME_STEP = 20
        MAX_FRAMES = 192
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
    frameSet = FrameSet( path, MAX_FRAMES, MAX_AGENTS, FRAME_STEP )

    outPath = '/projects/tawaf/sim/jun2011'
    grids = GridFileSequence( os.path.join( outPath, 'junk' ) )
    colorMap = FlameMap()

    R = 2.0
    
    def distFunc( dispX, dispY, radiusSqd ):
        """Constant distance function"""
        # This is the local density function provided by Helbing
        return np.exp( - ( (dispX * dispX + dispY * dispY) / radiusSqd ) )        

    dfunc = lambda x, y: distFunc( x, y, R * R )

    if ( False ):
        print "\tComputing density with R = %f" % R
        s = time.clock()
        grids.computeDensity(  minPt, size, res, dfunc, 3 * R, frameSet )
        print "\t\tTotal computation time: ", (time.clock() - s), "seconds"
        print "\tComputing density images",
        s = time.clock()
        imageName = 'data/dense'
        grids.densityImages( colorMap, imageName )
        pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
        print "Took", (time.clock() - s), "seconds"

    if ( True ):
        print "\tComputing speeds",
        s = time.clock()
        stats = grids.computeSpeeds( minPt, size, res, R, frameSet, timeStep, GridFileSequence.BLIT_SPEED )
        stats.write( os.path.join( outPath, 'speedStat.txt' ) )
        print "Took", (time.clock() - s), "seconds"
        print "\tComputing displacement images",
        s = time.clock()
        imageName = os.path.join( outPath, 'speed' )
        grids.speedImages( colorMap, imageName )
        pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
        print "Took", (time.clock() - s), "seconds"

    if ( False ):
        lines = [ GLLine( Vector2(0.81592, 5.12050), Vector2( 0.96233, -5.27461) ) ]
        print "\tComputing advection",
        s = time.clock()
        grids.computeAdvecFlow( minPt, size, res, dfunc, 3.0, 3 * R, frameSet, lines )
        print "Took", (time.clock() - s), "seconds"
        print "\tComputing advection images",
        s = time.clock()
        imageName = 'data/advec_'
        grids.makeImages( colorMap, imageName, 'advec' )
        pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
        print "Took", (time.clock() - s), "seconds"
        
    if ( False ):
        # flow lines
                     
        lines = ( GLLine( Vector2( 4.56230, -7.71608 ), Vector2( 81.49586, -4.55443  ) ),
                  GLLine( Vector2( 5.08924, 5.72094 ), Vector2( 82.28628, 8.61913  ) ),
                  GLLine( Vector2( 3.50842, 8.09218 ), Vector2( 2.71800, 51.30145  ) ),
                  GLLine( Vector2( -5.97654, 5.72094 ), Vector2( -8.87472, 51.56492  ) ),
                  GLLine( Vector2( -6.50348, -7.18914 ), Vector2( -40.75473, -53.56005  ) ),
                  GLLine( Vector2( -1.23406, -6.92567 ), Vector2( 1.13718, -51.18881  ) ),
                  GLLine( Vector2( 3.50842, -7.45261 ), Vector2( 44.08297, -45.65592 ) ) )
        flow = computeFlowLines( Vector2( 0, 0 ), lines, frameSet )
        file = open( 'data/flow.txt', 'w' )
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
    