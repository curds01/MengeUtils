import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
import Select

# OpenGL View
class View:
    """Contains the OpenGL view parameters for the scene"""
    VIDEO_FLAGS = pygame.OPENGL|pygame.DOUBLEBUF|pygame.RESIZABLE
    HELP_TEXT = 'View has no help'
    def __init__( self, imgSize, imgBottomLeft, viewSize, viewBottomLeft, winSize, font ):
        # the size of the displayed background and where it's bottom left-corner should be placed
        self.bgWidth = imgSize[0]
        self.bgHeight = imgSize[1]
        self.bgLeft = imgBottomLeft[0]
        self.bgBottom = imgBottomLeft[1]
        
        # the current view  - this is the LOGICAL size of what I'm viewing -- not the size of the window
        self.vWidth = viewSize[ 0 ]
        self.vHeight = viewSize[ 1 ]
        self.vLeft = viewBottomLeft[ 0 ]
        self.vBottom = viewBottomLeft[ 1 ]

        self.wWidth = winSize[ 0 ]
        self.wHeight = winSize[ 1 ]

        self.pixelSize = self.vWidth / float( self.wWidth )        # this is assuming square pixels

        # create characters
        self.char = [None for i in range( 256 ) ]
        for c in range( 256 ):
            self.char[ c ] = self._charMap( chr(c), font )
        self.char = tuple( self.char )
        self.lw = self.char[ ord('0') ][1]
        self.lh = self.char[ ord('0') ][2]

    def initWindow( self, title ):
        """Initializes the pygame window"""
        self.surface = pygame.display.set_mode( (self.wWidth, self.wHeight), View.VIDEO_FLAGS )
        pygame.display.set_caption( title )
        self.resizeGL( ( self.wWidth, self.wHeight ) )
        
    def screenToWorld( self, (x, y ) ):
        """Converts a screen-space value into a world-space value - the result is a 2-TUPLE"""
        x_GL = x / float( self.wWidth ) * self.vWidth + self.vLeft
        y_GL = (1.0 - y / float( self.wHeight ) ) * self.vHeight + self.vBottom
        return x_GL, y_GL

    def worldToScreen( self, (x,y) ):
        '''Converts world-space value into a screen-space value - the result is a 2-TUPLE'''
        x_S = int( ( x - self.vLeft ) * self.wWidth / self.vWidth )
        y_S = int( self.wHeight * ( 1.0 - ( y - self.vBottom ) / self.vHeight ) )
        return x_S, y_S

    def initGL( self ):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClearDepth(1.0)
        glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )
        
    def resizeGL( self, size ):
        self.wWidth, self.wHeight = size
        if self.wHeight == 0:
            self.wHeight = 1

        glViewport(0, 0, self.wWidth, self.wHeight)
        self.surface = pygame.display.set_mode( (self.wWidth, self.wHeight), View.VIDEO_FLAGS )
        centerX = self.vLeft + 0.5 * self.vWidth
        centerY = self.vBottom + 0.5 * self.vHeight
        self.vWidth =  self.wWidth * self.pixelSize
        self.vHeight = self.wHeight * self.pixelSize
        self.vLeft = centerX - 0.5 * self.vWidth
        self.vBottom = centerY - 0.5 * self.vHeight
        self.initGL()
        self._setOrtho()
        

    def select( self, x, y, selectable, selectEdges=False ):
        self._setOrtho( True, x, y )
        
        # this needs to be large enough to handle evrything that can push into
        #   the select buffer - THIS SHOULD WORK, but the agent context isn't
        #   using the select buffer.  :(
