# reads in a navigation mesh definition and outputs an obstacle definition.

from navMesh import Obstacle

def buildObstacles( nmObstacles ):
    '''Given a list of nav mesh obstacles, constructs lists of vertex references forming obstacles.

    @param      nmObstacles     A list of [navMesh.Obstacle].  The nav mesh obstacles to process.
    @returns    A list of lists of integers.  Each interior list is a sequence of vertex indices whic
                form an individual, closed obstacle.
    '''
    print "building obstacles"
    used = set()
    obstacles = []
    temp = [ x for x in nmObstacles ]
    for o in nmObstacles:
##        print "Testing obstacle: ", o
        if ( o not in used ):
            # this is the start of an obstacle
            used.add( o )
            obst = [ o.v0, o.v1 ]
            obstacles.append( obst )
            next = nmObstacles[ o.next ]
            while ( next != o ):
                used.add( next )
                obst.append( next.v1 )
                next = nmObstacles[ next.next ]
            obst.pop( -1 )      # this is because this loop will always close the loop with identical first and last vertices
    print "Constructed %d obstacles" % len( obstacles )
    return obstacles
                
def navMeshToObstacle( nmFileName, obstName ):
    '''Extracts the obstacles inherent in a given nav mesh file and writes
    to an obstacle file.

    @param      nmFileName      A string.  A path to a nav mesh file specification.
    @param      obstName        A string.  A path to the file to write the obstacle
                                specification.  If missing the .xml extension, it
                                will be added.
    '''
    if ( not obstName.lower().endswith( '.xml' ) ):
        obstName += '.xml'

    print "Reading navmesh file: %s" % nmFileName
    vertices = []   # simple list of vertex values
    obstacles = []  # list of obstacles
    try:
        with open( nmFileName, 'r' ) as f:
            # read vertices
            vertCount = int( f.readline() )
            vertices = [None for i in xrange(vertCount ) ]
            print "\t%d vertices" % (vertCount)
            for i in xrange( 0, vertCount ):
                line = f.readline()
                tokens = line.split()
                point = map( lambda x: float(x), tokens )
                vertices[ i ] = point

            line = f.readline().strip()
            while ( line == '' ):
                line = f.readline().strip()

            # read nodes
            nodeCount = int( line )
            print "\tSkipping %d nodes" % nodeCount
            for i in xrange( nodeCount ):
                f.readline()

            line = f.readline().strip()
            while ( line == '' ):
                line = f.readline().strip()

            # read obstacles
            obstCount = int( line )
            print "\tReading %d obstacles" % ( obstCount )
            obstacles = [ None for i in xrange( obstCount ) ]
            for i in xrange( 0, obstCount ):
                line = f.readline()
                obst = Obstacle()
                tokens = line.split()
                obst.v0, obst.v1, obst.n0, obst.next = map( lambda x: int(x), tokens )
                obstacles[ i ] = obst
    except IOError:
        print "Unable to open the nav mesh file %s" % ( nmFileName )

    obstacles = buildObstacles( obstacles )
    
    print "Writing obstacle file: %s" % obstName
    try:
        with open( obstName, 'w' ) as f:
            f.write( '''<?xml version="1.0"?>
<Experiment version="2.0">

    <ObstacleSet type="explicit" class="1">''')
            for o in obstacles:
                f.write('''
        <Obstacle closed="1">''' )
                for idx in o:
                    v = vertices[idx]
                    f.write( '''
            <Vertex p_x="%f" p_y="%f"/>''' % ( v[0], v[1] ) )
                f.write( '''
        </Obstacle>''' )
            f.write( '''
    </ObstacleSet>
</Experiment>''')
    except IOError:
        print "Unable to open the obstacle file for writing"

def exitError( msg, parser ):
    '''Prints an error message, writes the help, and exits the program.

    @param  msg     A string.  The explicit error message to print.
    @param  parser  An OptionParser instance.  used to write usage information.
    '''
    print '\n!!! %s\n' % msg
    parser.print_help()
    sys.exit(1)

def main():
    import os, optparse
    parser = optparse.OptionParser()
    parser.set_description( 'Given a navigation mesh file, extracts the obstacles and writes them to an obstacle xml file.' )
    parser.add_option( "-i", "--input", help="Name of nav mesh file to convert",
                       action="store", dest="nmFileName", default='' )
    parser.add_option( "-o", "--output", help="The name of the output file. The extension will automatically be added (.xml).",
                       action="store", dest="obstFileName", default='output' )
    options, args = parser.parse_args()

    nmFileName = options.nmFileName
    obstName = options.obstFileName

    if ( nmFileName == '' ):
        exitError( 'No nav mesh file defined', parser )
    if ( obstName == '' ):
        exitError( 'No obstacle file defined', parser )

    navMeshToObstacle( nmFileName, obstName )
    

if __name__ == '__main__':
    import sys
    main()
