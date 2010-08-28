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
def threadOutput( outFile, buffer, bufferLock ):
    """Reads grids from the buffer and writes them to the output file"""
    nextGrid = 0
    while ( buffer or ACTIVE_RASTER_THREADS ):
        # keep doing the work as long as the buffer has contents or there are active raster threads
        bufferLock.acquire()
        try:
            i = buffer.index( nextGrid )
            bg = buffer.pop( i )
            bufferLock.release()
##            print "Writing frame", nextGrid
            outFile.write( bg.grid.binaryString() )
            nextGrid += 1
        except ValueError:
            bufferLock.release()
            time.sleep( 1.0 )
    

class Point:
    """2D point"""
    def __init__( self, x, y ):
        self.x = x
        self.y = y

    def __str__( self ):
        return '(%.3f, %.3f)' % ( self.x, self.y )

    def __repr__( self ):
        return str( self )

    def distance( self, p ):
        return (p - self).length()

    def __sub__( self, p ):
        return Point( self.x - p.x, self.y - p.y )

    def __isub__( self, p ):
        self.x -= p.x
        self.y -= p.y
        return self

    def __add__( self, p ):
        return Point( self.x + p.x, self.y + p.y )

    def __iadd__( self, p ):
        self.x += p.x
        self.y += p.y
        return self

    def __div__( self, s ):
        return Point( self.x / s, self.y / s )

    def length( self ):
        return sqrt( self.x * self.x + self.y * self.y )

class Agent:
    """Basic agent class"""
    def __init__( self, position ):
        self.pos = position             # a Point object
        self.vel = None

    def __str__( self ):
        return '%s' % ( self.pos )

class Frame:
    """A set of agents for a given time frame"""
    def __init__( self, agentCount ):
        self.agents = [ Agent( Point(0,0) ) for i in range( agentCount ) ]

    def __str__( self ):
        s = 'Frame with %d agents' % ( len(self.agents) )
        for agt in self.agents:
            s += '\n\t%s' % agt
        return s

    def setPosition( self, i, pos ):
        self.agents[ i ].pos = pos

    def computeVelocity( self, prevFrame, dt ):
        """Computes the velocity for each agent based ona previous frame"""
        for i, agent in enumerate( self.agents ):
            agent.vel = ( agent.pos - prevFrame.agents[ i ].pos ) / dt

    def getPosition( self, i ):
        return self.agents[ i ].pos

class FrameSet:
    """A pseudo iterator for frames in an scb file"""
    def __init__( self, scbFile ):
        self.file = open( scbFile, 'rb' )
        data = self.file.read( 4 )
        print "SCB file version:", data
        data = self.file.read( 4 )
        self.agtCount = struct.unpack( 'i', data )[0]
        print "\t%d agents" % ( self.agtCount )
        self.frameSize = self.agtCount * 12 # three floats per agent, 4 bytes per float
        self.currFrame = -1

    def next( self, updateFrame=None ):
        """Returns the next frame in sequence from current point"""
        self.currFrame += 1
        if ( updateFrame ):
            frm = updateFrame
        else:
            frm = Frame( self.agtCount )
        for i in range( self.agtCount ):
            data = self.file.read( 12 ) # three 4-byte floats
            if ( data == '' ):
                frm = None
                break
            else:
                try:
                    x, y, o = struct.unpack( 'fff', data )                  
                    frm.setPosition( i, Point( x, y ) )
                except struct.error:
                    frm = None
                    break
        return frm, self.currFrame

    def setNext( self, index ):
        """Sets the set so that the call to next frame will return frame index"""
        if ( index < 0 ):
            index = 0
        self.currFrame = index
        byteAddr = self.currFrame * self.frameSize + 8      # +8 is the header offset
        self.file.seek( byteAddr )
        self.currFrame -= 1

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
        hCount = int( 2 * radius / cSize.x )
        if ( hCount % 2 == 0 ):
            hCount += 1
        vCount = int( 2 * radius / cSize.y )
        if ( vCount % 2 == 0 ):
            vCount += 1
        self.data = np.zeros( (hCount, vCount), dtype=np.float32 )
        centerX = hCount / 2
        centerY = vCount / 2
        for x in range( hCount ):
            for y in range( vCount ):
                offsetX = ( centerX - x ) * cSize.x
                offsetY = ( centerY - y ) * cSize.y
                dist = np.sqrt( offsetX * offsetX + offsetY * offsetY )
                self.data[ x, y ] = dFunc( dist )
                
