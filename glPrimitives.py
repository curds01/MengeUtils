# Classes to draw some of the primitives in a GL context
from primitives import Segment

class GLSegment( Segment):
    """Simple line object"""
    def __init__( self, p1, p2 ):
        Segment.__init__( self, p1, p2 )

    def __str__( self ):
        return "GLSegment (%s, %s)" % ( self.p1, self.p2 )

    def __repr__( self ):
        return str( self )

    def drawGL( self, color=(0.1, 1.0, 0.1) ):
        glPushAttrib( GL_COLOR_BUFFER_BIT )
        glBegin( GL_LINES )
        glColor3fv( color )
        glVertex2f( self.p1.x, self.p1.y )
        glVertex2f( self.p2.x, self.p2.y )
        glEnd()
        glPopAttrib()