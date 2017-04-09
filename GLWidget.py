from PyQt4 import QtCore, QtGui, QtOpenGL
from OpenGL.GL import *
from Context import *
from ObjSlice import AABB

# dragging parameters
NO_DRAG = 0
RECT = 1
PAN = 2
EDGE = 3
MOVE = 4
TEST = 5    # state to test various crap

# mouse buttons
LEFT = QtCore.Qt.LeftButton
MIDDLE = QtCore.Qt.MidButton
RIGHT = QtCore.Qt.RightButton
WHEEL_UP = 4
WHEEL_DOWN = 5

class GLWidget( QtOpenGL.QGLWidget ):
    '''Simple viewer to draw the scene in'''
    def __init__( self, bgSize, bgBtmLeft, viewSize, viewBtmLeft, winSize, parent=None ):
        QtOpenGL.QGLWidget.__init__( self, parent )

        # The external context for interacting with the scene
        self.context = None
        
        # everything that needs to be drawn in the scene
        #   drawn in the order given
        self.drawables = []

        # view manipulation stuff
        # the size of the displayed background and where it's bottom left-corner should be placed
        self.bgWidth = bgSize[0]
        self.bgHeight = bgSize[1]
        self.bgLeft = bgBtmLeft[0]
        self.bgBottom = bgBtmLeft[1]
        
        # the current view  - this is the LOGICAL size of what I'm viewing -- not the size of the window
        self.vWidth = viewSize[ 0 ]
        self.vHeight = viewSize[ 1 ]
        self.vLeft = viewBtmLeft[ 0 ]
        self.vBottom = viewBtmLeft[ 1 ]

        self.wWidth = winSize[ 0 ]
        self.wHeight = winSize[ 1 ]

        self.pixelSize = self.vWidth / float( self.wWidth )        # this is assuming square pixels

        ## mouse manip constants
        self.downX = 0
        self.downY = 0
        self.dragging = NO_DRAG

        self.setMouseTracking( True )

    def setUserContext( self, newContext ):
        '''Sets the interaction context'''
        self.context = newContext
        
    def setBG( self, bgSize, bgBtmLeft ):
        '''Sets the background values'''
        self.bgWidth = bgSize[0]
        self.bgHeight = bgSize[1]
        self.bgLeft = bgBtmLeft[0]
        self.bgBottom = bgBtmLeft[1]

    def setView( self, viewSize, viewBtmLeft ):
        """Sets the view parameters"""
        self.vWidth = viewSize[ 0 ]
        self.vHeight = viewSize[ 1 ]
        self.vLeft = viewBtmLeft[ 0 ]
        self.vBottom = viewBtmLeft[ 1 ]
        self.pixelSize = self.vWidth / float( self.wWidth )

    def initializeGL( self ):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClearDepth(1.0)
        glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )
        #print "OpenGL version", glGetString( GL_VERSION )

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        for drawable in self.drawables:
            drawable.drawGL()
        if ( self.context ):
            self.context.drawGL()

    def addDrawable( self, drawable ):
        '''Add a single drawable object'''
        self.drawables.append( drawable )

    def addDrawables( self, drawables ):
        '''Add a list of drawables'''
        self.drawables += drawables

    def removeDrawable( self, drawable ):
        '''Removes a single drawable object'''
        self.drawables.pop( self.drawables.index( drawable ) )

    def frameDrawables( self ):
        '''Modifies the view to frame all of the drawables'''
        if ( self.drawables ):
            bb = AABB()
            for drawable in self.drawables:
                bb.extend( drawable.getBB() )
            size = bb.getSize()
            w = size.x
            h = size.y
            # set the background and the view to be the same
            self.setBG( (w,h), (bb.min.x, bb.min.y) )
            center = bb.getCenter()
            ar = float( self.wWidth ) / self.wHeight
            if ( ar > 1 ):
                # wider than tall, height constrains
                h *= 1.05
                w = h * ar
            else:
                # higher than wide, width constrains
                w *= 1.05
                h = w / ar
            corner = (center.x - w / 2, center.y - h / 2)
            self.setView( (w,h), corner )
            self._setOrtho()
            self.updateGL()

    def resizeGL(self, width, height):
        self.wWidth, self.wHeight = (width, height)
        if self.wHeight == 0:
            self.wHeight = 1

        glViewport(0, 0, self.wWidth, self.wHeight)
        #pygame.display.set_mode( (self.wWidth, self.wHeight), View.VIDEO_FLAGS )
        centerX = self.vLeft + 0.5 * self.vWidth
        centerY = self.vBottom + 0.5 * self.vHeight
        self.vWidth =  self.wWidth * self.pixelSize
        self.vHeight = self.wHeight * self.pixelSize
        self.vLeft = centerX - 0.5 * self.vWidth
        self.vBottom = centerY - 0.5 * self.vHeight
        self.initializeGL()
        self._setOrtho()

    def _setOrtho( self, select=False, x=None, y=None ):
        try:
            self.pixelSize = self.vWidth / float( self.wWidth )
        except ZeroDivisionError:
            return
        
        glMatrixMode( GL_PROJECTION )
        if ( select ):
            SEL_WINDOW = 9
            glPushMatrix()        
            glLoadIdentity()
            viewport = glGetIntegerv( GL_VIEWPORT )
            gluPickMatrix( x, viewport[3] - y, SEL_WINDOW, SEL_WINDOW, viewport )
        else:
            glLoadIdentity()
        glOrtho( self.vLeft, self.vLeft + self.vWidth, self.vBottom, self.vBottom + self.vHeight, -1, 1 )
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def mousePressEvent(self, event):
        result = ContextResult()
        if ( self.context ):
            result = self.context.handleMouse( event, self )
            if ( result.isFinished() ):
                self.setUserContext( None )
        if ( not result.isHandled() ):
            btn = event.button()
            mods = event.modifiers()
            hasCtrl = mods & QtCore.Qt.ControlModifier
            if ( btn == LEFT ):
                self.downX, self.downY = event.x(), event.y()
                if ( int( hasCtrl ) ):
                    self.startPan()
                    self.dragging = PAN
            elif ( btn == MIDDLE ):
                pass
            elif ( btn == RIGHT ):
                pass
        if ( result.needsRedraw() ):
            self.updateGL()

    def mouseReleaseEvent( self, event ):
        result = ContextResult()
        if ( self.context ):
            result = self.context.handleMouse( event, self )
            if ( result.isFinished() ):
                self.setUserContext( None )
        if ( not result.isHandled() ):
            if ( self.dragging == PAN ):
                self.dragging = NO_DRAG
        if ( result.needsRedraw() ):
            self.updateGL()

    def mouseMoveEvent(self, event):
        result = ContextResult()
        if ( self.context ):
            result = self.context.handleMouse( event, self )
            if ( result.isFinished() ):
                self.setUserContext( None )
        if ( not result.isHandled() ):
            mods = event.modifiers()
            hasCtrl = mods & QtCore.Qt.ControlModifier
            if ( self.dragging == PAN ):
                dX, dY = self.screenToWorld( ( self.downX, self.downY ) )
                pX, pY = self.screenToWorld( ( event.x(), event.y() ) )
                self.pan( (dX - pX, dY - pY ) )
                result.setNeedsRedraw( True )
        if ( result.needsRedraw() ):
            self.updateGL()

    def wheelEvent( self, event ):
        result = ContextResult()
        if ( self.context ):
            result = self.context.handleMouse( event, self )
            if ( result.isFinished() ):
                self.setUserContext( None )
        if ( not result.isHandled() ):
            if ( event.delta() > 0 ):
                self.zoomIn( ( event.x(), event.y() ) )
            else:
                self.zoomOut( ( event.x(), event.y() ) )
            result.setNeedsRedraw( True )
        if ( result.needsRedraw() ):
            self.updateGL()

    def screenToWorld( self, (x, y ) ):
        """Converts a screen-space value into a world-space value"""
        x_GL = x / float( self.wWidth ) * self.vWidth + self.vLeft
        y_GL = (1.0 - y / float( self.wHeight ) ) * self.vHeight + self.vBottom
        return x_GL, y_GL
    
    def startPan( self ):
        self.vLeftOld = self.vLeft
        self.vBottomOld = self.vBottom

    def pan( self, (dX, dY) ):
        """Pans the view -- the offset is in world space"""
        self.vLeft = self.vLeftOld + dX
        self.vBottom = self.vBottomOld + dY
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
        x1, y1 = self.screenToWorld( center )

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