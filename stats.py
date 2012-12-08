# A simple class for recording per-frame stats during rasterization
import numpy as np

class StatRecord:
    '''A simple, callable object for accumulating statistical information about the
    quanity being computed and rasterized'''
    def __init__( self, agentCount ):
        # frame data is an N x 2 array.  N = number of times it is called.
        # It contains the following data:
        #   mean, std deviation, min, max
        self.frameData = []
        # agent data is the data for all of the agents in a single frame
        self.agentData = np.zeros( agentCount, dtype=np.float32 )
        self.currAgent = 0

    def __call__( self, value ):
        '''Assign the current value to the current agent'''
        self.agentData[ self.currAgent ] = value
        self.currAgent += 1

    def nextFrame( self ):
        '''Prepares the data for the next frame'''
        if ( self.currAgent ):
            self.frameData.append( ( self.agentData[:self.currAgent].mean(), self.agentData[:self.currAgent].std(), self.agentData[:self.currAgent].min(), self.agentData[:self.currAgent].max(), self.currAgent ) )
        else:
            self.frameData.append( ( 0.0, 0.0, 0.0, 0.0, 0 ) )
        self.currAgent = 0

    def write( self, fileName ):
        '''Outputs the data into a text file'''
        f = open( fileName, 'w' )
        for m, s, minVal, maxVal, agtCount in self.frameData:
            f.write( '{0:>15}{1:>15}{2:>15}{3:>15}{4:>15}\n'.format( m, s, minVal, maxVal, agtCount ) )
        f.close()

    def savePlot( self, fileName, title ):
        '''Saves a plot of the data to the specified filename'''
        plt.figure()
        data = np.array( self.frameData )
        x = np.arange( data.shape[0] ) + 1
        plt.errorbar( x, data[:,0], data[:,1] )
        plt.ylim( ( data[:,2].min(), data[:,3].max() ) )
        plt.title( title )
        plt.savefig( fileName )