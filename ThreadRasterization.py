# This file contains a function which perform thread rasterization functionality.
# It is imported into GridFileSequence file

from Grid import *
from Voronoi import *
import drawVoronoi

V_RAD = 1.0 # radius to compute constraint Voronoi

class BufferGrid:
    """Entry into a buffer for a grid"""
    def __init__( self, id, grid ):
        self.id = id
        self.grid = grid

    def __eq__( self, id ):
        return self.id == id

    def __str__( self ):
        return "BufferGrid %d, %f" % ( self.id, self.grid.maxVal() )

# The function that does the rasterization work
ACTIVE_RASTER_THREADS = 0
def threadConvolve( log, bufferLock, buffer, frameLock,    # thread info
                     frameSet, gridDomain, kernel ):        # the data to process
    '''Function for performing simple convolution across a sequence of pedestrian data.
    
    @param      log             An instance of RasterReport (see GridFileSequence.py).
                                Each thread gets its own copy.
    @param      bufferLock      A threading.Lock for accessing the buffer.
    @param      buffer          The buffer for storing the finished convolution.  Shared
                                across all threads.
    @param      frameLock       A threading.Lock for accessing the pedestrian data.
    @param      frameSet        An instance of a pedestrian data sequence.
    @param      gridDomain      An instance of AbstractGrid defining the extents and resolution
                                of the convolution domain.
    @param      kernel          An instance of a BaseKernel (see Kernels.py).  Convolution
                                is performed between this kernel and the data in frameSet.
    '''
    while ( True ):
        # create grid and rasterize
        # acquire frame
        frameLock.acquire()
        try:
            signal = Signals.PedestrianSignal( frameSet )
        except StopIteration:
            break
        finally:            
            frameLock.release()
            
        g = gridDomain.getDataGrid()
        kernel.convolve( signal, g )

        # update log
        log.setMax( g.maxVal() )
        log.incCount()
        # put into buffer
        bufferLock.acquire()
        buffer.append( BufferGrid( signal.index, g ) )
        bufferLock.release()

def threadVoronoiRasterize( log, bufferLock, buffer, frameLock, frameSet,
                            minCorner, size, resolution, distFunc, smoothParam,
                            domainX, domainY, obstacles=None, reflection=False ):
    while ( True ):
        vxCell = float(size.x)/resolution.x
        vyCell = float(size.y)/resolution.y
        PADDING_RAD = 1.0
        PADDING_SIZE = Vector2( PADDING_RAD * 1./vxCell, PADDING_RAD * 1./vyCell )
        # create grid and rasterize
        # acquire frame
        frameLock.acquire()
        try:
            frame, index = frameSet.next()
        except StopIteration:
            break
        finally:            
            frameLock.release()

        # Calculate new size for Voronoi with padding
        vDomainX = Vector2( domainX[0] - PADDING_RAD, domainX[1] + PADDING_RAD)
        vDomainY = Vector2( domainY[0] - PADDING_RAD, domainY[1] + PADDING_RAD )
        vMinCorner = Vector2( vDomainX[0], vDomainY[0])
        vSize = Vector2( vDomainX[1], vDomainY[1]) - vMinCorner
        vRes = Vector2( int(vSize.x/vxCell), int(vSize.y/vyCell) )
##        g = Grid( minCorner, size, resolution, domainX, domainY )
##        vRegion = Voronoi( minCorner, size, resolution, obstacles )
        g = Grid( vMinCorner, vSize, vRes, vDomainX, vDomainY )
        vRegion = Voronoi( vMinCorner, vSize, vRes, obstacles)
        # Compute density based on Voronoi region
        densityRegion = vRegion.computeVoronoiDensity( g, frame, minCorner, size,
                                                       resolution, domainX, domainY, PADDING_SIZE, V_RAD ) # Default agent radius is 1
        # TESTING : draw Voronoi diagram as image file
        if ( False ):
            import os
