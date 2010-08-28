# Converts Stephen's obstacle text definitions to an xml file

import sys
from ObjSlice import Segment, Polygon, buildPolygons
from primitives import Vector3

def readSegments( fileName ):
    """Reads the file and returns a list of segments"""
    f = open( fileName, 'r' )
    count = int( f.readline() )
    print "Files has %d segments" % ( count )
    segments = []
    for line in f.xreadlines():
        line = line.strip()
        if ( line ):
            print line.strip()
            x1, y1, x2, y2 = map( lambda x: float(x), line.strip().split() )
            segments.append( Segment( Vector3( x1, 0, y1 ), Vector3( x2, 0, y2 ) ) )
    f.close()
    return segments

def main():
    segments = readSegments( sys.argv[1] )
    for s in segments:
        print s
    polys = buildPolygons( segments, Vector3( 0, 1, 0 ) )
    for p in polys:
        print p

    print '<?xml version="1.0"?>'
    print '<Experiment>'
    for p in polys:
        print p.RVOString()
    print '</Experiment>'

if __name__ == '__main__':
    main()