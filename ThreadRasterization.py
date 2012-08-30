# This file contains a function which perform thread rasterization functionality.
# It is imported into GridFileSequence file

from Grid import *
from Voronoi import *
import drawVoronoi
import threading

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

DEBUG = False
printLock = threading.Lock()
def threadPrint( msg ):
    '''A simple function for doing threadsafe printing so that various output streams
    don't step on each other.  The calling thread's identity is pre-pended.

    @param      msg         A string.  The message to print.
    '''
    if ( DEBUG ):
        printLock.acquire()
        print '%s: %s' % ( threading.current_thread().getName(), msg )
        printLock.release()

# TODO: This could be refactored.
# The only difference between these three function is updating the signal and doing the work.
#   If a single class were passed which is responsible for offering methods:
#       getNextInput
#       processInput
#       getGridResult
#   Then this could be a single function, with a single argument that is responsible for
#   knowin what the work is.

def threadConvolve( log, bufferLock, buffer, frameLock,     # thread info
                    signal, frameSet,                       # the input signal
                    gridDomain, kernel ):                   # the convolution domain and convolution kernel
    '''Function for performing simple convolution across a sequence of pedestrian data.
    
    @param      log             An instance of RasterReport (see GridFileSequence.py).
                                Each thread gets its own copy.
    @param      bufferLock      A threading.Lock for accessing the buffer.
    @param      buffer          The buffer for storing the finished convolution.  Shared
                                across all threads.
    @param      frameLock       A threading.Lock for accessing the pedestrian data.
    @param      signal          An instance of the signal.  Each thread has a unique signal instance.
    @param      frameSet        An instance of signal data.  In each iteration, the signal's
                                data is set with this.
    @param      gridDomain      An instance of AbstractGrid defining the extents and resolution
                                of the convolution domain.
    @param      kernel          An instance of a BaseKernel (see Kernels.py).  Convolution
                                is performed between this kernel and the data in frameSet.
    '''
    needInit, iValue = kernel.needsInitOutput( signal )      
    while ( True ):
        # create grid and rasterize
        # acquire frame
        frameLock.acquire()
        try:
            signal.setData( frameSet )
        except StopIteration:
            break
        except:
            raise
        finally:            
            frameLock.release()
              
        g = gridDomain.getDataGrid( initVal=iValue, leaveEmpty=not needInit )
        threadPrint('Grid %d- %s' % ( signal.index, hex( id( g ) ) ) )
        kernel.convolve( signal, g )

        # update log
        log.setMax( g.maxVal() )
        log.setMin( g.minVal() )
        log.incCount()
        threadPrint( "\tAfter convolve: min/max/mean values: %f, %f, %f" % ( g.minVal(), g.maxVal(), g.cells.mean() ) )
        # put into buffer
        bufferLock.acquire()
        buffer.append( BufferGrid( signal.index, g ) )
        bufferLock.release()


def threadVoronoiDensity( log, bufferLock, buffer, frameLock,  # thread management
                          frameSet,            # the iterable set of sites
                          gridDomain,          # the domain over which the voronoi is computed
                          obstacles=None,      # the optional set of obstacles (for the constraints)
                          limit=-1                    
                   ):
    '''Function for computing the discrete, constrained voronoi diagram over a given domain.

    @param      log             An instance of RasterReport (see GridFileSequence.py).
                                Each thread gets its own copy.
    @param      bufferLock      A threading.Lock for accessing the buffer.
    @param      buffer          The buffer for storing the finished convolution.  Shared
                                across all threads.
    @param      frameLock       A threading.Lock for accessing the pedestrian data.
    @param      frameSet        An instance of site data.  Typically, it is pedestrian data
                                (real or synthesized).
    @param      gridDomain      An instance of AbstractGrid defining the extents and resolution
                                of the domain in which the Voronoi is computed.
    @param      obstacles        An instance of ???OBSTACLE???.  Enables the constrained voronoi
                                computations.  Currently not supported
    @param      limit           A float.  The maximum distance a point can be and still lie
                                in a voronoi region.
    '''
        
    while ( True ):
        # create grid and rasterize
        # acquire frame
        frameLock.acquire()
        try:
            frame, index = frameSet.next()
            ids = frameSet.getFrameIds()
        except StopIteration:
            break
        finally:            
            frameLock.release()

        try:
            density = computeVoronoiDensity( gridDomain, frame, ids, obstacles, limit )
        except Exception as e:
            print "ERROR", e
            raise

        # update log
        log.setMax( density.maxVal() )
        log.setMin( density.minVal() )
        log.incCount()
        threadPrint( "Grid %d has min/max/mean values: %f, %f, %f" % ( index, density.minVal(), density.maxVal(), density.cells.mean() ) )
        # put into buffer
        bufferLock.acquire()
        buffer.append( BufferGrid( index, density ) )
        bufferLock.release()

def threadVoronoi( log, bufferLock, buffer, frameLock,  # thread management
                   frameSet,            # the iterable set of sites
                   gridDomain,          # the domain over which the voronoi is computed
                   obstacles=None,      # the optional set of obstacles (for the constraints)
                   limit=10.0
                   ):
    '''Function for computing the discrete, constrained voronoi diagram over a given domain.

    @param      log             An instance of RasterReport (see GridFileSequence.py).
                                Each thread gets its own copy.
    @param      bufferLock      A threading.Lock for accessing the buffer.
    @param      buffer          The buffer for storing the finished convolution.  Shared
                                across all threads.
    @param      frameLock       A threading.Lock for accessing the pedestrian data.
    @param      frameSet        An instance of site data.  Typically, it is pedestrian data
                                (real or synthesized).
    @param      gridDomain      An instance of AbstractGrid defining the extents and resolution
                                of the domain in which the Voronoi is computed.
    @param      obstacles       An instance of ???OBSTACLE???.  Enables the constrained voronoi
                                computations.  Currently not supported
    @param      limit           A float.  The maximum distance a point can be and still lie
                                in a voronoi region.
    '''
        
    while ( True ):
        # create grid and rasterize
        # acquire frame
        frameLock.acquire()
        try:
            frame, index = frameSet.next()
            ids = frameSet.getFrameIds()
        except StopIteration:
            break
        finally:            
            frameLock.release()

        voronoi = computeVoronoi( gridDomain, frame, ids, obstacles, limit )

        # update log
        log.setMax( voronoi.maxVal() )
        log.setMin( voronoi.minVal() )
        log.incCount()
        threadPrint( "Grid %d has min/max/mean values: %f, %f, %f" % ( index, voronoi.minVal(), voronoi.maxVal(), voronoi.cells.mean() ) )
        # put into buffer
        bufferLock.acquire()
        buffer.append( BufferGrid( index, voronoi ) )
        bufferLock.release()
