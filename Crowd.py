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
        self.data = dFunc( X * X + Y * Y )

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
    def __init__( self, minCorner, size, resolution ):
        """Initializes the grid to span the space starting at minCorner,
        extending size amount in each direction with resolution cells"""
        self.minCorner = minCorner          # tuple (x, y)  - float
        self.size = size                    # tuple (x, y)  - float
        self.resolution = resolution        # tuple (x, y)  - int
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

    def clear( self ):
        # Cells are a 2D array accessible with (x, y) values
        #   x = column, y = row
        self.cells = np.zeros( ( self.resolution[0], self.resolution[1] ), dtype=np.float32 )

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

    

    def rasterizeSpeed( self, f2, f1, distFunc, maxRad, timeStep ):
        """Given two frames of agents, computes per-agent displacement and rasterizes the whole frame"""
        invDT = 1.0 / timeStep
        for i in range( len ( f2.agents ) ):
            ag2 = f2.agents[ i ]
            ag1 = f1.agents[ i ]
            disp = ( ag2.pos - ag1.pos ).magnitude()
            disp *= invDT
            center = self.getCenter( ag2.pos )

            l = center[0] - 1
            r = center[0] + 2
            b = center[1] - 1
            t = center[1] + 2
            
            if ( l < 0 ):
                l = 0
            if ( b < 0 ):
                b = 0
            if ( r >= self.resolution[0] ):
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                t = self.resolution[1]
            self.cells[ l:r, b:t ] =  disp            
##            self.cells[ center[0], center[1] ] = disp

    def rasterizeSpeed2( self, f2, f1, distFunc, maxRad, timeStep ):
        """Given two frames of agents, computes per-agent displacement and rasterizes the whole frame"""
        kernel = Kernel( maxRad, distFunc, self.cellSize )
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

    def surface( self, map, maxVal=1.0 ):
        """Creates a pygame surface"""
        return map.colorOnSurface( (0, maxVal ), self.cells )

class GridSequence:
    """A sequence of grids"""
    def __init__( self ):
        self.densityGrids = []
        self.maxDensity = 0.0
        self.speedGrids = []
        self.maxSpeed = 0.0

    def computeDensity( self, minCorner, size, resolution, distFunc, maxRad, frameSet ):
        frameSet.setNext( 0 )
        lastIdx = -1
        frame, thisIdx = frameSet.next()
        maxVal = 0
        while ( thisIdx > lastIdx ):
            g = Grid( minCorner, size, resolution )
            g.rasterizePosition2( frame, distFunc, maxRad )        
##            g.rasterizePosition( frame, distFunc, maxRad )
            M = g.maxVal()
            if ( M > maxVal ):
                maxVal = M
            self.densityGrids.append( g )
            lastIdx = thisIdx
            frame, thisIdx = frameSet.next()
        self.maxDensity = maxVal

    def computeSpeeds( self, minCorner, size, resolution, distFunc, maxRad, frameSet, timeStep ):
        """Computes the displacements from one cell to the next"""
        WINDOW_SIZE = 2  # the number of frames across which speed is computed
        frameSet.setNext( 0 )
        data = [ frameSet.next() for i in range( WINDOW_SIZE ) ]
        maxVal = 0
        while ( data[ -1 ][1] > data[ 0 ][1] ):
            f1, i1 = data.pop(0)
            f2, i2 = data[ -1 ]
            g = Grid( minCorner, size, resolution )
            g.rasterizeSpeed( f2, f1, distFunc, maxRad, timeStep )
            M = g.maxVal()
            if ( M > maxVal ):
                maxVal = M
            self.speedGrids.append( g )
            data.append( frameSet.next() )
        self.maxSpeed = maxVal


    def densityImages( self, colorMap, fileBase ):
        """Outputs the density images"""
        print "Density images in range:", 0, self.maxDensity
        for i, g in enumerate( self.densityGrids ):
            s = g.surface( colorMap, self.maxDensity )
            pygame.image.save( s, '%s%03d.png' % ( fileBase, i ) )

    def speedImages( self, fileBase ):
        """Outputs the density images"""
        print "Speed images in range:", 0, self.maxSpeed
        for i, g in enumerate( self.speedGrids ):
            s = g.surface( 1.0 / self.maxSpeed )
            pygame.image.save( s, '%s%03d.png' % ( fileBase, i ) )            

