# Various functions for placing agents
#   This assumes circular agents

#TODO: Use Poisson-disk distribution to fill an area
import numpy as np
import random

import sys
OBJ_READER_PATH = '\\projects\\objreader'
if ( not OBJ_READER_PATH in sys.path ):
    sys.path.insert( 0, OBJ_READER_PATH )
from primitives import Vector2
        
def distanceForDensity( maxDensity, radius ):
    '''Given the radius of an agent and the desired density, returns the average distance between agent BOUNDARIES.'''
    return 2.0 * ( 1.0 / np.sqrt( 2 * maxDensity * np.sqrt( 3.0 ) ) - radius )

def maxDensity( radius ):
    '''Computes the maximum collision-free density for circular agents of the given radius'''
    # This is based on maximally packing disks in a hexagonal lattice.
    return 1.0 / ( radius * radius * 2.0 * np.sqrt( 3.0 ) )

def effectiveRadius( maxDensity ):
    '''Given the desired density, returns the effective agent radius to produce that density.
    Effective radius is the radius of a large disk such that, if maximally packed, the density is
    the target density.'''
    return 1.0 / np.sqrt( 2 * maxDensity * np.sqrt( 3.0 ) )

def agentRows( startX, startY, agtDist, rankDist, noise, rankCount, rankPop, agentLimit=-1 ):
    '''Create rows of agents and returns an array of agent positions.
        The agents on a single row are all aligned, but each row is offset from the surrounding rows.

    @param      startX      float - the x-value of the anchor point of the first row
    @param      startY      float - the y-value of the anchor point of the first row
    @param      agtDist     float - the signed distance between agents on a rank.
                                  - if negative, the agents are distributed to the left of startX
    @param      rankDist    float - the signed distance between ranks
                                  - if negative, the ranks are aligned below startX 
    @param      noise       (float, float) - an optional 2-tuple representing normal
                                        distribution where noise[0] and noise[1] are the
                                        mean and standard deviation of the noise, respectively
    @param      rankCount   int - The total number of ranks
    @param      rankPop     int - The population of the LONGER rank (the shorter ranks have one less)
    @param      agentLimit  int - The maximum number of agents to create.  If agentLimit is <= 0,
                                   there is no limit.  Otherwise, agentLimit number of positions are
                                   defined.
    @returns    An Nx2 array of agent positions.  Each row is one
                agent position where the 0- and 1st columns are the
                x- and y-positions, respectively.
    '''
    if ( agentLimit > 0 ):
        totalAgents = agentLimit
    else:
        bigRanks = rankCount / 2 + ( rankCount % 2 )
        smallRanks = rankCount - bigRanks
        totalAgents = bigRanks * rankPop + smallRanks * ( rankPop - 1 )
    positions = np.empty( ( totalAgents, 2 ), dtype=np.float32 )
    
    a = 0    
    y = startY
    for rank in xrange( rankCount ):
        if ( a >= totalAgents ): break
        x = startX
        count = rankPop
        if ( rank % 2 ):
            x += agtDist * 0.5
            count -= 1
        for pos in xrange( count ):
            px = x
            py = y
            if ( noise ):
                px += random.gauss( noise[0], noise[1] )
                py += random.gauss( noise[0], noise[1] )
            positions[ a, : ] = ( px, py )
            a += 1
            if ( a >= totalAgents ): break
            x += agtDist
        y += rankDist
    return positions

