# This file contain GridFileSquence class which create grid for squence of frame

import numpy as np
import pygame
import struct
import threading
import time

from Grid import *
from primitives import Vector2
from ThreadRasterization import *


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
    
    def __init__( self, outFileName, domainX, domainY ):
        """ domainX is a Vector2 storing range of value x from user. domainX[0] stores min value and domainX[1] stores max value.
            domainY is a similar to domainX but in y-axis"""
        self.outFileName = outFileName
        self.domainX = domainX
        self.domainY = domainY

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

        THREAD_COUNT = 1
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
            if (distFunc != FUNCS_MAP['vsquare']):
                rasterThreads.append( threading.Thread( target=threadRasterize, args=( rasterLogs[-1], bufferLock, buffer,
                                                                                       frameLock, frameSet,
                                                                                       minCorner, size, resolution,
                                                                                       distFunc, maxRad,
                                                                                       self.domainX, self.domainY) )  )
            else:
                rasterThreads.append( threading.Thread( target=threadVoronoiRasterize, args=( rasterLogs[-1], bufferLock, buffer,
                                                                                       frameLock, frameSet,
                                                                                       minCorner, size, resolution,
                                                                                       distFunc, maxRad,
                                                                                       self.domainX, self.domainY) )  )
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

    def splatAgents( self, minCorner, size, resolution, radius, frameSet ):
        '''Simply splats the agents onto the grid'''
        print "Splatting agents:"
        print "\tminCorner:  ", minCorner
        print "\tsize:       ", size
        print "\tresolution: ", resolution
        print "\tradius:     ", radius
        outFile = open( self.outFileName + '.splat', 'wb' )
        outFile.write( struct.pack( 'ii', resolution[0], resolution[1] ) )  # size of grid
        outFile.write( struct.pack( 'i', 0 ) )                              # grid count
        outFile.write( struct.pack( 'ff', 0.0, 0.0 ) )                      # range of grid values

        frameSet.setNext( 0 )

        # all of this together should make a function which draws filled-in circles
        #   at APPROXIMATELY the center of the agents.
        maxRad = radius / 3.0   # this makes it work with the kernel generation
        def inCircle( dispX, dispY, rSqd ):
            dispSqd = ( dispX * dispX + dispY * dispY )
            return ( dispSqd <= rSqd ) * 1.0
        dFunc = lambda x, y: inCircle( x, y, radius * radius )

        gridCount = 0        
        while ( True ):
            try:
                frame, index = frameSet.next()
            except StopIteration:
                break
            grid = Grid( minCorner, size, resolution, self.domainX, self.domainY ,0.0)
            
            grid.rasterizePosition( frame, dFunc, maxRad )
            outFile.write( grid.binaryString() )
            gridCount += 1
            
        outFile.seek( 8 )
        outFile.write( struct.pack( 'i', gridCount ) )
        outFile.write( struct.pack( 'ff', 0.0, 1.0 ) )
        outFile.close()
        
    def computeSpeeds( self, minCorner, size, resolution, maxRad, frameSet, timeStep, excludeStates, speedType=NORM_CONTRIB_SPEED, timeWindow=1 ):
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
        while ( data[ -1 ][0] != None ):
            f1, i1 = data.pop(0)
            f2, i2 = data[ -1 ]
            g = gridFunc() 
            speedFunc( g, kernel, f2, f1, distFunc, maxRad, timeStep * timeWindow, excludeStates, stats )
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
    
    def computeProgress( self, minCorner, size, resolution, maxRad, frameSet, timeStep, excludeStates, timeWindow=1 ):
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
            g.rasterizeProgress( f2, initFrame, progress, excludeStates, stats )

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

    def computeAngularSpeeds( self, minCorner, size, resolution, maxRad, frameSet, timeStep, excludeStates, speedType=BLIT_SPEED, timeWindow=1 ):
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
            speedFunc( g, kernel, f2, f1, distFunc, maxRad, timeStep * timeWindow, excludeStates, stats )
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
            g = Grid( Vector2(0.0, 0.0), Vector2(10.0, 10.0), (w, h), self.domainX, self.domainY )
            for i in range( count ):
                data = f.read( gridSize )
                g.setFromBinary( data )
##                print "minVal " + str(minVal)
##                print "maxVal " + str(maxVal)
                s = g.surface( colorMap, minVal, maxVal )
##                print "i : " + str(i)
                pygame.image.save( s, '%s%03d.png' % ( fileBase, i ) )
            f.close()

    def speedImages( self, colorMap, fileBase, limit, maxFrames=-1 ):
        """Outputs the speed images"""
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

    def makeImages( self, colorMap, fileBase, suffix, imgFormat='png' ):
        """Outputs the density images"""
        try:
            f = open( self.outFileName + ".%s" % ( suffix ), "rb" )
        except:
            print "Can't open file: %.%s" % ( suffix ) % ( self.outFileName )
        else:
            w, h, count, minVal, maxVal = struct.unpack( 'iiiff', f.read( GridFileSequence.HEADER_SIZE ) )
            print "%s images in range:" % ( suffix ), minVal, maxVal
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
                pygame.image.save( s, '{0}{1:0{2}d}.{3}'.format( fileBase, i, digits, imgFormat ) )
            f.close()

    def computeAdvecFlow( self,  minCorner, size, resolution, distFunc, maxDist, kernelSize, frameSet, lines ):
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
        while ( True ):
            g = Grid( minCorner, size, resolution )
            g.rasterizeValue( f, distFunc, kernelSize )
            M = g.maxVal()
            if ( M > maxVal ):
                maxVal = M
            outFile.write( g.binaryString() )
            gridCount += 1
            try:
                f, i = frameSet.next( True )
            except StopIteration:
                break

        # add the additional information about grid count and maximum values            
        outFile.seek( 8 )
        outFile.write( struct.pack( 'i', gridCount ) )
        outFile.write( struct.pack( 'ff', 0.0, maxVal ) )
        outFile.close()               
    def computeRegionSpeed( self, frameSet, polygons, timeStep, excludeStates, timeWindow=1 ):
        '''Given an ordered set of polygons, computes the average speed for all agents in each polygon
        per time step.'''
        # NOTE: This only really applies to the tawaf.
        print "Computing regional speed:"
        print "\ttime step:       ", timeStep
        print "Number of polygons:", len(polygons)

        frameSet.setNext( 0 )        
        data = [ frameSet.next() for i in range( timeWindow + 1 ) ]

        regions = None
        speeds = []
        while ( data[ -1 ][0] ):
            f1, i1 = data.pop(0)
            f2, i2 = data[ -1 ]
            frameSpeeds, regions = findRegionSpeed( f1, f2, timeStep * timeWindow, polygons, excludeStates, regions )
            speeds.append( frameSpeeds )
            data.append( frameSet.next() )
        data = np.array( speeds )
        np.savetxt( self.outFileName + ".region", data, fmt='%.5f' )