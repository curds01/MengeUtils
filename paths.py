import os
import re

IN_DIR = '.'
OUT_DIR = '.'

def getPath( path, asInput=True ):
    '''Given the input path, computes the global path to it.

    It only applies the global in dir if path is a relative address'''
    if ( path == ''  ):
        # empty paths just get returned
        return path
    if ( os.path.isabs( path ) ):
        # paths beginning with a slash are already absolute
        return path

    root = OUT_DIR
    if ( asInput ):
        root = IN_DIR
        
    return os.path.normpath( os.path.join( root, path ) )
