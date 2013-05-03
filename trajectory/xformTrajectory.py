# This applies a constant transformation to all agent positions
#   across all frames - initial version only supports translation

import commonData
from dataLoader import loadTrajectory
from xform import TrajXform
import os

def xformTrajectory( data, xform ):
    '''Transforms the given trajectory file with the given trajectory.

    @param:     data            An instance of trajectory data.
    @param      xform           An instance of TrajXform.  The transform to
                                apply to the file's trajectories.
    @returns:       A new trajectory data set (of the same type) with the
                    trajectories transformed.
    '''
    # create new, empty trajectory set
    #   Set the path of each agent with the transformed point
    #
    newData = xform.apply( data )
    return newData

def xformTrajectoryFile( inFileName, xform ):
    '''Transforms the given trajectory file with the given trajectory.

    @param:     inFileName      A string.  The path to the trajectory file
                                to transform.
    @param      xform           An instance of TrajXform.  The transform to
                                apply to the file's trajectories.
    @returns:       A new trajectory data set (of the same type) with the
                    trajectories transformed.
    @raises:        ValueError if the data file can't be recognized.
    '''
    # load trajectory
    data = loadTrajectory( inFileName )
    # transform
    return xformTrajectory( data, xform )

def main():
    parser = optparse.OptionParser()
    parser.set_description( 'Translate all trajectories in a file' )
    parser.add_option( '-i', '--input', help='The name of the trajectory file to translate',
                       action='store', dest='inFileName', default=None )
    parser.add_option( '-o', '--output', help='The name of the output trajectory file to write.  If no name is give, output.ext is used (with the same extension and type as the input',
                       action='store', dest='outFileName', default=None )
    parser.add_option( '-x', '--xTranslate', help='The amount to move the trajectories along the x-axis',
                       action='store', dest='x', default=0.0, type='float' )
    parser.add_option( '-y', '--yTranslate', help='The amount to move the trajectories along the y-axis',
                       action='store', dest='y', default=0.0, type='float' )
    # TODO: eventually support z-translation
##    parser.add_option( '-z', '--zTranslate', help='The amount to move the trajectories along the x-axis',
##                       action='store', dest='z', default=0.0, type='float' )

    options, args = parser.parse_args()
    
    # validate
    if ( options.inFileName is None ):
        parser.print_help()
        print '\n!!! You must specify an input file'
        sys.exit(1)
        
    # transform the data
    xform = TrajXform()
    xform.setTranslate( options.x, options.y, 0.0 )
    newData = xformTrajectoryFile( options.inFileName, xform )

    # export the data
    outName = None
    if ( options.outFileName is None ):
        path, fileName = os.path.split( options.inFileName )
        name, ext = os.path.splitext( fileName )
        outName = 'output' + ext
    else:
        outName = options.outFileName

    newData.write( outName )    

if __name__ == '__main__':
    import sys
    import optparse
    main()
