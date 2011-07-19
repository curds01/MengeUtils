# initialize pilgrims for the tawaf
#   Create a single set of agents
#   densely fill a circle around the tawf
#   tight bound to the obstacles

import numpy as np
from obstacles import *
from primitives import Vector2
import random

#TAWAF_CENTER =

def writeXML( fileName, positions, agtRadius, obstacles ):
    '''Write the positions out to an xml file'''
    HEADER ='''<?xml version="1.0"?>

<Experiment time_step="0.05" gridSizeX="82" gridSizeY="82" visualization="1" useProxies="1" neighbor_dist="5">

  <AgentSet obstacleSet="3" process="1" vel_sample_count="250" neighbor_dist="3" max_neighbors="10" r="%f" class="0" g_r="3.0" pref_speed="1.04" ttc="0.5" max_speed="2.0" max_accel="10.0" or="0.0" safety_factor="1.5">
''' % agtRadius
    f = open( fileName, 'w' )
    f.write( HEADER )
    for p in positions:
        f.write( '    <Agent p_x="%f" p_y="%f" />\n' % ( p.x, p.y ) )
    TAIL = '  </AgentSet>\n'
    f.write( TAIL )
    for o in obstacles.polys:
        f.write( '  <Obstacle closed="%d" boundingbox="0" class="1">\n' % o.closed )
        for v in o.vertices:
            f.write( '    <Vertex p_x="%f" p_y="%f" />\n' % ( v.x, v.y ) )
        f.write( '  </Obstacle>\n' )
    f.write( '</Experiment>\n' )
                
    
def agentHexArea( radius ):
    '''Computes the area of the hexagon that bounds a circle of the given radius'''
    #
    #     _____x_
    #    /\  |  /\
    #   /  \ |a/  \
    #  /____\|/____\    - angle a is 30 degrees, so it's a 30-60-90 triangle
    #                   - the length of x is radius / sqrt(3)
    #                   - the area of this tri is R * R / sqrt(3) / 2
    #                   - there are 12 of these tris total area: 6 * R * R / sqrt(3)
    return 6.0 * radius * radius / np.sqrt( 3.0 )
    
def addAgents( agtCount, agtRadius, obstacles ):
    '''Place agents in a disk around the global center TAWAF_CENTER'''
    # pack them in as tightly as possible
    #   lay them out as hexes
    #   Make the radius as small as possible
    print "Maximum density for radius: %f = %f" % ( agtRadius, 2.0 / ( agtRadius * agtRadius * 4 * np.sqrt(3) ) )
    agtRadius *= 1.075   # 15% breathing room on both sides
    
    agtArea = agentHexArea( agtRadius ) * agtCount
    obstArea = 0.0
    for o, bb in obstacles:
        obstArea += o.area2D()
    totalArea = agtArea + obstArea
    R = np.sqrt( totalArea / np.pi )
    MAX_RADIUS = 48.0
    if ( R > MAX_RADIUS ):
        print "\n*** Tried to create a radius bigger than would fit: %f reduced to %f ***\n" % ( R, MAX_RADIUS )
        R = MAX_RADIUS
        B = R
        A = totalArea / ( np.pi * R )
    else:
        A = R
        B = R
    A2 = A * A
    B2 = B * B
##    R2 = R * R
    
    # now start laying down agents
    #   - start on the horizontal axis working left to right, then work above and below
    HEX_WIDTH = agtRadius * 2
    ROW_DISP = agtRadius * np.sqrt(3.0)
    y = 0.0
    row = 0
    positions = []
    while ( y < B):
        if ( len(positions) >= agtCount ):
            print "Reached %d agents with y = %f" % ( len( positions ), y )
            break
        # determine circle width at this y value
##        width = 2.0 * np.sqrt( R2 - y *y )
        width = 2.0 * np.sqrt( A2 * (1 - (y*y)/B2 ) )
        # even rows get odd number of agents, odd rowd get even number
        #   in other words, the row number plus the number that fit should always be odd
        hexFit = int( width / HEX_WIDTH )
        if ( ( row + hexFit ) % 2 == 0 ):
            hexFit += 1
        left = -HEX_WIDTH * hexFit / 2.0
        for i in range( hexFit ):
            x = left + i * HEX_WIDTH
            # row above
            if ( row == 0 ):
                points = [ Vector2( x, y ) ]
            else:
                points = [ Vector2( x, y ), Vector2( x, -y ) ]
            for p in points:
                valid = True
                for o, bb in obstacles:
                    inBB = bb.pointInside( p )
                    inO = o.pointInside( p )
                    if ( inBB and inO ):
                        valid = False
                        break
                if ( valid ):
                    positions.append( p )
        row += 1
        y += ROW_DISP
    print "\n*** %d total agents ***\n" % ( len(positions ) )
    return positions
    

def main():
    import optparse, sys
    parser = optparse.OptionParser()
    parser.add_option( "-o", "--obstacle", help="Obstacle file to load.",
                       action="store", dest='obstName', default='' )
    parser.add_option( "-r", "--radius", help="Agent radius (defaults to 0.23.)",
                       action="store", dest='agtRadius', default=0.23, type='float' )
    parser.add_option( "-c", "--count", help="Total number of agents to add (defaults to 1000).",
                       action="store", dest="agtCount", default=1000, type='int' )
    options, args = parser.parse_args()
    if ( options.obstName == '' ):
        parser.print_help()
        sys.exit(1)

    print "Obstacle file:", options.obstName
    print "Agent radius:", options.agtRadius
    print "Agent count: ", options.agtCount

    obstacles, junk = readObstacles( options.obstName )
    obstacles.inflate( options.agtRadius )
    obstacles = obstacles.obstacleBB()

    positions = addAgents( options.agtCount, options.agtRadius, obstacles )     
    random.shuffle( positions )

    obstacles, junk = readObstacles( options.obstName )
    writeXML( 'allMatafObst.xml', positions, options.agtRadius, obstacles )    
    
if __name__ == '__main__':
    main()