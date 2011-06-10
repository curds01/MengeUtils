# this creates a dummy scb file to test the density analysis
# it creates a large, regular grid of agents per a desired density

import numpy as np
import struct
import os

def writeSCB( fileName, agentData, frameCount ):
    '''Given the constant agent data, writes it out to an scb file'''
    f = open( fileName, 'wb' )
    f.write( '1.0\x00' )
    f.write( struct.pack('i', agentData.shape[0] ) )
##    for row in agentData:
##        print row[0], row[1], row[2]
##        f.write( struct.pack('fff', row[0], row[1], row[2] ) )
    for i in xrange( frameCount ):
        f.write( agentData.tostring() )
    f.close()

def makeAgentData( agtX, agtY, density ):
    '''Computes an NX3 array of data such that N = agtX * agtY and
    the positions of the agents are uniformly distributed to achieve
    the indicated density.
    '''
    # the density of the mob is the distance between the agents squared
    #   divided by 4 (i.e. that's the smallest regular grid)
    #   solve for distance
    agtDistance = np.sqrt( 1.0 / density )
    print "Density {0} people/m^2 implies distance of {1}".format( density, agtDistance )
    xPos = np.arange( agtX, dtype=np.float32 ) * agtDistance
    yPos = np.arange( agtY, dtype=np.float32 ) * agtDistance
    xPos -= xPos.mean()
    yPos -= yPos.mean()
    X, Y = np.meshgrid( xPos, yPos )
    data = np.zeros( ( agtX * agtY, 3 ), dtype=np.float32 )
    data[ :, 0 ] = X.flatten()
    data[ :, 1 ] = Y.flatten()
    return data

def main():
    DENSITY = 4.0   # people / m^2
    path = '/projects/tawaf/sim/jun2011'
##    FILENAME = ('dense_%.1f' % DENSITY).replace( '.', '_' ) + ".scb"
    FILENAME = 'denseTest.scb'
    FILENAME = os.path.join( path, FILENAME )
    AGT_COUNT = 20  # number of agents on side of grid

    data = makeAgentData( AGT_COUNT, AGT_COUNT, DENSITY )

    writeSCB( FILENAME, data, 30 )

    print "Wrote to:", FILENAME    

if __name__ == '__main__':
    main()
    