##        glSelectBuffer( Select.Selectable.ID * 2)
        glSelectBuffer( 4096L )
        
        glRenderMode( GL_SELECT )
            
        glInitNames()
        glPushName( 0 )

        selectable.drawGL( True, selectEdges )
        hits = list(glRenderMode( GL_RENDER ) )
        glMatrixMode( GL_PROJECTION )
        glPopMatrix()
        glMatrixMode( GL_MODELVIEW )
        return self._closestHit( hits )

    def _closestHit( self, buffer ):
        closest = -1
        if ( len(buffer) == 1):
            closest = buffer[0][2][0]
        elif ( len( buffer ) > 1 ):
            closestDist = buffer[0][0]
            closest = buffer[0][2][0]
            for hit in buffer[1:]:
                testDist = hit[0]
                if ( testDist < closestDist ):
                    closest = hit[2][0]
        return closest    

    def _setOrtho( self, select=False, x=None, y=None ):
        self.pixelSize = self.vWidth / float( self.wWidth )
        glMatrixMode( GL_PROJECTION )
        if ( select ):
            SEL_WINDOW = 25
            glPushMatrix()        
            glLoadIdentity()
            viewport = glGetIntegerv( GL_VIEWPORT )
            gluPickMatrix( x, viewport[3] - y, SEL_WINDOW, SEL_WINDOW, viewport )
        else:
            glLoadIdentity()
        glOrtho( self.vLeft, self.vLeft + self.vWidth, self.vBottom, self.vBottom + self.vHeight, -1, 1 )
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()        

    # view controls
    def changeViewWidth( self, delta ):
        self.vWidth += delta
        self._setOrtho()

    def zoomIn( self, center, pct = 0.10 ):
        """Zooms the view in around the center (in screen coords)"""
        # "zooming in" means that a pixel should be 1 + pct times larger than before
        x, y = self.screenToWorld( center )
        
        self.pixelSize *= 1.0 + pct
        viewScale = 1.0 - pct
        self.vWidth *= viewScale
        self.vHeight *= viewScale
        self.vLeft = x - ( center[0] / float( self.wWidth) * self.vWidth )
        self.vBottom = y - ( 1.0 - center[1] / float( self.wHeight) ) * self.vHeight
        self._setOrtho()

    def zoomOut( self, center, pct = 0.10 ):
        """Zooms the view out around the center (in screen coords)"""
        # "zooming out" means that a pixel should be 1 - pct times the original size
        x, y = self.screenToWorld( center )
        self.pixelSize *= 1.0 - pct
        viewScale = 1.0 + pct
        self.vWidth *= viewScale
        self.vHeight *= viewScale
        self.vLeft = x - ( center[0] / float( self.wWidth) * self.vWidth )
        self.vBottom = y - ( 1.0 - center[1] / float( self.wHeight) ) * self.vHeight
        self._setOrtho()

    def windowAspectRatio( self ):
        """Returns the window's aspect ratio"""
        return float( self.wWidth ) / float( self.wHeight )
    
    def zoomRectangle( self, rect ):
        """Zooms in based on the given rectangle"""
        rAR = rect.aspectRatio()
        wAR = self.windowAspectRatio()
        if ( rAR > wAR ):
            self.vLeft = rect.left
            self.vWidth = rect.width()
            self.vHeight = self.vWidth / wAR
            self.vBottom = rect.bottom - ( self.vHeight - rect.height() ) * 0.5
        elif ( rAR < wAR ):
            self.vBottom = rect.bottom
            self.vHeight = rect.height()
            self.vWidth = self.vHeight * wAR
            self.vLeft = rect.left - ( self.vWidth - rect.width() ) * 0.5
        else:
            self.vLeft = rect.left
            self.vWidth = rect.width()
            self.vBottom = rect.bottom
            self.vHeight = rect.height()
        self._setOrtho()

    def startZoom( self, pos ):
        '''Prepares the view for zoom -- given the screen space position of the beginning of the zoom'''
        self.vLeftOld = self.vLeft
        self.vBottomOld = self.vBottom
        self.pixelSizeOld = self.pixelSize
        self.vWidthOld = self.vWidth
        self.vHeightOld = self.vHeight
        self.zoomCenter = pos
        self.zoomCenterWorld = self.screenToWorld( pos )

    def zoom( self, dY ):
        '''Zooms in the view -- change in mouse y-position'''
        scale = dY / float(self.wHeight + 1)
        self.pixelSize = self.pixelSizeOld * ( scale + 1 )
        viewScale = 1.0 - scale
        self.vWidth = self.vWidthOld * viewScale
        self.vHeight = self.vHeightOld * viewScale
        self.vLeft = self.zoomCenterWorld[0] - ( self.zoomCenter[0] / float( self.wWidth ) * self.vWidth )
        val = self.zoomCenterWorld[1] - ( 1 - self.zoomCenter[1] / float( self.wHeight ) ) * self.vHeight
        self.vBottom = val
        self._setOrtho()

    def cancelZoom( self ):
        '''Cancels the zoom'''
        self.vLeft = self.vLeftOld
        self.vBottom = self.vBottomOld
        self.pixelSize = self.pixelSizeOld
        self.vWidth = self.vWidthOld
        self.vHeight = self.vHeightOld
        self._setOrtho()

    def startPan( self ):
        self.vLeftOld = self.vLeft
        self.vBottomOld = self.vBottom

    def pan( self, (dX, dY) ):
        """Pans the view -- the offset is in world space"""
        self.vLeft = self.vLeftOld + dX
        self.vBottom = self.vBottomOld + dY
        self._setOrtho()

    def cancelPan( self ):
        self.vLeft = self.vLeftOld
        self.vBottom = self.vBottomOld
        self._setOrtho()

    def _charMap(self, c, font):
        try:
            letter_render = font.render(c, True, (255,255,255), (0, 0, 0, 64 ))
            letter = pygame.image.tostring(letter_render, 'RGBA', 1)
            letter_w, letter_h = letter_render.get_size()
        except:
            letter = None
            letter_w = 0
            letter_h = 0
        return (letter, letter_w, letter_h)
    
    def printText( self, txt, pos ):
        """Prints text at the given screen coordinates"""
        # set up screen coords
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0.0, self.wWidth - 1.0, 0.0, self.wHeight - 1.0, -1.0, 1.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        vSpace = self.char[ ord( 'a' ) ][2]
        hSpace = self.char[ ord( 'a' ) ][1]
        length = len( txt )
        x, y = pos
        i = 0
        lx = 0
        while ( i < length ):
            c = txt[i]
            if ( c == '\n' ):
                y -= vSpace
                lx = 0
            elif ( c == '\t' ):
                lx += hSpace << 2
            else:
                glRasterPos2i( x + lx, y )
                ch = self.char[ ord( txt[ i ] ) ]
                glDrawPixels( ch[1], ch[2], GL_RGBA, GL_UNSIGNED_BYTE, ch[0] )
                lx += ch[1]
            i += 1
               
        glMatrixMode( GL_PROJECTION )
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

    def textSize( self, txt ):
        '''Given the text, computes the size of a bounding box for the text'''
        vSpace = self.char[ ord( 'a' ) ][2]
        hSpace = self.char[ ord( 'a' ) ][1]
        length = len( txt )
        
        w = 0
        h = vSpace

        i = 0
        lx = 0
        while ( i < length ):
            c = txt[i]
            if ( c == '\n' ):
                h += vSpace
                if ( lx > w ):
                    w = lx
                lx = 0
            elif ( c == '\t' ):
                lx += hSpace << 2
            else:
                ch = self.char[ ord( txt[ i ] ) ]
                lx += ch[1]
            i += 1
        if ( lx > w ):
            w = lx
            
        return (w, h)
        
##    def drawSubImg( self ):
##        global SUB_IMG
##        if ( SUB_IMG != None ):
##            glMatrixMode(GL_PROJECTION)
##            glPushMatrix()
##            glLoadIdentity()
##            glOrtho(0.0, self.wWidth - 1.0, 0.0, self.wHeight - 1.0, -1.0, 1.0)
##            glMatrixMode(GL_MODELVIEW)
##            glLoadIdentity()
##
##            x, y = ( 10, 10 )
##            glRasterPos2i( x, y )
##            w, h = SUB_IMG.get_size()
##            glDrawPixels( w, h, GL_RGBA, GL_UNSIGNED_BYTE, pygame.image.tostring( SUB_IMG, 'RGBA', 1 ) )
##                   
##            glMatrixMode( GL_PROJECTION )
##            glPopMatrix()
##            glMatrixMode(GL_MODELVIEW)
            