# A grid with rasterization functionality
##import IncludeHeader

##import julichData

from Grid import DataGrid
from primitives import Vector2
import numpy as np

class RasterGrid( DataGrid ):
    """Class to discretize scalar field computation"""
    def __init__( self, minCorner, size, resolution, initVal=0.0 ):
        """Initializes the grid to span the space starting at minCorner,
        extending size amount in each direction with resolution cells
        domainX is a Vector2 storing range of value x from user.
        domainX[0] stores min value and domainX[1] stores max value.
        domainY is a similar to domainX but in y-axis"""
        DataGrid.__init__( self, minCorner, size, resolution )
        self.initVal = initVal
        self.clear( np.float32 )

    def getValueInGrid( self, position ):
        """ Get the value stored in grid cell at given position
        @param position: a Vector2 of world position
        @return if position is valid in grid space then return value at that position
            otherwise return None """

        # Convert position in world space to grid space
        (x, y) = self.getCenter( position )
##        print "location in grid" + str ((x,y))
        if ( x >= self.resolution[0] ) or ( y >= self.resolution[1] ):
            return None
        if ( x < 0 ) or ( y < 0 ):
            return None
##        print position
##        print (x,y)
##        print self.cells[x][y]
        return self.cells[x][y]

    def computeClosestNeighbor( self, agent, frame ):
        '''compute distance from current agent to every other. Running in O(n^2) as
            we checking one against all others'''
        agentPos = agent[:2,]
        minDist = 1000.
        if (frame.shape[0] == 1):
            # Distance to the closet boundary
            return MAX_DIST
        for agt in frame:
            agtPos = agt[:2,]
            if (agentPos[0] == agtPos[0] and  agentPos[1] == agtPos[1]):
                # Agent and agt is the same
                continue
            diff = agtPos - agentPos
            localMin = np.sum(diff * diff, axis=0)
            if (localMin < minDist):
                minDist = localMin
        return np.sqrt(minDist)

    def rasterizePosition( self, frame, distFunc, smoothParam, obstacles=None ):
        """Given a frame of agents, rasterizes the whole frame"""
        # splat the kernel centered at the grid which contain agents
        if ((distFunc != FUNCS_MAP['variable-gaussian'])):
            kernel = Kernel( smoothParam, distFunc, self.cellSize )
            # This assumes the kernel dimensions are ODD-sized
            w, h = kernel.data.shape
            w /= 2
            h /= 2
            
        for agt in frame:
            pos = agt[:2,]
            if (distFunc == FUNCS_MAP['variable-gaussian']):
                # Using variable Gaussian. Compute new radius for every agent
                if obstacles is not None:
                    #distance to closest obstacle
                    distObst = obstacles.findClosestObject( Vector2(pos[0], pos[1]) )
                #distance to closest neighbor
                distNei = self.computeClosestNeighbor(agt, frame)
                # minRadius is the smallest distance to either obstacle or neighbor
                if (distObst < distNei):
                    minRadius = distObst
                else:
                    minRadius = distNei
                if (minRadius < BUFFER_DIST):
                    minRadius = BUFFER_DIST
                kernel = Kernel( minRadius, smoothParam, distFunc, self.cellSize )
                w, h = kernel.data.shape
                w /= 2
                h /= 2
            # END IF
            
            # get position of the agent the world grid
            center = self.getCenter( Vector2(pos[0], pos[1]) )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            try:
                if ( l < r and b < t and kl < kr and kb < kt ):
                    # Convolution
                    self.cells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ]
            except ValueError, e:
                print "Value error!"
                print "\tAgent at", center
                print "\tGrid resolution:", self.resolution
                print "\tKernel size:", kernel.data.shape
                print "\tTrying rasterize [ %d:%d, %d:%d ] to [ %d:%d, %d:%d ]" % ( kl, kr, kb, kt, l, r, b, t)
                raise e
    def reflectOverBoundary( self, flipL, flipR, flipT, flipB, kernel,
                             (kl, kr, kb, kt),( l,r,b,t)):
        if flipL:
            reflect = kernel.data[0:kl, kb:kt][::-1,::]
            if reflect.shape[0] > self.resolution[0]:
                start = 0
                end = self.resolution[0]
                self.cells[ start:end, b:t ] += reflect[ start:end, :: ]
            else:
                self.cells[ 0:reflect.shape[0], b:t ] += reflect
                        
        if flipR:
            reflect = kernel.data[-1:kr-1:-1,kb:kt]
            if reflect.shape[0] > self.resolution[0]:
                start = 0
                end = self.resolution[0]
                self.cells[ start:end, b:t ] += reflect[ (reflect.shape[0] - end):,:: ]
            else:
                self.cells[(r-reflect.shape[0]):r, b:t] += reflect
                        
        if flipB:
            reflect = kernel.data[kl:kr, 0:kb][::,::-1]
            if reflect.shape[1] > self.resolution[1]:
                start = 0
                end = self.resolution[1]
                self.cells[ l:r, start:end ] += reflect[ kl:kr, (reflect.shape[1] - end): ]
            else:
                self.cells[ l:r, 0:reflect.shape[1]] += reflect
                        
        if flipT:
            reflect = kernel.data[ kl:kr, -1:kt-1:-1 ]
            if reflect.shape[1] > self.resolution[1]:
                start = 0
                end = self.resolution[1]
                self.cells[ l:r, start:end ] += reflect[ ::, start:end ]
            else:
                self.cells[ l:r, (t - reflect.shape[1]):t ] += reflect
    
        if flipL and flipT:
            reflect = kernel.data[0:kl,-1:kt-1:-1][::-1,::]
            if ( reflect.shape[0] > self.resolution[0] ) and \
                ( not reflect.shape[1] > self.resolution[1] ):
                start = 0
                end = self.resolution[0]
                self.cells[ start:end, (t - reflect.shape[1]):t ] += reflect[start:end, ::]
            elif ( reflect.shape[1] > self.resolution[1] ) and\
                ( not reflect.shape[0] > self.resolution[0] ):
                start = 0
                end = self.resolution[1]
                self.cells[ l:r, start:end ] += reflect[ ::, start:end ]
            elif ( reflect.shape[1] > self.resolution[1] ) and\
                ( reflect.shape[0] > self.resolution.shape[0] ):
                self.cells[ 0:self.resolution[0], 0:self.resolution[1] ] += \
                        reflect[ 0:self.resolution[0], 0:self.resolution[1] ]
            else:
                self.cells[ l:(l + reflect.shape[0]),
                            (t - reflect.shape[1]):t ] += reflect
                        
        if flipL and flipB:
            reflect = kernel.data[0:kl, 0:kb][::-1,::-1]
            if ( reflect.shape[0] > self.resolution[0] ) and \
                ( not reflect.shape[1] > self.resolution[1] ):
                start = 0
                end = self.resolution[0]
                self.cells[ start:end, 0:reflect.shape[1] ] += reflect[start:end, ::]
            elif ( reflect.shape[1] > self.resolution[1] ) and\
                 ( not reflect.shape[0] > self.resolution[0] ):
                start = 0
                end = self.resolution[1] 
                self.cells[ l:r, start:end ] += reflect[ kl:kr, (reflect.shape[1] - end): ]
            elif ( reflect.shape[1] > self.resolution[1] ) and\
                 ( reflect.shape[0] > self.resolution.shape[0] ):
                self.cells[ 0:self.resolution[0], 0:self.resolution[1] ] += \
                        reflect[ 0:self.resolution[0], (reflect.shape[1] - end): ]
            else:
                self.cells[ 0:reflect.shape[0],
                            0:reflect.shape[1] ] += reflect
                        
        if flipR and flipB:
            reflect = kernel.data[-1:kr-1:-1, 0:kb][::,::-1]
            if ( reflect.shape[0] > self.resolution[0] ) and \
                ( not reflect.shape[1] > self.resolution[1] ):
                start = 0
                end = self.resolution[0]
                self.cells[ start:end, 0:reflect.shape[1] ] += reflect[(reflect.shape[0]-end):,::]
            elif ( reflect.shape[1] > self.resolution[1] ) and\
                ( not reflect.shape[0] > self.resolution[0] ):
                start = 0
                end = self.resolution[1]
                self.cells[ l:r, start:end ] += reflect[ kl:kr, (reflect.shape[1] - end): ]
            elif ( reflect.shape[1] > self.resolution[1] ) and\
                ( reflect.shape[0] > self.resolution.shape[0] ):
                self.cells[ 0:self.resolution[0], 0:self.resolution[1] ] += \
                            reflect[ (reflect.shape[0]-end):, (reflect.shape[1] - end): ]
            else:
                self.cells[ (r-reflect.shape[0]):r, 0:reflect.shape[1] ] += reflect
                        
        if flipR and flipT:
            reflect = kernel.data[-1:kr-1:-1, -1:kt-1:-1]
            if ( reflect.shape[0] > self.resolution[0] ) and \
                ( not reflect.shape[1] > self.resolution[1] ):
                start = 0
                end = self.resolution[0]
                self.cells[ start:end, (t - reflect.shape[1]):t ] += reflect[(reflect.shape[0]-end):,::]
            elif ( reflect.shape[1] > self.resolution[1] ) and\
                 ( not reflect.shape[0] > self.resolution[0] ):
                start = 0
                end = self.resolution[1]
                self.cells[ l:r, star:end ] += reflect[ ::, start:end ]
            elif ( reflect.shape[1] > self.resolution[1] ) and\
                ( reflect.shape[0] > self.resolution.shape[0] ):
                self.cells[ 0:self.resolution[0], 0:self.resolution[1] ] += \
                reflect[ (reflect.shape[0]-end):, 0:self.resolution[1] ]
            else:
                self.cells[ (r-reflect.shape[0]):r, (t - reflect.shape[1]):t  ] += reflect       

    def rasterizePositionWithReflection( self, frame, distFunc, smoothParam, obstacles=None ):
        """Given a frame of agents, rasterizes the whole frame"""
        # splat the kernel centered at the grid which contain agents
        if ((distFunc != FUNCS_MAP['variable-gaussian'])):
            kernel = Kernel( smoothParam, distFunc, self.cellSize )
            # This assumes the kernel dimensions are ODD-sized
            w, h = kernel.data.shape
            w /= 2
            h /= 2

        for agt in frame:
            pos = agt[:2,]
            if (distFunc == FUNCS_MAP['variable-gaussian']):
                # Using variable Gaussian. Compute new radius for every agent
                if obstacles is not None:
                    #distance to closest obstacle
                    distObst = obstacles.findClosestObject( Vector2(pos[0], pos[1]) )
                #distance to closest neighbor
                distNei = self.computeClosestNeighbor(agt, frame)
                # minRadius is the smallest distance to either obstacle or neighbor
                if (distObst < distNei):
                    minRadius = distObst
                else:
                    minRadius = distNei
                if (minRadius < BUFFER_DIST):
                    minRadius = BUFFER_DIST
                kernel = Kernel( minRadius, smoothParam, distFunc, self.cellSize )
                w, h = kernel.data.shape
                w /= 2
                h /= 2
            # END IF
            
            # Get position of the agent the world grid
            center = self.getCenter( Vector2(pos[0], pos[1]) )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            flipL = False
            flipR = False
            flipT = False
            flipB = False
            reflect = None
            if ( l < 0 ):
                flipL = True
                kl -= l
                l = 0
            if ( b < 0 ):
                flipB = True
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                flipR = True
                kr -= r - self.resolution[0]
                r = self.resolution[0]
                
            if ( t >= self.resolution[1] ):
                flipT = True
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            try:
               if ( l < r and b < t and kl < kr and kb < kt ):
                    # Convolution
                    self.reflectOverBoundary( flipL, flipR, flipT, flipB, kernel,
                                              (kl, kr, kb, kt),( l,r,b,t) )
                    self.cells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ]
            except ValueError, e:
                print "Value error!"
                print "\tAgent at", center
                print "\tGrid resolution:", self.resolution
                print "\tKernel size:", kernel.data.shape
                print "\tTrying rasterize [ %d:%d, %d:%d ] to [ %d:%d, %d:%d ]" % ( kl, kr, kb, kt, l, r, b, t)
                raise e

    def rasterizePosition2( self, frame, distFunc, maxRad ):
        """Given a frame of agents, rasterizes the whole frame"""
        kernel = Kernel2( maxRad, self.cellSize )
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        for agt in frame.agents:
            center = self.getCenter( agt.pos )
            centerWorld = Vector2( center[0] * self.cellSize[0] + self.minCorner[0],
                                   center[1] * self.cellSize[1] + self.minCorner[1] )
            kernel.instance( distFunc, centerWorld, agt.pos )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            self.cells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ]