class Grid:
    """Class to discretize scalar field computation"""
    def __init__( self, minCorner, size, resolution ):
        """Initializes the grid to span the space starting at minCorner,
        extending size amount in each direction with resolution cells"""
        self.minCorner = minCorner          # tuple (x, y)  - float
        self.size = size                    # tuple (x, y)  - float
        self.resolution = resolution        # tuple (x, y)  - int
        self.clear()
        self.cellSize = Point( size.x / float( resolution[0] ), size.y / float( resolution[1] ) )
        
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

    def rasterizeSpeed( self, f2, f1, distFunc, maxRad, timeStep ):
        """Given two frames of agents, computes per-agent displacement and rasterizes the whole frame"""
        kernel = Kernel( maxRad, distFunc, self.cellSize )
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        invDT = 1.0 / timeStep
        for i in range( len ( f2.agents ) ):
            ag2 = f2.agents[ i ]
            ag1 = f1.agents[ i ]
            disp = ( ag2.pos - ag1.pos ).length() * invDT
##            print "Agent %d travels:" % i , disp
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
            g.rasterizePosition( frame, distFunc, maxRad )
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

        THREAD_COUNT = 3
        # file output
        outFile = open( self.outFileName + '.density', 'wb' )
        outFile.write( struct.pack( 'ii', resolution[0], resolution[1] ) )  # size of grid
        outFile.write( struct.pack( 'i', 0 ) )                              # grid count
        outFile.write( struct.pack( 'ff', 0.0, 0.0 ) )                      # range of grid values
        buffer = []
        bufferLock = threading.Lock()
        saveThread = threading.Thread( target=threadOutput, args=(outFile, buffer, bufferLock ) )
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
            print "ACTIVE_RASTER_THREADS:", ACTIVE_RASTER_THREADS
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
            g = Grid( Point(0.0, 0.0), Point(10.0, 10.0), (w, h) )
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
            print "Density images in range:", minVal, maxVal
            gridSize = w * h * 4
            g = Grid( Point(0.0, 0.0), Point(10.0, 10.0), (w, h) )
            for i in range( count ):
                data = f.read( gridSize )
                g.setFromBinary( data )
                s = g.surface( colorMap, maxVal )
                pygame.image.save( s, '%s%03d.png' % ( fileBase, i ) )
            f.close()
                       
class CrowdVis:
    """Visualizes discrete agents"""
    def __init__( self ):
        pass

def main():
    """Test the functionality"""
    from math import pi, exp
    pygame.init()
    CELL_SIZE = 0.2
    # I want cell-size to be approximately 0.4 - i.e. a single person
    if ( False ):
        size = Point(12.0, 12.0 )
        minPt = Point( size.x / -2.0, size.y / -2.0 )
        res = (int( size.x / CELL_SIZE ), int( size.y / CELL_SIZE ) )
        path = 'data/Circle10/playbackPLE.scb'
    elif ( True ):
        size = Point(60.0, 60.0 )
        minPt = Point( size.x / -2.0, size.y / -2.0 )
        res = (int( size.x / CELL_SIZE ), int( size.y / CELL_SIZE ) )
        path = '/projects/SG10/CrowdViewer/Exe/Win32/2circle/playback.scb'        
##        path = '/projects/SG10/CrowdViewer/Exe/Win32/2circle/playbackRVO.scb'
    elif ( False ):
        size = Point( 150.0, 110.0 )
        minPt = Point( -70.0, -55.0 )
        res = (int( size.x / CELL_SIZE ), int( size.y / CELL_SIZE ) )
        path = 'data/bigtawaf/playback.scb'
##        path = 'data/tawaf/playback.scb'
    elif ( False ):
        size = Point( 15, 5 )
        minPt = Point( -1.0, -2.5 )
        res = (int( size.x / CELL_SIZE ), int( size.y / CELL_SIZE ) )
        path = 'linear.scb'
    elif ( True ):
        size = Point( 30, 5 )
        minPt = Point( -1.0, -2.5 )
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
    def distFunc( dist, radiusSqd ):
        """Constant distance function"""
        # This is the local density function provided by Helbing
        return 1.0 / ( pi * radiusSqd ) * exp( - (dist * dist / radiusSqd ) )        

    dfunc = lambda x: distFunc( x, R * R )

    if ( True ):
        print "\tComputing density",
        s = time.clock()
        grids.computeDensity(  minPt, size, res, dfunc, 3 * R, frameSet )
        print "Took", (time.clock() - s), "seconds"
        print "\tComputing density images",
        s = time.clock()
        imageName = 'data/dense'
        grids.densityImages( colorMap, imageName )
        pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
        print "Took", (time.clock() - s), "seconds"

    print "\tComputing displacements",
    s = time.clock()
    grids.computeSpeeds( minPt, size, res, dfunc, 3 * R, frameSet, 0.1 )
    print "Took", (time.clock() - s), "seconds"
    print "\tComputing displacement images",
    s = time.clock()
    imageName = 'data/displace'
    grids.speedImages( colorMap, imageName )
    pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
    print "Took", (time.clock() - s), "seconds"
##    print "\t",
##    grids.speedImages( 'tempVel' )
    

if __name__ == '__main__':
    main()