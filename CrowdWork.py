# Class for performing the work of crowd analysis

import time
from PyQt4 import QtGui, QtCore
from primitives import Vector2
from scbData import FrameSet
from ColorMap import *
import Crowd
import os

class CrowdAnalyzeThread( QtCore.QThread ):
    '''Class to perform the crowd analysis'''
    processMessage = QtCore.pyqtSignal(str)
    
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
        
        tempFile = os.path.join( self.data[ 'tempDir' ], self.data[ 'tempName' ] )
        grids = Crowd.GridFileSequence( tempFile )
        colorMap = COLOR_MAPS[ self.data[ 'colorMap' ] ]()

        R = self.data[ 'kernelSize' ]

        def distFunc( dist, radiusSqd ):
            """Constant distance function"""
            # This is the local density function provided by Helbing
            return 1.0 / ( pi * radiusSqd ) * exp( - (dist * dist / radiusSqd ) )        

        dfunc = lambda x: distFunc( x, R * R )

        densityAction = self.data[ 'DENSE_ACTION' ]
        if ( densityAction == 1 or densityAction == 3 ):
            self.processMessage.emit( 'Computing densities...' )
            s = time.clock()
            grids.computeDensity( domainMin, domainSize, res, dfunc, 3 * R, frameSet )
            self.processMessage.emit( 'done in %.2f seconds' % ( time.clock() - s ) )
        if ( densityAction >= 2 ):
            imageName = os.path.join( self.data[ 'outDir' ], 'density_' )
            self.processMessage.emit( 'Creating density images...' )
            s = time.clock()
            grids.makeImages( colorMap, imageName, 'density' )
            pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
            self.processMessage.emit( 'done in %.2f seconds' % ( time.clock() - s ) )

        speedAction = self.data[ 'SPEED_ACTION' ]
        if ( speedAction == 1 or speedAction == 3 ):
            self.processMessage.emit( 'Computing speeds...' )
            s = time.clock()
            grids.computeSpeeds( domainMin, domainSize, res, 3 * R, frameSet, float( self.data[ 'timeStep' ] ), Crowd.GridFileSequence.BLIT_SPEED, int( self.data[ 'speedWindow' ] ) )
            self.processMessage.emit( 'done in %.2f seconds' % ( time.clock() - s ) )
        if ( speedAction >= 2 ):
            imageName = os.path.join( self.data[ 'outDir' ], 'speed_' )
            self.processMessage.emit( 'Creating speed images...' )
            s = time.clock()
            grids.makeImages( colorMap, imageName, 'speed' )
            pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
            self.processMessage.emit( 'done in %.2f seconds' % ( time.clock() - s ) )            

        advecAction = self.data[ 'ADVEC_ACTION' ]
        if ( advecAction == 1 or advecAction == 3 ):
            self.processMessage.emit( 'Computing advection...' )
            s = time.clock()
            grids.computeAdvecFlow( domainMin, domainSize, res, dfunc, 3.0, 3 * R, frameSet, self.data[ 'ADVEC_LINES' ] )
            self.processMessage.emit( 'done in %.2f seconds' % ( time.clock() - s ) )
        if ( advecAction >= 2 ):
            imageName = os.path.join( self.data[ 'outDir' ], 'advec_' )
            self.processMessage.emit( 'Creating flow advection images...' )
            s = time.clock()
            grids.makeImages( colorMap, imageName, 'advec' )
            pygame.image.save( colorMap.lastMapBar(7), '%sbar.png' % ( imageName ) )
            self.processMessage.emit( 'done in %.2f seconds' % ( time.clock() - s ) )        
        
        self.processMessage.emit( 'FINISHED' )