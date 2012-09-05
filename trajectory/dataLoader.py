# handles loading trajectory functions automatically

import scbData
import julichData
import os

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
        data.setNext(0)
    except scbData.SCBError:
        try:
            data = julichData.JulichData( 1/ 16.0 )
            data.readFile( fileName )
            data.setNext(0)
        except:
            raise ValueError, "Unrecognized trajectory data"
    return data

def isTrajectory( fileName ):
    '''Determines if the given file is a trajectory file.

    @param      fileName        A string.  The path to a file to test.
    @returns    A boolean.  True if the file is a valid trajectory,
                False otherwise.
    '''
    if ( not os.path.isfile( fileName ) ):
        return False
    valid = scbData.NPFrameSet.isValid( fileName )
    if ( not valid ):
        return julichData.JulichData.isValid( fileName )
    return valid