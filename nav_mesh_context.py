# The interactive context for editing goals

import pygame
from OpenGL.GL import *

from RoadContext import PGContext, MouseEnabled, PGMouse
from Context import BaseContext, ContextResult
from navMesh import NavMesh

# Features:
#   Edit a nav mesh
#       Build polygons
#           - place vertices
#               - lock to obstacle vertices
#           - build polygon off of vertices
#           - do I detect if they are convex?
#       Edit polygons
#           - split polygon
#           - move vertices
#   Workflow
#       - similar to graph
#           - moving mouse will find nearby vertex
#           - left click and drag
#               - if vertex highlighed, it activates it and moves it.
#               - if vertex is *not* highlighted, a vertex is added and moves it.
#               - if a vertex is moved "on top" of another vertex, it merges in
#                   - updating incident faces accordingly.
#           - middle click and drag from vertex to vertex
#               - If I drag from v0 to v1 (then up)
#                   - if they traverse an existing polygon and can cut the polygon into to
#                     valid polygons, create two polygons from one.
#               - If I drag from v0, v1, ..., vk (then up)
#                   As soon as I have three, automatically close the polygon
#                   - right click cancels
#                   - if it is a sub-region of another node, cancel
#                   - Upon relase, if it encloses a novel region, add a node.
#                       - update obstacles and edges.
#           - delete vertex
#               - remove from all nodes incident to it.
#               - If inciden tnode is reduced to two vertices, remove the node
#           - Operate on face
#               - switch to face mode.
#               - movement highlights
#               - can delete
#               - can add it to a group
#                   - prompt for name?
#           - operate on edge
#               - move
#               - collapse
#               - delete
#                   - if interior, two adjacent faces merge
#                       - checked for convexity
#                   - if exterior face gets deleted (edges and obstacles get updated).
#               - extrude
#           - Can I create groups?
#       - Operations on graph
#           - add vertex, face
#           - delete vertex, vertex, face
#           - merge faces
#           - merge vertices
#           - Confirm convexity (indciate non-convexity)
#   Design
#       What actions need to be disambiguated
#           Hover
#               - highlight vertex
#               - highlight edge
#               - highlight face
#           Keystroke
#               - delete: delete highlighted feature
#               - e?: extrude highlighted edge -- does this require a drag or just a move?
#               - c?: collapse highlighted edge
#           Click
#               - Left MB
#                   - vertex highlighted: cause the vertex to be dragged
#                   - edge  hihlighted: cause edge to be dragged
#                   - face highlighted: case face to be dragged
#                   - nothing highlighted, create vertex and cause the new vertex to be dragged.
#               - Right MB
#                   - if dragging, cancel the drag action (could be create and move or extrude, etc).
#               - Middle MB
#                   - vertex highlighted: begin connecting highlighted vertex to next vertex
#           Drag
#               - Dragging button
#                   - left
#                       - moving vertex reposition the vertex; if near another vertex, mark it for merging
#                       - moving edge/extruding edge; reposition the edge
#                       - moving face: reposition the face
#                   - middle
#                       - Draw polygon connecting selected vertices
#               - Release
#                   - complete action and make permanent
#           

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
