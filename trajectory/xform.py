# Class for transforming trajectory sets
import commonData
from scbData import SCBDataMemory
from copy import deepcopy
import numpy as np

class TrajXform:
    '''A transformation on trajectories'''
    def __init__( self ):
        # TODO: Add other transformations (scale and rotate)
        self.tx = 0.0
        self.ty = 0.0
        self.tz = 0.0

    def __str__( self ):
        return "Xform: trans( %.3f, %.3f, %.3f )" % ( self.tx, self.ty, self.tz )

    def setTranslate( self, x=0.0, y=0.0, z=0.0 ):
        '''Sets the translation properties of the transformation.

        @param      x:      A float. The x-component.
        @param      y:      A float. The y-component.
        @param      z:      A float. The z-component.
        '''
        self.tx = x
        self.ty = y
        self.tz = z

    def apply( self, data ):
        '''Applies this transformation to the agents in the given data.

        @param:     data    An instance of trajectory data.
        @return     An instance of trajectory data with the transformed trajectories.
        @raises:    ValueError if the data is not of a recognizable format.
        '''
        if ( data.getType() == commonData.SCB_DATA ):
            return self.applySCB( data )
        elif ( data.getType() == commonData.JULICH_DATA ):
            return self.applyJulich( data )
        else:
            raise ValueError, "Unrecognized trajectory data"

    def applySCB( self, data ):
        '''Applies this transformation to the agents in the given SCB data.

        @param:     data    An instance of SCBData.
        '''
        agtData = data.fullData()
        agtData[ :, 0, : ] += self.tx
        agtData[ :, 1, : ] += self.ty
        # does this have z-info?
        if ( self.tz != 0.0 ):
            raise AttributeError, "Z-translation not supported in trajectory transform"
        newData = SCBDataMemory()
        newData.setData( agtData, data.version, data.simStepSize )
        return newData

    def applyJulich( self, data ):
        '''Applies this transformation to the agents in the given SCB data.

        @param:     data    An instance of JulichData.
        '''
        newData = deepcopy( data )
        offset = np.array( ( self.tx, self.ty ), dtype=np.float32 )
        offset.shape = (1, -2 )
        for ped in newData.pedestrians:
            ped.traj[ :, :2 ] += offset
            
        return newData
    