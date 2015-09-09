# The interactive context for editing goals

from RoadContext import PGContext, MouseEnabled, PGMouse
from Context import BaseContext, ContextResult
import pygame
from OpenGL.GL import *
import GoalEditor
import Goals
import paths
import xml.dom as dom
from math import sqrt

class GoalContext( PGContext, MouseEnabled ):
    '''A context for drawing goal regions (for now just AABB)'''
    #TODO: Add other goal types
    HELP_TEXT = 'Goal Context' + \
                '\n\tWork with Goals and GoalSets' + \
                '\n' + \
                '\n\tLeft arrow         Select previous goal set' + \
                '\n\tRight arrow        Select next goal set' + \
                '\n\tCtrl-s             Save goal sets to "goals.xml"' + \
                '\n\tCtrl-n             Create new goal set' + \
                '\n\tCtrl-delete        Delete current goal set (and all goals)' + \
                '\n\tCtrl-x             Delete highlighted goal' + \
                '\n\tLeft click         Begin editing active goal' + \
                '\n\tp                  Create point goals' + \
                '\n\t\tLeft click       In empty space to create a point goal' +\
                '\n\t\tLeft drag        To move highlighted point goal' +\
                '\n\tc                  Create circle goals' + \
                '\n\t\tLeft click       In empty space to create a circle goal' + \
                '\n\t\tLeft click       On highlighted circle goal to begin editing' + \
                '\n\t\tLeft drag        On circle center to move' + \
                '\n\t\tLeft drag        On circle permiter to change radius' + \
                '\n\t\tLeft click       In empty space to stop editing' + \
                '\n\t\tRight click      To cancel move/radius operation or end editing' + \
                '\n\ta                  Create AABB goals' + \
                '\n\t\tLeft drag        In empty space to draw a new AABB goal' + \
                '\n\t\tLeft click       On highlighted AABB to edit' + \
                '\n\t\tLeft drag        On highlighted corner to reshape AABB' + \
                '\n\t\tLeft drag        Inside to move the AABB' + \
                '\n\t\tLeft click       In empty space to stop editing' + \
                '\n\t\tRight click      To cancel movement of AABB corner or end editing' + \
                '\n\to                 Create OBB goals' + \
                '\n\t\tLeft drag        In empty space to draw a new OBB goal' + \
                '\n\t\tLeft click       On highlighted OBB to edit' + \
                '\n\t\tLeft drag        Inside to move OBB' + \
                '\n\t\tLeft drag        On red corner to resize OBB' + \
                '\n\t\tLeft drag        On blue corner to reorient OBB' + \
                '\n\t\tLeft click       In empty space to stop editing' + \
                '\n\t\tRight click      To cancel movement of OBB corner or end editing' + \
                ''
    # state for acting on goal sets
    POINT = 1
    CIRCLE = 2
    AABB = 4
    OBB = 8
    CREATE = 0xf
    EDIT_POINT = 0x10
    EDIT_CIRCLE = 0x60
    MOVE_CIRCLE = 0x40
    SIZE_CIRCLE = 0x20
    EDIT_AABB = 0x380
    MIN_AABB = 0x80
    MAX_AABB = 0x100
    MOVE_AABB = 0x200
    EDIT_OBB = 0x1C00
    MOVE_OBB = 0x400
    SIZE_OBB = 0x800
    TURN_OBB = 0x1000

    STATE_NAMES = { POINT:'point', CIRCLE:'circle', AABB:'AABB', OBB:'OBB',
                    EDIT_POINT:'point', EDIT_CIRCLE:'circle', EDIT_AABB:'AABB', EDIT_OBB:'OBB',
                    MOVE_CIRCLE:'circle', SIZE_CIRCLE:'circle',
                    MIN_AABB:'AABB', MAX_AABB:'AABB', MOVE_AABB:'AABB',
                    MOVE_OBB:'OBB', SIZE_OBB:'OBB', TURN_OBB:'OBB'
                    }    
    
    def __init__( self, goalEditor ):
        '''Constructor.

        @param      goalEditor       The GoalEditor instance
        '''
        PGContext.__init__( self )
        MouseEnabled.__init__( self )

        self.goalEditor = goalEditor
        self.state = self.POINT
        self.editGoal = None

        self.lastActive = 0
        
    def activate( self ):
        '''Called when the set gets activated'''
        self.goalEditor.editSet = self.lastActive
        self.goal = None
        
    def deactivate( self ):
        '''Called when the set gets activated'''
        self.lastActive = self.goalEditor.editSet
        self.goalEditor.editSet = -1
        self.stopEditing()
        
        
    def setState( self, newState ):
        '''Sets the contexts new activity state'''
        if ( self.state != newState ):
            self.state = newState
        
    def handleKeyboard( self, event, view ):
        """The context handles the keyboard event as it sees fit and reports it's status with a ContextResult.

        @param      event       The keyboard event.
        @param      view        An instance of the opengl viewer.
        """
        result = PGContext.handleKeyboard( self, event, view )
        
        if ( not result.isHandled() ):
            mods = pygame.key.get_mods()
            hasCtrl = mods & pygame.KMOD_CTRL
            hasAlt = mods & pygame.KMOD_ALT
            hasShift = mods & pygame.KMOD_SHIFT
            noMods = not( hasShift or hasCtrl or hasAlt )

            if ( event.type == pygame.KEYDOWN ):
                if ( event.key == pygame.K_RIGHT and noMods ):
                    oldActive = self.goalEditor.editSet
                    self.goalEditor.editSet = ( self.goalEditor.editSet + 1 ) % self.goalEditor.setCount()
                    self.stopEditing()
                    result.set( True, oldActive != self.goalEditor.editSet )
                elif ( event.key == pygame.K_LEFT and noMods ):
                    oldActive = self.goalEditor.editSet
                    self.goalEditor.editSet = ( self.goalEditor.editSet -  1 ) % self.goalEditor.setCount()
                    self.stopEditing()
                    result.set( True, oldActive != self.goalEditor.editSet )
                elif ( event.key == pygame.K_s and hasCtrl ):
                    self.saveGoals()
                    result.set( True, False )
                elif ( event.key == pygame.K_n and hasCtrl ):
                    self.goalEditor.editSet = self.goalEditor.newSet()
                    result.set( True, True )
                elif ( event.key == pygame.K_DELETE and hasCtrl ):
                    self.goalEditor.deleteSet( self.goalEditor.editSet )
                    self.goalEditor.editSet = self.goalEditor.editSet % self.goalEditor.setCount()
                    result.set( True, True )
                elif ( event.key == pygame.K_x and hasCtrl ):
                    if ( self.goalEditor.activeGoal > -1 ):
                        self.goalEditor.deleteGoal( self.goalEditor.editSet, self.goalEditor.activeGoal )
                        self.stopEditing()
                        result.set( True, True )
                elif ( event.key == pygame.K_p and noMods ):
                    result.set( True, self.state != self.POINT )
                    self.setState( self.POINT )
                elif ( event.key == pygame.K_c and noMods ):
                    result.set( True, self.state != self.CIRCLE )
                    self.setState( self.CIRCLE )
                elif ( event.key == pygame.K_a and noMods ):
                    result.set( True, self.state != self.AABB )
                    self.setState( self.AABB )
                elif ( event.key == pygame.K_o and noMods ):
                    result.set( True, self.state != self.OBB )
                    self.setState( self.OBB )
                # TODO:
                #   Set goal weight
                #   Set goal capacity
        return result        

    def stopEditing( self ):
        '''Changes the edit state to its corresponding creation state'''
        if ( not self.state & self.CREATE ):
            self.editGoal = None
            self.goalEditor.activeGoal = -1
                    
            if ( self.state & self.EDIT_AABB ):
                self.state = self.AABB
            elif ( self.state & self.EDIT_CIRCLE ):
                self.state = self.CIRCLE
            elif ( self.state & self.EDIT_POINT ):
                self.state = self.POINT
            elif ( self.state & self.EDIT_OBB ):
                self.state = self.OBB
    
    def saveGoals( self, fileName='goals.txt' ):
        '''Saves the goals to the specified file.

        @param      fileName        The name to write the goals to.
        '''
        Goals.DIGITS = 2
        path = paths.getPath( fileName, False )
        print "Writing goals to:", path
        f = open( path, 'w' )
        f.write ('''<?xml version="1.0"?>
<Population >
''')
        for gs in self.goalEditor:
            node = gs.xmlElement()
            if ( node ):
                node.writexml( f, indent='    ', addindent='    ', newl='\n' )
        f.write( '\n</Population>' )
        f.close()

    def handleMouse( self, event, view ):
        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult

        @param      event       The mouse event.
        @param      view        An instance of the opengl viewer.
        """
        result = ContextResult()
        
        mods = pygame.key.get_mods()
        hasCtrl = mods & pygame.KMOD_CTRL
        hasAlt = mods & pygame.KMOD_ALT
        hasShift = mods & pygame.KMOD_SHIFT
        noMods = not( hasShift or hasCtrl or hasAlt )

        if ( noMods ):
            if ( event.type == pygame.MOUSEMOTION ):
                if ( self.state & self.CREATE ):
                    result.setHandled( True )
                    pX, pY = event.pos
                    selID = view.select( pX, pY, self.goalEditor )
                    result.setNeedsRedraw( selID != self.goalEditor.activeGoal )
                    self.goalEditor.activeGoal = selID
                elif ( self.state == self.EDIT_POINT ):
                    pX, pY = view.screenToWorld( event.pos )
                    self.editGoal.set( pX, pY )
                    result.set( True, True )
                elif ( self.state & self.EDIT_CIRCLE ):
                    result.setHandled( True )
                    if ( self.dragging ):
                        dX, dY = view.screenToWorld( event.pos )
                        if ( self.state == self.MOVE_CIRCLE ):
                            dx = dX - self.downWorld[ 0 ]
                            dy = dY - self.downWorld[ 1 ]
                            self.editGoal.setPos( dx + self.tempValue[0],
                                                  dy + self.tempValue[1] )
                        elif ( self.state == self.SIZE_CIRCLE ):
                            dX -= self.editGoal.p.x
                            dY -= self.editGoal.p.y
                            r = sqrt( dX * dX + dY * dY )
                            self.editGoal.setRadius( r )
                        result.set( True, True )
                    else:
                        result.setNeedsRedraw( self.setCircleEdit( event.pos, view ) )
                elif ( self.state & self.EDIT_AABB ):
                    result.setHandled( True )
                    if ( self.dragging ):
                        x, y = view.screenToWorld( event.pos )
                        if ( self.state == self.MIN_AABB ):
                            self.editGoal.setMin( x, y )
                        elif ( self.state == self.MAX_AABB ):
                            self.editGoal.setMax( x, y )
                        elif ( self.state == self.MOVE_AABB ):
                            dx = x - self.downWorld[ 0 ]
                            dy = y - self.downWorld[ 1 ]
                            self.editGoal.set( dx + self.tempValue[0],
                                               dy + self.tempValue[1],
                                               dx + self.tempValue[2],
                                               dy + self.tempValue[3] )
                            
                        result.set( True, True )
                    else:
                        result.setNeedsRedraw( self.setAABBEdit( event.pos, view ) )
                elif ( self.state & self.EDIT_OBB ):
                    result.setHandled( True )
                    if ( self.dragging ):
                        x, y = view.screenToWorld( event.pos )
                        if ( self.state == self.MOVE_OBB ):
                            dx = x - self.downWorld[ 0 ]
                            dy = y - self.downWorld[ 1 ]
                            self.editGoal.setPivot( dx + self.tempValue[0], dy + self.tempValue[1] )
                        elif ( self.state == self.SIZE_OBB ):
                            self.editGoal.setOppositeCorner( x, y )
                        elif ( self.state == self.TURN_OBB ):
                            self.editGoal.aim( x, y )                            
                        result.set( True, True )
                    else:
                        result.setNeedsRedraw( self.setOBBEdit( event.pos, view ) )
            elif ( event.type == pygame.MOUSEBUTTONDOWN ):
                if ( event.button == PGMouse.LEFT ):
                    self.cacheDownClick( event.pos, view.screenToWorld( event.pos ) )
                    if ( self.goalEditor.activeGoal > -1 ):
                        self.startEdit( view )
                        result.set( True, True )
                    else:
                        self.startCreate( view )
                        result.set( True, True )
                elif ( event.button == PGMouse.RIGHT ):
                    if ( self.state == self.EDIT_POINT ):
                        self.editGoal.set( self.tempValue[0], self.tempValue[1] )
                        self.editGoal = None
                        self.goalEditor.activeGoal = -1
                        self.state = self.POINT
                        result.set( True, True )
                    elif ( self.state & self.EDIT_CIRCLE ):
                        if ( self.state == self.EDIT_CIRCLE ):
                            self.editGoal = None
                            self.goalEditor.activeGoal = -1
                            self.state = self.CIRCLE
                        elif ( self.state != self.EDIT_CIRCLE ):
                            self.editGoal.set( self.tempValue[0], self.tempValue[1], self.tempValue[2] )
                            self.state = self.EDIT_CIRCLE
                            self.dragging = False
                        result.set( True, True )
                    elif ( self.state & self.EDIT_AABB ):
                        if ( self.state == self.EDIT_AABB ):
                            self.editGoal = None
                            self.goalEditor.activeGoal = -1
                            self.state = self.AABB
                        elif ( self.state != self.EDIT_AABB ):
                            self.editGoal.set( self.tempValue[0], self.tempValue[1], self.tempValue[2], self.tempValue[3] )
                            self.state = self.EDIT_AABB
                            self.dragging = False
                        result.set( True, True )
                    elif ( self.state & self.EDIT_OBB ):
                        if ( self.state == self.EDIT_OBB ):
                            self.editGoal = None
                            self.goalEditor.activeGoal = -1
                            self.state = self.OBB
                        elif ( self.state != self.EDIT_OBB ):
                            self.editGoal.set( self.tempValue[0], self.tempValue[1], self.tempValue[2], self.tempValue[3], self.tempValue[4] )
                            self.state = self.EDIT_OBB
                            self.dragging = False
                        result.set( True, True )
            elif ( event.type == pygame.MOUSEBUTTONUP ):
                if ( event.button == PGMouse.LEFT ):
                    if ( self.state == self.EDIT_POINT ):
                        self.state = self.POINT
                        result.set( True, True )
                    elif ( self.state & self.EDIT_CIRCLE and self.state != self.EDIT_CIRCLE ):
                        self.state = self.EDIT_CIRCLE
                        self.dragging = False
                        result.set( True, True )
                    elif ( self.state & self.EDIT_AABB and self.state != self.EDIT_AABB ):
                        self.editGoal.fixPoints()
                        self.state = self.EDIT_AABB
                        self.dragging = False
                        result.set( True, True )
                    elif ( self.state & self.EDIT_OBB and self.state != self.EDIT_OBB ):
                        self.editGoal.fix()
                        self.state = self.EDIT_OBB
                        self.dragging = False
                        result.set( True, True )
        return result

    def cacheDownClick( self, screenPos, worldPos ):
        '''Caches the down click position.

        @param      screenPos       A 2-tuple of ints.  The screenspace position of the mouse.
        @param      worldPos        A 2-tuple of flaots.  The worldspace position of the mouse.
        '''
        self.downX, self.downY = screenPos
        self.downWorld = worldPos
        
    def startCreate( self, view ):
        '''Sets the state of the context to begin editing the active goal.

        @param      view        A pointer to the OpenGL viewer.
        '''
        if ( self.state == self.POINT ):
            self.editGoal = Goals.PointGoal()
            self.editGoal.set( self.downWorld[0], self.downWorld[1] )
            self.goalEditor.activeGoal = self.goalEditor.addGoal( self.goalEditor.editSet, self.editGoal )
            self.startEdit( view )
        elif ( self.state == self.CIRCLE ):
            self.editGoal = Goals.CircleGoal()
            self.editGoal.set( self.downWorld[0], self.downWorld[1], 0.0 )
            self.goalEditor.activeGoal = self.goalEditor.addGoal( self.goalEditor.editSet, self.editGoal )
            self.startEdit( view )
        elif ( self.state == self.AABB ):
            self.editGoal = Goals.AABBGoal()
            self.editGoal.set( self.downWorld[0], self.downWorld[1], self.downWorld[0], self.downWorld[1] )
            self.goalEditor.activeGoal = self.goalEditor.addGoal( self.goalEditor.editSet, self.editGoal )
            self.state = self.AABB
            self.startEdit( view )
        elif ( self.state == self.OBB ):
            self.editGoal = Goals.OBBGoal()
            self.editGoal.set( self.downWorld[0], self.downWorld[1], 0.0, 0.0, 0.0 )
            self.goalEditor.activeGoal = self.goalEditor.addGoal( self.goalEditor.editSet, self.editGoal )
            self.state = self.OBB
            self.startEdit( view )

    def startEdit( self, view ):
        '''Sets the state of the context to begin editing the active goal.

        @param      view        A pointer to the OpenGL viewer.
        '''
        self.editGoal = self.goalEditor.getGoal( self.goalEditor.editSet, self.goalEditor.activeGoal )
        if ( isinstance( self.editGoal, Goals.CircleGoal ) ):
            self.setCircleEdit( (self.downX, self.downY ), view, True )
            if ( self.state & self.EDIT_CIRCLE and self.state != self.EDIT_CIRCLE ):
                self.tempValue = ( self.editGoal.p.x, self.editGoal.p.y, self.editGoal.r )
                self.dragging = True
        elif ( isinstance( self.editGoal, Goals.PointGoal ) ):
            self.tempValue = ( self.editGoal.p.x, self.editGoal.p.y )
            self.state = self.EDIT_POINT
        elif ( isinstance( self.editGoal, Goals.AABBGoal ) ):
            self.setAABBEdit( (self.downX, self.downY ), view, self.state == self.EDIT_AABB )
            if ( self.state & self.EDIT_AABB and self.state != self.EDIT_AABB ):
                self.tempValue = ( self.editGoal.minPt.x, self.editGoal.minPt.y, self.editGoal.maxPt.x, self.editGoal.maxPt.y )
                self.dragging = True
        elif ( isinstance( self.editGoal, Goals.OBBGoal ) ):
            self.setOBBEdit( (self.downX, self.downY ), view, self.state == self.EDIT_OBB )
            if ( self.state & self.EDIT_OBB and self.state != self.EDIT_OBB ):
                self.tempValue = ( self.editGoal.pivot.x, self.editGoal.pivot.y, self.editGoal.size.x, self.editGoal.size.y, self.editGoal.angle )
                self.dragging = True

    def setCircleEdit( self, mousePos, view, missDeselect=False ):
        '''Sets the circle state based on the current mouse position.

        @param      mousePos        A 2-tuple of ints. The screen space coordinates of the mouse.
        @param      view            A pointer to the OpenGL viewer.
        @param      missDeselect    If the mouse isn't near the center or radius, then it deselects
                                    the active object.
        @returns    A boolean if the edit state changed.
        '''
        cX, cY = view.worldToScreen( ( self.editGoal.p.x, self.editGoal.p.y ) )
        rX, rY = view.worldToScreen( ( self.editGoal.r + self.editGoal.p.x, self.editGoal.p.y ) )
        radS = rX - cX
        dX = mousePos[0] - cX
        dY = mousePos[1] - cY
        distSqd = dX * dX + dY * dY
        dist = sqrt( distSqd )
        delta = abs( dist - radS )
        if ( delta < 7 ):
            changed = self.state != self.SIZE_CIRCLE
            self.state = self.SIZE_CIRCLE
        else:
            changed = False
            if ( dist < radS ):
                changed = self.state != self.MOVE_CIRCLE
                self.state = self.MOVE_CIRCLE
            else:
                if ( missDeselect ):
                    changed = True
                    self.state = self.CIRCLE
                    self.editGoal = None
                    self.goalEditor.activeGoal = -1
                else:
                    changed =  self.state != self.EDIT_CIRCLE 
                    self.state = self.EDIT_CIRCLE
        return changed

    def setAABBEdit( self, mousePos, view, missDeselect=False ):
        '''Sets the AABB state based on the current mouse position.

        @param      mousePos        A 2-tuple of ints. The screen space coordinates of the mouse.
        @param      view            A pointer to the OpenGL viewer.
        @param      missDeselect    If True and the mouse isn't near the min or max corners, 
                                    then it deselects the active object.
        @returns    A boolean if the edit state changed.
        '''
        cX, cY = view.worldToScreen( ( self.editGoal.minPt.x, self.editGoal.minPt.y ) )
        dX = mousePos[0] - cX
        dY = mousePos[1] - cY
        distSqd = dX * dX + dY * dY
        changed = False
        if ( distSqd < 49 ):
            changed = self.state != self.MIN_AABB
            self.state = self.MIN_AABB
        else:
            cX, cY = view.worldToScreen( ( self.editGoal.maxPt.x, self.editGoal.maxPt.y ) )
            dX = mousePos[0] - cX
            dY = mousePos[1] - cY
            distSqd = dX * dX + dY * dY
            if ( distSqd < 49 ):
                changed = self.state != self.MAX_AABB
                self.state = self.MAX_AABB
            else:
                # determine if it is within the distance of the segments
                worldPos = view.screenToWorld( mousePos )
                if ( self.editGoal.isInside( worldPos ) ):
                    changed = self.state != self.MOVE_AABB
                    self.state = self.MOVE_AABB
                else:
                    if ( missDeselect ):
                        changed = True
                        self.state = self.AABB
                        self.editGoal = None
                        self.goalEditor.activeGoal = -1
                    else:
                        changed =  self.state != self.EDIT_AABB
                        self.state = self.EDIT_AABB
        return changed    
   
    def setOBBEdit( self, mousePos, view, missDeselect=False ):
        '''Sets the OBB state based on the current mouse position.

        @param      mousePos        A 2-tuple of ints. The screen space coordinates of the mouse.
        @param      view            A pointer to the OpenGL viewer.
        @param      missDeselect    If True and the mouse isn't near the min or max corners, 
                                    then it deselects the active object.
        @returns    A boolean if the edit state changed.
        '''
        opp = self.editGoal.oppositeCorner()
        cX, cY = view.worldToScreen( opp )
        dX = mousePos[0] - cX
        dY = mousePos[1] - cY
        distSqd = dX * dX + dY * dY
        changed = False
        if ( distSqd < 49 ):
            changed = self.state != self.SIZE_OBB
            self.state = self.SIZE_OBB
        else:
            adj = self.editGoal.adjacentCorner()
            cX, cY = view.worldToScreen( adj )
            dX = mousePos[0] - cX
            dY = mousePos[1] - cY
            distSqd = dX * dX + dY * dY
            if ( distSqd < 49 ):
                changed = self.state != self.TURN_OBB
                self.state = self.TURN_OBB
            else:
                # determine if it is within the distance of the segments
                worldPos = view.screenToWorld( mousePos )
                if ( self.editGoal.isInside( worldPos ) ):
                    changed = self.state != self.MOVE_OBB
                    self.state = self.MOVE_OBB
                else:
                    if ( missDeselect ):
                        changed = True
                        self.state = self.OBB
                        self.editGoal = None
                        self.goalEditor.activeGoal = -1
                    else:
                        changed =  self.state != self.EDIT_OBB
                        self.state = self.EDIT_OBB
        return changed    
   
    def drawGL( self, view ):
        '''Draws the current rectangle to the open gl context'''
        PGContext.drawGL( self, view )

        view.printText( 'Creating %s goals' % self.STATE_NAMES[ self.state ], ( 10, 45 ) )        
        view.printText( "%d goals in %d sets" % ( self.goalEditor.goalCount(), self.goalEditor.setCount() ), (20,30) )
        if ( self.goalEditor.activeGoal != -1 ):
            g = self.goalEditor[ self.goalEditor.editSet ][ self.goalEditor.activeGoal ]
            area = g.area()
            view.printText( "Goal %d area: %f m^2" % ( g.id, area ), (20, 0) )
        gs = self.goalEditor[ self.goalEditor.editSet ]
        msg = 'Goal set %d with %d goals' % ( gs.id, len(gs) )
        view.printText( msg, (20, 15) )

        # special display for editing
        if ( self.editGoal ):
            glPushAttrib( GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT | GL_POINT_BIT | GL_LINE_BIT )
            glDisable( GL_DEPTH_TEST )
            glPointSize( 5 )
            glLineWidth( 3 )
            glColor4f( 0.7, 0.7, 0.1, 0.25 )
            if ( self.state & self.EDIT_CIRCLE ):
                if ( self.state == self.SIZE_CIRCLE ):
                    glLineWidth( 4 )
                    GoalEditor.drawCircleGoal( self.editGoal )
            elif ( self.state & self.EDIT_AABB ):
                if ( self.state == self.MIN_AABB ):
                    glPointSize( 7 )
                else:
                    glPointSize( 4 )
                glBegin( GL_POINTS )
                glVertex3f( self.editGoal.minPt.x, self.editGoal.minPt.y, 0.0 )
                glEnd()
                if ( self.state == self.MAX_AABB ):
                    glPointSize( 7 )
                else:
                    glPointSize( 4 )
                glBegin( GL_POINTS )
                glVertex3f( self.editGoal.maxPt.x, self.editGoal.maxPt.y, 0.0 )
                glEnd()
            elif ( self.state & self.EDIT_OBB ):
                # size widget
                if ( self.state == self.SIZE_OBB ):
                    glPointSize( 7 )
                else:
                    glPointSize( 4 )
                glColor3f( 1.0, 0.0, 0.0 )
                opp = self.editGoal.oppositeCorner()
                glBegin( GL_POINTS )
                glVertex3f( opp[0], opp[1], 0.0 )
                glEnd()

                # turn corner                
                if ( self.state == self.TURN_OBB ):
                    glPointSize( 7 )
                else:
                    glPointSize( 4 )
                glColor3f( 0.1, 0.1, 1.0 )
                adj = self.editGoal.adjacentCorner()
                glBegin( GL_POINTS )
                glVertex3f( adj[0], adj[1], 0.0 )
                glEnd()

            glPopAttrib()

