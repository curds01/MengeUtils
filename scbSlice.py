# this takes an scb file and mutliple scb files by chopping it up into
# smaller files

import struct
import sys
import os

DEFAULT_OUTPUT = 'output.scb'
import numpy as np

def readHeader( inFile ):
    '''Reads the header of the scb file and returns the following data:
        version # (as a number)
        '''
    version = float( inFile.read( 4 )[:-1] )
    print "Version", version
    agtCount = struct.unpack( 'i', inFile.read( 4 ) )[0]
    stepSize = 0.0
    ids = None
    
    if ( version == 2.0 ):
        stepSize = struct.unpack( 'f', inFile.read( 4 ) )[0]
        idReadSize = agtCount * 4
        ids = inFile.read( idReadSize )
    print agtCount
    print stepSize

    return version, agtCount, stepSize, ids

def writeHeader( file, version, agentCount, timeStep=0.0, ids=None ):
    '''Writes the scb header to the file'''
    if ( version == 1 ):
        file.write( '1.0\x00' )
        file.write( struct.pack( 'i', agentCount ) )
    if ( version == 2 ):
        file.write( '2.0\x00' )
        file.write( struct.pack( 'i', agentCount ) )
        file.write( struct.pack( 'f', timeStep ) )
        file.write( ids )
        
def sliceSCB( inFile, outBase, count ):
    '''Reads the input scb file, inFile, and separates it into count,
    roughly equally sized, files.  All files have a name in the format:
    outBase##.scb'''
    FLOAT_SIZE = 4      # bytes per float
    AGENT_SIZE = 3      # floats per agent
    version, agtCount, stepSize, ids = readHeader( inFile )
    dataPos = inFile.tell()
    framesize = agtCount * FLOAT_SIZE * AGENT_SIZE

    # pass 1, count the number of frames
    frameCount = 0
    data = inFile.read( framesize )
    while ( data != '' ):
        frameCount += 1
        data = inFile.read( framesize )

    counts = np.zeros( count, dtype=np.int ) + frameCount
    counts /= count
    counts[0] += frameCount - np.sum( counts )
    padding = int( np.ceil( np.log10( count ) ) )
    print "Total frames:", frameCount
    print "Frame counts:", counts

    # pass 2, write out the files
    inFile.seek( dataPos )
    for i in range( count ):
        fName = '{0:s}{1:0{2}d}.scb'.format( outBase, i, padding )
        f = open( fName, 'wb' )
        writeHeader( f, version, agtCount, stepSize, ids )
        f.write( inFile.read( framesize * counts[i] ) )
        f.close()

def usage():
    print "Divide an scb file -- slice it into multiple scb files"
    print
    print "scbSlice -in filename <-out filename> -n # "
    print
    print "  -in filename     - the name of the file to truncate"
    print "                     must be valid scb file"
    print "  -n #             - an integer, the number of pieces"
    print "                     to chop the scb file into"
    print "  -out filename    - the name of the output file."
    print "                     if not provided, output file defaults to %s" % ( DEFAULT_OUTPUT )
    sys.exit(1)

def outBaseName( fileName ):
    '''Given the filename indicated, produces a basename for the output.scb
    the base name is unadorned by extensions.'''
    base, ext = os.path.splitext( fileName )
    if ( ext == '.scb' ):
        return base
    else:
        return fileName
    
def main():
    """Determine the input file, output file and number of frames"""
    from commandline import SimpleParamManager
    
    # parse command-line arguments
    try:
        pMan = SimpleParamManager( sys.argv[1:], {'in':'', 'out':DEFAULT_OUTPUT, 'n':0 } )
    except IOError:
        usage()

    inName = pMan[ 'in' ]
    outName = pMan[ 'out' ]
    count = int( pMan[ 'n' ] )
    
    if ( count < 2 ):
        print "ERROR! Can't chop the file into %d pieces" % ( count )
        usage()
    try:
        inFile = open( inName, 'rb' )
    except IOError:
        print "ERROR! Couldn't open input file %s" % ( inName )
        usage()

    outName = outBaseName( outName )        

    sliceSCB( inFile, outName, count )

if __name__ == '__main__':
    main()