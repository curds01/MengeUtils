# Class for performing the work of crowd analysis

import time
from PyQt4 import QtGui, QtCore
from primitives import Vector2, Segment, segmentsFromString
from scbData import FrameSet, NPFrameSet
from ColorMap import *
import Crowd
import os, sys
from GFSVis import visualizeGFS

# TODO: Switch everything to NPFrameSet

class CrowdAnalyzeThread( QtCore.QThread ):
    '''Class to perform the crowd analysis'''
    def __init__( self, data, parent=None ):
        QtCore.QThread.__init__( self, parent )
        self.data = data

    def run( self ):
        '''The work of the thread'''
        cellSize = float( self.data[ 'cellSize' ] )
        domainSize = Vector2( float(self.data[ 'sizeX' ] ), float( self.data[ 'sizeY' ] ) )
        domainMin = Vector2( float( self.data[ 'minPtX' ] ), float( self.data[ 'minPtY' ] ) )
        res = (int( domainSize.x / cellSize ), int( domainSize.y / cellSize ) )
        scbFile = self.data[ 'SCB' ]

        frameSet = FrameSet( scbFile )

        outPath = self.data[ 'tempDir' ]
        if ( not os.path.exists( outPath ) ):
            os.makedirs( outPath )
        tempFile = os.path.join( self.data[ 'tempDir' ], self.data[ 'tempName' ] )
        grids = Crowd.GridFileSequence( tempFile )
        colorMap = COLOR_MAPS[ self.data[ 'colorMap' ] ]()

        R = self.data[ 'kernelSize' ]

        def distFunc( X, Y, radiusSqd ):
            """Constant distance function"""
            # This is the local density function provided by Helbing
            dist = np.sqrt( X * X + Y * Y )
            return 1.0 / ( np.pi * radiusSqd ) * np.exp( - (dist * dist / radiusSqd ) )        

        dfunc = lambda x, y: distFunc( x, y, R * R )

        densityAction = self.data[ 'DENSE_ACTION' ]
        if ( densityAction == 1 or densityAction == 3 ):
            print 'Computing densities...'
            s = time.clock()
            grids.computeDensity( domainMin, domainSize, res, dfunc, 3 * R, frameSet )
            print '    done in %.2f seconds' % ( time.clock() - s )
        if ( densityAction >= 2 ):
            imgPath = os.path.join( self.data[ 'outDir' ], 'density' )
            if ( not os.path.exists( imgPath ) ):
                os.makedirs( imgPath )
            imageName = os.path.join( imgPath, 'density_' )
            print 'Creating density images...'
            s = time.clock()
            reader = GridFileSequenceReader( grids.outFileName + ".density"  )
            visualizeGFS( reader, colorMap, imageName, self.data[ 'imgFormat' ], 1.0, grids.obstacles )
            print '    done in %.2f seconds' % ( time.clock() - s ) 

        speedAction = self.data[ 'SPEED_ACTION' ]
        if ( speedAction == 1 or speedAction == 3 ):
            print 'Computing speeds...'
            s = time.clock()
            grids.computeSpeeds( domainMin, domainSize, res, 3 * R, frameSet, float( self.data[ 'timeStep' ] ), [], Crowd.GridFileSequence.BLIT_SPEED, int( self.data[ 'speedWindow' ] ) )
            print '    done in %.2f seconds' % ( time.clock() - s )
        if ( speedAction >= 2 ):
            imgPath = os.path.join( self.data[ 'outDir' ], 'speed' )
            if ( not os.path.exists( imgPath ) ):
                os.makedirs( imgPath )
            imageName = os.path.join( imgPath, 'speed_' )
            print 'Creating speed images...' 
            s = time.clock()
            reader = GridFileSequenceReader( grids.outFileName + ".speed"  )
            visualizeGFS( reader, colorMap, imageName, self.data[ 'imgFormat' ], 1.0, grids.obstacles )
            print '    done in %.2f seconds' % ( time.clock() - s ) 

        frameSet = NPFrameSet( scbFile )
        flowAction = self.data[ 'FLOW_ACTION' ]
        if ( flowAction == 1 or flowAction == 3 ):
            segments = segmentsFromString( self.data[ 'flowLines' ], Segment )
            print 'Computing flow across %d segments' % len(segments) 
            s = time.clock()
            Crowd.computeFlow( frameSet, segments, tempFile )
            print '    done in %.2f seconds' % ( time.clock() - s ) 
        if ( flowAction >= 2 ):
            print 'Computing flow plots...' 
            s=time.clock()
            # plot the beasts
            Crowd.plotFlow( tempFile, frameSet.simStepSize )
            print '    done in %.2f seconds' % ( time.clock() - s ) 
        
        print 'FINISHED'