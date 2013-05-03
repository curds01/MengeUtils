# Common data for trajectory data

# enumeration of the trajectory data types
UNKNOWN_DATA = 0
SCB_DATA = 1
JULICH_DATA = 2

# mapping from enumeration to printable string and vice versa
DATA_STR = { SCB_DATA:'scb', JULICH_DATA:'julich',
             'scb':SCB_DATA, 'julich':JULICH_DATA }

def trajectoryTypes():
    '''Returns a list of strings representing the recognized trajectory types.

    @returns:   A list of strings.  The string representation of each trajectory type.
                The string is suitable for use with the DATA_STR mapping.
    '''
    names = [ DATA_STR[ SCB_DATA ], DATA_STR[ JULICH_DATA ] ]
    names.sort()
    return names

