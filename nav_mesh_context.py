# The interactive context for editing goals

import pygame
from OpenGL.GL import *

from RoadContext import PGContext, MouseEnabled, PGMouse
from Context import BaseContext, ContextResult
from navMesh import NavMesh

class NavMeshContext(PGContext, MouseEnabled):
    '''A context for editing navigation meshes'''
    # TODO:
    #  1. Take in the obstacle set to use for vertex snapping.
    HELP_TEXT = 'Navigation Mesh Context' \
                '\n\tDisplay' \
                '\n\t\tn - toggle node id display' \
                '\n\t\te - toggle edge id display' \
                '\n\t\to - toggle obstacle id display'

    def __init__(self, nav_mesh=None):
        PGContext.__init__(self)
        MouseEnabled.__init__(self)

        # display properties
        self.show_node_ids = True
        self.show_edge_ids = True
        self.show_obstacle_ids = True
        
        self.nav_mesh = nav_mesh
        if self.nav_mesh is None:
            self.nav_mesh = NavMesh()

    def handleKeyboard(self, event, view):
        result = PGContext.handleKeyboard( self, event, view )
        if not result.isHandled():
            mods = pygame.key.get_mods()
            hasCtrl = mods & pygame.KMOD_CTRL
            hasAlt = mods & pygame.KMOD_ALT
            hasShift = mods & pygame.KMOD_SHIFT
            noMods = not( hasShift or hasCtrl or hasAlt )
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_n and noMods:
                    self.show_node_ids = not self.show_node_ids
                    result.set(True, True)
                if event.key == pygame.K_e and noMods:
                    self.show_edge_ids = not self.show_edge_ids
                    result.set(True, True)
                if event.key == pygame.K_o and noMods:
                    self.show_obstacle_ids = not self.show_obstacle_ids
                    result.set(True, True)
                    
        return result

    def drawGL(self, view):
        '''Draws the navigation mesh to the open gl context'''
        PGContext.drawGL( self, view )

        glPushAttrib(GL_COLOR_BUFFER_BIT | GL_ENABLE_BIT | GL_POINT_BIT |
                     GL_DEPTH_BUFFER_BIT | GL_POLYGON_MODE)

        # Draw the shaded regions of the faces.
        glDepthMask(False)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glColor4f(0.5, 0.8, 1.0, 0.5)
        for node in self.nav_mesh.nodes:
            glBegin(GL_POLYGON)
            for v_idx in node.poly.verts:
                v = self.nav_mesh.vertices[v_idx - 1]
                glVertex3f(v.x, v.y, node.getElevation(v))
            glEnd()

        # draw edges
        glDisable(GL_BLEND)
        glColor4f(0.2, 0.8, 0.2, 1.0)
        glBegin(GL_LINES)
        for i, edge in enumerate(self.nav_mesh.edges):
            v0 = self.nav_mesh.vertices[edge.v0]
            v1 = self.nav_mesh.vertices[edge.v1]
            glVertex3f(v0.x, v0.y, edge.n0.getElevation(v0))
            glVertex3f(v1.x, v1.y, edge.n0.getElevation(v1))
        
        
        # draw obstacles
        glColor4f(0.8, 0.2, 0.2, 1.0)
        for obst in self.nav_mesh.obstacles:
            v0 = self.nav_mesh.vertices[obst.v0]
            v1 = self.nav_mesh.vertices[obst.v1]
            glVertex3f(v0.x, v0.y, obst.n0.getElevation(v0))
            glVertex3f(v1.x, v1.y, obst.n0.getElevation(v1))
            
        glEnd()
        glPopAttrib()

        if self.show_node_ids:
            for i, n in enumerate(self.nav_mesh.nodes):
                p_WC = n.center
                p_SC = view.worldToScreen(p_WC)
                view.printText('{}'.format(i), p_SC)
                
        if self.show_edge_ids:
            for i, e in enumerate(self.nav_mesh.edges):
                v0 = self.nav_mesh.vertices[e.v0]
                v1 = self.nav_mesh.vertices[e.v1]
                p_WL = (v0 + v1) / 2
                p_SL = view.worldToScreen(p_WL)
                view.printText('{}'.format(i), p_SL)
                
        if self.show_obstacle_ids:
            for i, o in enumerate(self.nav_mesh.obstacles):
                v0 = self.nav_mesh.vertices[o.v0]
                v1 = self.nav_mesh.vertices[o.v1]
                p_WL = (v0 + v1) / 2
                p_SL = view.worldToScreen(p_WL)
                view.printText('{}'.format(i), p_SL)