##            filePath = r'\Users\ksuvee\Documents\Density_project\VoronoiRegion'
            filePath = r'\Users\TofuYui\Google Drive\Density_project\VoronoiRegion'
            if ( not os.path.exists( filePath ) ):
                os.makedirs( filePath  )
            fileName = os.path.join( filePath, 'vRegion%s.png' % (index))
            drawVoronoi.drawVoronoi( vRegion.ownerGrid.cells, fileName, obstacles, vRegion.ownerGrid)

        # Perform Function convolution
        densityGrid = Grid( densityRegion.minCorner, densityRegion.size, densityRegion.resolution, initVal=0.0 )
        densityRegion.rasterizeVoronoiDensity( frame, distFunc, smoothParam, densityGrid )
        
        # update log
        # print densityGrid.maxVal()
        log.setMax( densityGrid.maxVal() )
        log.incCount()
        # put into buffer
        bufferLock.acquire()
        buffer.append( BufferGrid( index, densityGrid ) )
        bufferLock.release()

        # acquire next frame ALWAYS GET COMMENT
##        frameLock.acquire()
##        frame, index = frameSet.next()
##        frameLock.release()

##def threadStandardVoronoiRasterize( log, bufferLock, buffer, frameLock, frameSet,
##                                    minCorner, size, resolution, boundIndexX, boundIndexY,
##                                    boundArea, domainX, domainY, obstacles=None ):
##    while ( True ):
##        vxCell = float(size.x)/resolution.x
##        vyCell = float(size.y)/resolution.y
##        PADDING_RAD = 1.0
##        PADDING_SIZE = Vector2( PADDING_RAD * 1./vxCell, PADDING_RAD * 1./vyCell )
##        # create grid and rasterize
##        # acquire frame
##        frameLock.acquire()
##        try:
##            frame, index = frameSet.next()
##        except StopIteration:
##            break
##        finally:            
##            frameLock.release()
##
##        # Calculate new size for Voronoi with padding
##        vDomainX = Vector2( domainX[0] - PADDING_RAD, domainX[1] + PADDING_RAD)
##        vDomainY = Vector2( domainY[0] - PADDING_RAD, domainY[1] + PADDING_RAD )
##        vMinCorner = Vector2( vDomainX[0], vDomainY[0])
##        vSize = Vector2( vDomainX[1], vDomainY[1]) - vMinCorner
##        vRes = Vector2( int(vSize.x/vxCell), int(vSize.y/vyCell) )
####        g = Grid( minCorner, size, resolution, domainX, domainY )
####        vRegion = Voronoi( minCorner, size, resolution, obstacles )
##        g = Grid( vMinCorner, vSize, vRes, vDomainX, vDomainY )
##        vRegion = Voronoi( vMinCorner, vSize, vRes, obstacles)
##        # Compute density based on Voronoi region
##        densityRegion = vRegion.computeVoronoiDensity( g, frame, minCorner, size,
##                                                       resolution, domainX, domainY, PADDING_SIZE, V_RAD ) # Default agent radius is 1
##        # TESTING : draw Voronoi diagram as image file
##        if ( False ):
##            import os
####            filePath = r'\Users\ksuvee\Documents\Density_project\VoronoiRegion'
##            filePath = r'\Users\TofuYui\Google Drive\Density_project\VoronoiRegion'
##            if ( not os.path.exists( filePath ) ):
##                os.makedirs( filePath  )
##            fileName = os.path.join( filePath, 'vRegion%s.png' % (index))
##            drawVoronoi.drawVoronoi( vRegion.ownerGrid.cells, fileName, obstacles, vRegion.ownerGrid )
##
##        densityGrid = Grid( densityRegion.minCorner, densityRegion.size, densityRegion.resolution, initVal=0.0 )
##        sumDensity = np.sum( densityRegion.cells[ boundIndexX[0]:boundIndexX[1],
##                                                  boundIndexY[0]:boundIndexY[1] ] )
##        densityGrid.cells[ boundIndexX[0]:boundIndexX[1],
##                           boundIndexY[0]:boundIndexY[1] ] = sumDensity/boundArea
##        # update log
##        log.setMax( densityGrid.maxVal() )
##        log.incCount()
##        # put into buffer
##        bufferLock.acquire()
##        buffer.append( BufferGrid(index, densityGrid ) )
##        bufferLock.release()
##
##
##def threadStandardRasterize( log, bufferLock, buffer, frameLock, frameSet,
##                            minCorner, size, resolution, defineRegionX, defineRegionY,
##                            domainX, domainY ):
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
##        g = Grid( minCorner, size, resolution, domainX, domainY )
##        g.rasterizeStandard( frame, defineRegionX, defineRegionY )
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