def agentCols( startX, startY, agtDist, rankDist, noise, rankCount, rankPop, agentLimit=-1 ):
    '''Create columns of agents and returns an array of agent positions.
        The agents on a single columns are all aligned, but each columns is offset from the surrounding columns.

    @param      startX      float - the x-value of the anchor point of the first columns
    @param      startY      float - the y-value of the anchor point of the first columns
    @param      agtDist     float - the signed distance between agents on a rank.
                                  - if negative, the agents are distributed below startY
    @param      rankDist    float - the signed distance between ranks
                                  - if negative, the ranks are distributed to the left of startX
    @param      noise       (float, float) - an optional 2-tuple representing normal
                                        distribution where noise[0] and noise[1] are the
                                        mean and standard deviation of the noise, respectively
    @param      rankCount   int - The total number of ranks
    @param      rankPop     int - The population of the LONGER rank (the shorter ranks have one less)
    @param      agentLimit  int - The maximum number of agents to create.  If agentLimit is <= 0,
                                   there is no limit.  Otherwise, agentLimit number of positions are
                                   defined.
    @returns    An Nx2 array of agent positions.  Each row is one
                agent position where the 0- and 1st columns are the
                x- and y-positions, respectively.
    '''
    if ( agentLimit > 0 ):
        totalAgents = agentLimit
    else:
        bigRanks = rankCount / 2 + ( rankCount % 1 )
        smallRanks = rankCount - bigRanks
        totalAgents = bigRanks * rankPop + smallRanks * ( rankPop - 1 )
    positions = np.empty( ( totalAgents, 2 ), dtype=np.float32 )
    
    a = 0
    x = startX
    for rank in xrange( rankCount ):
        if ( a >= totalAgents ): break
        y = startY
        count = rankPop
        if ( rank % 2 ):
            y += agtDist * 0.5
            count -= 1
        for pos in xrange( count ):
            px = x
            py = y
            if ( noise ):
                px += random.gauss( noise[0], noise[1] )
                py += random.gauss( noise[0], noise[1] )
            positions[ a, : ] = ( px, py )
            a += 1
            if ( a >= totalAgents ): break
            y += agtDist
        x += rankDist
    return positions


# rank organization - rows or columns
COLUMN_RANK = 1
ROW_RANK = 2

def rankDistances( radius ):
    '''Given the effective radius of an agent, computes the distance ALONG the rank between agent
    centers and between ranks.
    @param  radius      float - the effective radius for the target density.
    @returns    ( onRankDist, interRankDist ) - A 2-tuple of floats representing the distance
                between agents on the same rank, and distance between ranks of agents.
    '''
    return 2.0 * radius, np.sqrt( 3.0 ) * radius

def fillRectangle( radius, minX, minY, maxX, maxY, avgDensity, rankDir, noise=None ):
    '''Produces positions for agents.  The agents completely fill a rectangle specified by opposite
       corners (minX, minY), (maxX, maxy) and are spaced such that they produce the average density
       requested.  Finally, they are lined up in ranks according to the direction specified with
       positional noise applied as given.  The block is CENTERED in the rectangle.

    @param      radius      float - the physical radius of the agents
    @param      minX        float - the x-value left-most extent of the rectangle
    @param      minY        float - the y-value lower-most extent of the rectangle
    @param      maxX        float - the x-value right-most extent of the rectangle
    @param      maxY        float - the y-value upper-most extent of the rectangle
    @param      avgDensity  float - the average density of the positions
    @param      rankDir     int - value from the set {COLUMN_RANK, ROW_RANK} specifies in which
                                  direction the agents form lines (y- or x-axis, respecitvely).
    @param      noise       (float, float) - an optional 2-tuple representing normal
                                        distribution where noise[0] and noise[1] are the
                                        mean and standard deviation of the noise, respectively
    @returns    An Nx2 array of agent positions.  Where N is the number of agents required to fill
                the space.  The ith row consists of the x- and y-positions of the ith agent.
    '''
    R = effectiveRadius( avgDensity )
    D = 2 * R
    maxX -= radius
    maxY -= radius
    minY += radius
    minX += radius
    width = maxX - minX
    height = maxY - minY
    if ( rankDir == COLUMN_RANK ):
        tmp = height
        height = width
        width = tmp
        tmp = maxX
        maxX = maxY
        maxY = tmp
        tmp = minX
        minX = minY
        minY = tmp

    nbrDist, rankDist = rankDistances( R )
    # number of agents on a major rank
    if ( width <= nbrDist ):
        assert AttributeError, "Width of rectangle too small to support ranks with desired average density" 
    rowPop = int( width / nbrDist ) + 1       # number of agents on major row
    xOffset = ( width - nbrDist * rowPop ) * 0.5 + R   # center them horizontally
    rankCount = int( height / rankDist ) + 1
    yOffset = ( height - ( rankCount * rankDist ) ) * 0.5 + R
    pos = agentRows( minX + xOffset, minY + yOffset, nbrDist, rankDist, noise, rankCount, rowPop )
    if ( rankDir == COLUMN_RANK ):
        return pos[:, ::-1 ]
    else:
        return pos

