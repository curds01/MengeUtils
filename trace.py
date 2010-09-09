# Performs the work of creating traces on a crowd
# This draws the traces using pygame and pygame line drawing
#   Each link in the trace has constant transparency
#   Alternatively, one could use OpenGL and send a GL_LINES with increasing transparency.
#       in that case, transparency would be linearly blended along each line segment.
import pygame

pygame.display.init()

# set of colors to randomly color agents
COLORS = ( ( 255, 0 ,0 ),
           ( 255, 128, 0 ),
           ( 255, 255, 0 ),
           ( 128, 255, 0 ),
           ( 0, 255, 0 ),
           ( 0, 255, 128 ),
           ( 0, 255, 255 ),
           ( 0, 128, 255 ),
           ( 0, 0, 255 ),
           ( 128, 0, 255 ),
           ( 255, 0, 255 ),
           ( 255, 0, 128 )
           )
COLOR_COUNT = len( COLORS )

def getImgSpace( minCorner, cellSize, point ):
    """Takes a point in world space and transforms it to screen space"""
    trans = point - minCorner
    return trans / cellSize

def drawTrace( surf, i, trace, preSize, postSize, width=2 ):
    """Draws a trace onto the surface.

    The trace is defined by a list of Vector2s.
    Line segments are drawn between sequential pairs of Vector2s.
    The color is given by the index.
    The transparency of each link is determiend by how far into the backward or forward trace the link is"""
    color = COLORS[ i % COLOR_COUNT ]

    # backward trace
    for i in range( preSize ):
        A = int( 255 * float( i + 1 ) / float( preSize + 1 ) )
        pygame.draw.line( surf, color + (A,), trace[i].asTuple(), trace[i+1].asTuple(), width )
    
    # forward trace
    tIdx = preSize
    for i in range( postSize ):
        A = int( 255 * float( postSize - 1 - i ) / ( postSize + 1 ) )
        pygame.draw.line( surf, color + (A,), trace[tIdx].asTuple(), trace[ tIdx + 1].asTuple(), width )
        tIdx += 1
                         

def renderTraces( minCorner, size, resolution, frameSet, preWindow, postWindow, fileBase ):
        """Creates a sequence of images of the traces of the agents.

        The trace extends temporally backwards preWindow frames.
        The trace extends temporally forwards postWindow frames.
        The dimensions of the rasterized grid are determined by: minCorner, size, resolution.
        The rendered colors are then output via the colorMap and fileBase name.
        """
        SAMPLE = 11
        cellSize = size.x / float( resolution[ 0 ] )    # assume square grid
        frameSet.setNext( 0 )
        traces = [ [] for i in range( frameSet.agtCount ) ]

        # For the first preWindow + postWindow create a sequence of positions for each agent
        frame, index = frameSet.next()
        for i in range( preWindow + postWindow ):            
            for i, agt in enumerate( frame.agents ):
                if ( i % SAMPLE ): continue
                traces[ i ].append( getImgSpace( minCorner, cellSize, agt.pos ) )
                
            frame, index = frameSet.next()

        surface = pygame.Surface( resolution, pygame.SRCALPHA )
        
        # For the rest of the frames
        fIndex = 0
        while ( frame ):
            surface.fill( (0, 0, 0, 0 ) )            
            for i, agt in enumerate( frame.agents ):
                if ( i % SAMPLE ): continue
                traces[ i ].append( getImgSpace( minCorner, cellSize, agt.pos ) )
                drawTrace( surface, i, traces[i], preWindow, postWindow, 2 )
                traces[ i ].pop( 0 )
            pygame.image.save( surface, '%s%04d.png' % ( fileBase, fIndex ) )
            frame, index = frameSet.next()
            fIndex += 1