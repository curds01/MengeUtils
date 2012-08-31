# This file contains standard including file for the objreader
import os
import sys
import getpass

if ( getpass.getuser() == 'ksuvee' or getpass.getuser() == 'TofuYui' ):

    TOP_DIR = os.path.dirname( os.path.dirname(__file__) )

    sys.path.insert( 2, TOP_DIR + r'\density' )

elif ( getpass.getuser() == 'seanc' or getpass.getuser() == 'Sean'):
    PATHS = (
            )
    for path in PATHS:
        if ( not path in sys.path ):
            sys.path.insert( 0, path )

