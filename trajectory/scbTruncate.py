# this takes an scb file and creates another scb file, truncated
#   it outputs a subsequence of frames

import struct
import sys
import scbData

DEFAULT_OUTPUT = 'output.scb'

def copyNFrames( inName, outName, start, count, step, tgtAgtCount, agtStride ):
    """Copies at most count frames from the scb inName to
    the outName.  It copies every step-th frame.
    Similarly it copies up to tgtAgtCount agents and selects them by sampling
    every agtStride-th agent.
    Reports number of frames copied.  Copying
    includes header.
    If count == -1, all frames are copied."""
    data = scbData.NPFrameSet( inName, startFrame=start, maxFrames=count, maxAgents=tgtAgtCount, frameStep=step, agtStep=agtStride )
    data.write( outName )
    return data.totalFrames()

def copyAgent( inName, outName, start, count, step, agtID ):
    """Copies at most count frames from the scb inName to
    the outName for one specific agent: agtID.  It copies every step-th frame.
    Reports number of frames copied.  Copying includes header.
    If count == -1, all frames are copied."""
    data = scbData.NPFrameSet( inName, startFrame=start, maxFrames=count, frameStep=step )
    data.writeAgent( outName, agtID )
    return data.totalFrames()

def main():
    """Determine the input file, output file and number of frames"""
    import optparse
    parser = optparse.OptionParser()
    parser.set_description( 'Allows extraction of a subset of data from an scb file into a new scb file.  The subset can include: truncation of the first N frames, a uniform sampling of every Kth frame up to N frames, the first M agents, or a particular agent, with combinations of the previous.' )
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
    parser.add_option( '', '--agentSample', help='The sample rate at selecting agents.  I.e. select every Nth agent.  Default is 1.',
                       action='store', dest='agtStride', type='int', default=1 )
    parser.add_option( '-e', '--extractAgent', help='Extract a single agent from the set by ID',
                       action='store', dest='extract', default=-1, type='int' )
    parser.add_option( '-b', '--beginFrame', help='The frame at which to start the extraction',
                       action='store', dest='begin', type='int', default=0 )

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
    if ( options.extract != -1 ):
        print "1 (targeted: %d)" % ( options.extract )
    elif ( agentCount == -1 ):
        print "All agents"
    else:
        print agentCount
    print "\tAgent stride:", options.agtStride

    if ( options.extract != -1 ):
        nCopied = copyAgent( inName, outName, options.begin, count, step, options.extract )
    else:
        nCopied = copyNFrames( inName, outName, options.begin, count, step, agentCount, options.agtStride )
    print "Copied %d frames into %s" % ( nCopied, outName )

if __name__ == '__main__':
    main()