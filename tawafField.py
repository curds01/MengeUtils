# A throw away script designed to instantiate a vector field for the tawaf

from roadmapBuilder import readObstacles
from vField import VectorField
import numpy as np

def spiralField( field, radWeight ):
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
    field.data = dir
    
def usage():
    print "tawafField.py -obst obstFile.xml <-field fieldName> <-cell cellSize> <-radial radWeight> <-square>"
    print "\tCreate a vector field for the tawaf"
    print
    print "Arguments:"
    print "    -obst obstFile.xml    - required.  The obstacle definition for"
    print "                           the tawaf."
    print "    -field fieldName      - optional.  The vector field will be saved as"
    print "                           this name.  If no name is provided, it will be."
    print "                           saved as \"tawafField_##.txt\".  Where ## is the radial"
    print "                           weight (see below.)"
    print "    -cell CellSize        - optional.  A float dictating the size of a grid"
    print "                           in the same space as the obstacles"
    print "    -radial radWeight     - optional.  The component of the velocity in"
    print "                            each cell that is towards the center.  Defaults to 0.2."
    print "    -square               - Determines if the grid is square."

def main():
    from commandline import SimpleParamManager
    import sys

    try:
        pMan = SimpleParamManager( sys.argv[1:], {'obst':'', 'field':'', 'cell':1.0, 'radial':0.2, 'square':False } )
    except IOError:
        usage()

    obstName = pMan[ 'obst' ]
    fieldName = pMan[ 'field' ]
    cellSize = float( pMan[ 'cell' ] )
    radWeight = float( pMan[ 'radial' ] )

    if ( obstName == '' ):
        usage()
        sys.exit(1)

    if ( fieldName == '' ):
        # construct a default name
        fieldName = 'tawafField_{0:.2f}'.format( radWeight )
        fieldName = fieldName.replace( '.', '_' ) + ".txt"
    makeSquare = pMan[ 'square' ]

    print "Creating vector field based on:", obstName
    obstacles, bb = readObstacles( obstName )

    print "\tObstacle bounding box:", bb
    print "\tVector field cell size:", cellSize
    bbSize = bb.max - bb.min
    if ( makeSquare ):
        maxSize = max( bbSize.x, bbSize.y )
        bbSize.x = maxSize
        bbSize.y = maxSize
    field = VectorField( ( bb.min.x, bb.min.y ), ( bbSize.x, bbSize.y ), cellSize )
    # do work
    spiralField( field, radWeight )
    print "\tVector field saving to:", fieldName,
    field.write( fieldName )
    print "SAVED!"
    

if __name__ == '__main__':
    main()