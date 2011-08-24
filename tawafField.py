# A throw away script designed to instantiate a vector field for the tawaf

from obstacles import readObstacles
from vField import VectorField
import numpy as np

def spiralField( field, radWeight, flip=False ):
    '''The tawaf spiral field -- velocities have a tangential component and some
    component inwards'''
    # this is quick and dirty - it relies on knowing the implementation of
    # VectorField
    print "spiralField"
    centers = field.centers
    print "\tcenters.shape:", centers.shape
    mag = np.sqrt( np.sum( centers * centers, axis=2 ) )
    mag.shape = (mag.shape[0], mag.shape[1], 1)
    print "\tmag.shape:", mag.shape
    unitDir = centers / mag
    tanDir = np.zeros_like( centers )
    tanDir[ :, :, 0 ] = -unitDir[ :, :, 1 ]
    tanDir[ :, :, 1 ] = unitDir[ :, :, 0 ]
    radDir = -unitDir
    dir = radWeight * radDir + (1 - radWeight ) * tanDir
    # renormalize
    mag = np.sqrt( np.sum( dir * dir , axis=2 ) )
    mag.shape = (mag.shape[0], mag.shape[1], 1)
    dir *= 1.0 / mag
    if ( flip ):
        field.data = -dir
    else:
        field.data = dir
    

def main():
    import optparse
    import sys

    parser = optparse.OptionParser()
    parser.add_option( "-o", "--obstacle", help="Obstacle file to load.",
                       action="store", dest='obstName', default='' )
    parser.add_option( "-f", "--field", help="The name of the output file.  Default value is tawafField_##.txt, where ** is the radial weight.",
                       action="store", dest='fieldName', default='' )
    parser.add_option( "-r", "--radiusWeight", help="The component of the velocity in each cell that is towards the center.  Default is 0.2.)",
                       action="store", dest='radWeight', default=0.23, type='float' )
    parser.add_option( "-c", "--cellSize", help="The size of a grid cell (in meters). Defaults to 2.0",
                       action="store", dest="cellSize", default=2.0, type='float' )
    parser.add_option( "-q", "--square", help="Forces the grid to be square",
                       action="store_true", dest="square", default=False )
    parser.add_option( "-l", "--flip", help="Reverses the direction of the field",
                       action="store_true", dest="flip", default=False )
    options, args = parser.parse_args()
    
    if ( options.obstName == '' ):
        parser.print_help()
        sys.exit(1)

    if ( options.fieldName == '' ):
        # construct a default name
        fieldName = 'tawafField_{0:.2f}'.format( options.radWeight )
        fieldName = fieldName.replace( '.', '_' ) + ".txt"
    makeSquare = options.square

    print "Creating vector field based on:", options.obstName
    obstacles, bb = readObstacles( options.obstName )

    print "\tObstacle bounding box:", bb
    print "\tVector field cell size:", options.cellSize
    bbSize = bb.max - bb.min
    if ( makeSquare ):
        maxSize = max( bbSize.x, bbSize.y )
        bbSize.x = maxSize
        bbSize.y = maxSize
    field = VectorField( ( bb.min.x, bb.min.y ), ( bbSize.x, bbSize.y ), options.cellSize )
    # do work
    spiralField( field, options.radWeight, options.flip )
    print "\tVector field saving to:", options.fieldName,
    field.write( options.fieldName )
    print "SAVED!"
    

if __name__ == '__main__':
    main()