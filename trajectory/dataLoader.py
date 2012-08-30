# handles loading trajectory functions automatically

import scbData
import julichData

def loadTrajectory( fileName ):
    '''Loads a trajectory file - actual data or simulated data.

    @param      fileName        A string.  The path to the trajectory data
                                to load.
    @returns    An instance of the trajectory data structure appropriate
                to the data type.
    @raises     ValueError if the data in the file can't be recognized.
    '''
    try:
        data = scbData.NPFrameSet( fileName )
    except scbData.SCBError:
        try:
            data = julichData.JulichData( 1/ 16.0 )
            data.readFile( fileName )
        except:
            raise ValueError, "Unrecognized trajectory data"
    return data
