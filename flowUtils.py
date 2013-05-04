# A set of utilities for working with flow lines
from primitives import segmentsFromString

def flowLinesToString( lines, names ):
    '''Given the lines and names of flow lines, outputs a parsable string.'''
    assert( len( lines ) == len( names ) )
    s = ','.join( names ) + "~"
    for i, line in enumerate( lines ):
        s += ' %.5f %.5f %.5f %.5f' % ( line.p1.x, line.p1.y, line.p2.x, line.p2.y )
    return s

def flowLinesFromString( s, LineClass ):
    '''Given a string of the format provided by flowLinesToString produces
    a list of strings and names.

    @param      s           A formatted flow line string.  The string
                            can be of the old format (for which no names
                            are listed.  Names will be created ).
    @param      LineClass   The type of line class to instantiate.
    @return     A 2-tuple of lists: [ names, lines ]
                names: a list of strings, one per line
                lines: a list of instances of class LineClass
    '''
    tokens = s.split( '~' )
    if ( len( tokens ) == 1 ):
        # old format
        lines = segmentsFromString( tokens[0], LineClass )
        names = [ 'Line %d' % i for i in xrange( len( lines ) ) ]
    else:
        names = tokens[0].split(',')
        lines = segmentsFromString( tokens[1], LineClass )
    return names, lines