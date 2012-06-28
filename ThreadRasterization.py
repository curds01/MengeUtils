# This file contains a function which perform thread rasterization functionality.
# It is imported into GridFileSequence file

from Grid import *
from Voronoi import *

class BufferGrid:
    """Entry into a buffer for a grid"""
    def __init__( self, id, grid ):
        self.id = id
        self.grid = grid

    def __eq__( self, id ):
        return self.id == id

    def __str__( self ):
        return "BufferGrid %d, %f" % ( self.id, self.grid.maxVal() )

# The   that does the rasterization work
ACTIVE_RASTER_THREADS = 0
def threadRasterize( log, bufferLock, buffer, frameLock, frameSet,
                     minCorner, size, resolution, distFunc, maxRad,
                     domainX, domainY ):
    while ( True ):
        # create grid and rasterize
        # acquire frame
        frameLock.acquire()
        try:
            frame, index = frameSet.next()
        except StopIteration:
            break
        finally:            
            frameLock.release()
        g = Grid( minCorner, size, resolution, domainX, domainY )
        g.rasterizePosition( frame, distFunc, maxRad )
        # update log
        log.setMax( g.maxVal() )  # TODO :: FIX THIS PROBLEM
        log.incCount()
        # put into buffer
        bufferLock.acquire()
        buffer.append( BufferGrid(index, g ) )
        bufferLock.release()
##        # acquire next frame
##        frameLock.acquire()
##        frame, index = frameSet.next()
##        frameLock.release()

def threadVoronoiRasterize( log, bufferLock, buffer, frameLock, frameSet,
                            minCorner, size, resolution, distFunc, maxRad,
                            domainX, domainY ):
    while ( True ):
        # create grid and rasterize
        # acquire frame
        frameLock.acquire()
        try:
            frame, index = frameSet.next()
        except StopIteration:
            break
        finally:            
            frameLock.release()
            
        g = Grid( minCorner, size, resolution, domainX, domainY )
        vRegion = Voronoi( minCorner, size, resolution )
        # Compute density based on Voronoi region
        densityGrid = vRegion.computeVoronoiDensity( g, frame ) # Default agent radius is 1
        # Perform Function convolution
        densityGrid.rasterizeVoronoiDensity( frame, distFunc, maxRad )
##        g.rasterizePosition( frame, distFunc, maxRad )
        # update log
        log.setMax( g.maxVal() )  # TODO :: FIX THIS PROBLEM
        log.incCount()
        # put into buffer
        bufferLock.acquire()
        buffer.append( BufferGrid(index, g ) )
        bufferLock.release()
##        # acquire next frame
##        frameLock.acquire()
##        frame, index = frameSet.next()
##        frameLock.release()