##    def rasterizeStandard( self, frame, defineRegionX, defineRegionY ):
##        """ Compute density by countaing number of people in the region then divided by area of region
##        @param defineRegionX: a pair of minimum and maximum to define region in x axis
##        @param defineRegionY: a pair of center and width to define region in y axis"""
##        agentInRegion = 0
##        frame.shape = (1, frame.shape[0], frame.shape[1])
##        density = julichData.rhoOccupantEstimation( frame, [ defineRegionX ], defineRegionY[1], center=defineRegionY[0] )
##        regionBottom = self.getCenter( Vector2( defineRegionX[0], defineRegionY[0] - defineRegionY[1]* 0.5 ) )
##        regionTop = self.getCenter( Vector2( defineRegionX[1], defineRegionY[0] + defineRegionY[1]* 0.5 ) )
##        self.cells[ regionBottom[0]:regionTop[0], regionBottom[1]: regionTop[1] ] = density

                
    def rasterizeVoronoiDensity( self, frame, distFunc, smoothParam, densityGrid ):
        """ Compute density based on Voronoi density region and convolute with unifrom kernel """
        #densityGrid = Grid( self.minCorner, self.size, self.resolution, initVal=0.0 )
        kernelArea = np.sqrt( smoothParam * smoothParam )
        """ Function to convolute kernel over the density computed using Voronoi"""
        kernel = Kernel( smoothParam, None, distFunc, self.cellSize )
        # This assume the kernel dimensions are ODD-sized
        w, h = kernel.data.shape
        area = w * h
        w /= 2
        h /= 2

        
        # Independently convolute
        for i in xrange( 0, self.cells.shape[0] ):  
            for j in xrange( 0, self.cells.shape[1] ):
                l = i - w
                r = i + w + 1
                b = j - h
                t = j + h + 1
                kl = 0
                kb = 0
                kr, kt = kernel.data.shape
                if ( l < 0 ):
                    kl -= l
                    l = 0
                if ( b < 0 ):
                    kb -= b
                    b = 0
                if ( r >= self.resolution[0] ):
                    kr -= r - self.resolution[0]
                    r = self.resolution[0]
                if ( t >= self.resolution[1] ):
                    kt -= t - self.resolution[1]
                    t = self.resolution[1]
                try:
                    if ( l < r and b < t and kl < kr ):
                        # Convolution self.cells store density valued calculated based on Voronoi region
                        # if self.cells[i,j] is 0 then the multiplication will result in 0
                        density = (self.cells[ l:r, b:t ] * kernel.data[ kl:kr, 0:1 ])
                        density = (density.sum())/(1.)
                        densityGrid.cells[i, j] += density
                except ValueError, e:
                    print "Value error!"
                    print "\tAgent at", center
                    print "\tGrid resolution:", self.resolution
                    print "\tKernel size:", kernel.data.shape
                    print "\tTrying rasterize [ %d:%d, %d:%d ] to [ %d:%d, %d:%d ]" % ( kl, kr, kb, kt, l, r, b, t)
                    raise e
        # Independently convolute
        for i in xrange( 0, self.cells.shape[0] ):  
            for j in xrange( 0, self.cells.shape[1] ):
                l = i - w
                r = i + w + 1
                b = j - h
                t = j + h + 1
                kl = 0
                kb = 0
                kr, kt = kernel.data.shape
                if ( l < 0 ):
                    kl -= l
                    l = 0
                if ( b < 0 ):
                    kb -= b
                    b = 0
                if ( r >= self.resolution[0] ):
                    kr -= r - self.resolution[0]
                    r = self.resolution[0]
                if ( t >= self.resolution[1] ):
                    kt -= t - self.resolution[1]
                    t = self.resolution[1]
                try:
                    if ( l < r and b < t and kb < kt ):
                        # Convolution self.cells store density valued calculated based on Voronoi region
                        # if self.cells[i,j] is 0 then the multiplication will result in 0
                        density = (self.cells[ l:r, b:t ] * kernel.data[ 0:1, kb:kt ])
                        density = (density.sum())/(1.)
                        densityGrid.cells[i, j] += density
                except ValueError, e:
                    print "Value error!"
                    print "\tAgent at", center
                    print "\tGrid resolution:", self.resolution
                    print "\tKernel size:", kernel.data.shape
                    print "\tTrying rasterize [ %d:%d, %d:%d ] to [ %d:%d, %d:%d ]" % ( kl, kr, kb, kt, l, r, b, t)
                    raise e
    
    def rasterizeValue( self, frame, distFunc, maxRad ):
        """Given a frame of agents, rasterizes the whole frame"""
        kernel = Kernel( maxRad, distFunc, self.cellSize )
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        for agt in frame.agents:
            center = self.getCenter( agt.pos )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            self.cells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ] * agt.value            

    def rasterizeContribSpeed( self, kernel, f2, f1, distFunc, maxRad, timeStep ):
        """Given two frames of agents, computes per-agent displacement and rasterizes the whole frame"""
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        invDT = 1.0 / timeStep
        countCells = np.zeros_like( self.cells )
        maxSpd = 0
        for i in range( len ( f2.agents ) ):
            ag2 = f2.agents[ i ]
            ag1 = f1.agents[ i ]
            disp = ( ag2.pos - ag1.pos ).magnitude()
            disp *= invDT
            if ( disp > maxSpd ): maxSpd = disp
            center = self.getCenter( ag2.pos )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            self.cells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ] * disp
            countCells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ]
        countMask = countCells == 0
        countCells[ countMask ] = 1
        print "Counts: max", countCells.max(), "min:", countCells.min(),
        print "Accum max:", self.cells.max(), 
        self.cells /= countCells
        print "Max speed:", maxSpd, "max cell", self.cells.max()

    def rasterizeProgress( self, f2, initFrame, prevProgress, excludeStates=(), callBack=None ):
        '''Given the current frame and the initial frame, computes the fraction of the circle that
        each agent has travelled around the kaabah.'''
        # TODO: don't let this be periodic.
        TWO_PI = 2.0 * np.pi
        for i in range( len( f2.agents ) ):
            # first compute progress based on angle between start and current position
            ag2 = f2.agents[ i ]
            if ( ag2.state in excludeStates ): continue
            ag1 = initFrame.agents[ i ]
            dir2 = ag2.pos.normalize()
            dir1 = ag1.pos.normalize()
            angle = np.arccos( dir2.dot( dir1 ) )
            cross = dir1.det( dir2 )
            if ( cross < 0 ):
                angle = TWO_PI - angle
            progress = angle / TWO_PI

            # now determine direction from best progress so far
            
            if ( progress > prevProgress[i,2] ):
                best = Vector2( prevProgress[i,0], prevProgress[i,1] )
                cross = best.det( dir2 )
                if ( cross < 0 ):
                    # if I'm moving backwards from best progress BUT I'm apparently improving progress
                    #   I've backed over the 100% line.
                    progress = 0.0
                else:
                    prevProgress[ i, 2 ] = progress
                    prevProgress[ i, 0 ] = dir2[0]
                    prevProgress[ i, 1 ] = dir2[1]

            center = self.getCenter( ag2.pos )
            INFLATE = True # causes the agents to inflate more than a single cell
            if ( INFLATE ):
                l = center[0] - 1
                r = l + 3
                b = center[1] - 1
                t = b + 3
            else:
                l = center[0]
                r = l + 1
                b = center[1]
                t = b + 1
            
            if ( l < 0 ):
                l = 0
            if ( b < 0 ):
                b = 0
            if ( r >= self.resolution[0] ):
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                t = self.resolution[1]
            self.cells[ l:r, b:t ] =  progress
            if ( callBack ):
                callBack( progress )            

    def rasterizeSpeedBlit( self, kernel, f2, f1, distFunc, maxRad, timeStep, excludeStates=(), callBack=None, maxSpeed=2.5 ):
        """Given two frames of agents, computes per-agent displacement and rasterizes the whole frame"""
        invDT = 1.0 / timeStep
        # compute speeds
        disp = f2[:, :2] - f1[:,:2]
        speed = np.sqrt( np.sum( disp * disp, axis = 1 ) ) * invDT
        tooFast = speed > maxSpeed
        if ( np.sum( tooFast ) > 0 ):
            topSpeed = speed[ ~tooFast ]
            speed[ tooFast ] = topSpeed
        for i in xrange( f2.shape[0] ):
            if ( excludeStates ):
                pass

            p = Vector2( f2[i, 0], f2[i, 1] )
            center = self.getCenter( p )

            INFLATE = True # causes the agents to inflate more than a single cell
            if ( INFLATE ):
                l = center[0] - 1
                r = l + 3
                b = center[1] - 1
                t = b + 3
            else:
                l = center[0]
                r = l + 1
                b = center[1]
                t = b + 1

            # outside
            if ( l >= self.resolution[0] or r < 0 or
                 b >= self.resolution[1] or t < 0 ):
                continue
            # clip            
            if ( l < 0 ):
                l = 0
            if ( b < 0 ):
                b = 0
            if ( r >= self.resolution[0] ):
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                t = self.resolution[1]
            self.cells[ l:r, b:t ] =  speed[i]
            if ( callBack ):
                callBack( speed[i] )

    def rasterizeOmegaBlit( self, kernel, f2, f1, distFunc, maxRad, timeStep, excludeStates=(), callBack=None ):
        """Given two frames of agents, computes per-agent angular speed and rasterizes the whole frame"""
        invDT = 1.0 / timeStep
        RAD_TO_ANGLE = 180.0 / np.pi * invDT
        for i in range( len ( f2.agents ) ):
            # compute the angle around the origin
            ag2 = f2.agents[ i ]
            if ( ag2.state in excludeStates ): continue
            ag1 = f1.agents[ i ]
            dir2 = ag2.pos.normalize()
            dir1 = ag1.pos.normalize()
            angle = np.arccos( dir2.dot( dir1 ) ) * RAD_TO_ANGLE
            cross = dir1.det( dir2 )
            if ( cross < 0 ):
                angle = -angle
                
            center = self.getCenter( ag2.pos )
            INFLATE = True # causes the agents to inflate more than a single cell
            if ( INFLATE ):
                l = center[0] - 1
                r = l + 3
                b = center[1] - 1
                t = b + 3
            else:
                l = center[0]
                r = l + 1
                b = center[1]
                t = b + 1
            
            if ( l < 0 ):
                l = 0
            if ( b < 0 ):
                b = 0
            if ( r >= self.resolution[0] ):
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                t = self.resolution[1]
            self.cells[ l:r, b:t ] =  angle
            if ( callBack ):
                callBack( angle )

    def rasterizeDenseSpeed( self, denseFile, kernel, f2, f1, distFunc, maxRad, timeStep ):
        '''GIven two frames of agents, computes per-agent speed and rasterizes the whole frame.agents
        Divides the rasterized speeds by density from the denseFile'''
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        invDT = 1.0 / timeStep
        countCells = np.zeros_like( self.cells )
        maxSpd = 0
        for i in range( len ( f2.agents ) ):
            ag2 = f2.agents[ i ]
            ag1 = f1.agents[ i ]
            disp = ( ag2.pos - ag1.pos ).magnitude()
            disp *= invDT
            if ( disp > maxSpd ): maxSpd = disp
            center = self.getCenter( ag2.pos )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            self.cells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ] * disp
        dataStr = denseFile.read( self.resolution[0] * self.resolution[1] * 4 ) # total floats X 4 bytes per float
        density = np.fromstring( dataStr, dtype=np.float32 )
