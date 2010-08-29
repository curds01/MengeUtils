# this takes an scb file and creates another scb file, truncated
#   it outputs a subsequence of frames

import struct
import sys

DEFAULT_OUTPUT = 'output.scb'

def copyNFrames( inFile, outFile, count, step ):
    """Copies at most count frames from the scb inFile to
    the outFile.  It copies every step-th frame.
    Reports number of frames copied.  Copying
    includes header"""
    # assume both inFile and outFile are at position 0
    # copy header - 4 bytes for version, 4 bytes for agent count
    header = inFile.read( 8 )
    outFile.write( header )
    agtCount = struct.unpack( 'i', header[4:] )[0]
    frameSize = agtCount * 4 * 3  # three, four-byte floats per agent
    actual = 0
    readFrame = 0
    while ( actual < count ):
        data = inFile.read( frameSize )
        if ( data ):
            if ( readFrame % step == 0 ):
                outFile.write( data )
                actual += 1
            readFrame += 1
        else:
            break
    return actual
    

def usage():
    print "Truncate an scb file"
    print
    print "scbTruncate -in filename <-out filename.scb> -n # -step #"
    print
    print "  -in filename     - the name of the file to truncate"
    print "                     must be valid scb file"
    print "  -n #             - an integer, at most n frames will be"
    print "                     included in the truncated file"
    print "  -out filename    - the name of the output file."
    print "                     if not provided, output file defaults to %s" % ( DEFAULT_OUTPUT )
    print "  -step #          - the number of frames between the sampled frames"
    print "                      defaults to 1 (i.e. EVERY frame"
    sys.exit(1)
    
def main():
    """Determine the input file, output file and number of frames"""
    from commandline import SimpleParamManager
    
    # parse command-line arguments
    try:
        pMan = SimpleParamManager( sys.argv[1:], {'in':'', 'out':DEFAULT_OUTPUT, 'n':0, 'step':1 } )
    except IOError:
        usage()

    inName = pMan[ 'in' ]
    outName = pMan[ 'out' ]
    count = int( pMan[ 'n' ] )
    step = int( pMan['step'] )
    
    if ( not count ):
        print "ERROR! Invalid number of frames: ", count
        usage()
    try:
        inFile = open( inName, 'rb' )
    except IOError:
        print "ERROR! Couldn't open input file %s" % ( inName )
        usage()
    try:
        outFile = open( outName, 'wb' )
    except IOError:
        print "ERROR! Couldn't open output file:", outFile
        usage()

    nCopied = copyNFrames( inFile, outFile, count, step )
    print "Copied %d frames into %s" % ( nCopied, outName )

if __name__ == '__main__':
    main()