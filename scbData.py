## Reads SCB data

## This file is a hack.  I have lots of files that directly reference this, although I've moved the functionality
##  This hack gives them access to the functionality still, but warns them that things need to move.

from trajectory.scbData import *
import warnings

warnings.warn( 'The scbData functionality exists in the "trajetory" submodule - please change your reference', DeprecationWarning, stacklevel=2 )

def main():
    '''A simple script for summarizing the script'''
    import sys
    if ( len( sys.argv ) < 1 ):
        print "Provide the name of an scb file to get summary"
        sys.exit(1)

    data = NPFrameSet( sys.argv[ 1 ] )
    print "SCB file loaded"
    print "\tVersion:", data.version
    print "\tAgents: ", data.agentCount()
    print "\tTime step:", data.simStepSize
    print "\tDuration (frames):", data.totalFrames()
    print "\tInitial positions:"
##    data.setNext( 0 )
##    f, i = data.next()
##    for r, row in enumerate( f ):
##        print "\t\tAgent %d:" % r, row[0], row[1]
    
if __name__ == '__main__':
    main()
    
