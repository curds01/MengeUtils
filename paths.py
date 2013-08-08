import os
import re

IN_DIR = '.'
OUT_DIR = '.'

def setInDir( inPath ):
    '''Sets the input path to the given path.  If it does not exist, raises an OSError'''
    global IN_DIR
    if ( not os.path.exists( inPath ) ):
        print "Input path does not exist!"
        raise OSError
    if ( not os.path.isdir( inPath ) ):
        print "Input path does not specify a folder!"
        raise OSError
    IN_DIR = inPath

def setOutDir( outPath ):
    '''Sets the output directory.  If it doesn't already exist, it creates it.'''
    global OUT_DIR
    if ( not os.path.exists( outPath ) ):
        print "Path does not exist!  Creating:", outPath
        os.makedirs( outPath )
    OUT_DIR = outPath

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