def corridorMob( radius, p0, p1, avgDensity, rankDir, agentCount, noise=None ):
    '''Creates a "corridor mob" of agents.  It is a group of agents constrained on three sides (front and sides)
    but can keep going indefinitely far to the back.   The limit is specified by the number of agents.  The mob is
    centered along the "front" line.  The direction of the mob is predicated on the ordering of the front line.  It
    moves in the direction perpendicular to the line definition (p1 - p0) rotated 90 degrees counter clockwise.

    @param      radius      float - the physical radius of the agents
    @param      p0          Vector2 - The first point in the front line
    @param      p1          Vector2 - The second point in the front line
    @param      avgDensity  float - the average density of the positions
    @param      rankDir     int - value from the set {COLUMN_RANK, ROW_RANK} specifies in which
                                  direction the agents form lines (y- or x-axis, respecitvely).
                                  row rank is parallel with the front line, column is perpendicular
    @param      noise       (float, float) - an optional 2-tuple representing normal
                                        distribution where noise[0] and noise[1] are the
                                        mean and standard deviation of the noise, respectively
    @param      agentCount  int - the total number of agents to create
    @returns    An Nx2 array of agent positions.  Where N is the number of agents required to fill
                the space.  The ith row consists of the x- and y-positions of the ith agent.
    '''
    # create a y-axis-aligned box, centered on the origin.  These positions will then get transformed to the line
    midPt = ( p0 + p1 ) * 0.5
    lineDir = (p1 - p0).normalize()
    xAxis = lineDir
    yAxis = Vector2( -lineDir.y, lineDir.x )
    # offset
    P0 = p0 - midPt
    P1 = p1 - midPt
    # rotate
    P0 = Vector2( P0.dot( xAxis ), P0.dot( yAxis ) )
    P1 = Vector2( P1.dot( xAxis ), P1.dot( yAxis ) )
    
    minX = P0.x #+ radius
    maxX = P1.x #- radius
    width = maxX - minX

    R = effectiveRadius( avgDensity )
    D = 2 * R
    nbrDist, rankDist = rankDistances( R )
    if ( rankDir == ROW_RANK ):
        if ( width <= nbrDist ):
            assert AttributeError, "Width of corridor too small to support ranks with desired average density" 
        rowCount = int( width / nbrDist )
        xOffset = ( width - nbrDist * rowCount ) * 0.5 + R   # center them horizontally
        rankCount = ( agentCount / ( 2 * rowCount - 1 ) + 1) * 2 
        pos = agentRows( minX + xOffset, R, nbrDist, rankDist, noise, rankCount, rowCount, agentCount )
    elif ( rankDir == COLUMN_RANK ):
        if ( width <= rankDist ):
            assert AttributeError, "Width of corridor too small to support ranks with desired average density"
        rankCount = int( width / rankDist )
        xOffset = ( width - rankDist * rankCount ) * 0.5 + R   # center them horizontally
        rankPop = agentCount / rankCount + 1
        pos = agentCols( minX + xOffset, R, nbrDist, rankDist, noise, rankCount, rankPop, agentCount )
    else:
        raise AttributeError, "invalid rank direction: %s" % ( str( rankDir ) )

    # translate the points back
    P_x = np.dot( pos, ( xAxis.x, -xAxis.y ) )
    P_y = np.dot( pos, ( -yAxis.x, yAxis.y ) )

    pos[:,0] = P_x + midPt.x
    pos[:,1] = P_y + midPt.y

    return pos

