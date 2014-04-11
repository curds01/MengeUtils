# transforms vector fields
#
#   Given a vector field, the following operations can be performed on it
#       Scale: Transform the domain by scaling it around the origin
#               It can only be scaled uniformly to maintain the square cells.
#               It can also be used to flip the vectors.
#       Translate: Move the domain of the vector field.

import vField
import numpy as np

def transformField( field, scale, translate ):
    '''Performs a transformation on the domain of a vector field.

    @param      field       An instance of vField.VectorField.  This will be changed
                            IN PLACE.
    @param      scale       A 2-tuple of floats.  The x- and y-scale values.
    @param      translate   A 2-tuple of floats.  The x- and y-translate values.
    '''
    print "Transforming field:"
    print "\tMin point:", field.minPoint
    print "\tSize:", field.size
    print "\tCell size:", field.cellSize
    if ( scale[0] != 1.0 or scale[1] != 1.0 ):
        print "Scaling", scale
        # cache magnitudes
        field.minPoint[0] *= scale[0]
        field.minPoint[1] *= scale[1]
        field.cellSize *= abs( scale[0] )
        field.size[0] *= abs(scale[0])
        field.size[1] *= abs(scale[1])
        if ( scale[0] < 0 ):
            # reverse all x-directions
            field.data[ :, :, 0 ] = -field.data[ :, :, 0 ]
            field.data[ :, :, : ] = field.data[ :, ::-1, : ]
            field.minPoint[0] -= field.size[1]
        if ( scale[1] < 0 ):
            # reverse all y-directions
            field.data[ :, :, 1 ] = -field.data[ :, :, 1 ]
            field.data[ :, :, : ] = field.data[ ::-1, :, : ]
            field.minPoint[1] -= field.size[0]
    if ( translate[0] != 0.0 or translate[1] != 0.0 ):
        field.minPoint[0] += translate[0]
        field.minPoint[1] += translate[1]
    print "Transformed field:"
    print "\tMin point:", field.minPoint
    print "\tSize:", field.size
    print "\tCell size:", field.cellSize
    
    
def main():
    parser = optparse.OptionParser()
    parser.set_description( 'Transform the DOMAIN of a vector field.  Although negatively scaling a vector field WILL reverse the vector directions.  Finally, scale is applied before transformation' )
    parser.add_option( '-i', '--input', help='The name of the vector field file to transform',
                       action='store', dest='inFileName', default=None )
    parser.add_option( '-o', '--output', help='The name of the output vectof field file to write.',
                       action='store', dest='outFileName', default=None )
    parser.add_option( '-s', '--scale', help='A pair of values indicating the x and y scale values.  NOTE: this merely transforms the domain; vector values will maintain previous magnitude.  The field only supports SQUARE cells so |scale x| == |scale y| must be true.',
                       nargs=2, action='store', dest='scale', type='float', default=(1.0,1.0) )
    parser.add_option( '-t', '--transoate', help='A pair of values indicating the x and y translate values.',
                       nargs=2, action='store', dest='translate', type='float', default=(0.0,0.0) )

    options, args = parser.parse_args()
    
    # validate
    if ( options.inFileName is None ):
        parser.print_help()
        print '\n!!! You must specify an input file'
        sys.exit(1)

    if ( options.inFileName is None ):
        parser.print_help()
        print '\n!!! You must specify an output file'
        sys.exit(1)

    if ( abs( options.scale[0] ) != abs( options.scale[1] ) ):
        parser.print_help()
        print '\n!!! The scale values must have the same magnitude to maintain square grid cells!'
        sys.exit(1)

    field = vField.VectorField( (0,0), (1, 1), 1 )
    field.read( options.inFileName )
        
    # transform the data
    transformField( field, options.scale, options.translate )

    # export the data
    field.writeAscii( options.outFileName )

if __name__ == '__main__':
    import sys
    import optparse
    main()
