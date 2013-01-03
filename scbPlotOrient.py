# This creates plots of agent orientation
from trajectory import NPFrameSet
import numpy as np
import pylab as plt
import sys

class PlotException( Exception ):
    pass

def plotOrientation( fileName, agtID, useDegrees ):
    '''Creates a plot of the orientation of the specified agent(s).

    @param  fileName:   A string.  The path to the scb file to open.
    @param  agtID:      An index.  The index of the target agent.  If
                        negative plot all agents.
    @param  useDegrees: A boolean.  If true, convert the data from radians to
                        degrees.
    '''
    data = NPFrameSet( fileName )
    fullData = data.fullData()
    
    if ( agtID > -1 ):
        # single agent
        if ( agtID >= fullData.shape[0] ):
            print '\n*** Target agent id (%d) not valid.  Should be in the range [0, %d]\n' % ( agtID, fullData.shape[0] - 1 )
            raise PlotException
        orientation = fullData[ agtID, 2, : ]
        ylabel = "Orientation (radians)"
        ylim = ( (0, 2 * np.pi ) )
        if ( useDegrees ):
            orientation *= (180.0 / np.pi )
            ylabel = "Orientation (degrees)"
            ylim = ( (0, 360.0 ) )
        plt.plot( orientation )
        plt.title( "Orientation of agent %d" % ( agtID ) )
        plt.ylabel( ylabel  )
        plt.xlabel( "Time (frame)" )
        plt.ylim( ylim )
    else:
        # all agents
        orientation = fullData[ :, 2, : ]
        ylabel = "Orientation (radians)"
        ylim = ( (0, 2 * np.pi ) )
        if ( useDegrees ):
            orientation *= (180.0 / np.pi )
            ylabel = "Orientation (degrees)"
            ylim = ( (0, 360.0 ) )
        plt.plot( orientation.T )
        plt.title( "Orientation of all agents" )
        plt.ylabel( ylabel  )
        plt.xlabel( "Time (frame)" )
        plt.ylim( ylim )
        
    plt.show()

def main():
    '''Create the orientation plot for scb data'''
    parser = optparse.OptionParser()
    parser.set_description( 'Create a plot of the orientation of an agent with respect to time.')
    parser.add_option( '-i', '--input', help='The scb data containing the data to plot.',
                       action='store', dest='inFileName', default=None )
    parser.add_option( '-a', '--agent', help='The agent index to plot.  If negative, will plot all agents.  Default is -1.',
                       action='store', dest='agtID', type='int', default=-1 )
    parser.add_option( '-d', '--degrees', help='Plot in degrees.  Default is to plot with radians',
                       action='store_true', default=False, dest='degrees' )

    options, args = parser.parse_args()

    if ( options.inFileName == None ):
        parser.print_help()
        print '\n*** You must specify an scb file. ***'
        sys.exit(1)
        
    print "Plotting orientation"
    print "\tFile:", options.inFileName
    print "\tAgent:", options.agtID

    try:
        plotOrientation( options.inFileName, options.agtID, options.degrees )
    except PlotException as e:
        parser.print_help()
        sys.exit(1)
    
if __name__ == '__main__':
    import optparse
    main()
    