class GridFileSequence:
    """Creates a grid sequence from a frame file and streams the resulting grids to
       a file"""
    HEADER_SIZE = 20        # 20 bytes: resolution, grid count, min/max values
    def __init__( self, outFileName ):
        self.outFileName = outFileName

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

    def computeSpeeds( self, minCorner, size, resolution, distFunc, maxRad, frameSet, timeStep, timeWindow=1 ):
        """Computes the displacements from one cell to the next"""
        outFile = open( self.outFileName + '.speed', 'wb' )
        outFile.write( struct.pack( 'ii', resolution[0], resolution[1] ) )  # size of grid
        outFile.write( struct.pack( 'i', 0 ) )                              # grid count
        outFile.write( struct.pack( 'ff', 0.0, 0.0 ) )                      # range of grid values
        maxVal = 0        
        gridCount = 0
        gridSize = resolution[0] * resolution[1]

        frameSet.setNext( 0 )        
        data = [ frameSet.next() for i in range( timeWindow + 1 ) ]
        # continue while the index of the last frame on the queue is greater than the index of the first frame
        while ( data[ -1 ][0] ): 
            f1, i1 = data.pop(0)
            f2, i2 = data[ -1 ]
            g = Grid( minCorner, size, resolution )
            g.rasterizeSpeed( f2, f1, distFunc, maxRad, timeStep * timeWindow )
            M = g.maxVal()
            if ( M > maxVal ):
                maxVal = M
            outFile.write( g.binaryString() )
            gridCount += 1
            data.append( frameSet.next() )

        # add the additional information about grid count and maximum values            
        outFile.seek( 8 )
        outFile.write( struct.pack( 'i', gridCount ) )
        outFile.write( struct.pack( 'ff', 0.0, maxVal ) )
        outFile.close()            

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
                s = g.surface( colorMap, maxVal )
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
                data = f.read( gridSize )
                g.setFromBinary( data )
                s = g.surface( colorMap, maxVal )
                pygame.image.save( s, '%s%03d.png' % ( fileBase, i ) )
            f.close()

    def makeImages( self, colorMap, fileBase, ext ):
        """Outputs the density images"""
        try:
            f = open( self.outFileName + ".%s" % ( ext ), "rb" )
        except:
            print "Can't open desnity file: %.%s" % ( ext ) % ( self.outFileName )
        else:
            w, h, count, minVal, maxVal = struct.unpack( 'iiiff', f.read( GridFileSequence.HEADER_SIZE ) )
            print "%s images in range:" % ( ext ), minVal, maxVal
            gridSize = w * h * 4
            g = Grid( Vector2(0.0, 0.0), Vector2(10.0, 10.0), (w, h) )
            for i in range( count ):
                data = f.read( gridSize )
                g.setFromBinary( data )
                try:
                    s = g.surface( colorMap, maxVal )
                except MemoryError:
                    print "Error on frame", i
                    raise
                pygame.image.save( s, '%s%03d.png' % ( fileBase, i ) )
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
    pygame.init()
    CELL_SIZE = 0.2
    # I want cell-size to be approximately 0.4 - i.e. a single person
    if ( True ):
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
##        path = 'data/bigtawaf/playback.scb'
##        path = 'data/bigtawaf/playback_1agt_20step_30Skip.scb'
        path = 'data/bigtawaf/playback_30step_Allframe.scb'
##        path = 'data/bigtawaf/playback_All_step30_agt100.scb'
##        path = 'data/bigtawaf/playback_50step_20frame.scb'
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
    frameSet = FrameSet( path )

    grids = GridFileSequence( 'junk' )
    colorMap = FlameMap()

    R = 2.0
    print "Density for %s with R = %f" % ( path, R )
    def distFunc( distSqd, radiusSqd ):
        """Constant distance function"""
        # This is the local density function provided by Helbing
        return 1.0 / ( pi * radiusSqd ) * np.exp( - (distSqd / radiusSqd ) )        

    dfunc = lambda x: distFunc( x, R * R )

    if ( True ):
        print "\tComputing density"
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
        print "\tComputing displacements",
        s = time.clock()
        speedRadius = CELL_SIZE / np.sqrt( -np.log(0.5) )
        dfunc = lambda x: np.exp( -( x / ( speedRadius * speedRadius ) ) )
        grids.computeSpeeds( minPt, size, res, dfunc, 3 * speedRadius, frameSet, 1.0 )
        print "Took", (time.clock() - s), "seconds"
        print "\tComputing displacement images",
        s = time.clock()
        imageName = 'data/displace'
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
##    print "\t",
##    grids.speedImages( 'tempVel' )
    

if __name__ == '__main__':
    main()
    