def rectMob( radius, anchor, vertCenter, horzCenter, aspectRatio, avgDensity, rankDir, agentCount, noise=None, orient=0.0 ):
    '''Creates a rectangular mob of people.  The mob is anchored on the given point and the rows
    and columns are configured based on the desired aspect ratio and average density.

    @param      radius      float - physical radius of the agents    
    @param      anchor      Vector2 - The anchor of the mob
    @param      vertCenter  float - The vertical alignment of the mob to the anchor point.  If vertCenter
                            is zero, it aligns to the bottom, 1 aligns to the top, 0.5 to the center, etc.
    @param      horzCenter  float - the horizontal alignment of the mob to the anchor point. If horzCetner
                            is zero, it aligns to the left, 1 alings to the right, 0.5 to the center, etc.
    @param      aspectRatio float - the desired aspect ratio of the mob
    @param      avgDensity  float - the average density of the positions
    @param      rankDir     int - value from the set {COLUMN_RANK, ROW_RANK} specifies in which
                                  direction the agents form lines (y- or x-axis, respecitvely).
                                  row rank is parallel with the front line, column is perpendicular
    @param      agentCount  int - the total number of agents to create
    @param      noise       (float, float) - an optional 2-tuple representing normal
                                        distribution where noise[0] and noise[1] are the
                                        mean and standard deviation of the noise, respectively
    @param      orient      float - the orientation of the rectanble as given by the angle
                                    (in degrees).
    @returns    An Nx2 array of agent positions.  Where N is greater than or equal to agentCount
                the space.  The ith row consists of the x- and y-positions of the ith agent.
    '''
    assert( horzCenter >= 0.0 and horzCenter <= 1.0 )
    assert( vertCenter >= 0.0 and vertCenter <= 1.0 )
    
    R = effectiveRadius( avgDensity )
    D = 2 * R
    nbrDist, rankDist = rankDistances( R )
    if ( rankDir == COLUMN_RANK ):
        horzDist = rankDist
        vertDist = nbrDist
    elif ( rankDir == ROW_RANK ):
        horzDist = nbrDist
        vertDist = rankDist
    else:
        raise AttributeError, "invalid rank direction: %s" % ( str( rankDir ) )

    # scale factor which, given a value for a, determines the value for b    
    bFromA = horzDist * aspectRatio / vertDist
    a = 1
    while ( True ):
        b = int( np.ceil ( bFromA * a ) )
        majorRows = b / 2 + b % 2
        minorRows = b - majorRows
        est = majorRows * a + minorRows * ( a - 1 )
        if ( est >= agentCount ):
            break
        a += 1
    # dimensions of rectangle
    W = horzDist * a + 2 * radius
    H = vertDist * b + 2 * radius
    minX = -horzCenter * W
    maxX = minX + W
    minY = ( vertCenter - 1)* H
    maxY = minY + H

    pos = fillRectangle( radius, minX, minY, maxX, maxY, avgDensity, rankDir, noise )
    
    # transform generic positions for orientation and anchor
    xAxis = np.array( ( np.cos( orient * np.pi / 180.0 ), np.sin( orient * np.pi / 180.0 ) ) )
    yAxis = np.array( ( xAxis[1], -xAxis[0] ) )
    P_x = np.dot( pos, xAxis )
    P_y = np.dot( pos, yAxis )
    pos[:,0] = P_x + anchor[0]
    pos[:,1] = P_y + anchor[1]
    return pos


def getAABB( positions ):
    '''Given the agent positions, reports the axis-aligned bounding box for the group.

    @param      positions       An Nx2 array of floats.  First and second columns are
                                the x- and y-positions, respectively.
    @returns    Two 2-tuples.  (minX, minY), (maxX, maxY)
    '''
    return ( positions[:,0].min(), positions[:,1].min() ), ( positions[:,0].max(), positions[:,1].max() )

if __name__ == '__main__':
    def test():
        import sceneXML as XML
        import obstacles
        obst, bb = obstacles.readObstacles( 'junkObstacles.xml' )
        expParam = XML.ExpParams()
        agtParam = XML.AgentSetParams()
        R = 0.18
        agtParam.set( 'Common', 'r', R )
        noise = (0.1, 0.03 )
        if ( False ):
            pos = fillRectangle( R, bb.min.x, bb.min.y, bb.max.x, bb.max.y, 4.5, COLUMN_RANK, noise )
        elif ( False ):
            p0 = Vector2( -0, 1 )
            p1 = Vector2( 3, -4 )
            pos = corridorMob( R, p1, p0, 2.0, COLUMN_RANK, 200, None )
        elif ( True ):
            center = np.array( ( 0.0, 0.0 ), dtype=np.float32 )#Vector2( -3.0, 1.0 )
            pos = rectMob( R, center, 0.0, 0.0, 2.0, 3.0, COLUMN_RANK, 60, None, 25 )
        xml = XML.sceneXML( expParam, (pos,), (agtParam,), obst )

        f = open( 'junk.xml', 'w' )
        f.write( xml )
        f.close()
    
    #test()        
    #p = corridorMob( .2, Vector2(-8, -4.9), Vector2(-8, 4.9), .8, COLUMN_RANK, 600, noise=(0,.2))
    p = corridorMob( .2,  Vector2(8, 4.9), Vector2(8, -4.9), .8, COLUMN_RANK, 600, noise=(0,.2))
    
    for item in p:
        print '<Agent p_x="'+str(item[0])+'" p_y="'+str(item[1])+'" />'
