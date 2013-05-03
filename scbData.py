## Reads SCB data

## This file is a hack.  I have lots of files that directly reference this, although I've moved the functionality
##  This hack gives them access to the functionality still, but warns them that things need to move.

from trajectory.scbData import *
import warnings

warnings.warn( 'The scbData functionality exists in the "trajetory" submodule - please change your reference', DeprecationWarning, stacklevel=2 )

if __name__ == '__main__':
    main()
    
