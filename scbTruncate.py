# this takes an scb file and creates another scb file, truncated
#   it outputs a subsequence of frames

import struct
import sys
import scbData

DEFAULT_OUTPUT = 'output.scb'

def copyNFrames( inName, outName, count, step, tgtAgtCount ):
    """Copies at most count frames from the scb inName to
    the outName.  It copies every step-th frame.
    Reports number of frames copied.  Copying
    includes header.
    If count == -1, all frames are copied."""
    # assume both inFile and outFile are at position 0
    # copy header - 4 bytes for version, 4 bytes for agent count
    data = scbData.NPFrameSet( inName, maxFrames=count, maxAgents=tgtAgtCount, frameStep=step )
    data.write( outName )
    return data.totalFrames()

def usage():
    print "Truncate an scb file"
    print
    print "scbTruncate -in filename <-out filename.scb> -n # -step # <-agt *>"
    print
    print "  -in filename     - the name of the file to truncate"
    print "                     must be valid scb file"
    print "  -n #             - an integer, at most n frames will be"
    print "                     included in the truncated file"
    print "  -out filename    - the name of the output file."
    print "                     if not provided, output file defaults to %s" % ( DEFAULT_OUTPUT )
    print "  -step #          - the number of frames between the sampled frames"
    print "                      defaults to 1 (i.e. EVERY frame"
    print "  -agt #           - up to the first # agents will be exported"
    print "                     by default, all are exported"
    sys.exit(1)
    
def main():
    """Determine the input file, output file and number of frames"""
    import optparse
    parser = optparse.OptionParser()
    parser.add_option( '-i', '--in', help='The name of the file to truncate (must be valid scb file)',
                       action='store', dest='inFileName', default='' )
    parser.add_option( '-n', '--numFrames', help='The number of frames to include in the truncated file (default is all frames, -1)',
                       action='store', dest='n', type='int', default=-1 )
    parser.add_option( '-o', '--out', help='The name of the output truncated scb file',
                       action='store', dest='outFileName', default=DEFAULT_OUTPUT )
    parser.add_option( '-s', '--stride', help='The stride value of the sampled frames.  The default value is 1 (i.e. every frame)',
                       action='store', dest='stride', type='int', default='1' )
    parser.add_option( '-a', '--agentCount', help='The maximum number of agents to include (-1 is all agents)',
                       action='store', dest='agtCount', type='int', default=-1 )

    options, args = parser.parse_args()    

    inName = options.inFileName
    outName = options.outFileName
    count = options.n
    step = options.stride
    agentCount = options.agtCount
    
    if ( not count ):
        print "ERROR! Invalid number of frames: ", count
        usage()

    print "Truncating scb file: ", inName
    print "\tOutput file:", outName
    print "\tMaximum number of frames:",
    if ( count == -1 ):
        print "ALL FRAMES"
    else:
        print count
    print "\tFrame sample stride:", step
    print "\tMaximum number of agents",
    if ( agentCount == -1 ):
        print "All agents"
    else:
        print agentCount
            
    nCopied = copyNFrames( inName, outName, count, step, agentCount )
    print "Copied %d frames into %s" % ( nCopied, outName )

if __name__ == '__main__':
    main()