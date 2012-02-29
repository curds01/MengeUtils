# A general class for passing algorithm configurations around
class Config:
    """An analysis configuration state"""
    # use to execute a run, can also be saved and read to a file
    def __init__( self ):
        self.state = {}

    def __getitem__( self, key ):
        return self.state[ key ]

    def __setitem__( self, key, value ):
        self.state[ key ] = value

    def __str__( self ):
        s = ''
        for key, val in self.state.items():
            s += '%s || %s\n' % ( key, val )
        return s

    def toFile( self, f ):
        f.write( str( self ) )

    def fromFile( self, f ):
        self.state = {}
        for x in f.xreadlines():
            tok = x.split('||')
            self.state[ tok[0].strip() ] = tok[1].strip()