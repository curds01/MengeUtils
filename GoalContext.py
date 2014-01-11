# The interactive context for editing goals

from RoadContext import PGContext, MouseEnabled, PGMouse
from Context import BaseContext, ContextResult
import pygame
from OpenGL.GL import *
import Goals
import paths
import xml.dom as dom

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
                '\n\tDown click on one corner, drag to opposite corner' + \
                '\n\tGoal region definition will be printed to console' + \
                '\n\tupon mouse release.'

    def __init__( self, goalEditor ):
        '''Constructor.

        @param      goalEditor       The GoalEditor instance
        '''
        PGContext.__init__( self )
        MouseEnabled.__init__( self )

        self.goalEditor = goalEditor
        self.lastActive = 0
        
        self.p0 = None
        self.p1 = None
        self.goalID = 0

        self.history = []

    def activate( self ):
        '''Called when the set gets activated'''
        self.goalEditor.editSet = self.lastActive
        
    def deactivate( self ):
        '''Called when the set gets activated'''
        self.lastActive = self.goalEditor.editSet
        self.goalEditor.editSet = -1
        
    def handleKeyboard( self, event, view ):
        """The context handles the keyboard event as it sees fit and reports it's status with a ContextResult"""
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
                    result.set( True, oldActive != self.goalEditor.editSet )
                elif ( event.key == pygame.K_LEFT and noMods ):
                    oldActive = self.goalEditor.editSet
                    self.goalEditor.editSet = ( self.goalEditor.editSet -  1 ) % self.goalEditor.setCount()
                    result.set( True, oldActive != self.goalEditor.editSet )
                elif ( event.key == pygame.K_s and hasCtrl ):
                    self.saveGoals()
                    result.set( True, False )
                elif ( event.key == pygame.K_n and hasCtrl ):
                    self.goalEditor.editSet = self.goalEditor.newGoalSet()
                    result.set( True, True )
        return result        

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

        
##    def handleMouse( self, event, view ):
##        """The context handles the mouse event as it sees fit and reports it's status with a ContextResult"""
##        result = ContextResult()
##        
##        mods = pygame.key.get_mods()
##        hasCtrl = mods & pygame.KMOD_CTRL
##        hasAlt = mods & pygame.KMOD_ALT
##        hasShift = mods & pygame.KMOD_SHIFT
##        noMods = not( hasShift or hasCtrl or hasAlt )
##
##        if ( noMods ):
##            if ( event.type == pygame.MOUSEBUTTONDOWN ):
##                if ( event.button == PGMouse.LEFT ):
##                    self.downX, self.downY = event.pos
##                    self.p0 = view.screenToWorld( ( self.downX, self.downY ) )
##                    self.dragging = True
##                    result.setHandled( True )
##                elif ( event.button == PGMouse.RIGHT and self.dragging ):
##                    self.dragging = False
##                    self.p0 = self.p1 = None
##                    result.set( True, True )
##            elif ( event.type == pygame.MOUSEMOTION and self.dragging ):
##                self.downX, self.downY = event.pos
##                self.p1 = view.screenToWorld( ( self.downX, self.downY ) )
##                result.set( True, True )
##            elif ( event.type == pygame.MOUSEBUTTONUP ):
##                if ( event.button == PGMouse.LEFT and self.dragging ):
##                    self.printGoalBox()
##                    self.dragging = False
##                    result.set( True, True )
##
##        return result

##    def printGoalBox( self ):
##        '''Writes the goal box xml definition to the console'''
##        # print xml
##        if ( not ( self.p0 is None or self.p1 is None ) ):
##            s = '<Goal type="AABB" id="{0}" xmin="{1:.3f}" xmax="{2:.3}" ymin="{3:.3f}" ymax="{4:.3f}" />'.format(
##                self.goalID,
##                min( self.p0[0], self.p1[0] ),
##                max( self.p0[0], self.p1[0] ),
##                min( self.p0[1], self.p1[1] ),
##                max( self.p0[1], self.p1[1] )
##                )
##            self.history.append( ( self.p0, self.p1 ) )
##            print s
##            self.goalID += 1
##            self.p0 = self.p1 = None
    
    def drawGL( self, view ):
        '''Draws the current rectangle to the open gl context'''
        PGContext.drawGL( self, view )
        view.printText( "%d goals in %d sets" % ( self.goalEditor.goalCount(), self.goalEditor.setCount() ), (10,30) )
        gs = self.goalEditor[ self.goalEditor.editSet ]
        msg = 'Goal set %d with %d goals' % ( gs.id, len(gs) )
        view.printText( msg, (15, 15) )
##        if ( self.history ):
##            glPushAttrib( GL_COLOR_BUFFER_BIT | GL_LINE_BIT )
##            glColor3f( 0.1, 0.5, 0.0 )
##            glLineWidth( 2.0 )
##            for p0, p1 in self.history:
##                glBegin( GL_LINE_LOOP )
##                glVertex3f( p0[0], p0[1], 0.0 )
##                glVertex3f( p1[0], p0[1], 0.0 )
##                glVertex3f( p1[0], p1[1], 0.0 )
##                glVertex3f( p0[0], p1[1], 0.0 )
##                glEnd()
##            
##            glPopAttrib()
                
        if ( not ( self.p0 is None or self.p1 is None ) ):
            glPushAttrib( GL_COLOR_BUFFER_BIT | GL_LINE_BIT )
            glColor3f( 1.0, 1.0, 0.0 )
            glLineWidth( 2.0 )
            
            glBegin( GL_LINE_LOOP )
            glVertex3f( self.p0[0], self.p0[1], 0.0 )
            glVertex3f( self.p1[0], self.p0[1], 0.0 )
            glVertex3f( self.p1[0], self.p1[1], 0.0 )
            glVertex3f( self.p0[0], self.p1[1], 0.0 )
            glEnd()
            
            glPopAttrib()
            
        PGContext.drawGL( self, view )
    
