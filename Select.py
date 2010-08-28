# Class for handling selection
from OpenGL.GL import *
from OpenGL.GLU import *

selectables = []

class Selectable:
    ID = 0
    def __init__( self ):
        self.id = Selectable.ID
        self.selected = False
        Selectable.ID += 1
        selectables.append( self )

    def setSelected( self ):
        self.selected = True

    def clearSelected( self ):
        self.selected = False

def closestHit( buffer ):
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
    if ( closest > -1 ):
        return selectables[ closest ]
    else:
        return None

# todo
#  the camera should have the following knowledge
#       1. viewpoint location
#       2. target location
#       3. up vector (right now implied as <0 1 0>
#       4. Screen size
#       5. Near and Far planes
##def select( scene, x, y, camera ):
##    # Given a screen (x, y) coordinate, a scene to select from and a camera
##    # returns a scene-defined id of the selected node
##    global selected, update
##    glMatrixMode( GL_PROJECTION )
##    glPushMatrix()
##    glLoadIdentity()
##    viewport = glGetIntegerv(GL_VIEWPORT )
##    gluPickMatrix( x, camera.viewport[3] - y, 3, 3, camera.viewport )
##    gluPerspective(45, 1.0*camera.screenWidth/camera.screenHeight, camera.near, camera.far)
##    glMatrixMode( GL_MODELVIEW )
##    glLoadIdentity()
##    camera.setGLView()
##    
##    glSelectBuffer( 512L )
##    glRenderMode( GL_SELECT )
##    
##    glInitNames()
##    glPushName( 0 )
##    scene.drawGL( True )
##    hits = list(glRenderMode( GL_RENDER ) )
##    glMatrixMode( GL_PROJECTION )
##    glPopMatrix()
##    glMatrixMode( GL_MODELVIEW )
##    return closestHit( hits )
    