##        density[ density == 0 ] = 1
        density = density.reshape( self.cells.shape )
##        density[ density == 0 ] = 1
        print "Density: max", density.max(), "min:", density.min(),
        print "Accum max:", self.cells.max(), 
##        self.cells /= density
        print "Max speed:", maxSpd, "max cell", self.cells.max()
        
    def rasterizeSpeedGauss( self, kernel, f2, f1, distFunc, maxRad, timeStep, maxSpeed=2.5 ):
        """Given two frames of agents, computes per-agent displacement and rasterizes the whole frame"""
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        invDT = 1.0 / timeStep
        for i in range( len ( f2.agents ) ):
            ag2 = f2.agents[ i ]
            ag1 = f1.agents[ i ]
            disp = ( ag2.pos - ag1.pos ).magnitude()
            disp *= invDT
            center = self.getCenter( ag2.pos )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= b
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            self.cells[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ] * disp

    def rasterizeVelocity( self, X, Y, kernel, f2, f1, distFunc, maxRad, timeStep, maxSpeed=2.5 ):
        """Given two frames of agents, computes per-agent displacement and rasterizes the whole frame"""
        w, h = kernel.data.shape
        w /= 2
        h /= 2
        invDT = 1.0 / timeStep
        X.fill( 0.0 )
        Y.fill( 0.0 )
        for i in range( len ( f2.agents ) ):
            ag2 = f2.agents[ i ]
            ag1 = f1.agents[ i ]
            disp = ag2.pos - ag1.pos
            disp *= invDT
            center = self.getCenter( ag2.pos )
            l = center[0] - w
            r = center[0] + w + 1
            b = center[1] - h
            t = center[1] + h + 1
            kl = 0
            kb = 0
            kr, kt = kernel.data.shape
            if ( l < 0 ):
                kl -= l
                l = 0
            if ( b < 0 ):
                kb -= bvRe
                b = 0
            if ( r >= self.resolution[0] ):
                kr -= r - self.resolution[0]
                r = self.resolution[0]
            if ( t >= self.resolution[1] ):
                kt -= t - self.resolution[1]
                t = self.resolution[1]
            X[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ] * disp[0]
            Y[ l:r, b:t ] += kernel.data[ kl:kr, kb:kt ] * disp[1]
        self.cells = X + Y
        #self.cells = np.sqrt( X * X + Y * Y )

    def swapValues( self, oldVal, newVal ):
        """Replaces all cells with the value oldVal with newVal"""
        self.cells[ self.cells == oldVal ] = newVal

    def clampMax( self, maxValue ):
        '''Makes sure that the grid contains no value greater than maxValue'''
        self.cells[ self.cells > maxValue ] = maxValue