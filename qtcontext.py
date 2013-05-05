from PyQt4 import QtCore, QtGui, QtOpenGL
from Context import *
from flowContext import FlowLineContext

class QtEventProcessor():
    '''QT-specific context - translates QT events to canonical events'''
    # mapping from supported QT events to canonical event types
    EVT_MAP = { QtCore.QEvent.MouseButtonPress:MouseEvent.DOWN,
                QtCore.QEvent.MouseButtonRelease:MouseEvent.UP,
                QtCore.QEvent.MouseMove:MouseEvent.MOVE }
    
    def isMouseEvent( self, evt ):
        '''Reports if the given event is a supported mouse event'''
        eType = evt.type()
        return ( eType == QtCore.QEvent.MouseButtonPress or
                 eType == QtCore.QEvent.MouseButtonRelease or
                 eType == QtCore.QEvent.MouseMove )
    
    def canonicalEvent( self, evt ):
        '''Converts the given QT event to a canonical event.

        @param  evt     An instace of QtCore.QEvent
        @returns        An instance of Context.Event
        @raises         ValueError if the event is unrecognized.
        '''
        if ( self.isMouseEvent( evt ) ):
            eType = self.EVT_MAP[ evt.type() ]
            qtBtn = evt.button()
            if ( qtBtn == QtCore.Qt.LeftButton ):
                eBtn = MouseEvent.LEFT
            elif ( qtBtn == QtCore.Qt.RightButton ):
                eBtn = MouseEvent.RIGHT
            elif ( qtBtn == QtCore.Qt.MidButton ):
                eBtn = MouseEvent.MIDDLE
            elif ( eType == MouseEvent.MOVE ):
                eBtn = MouseEvent.NO_BTN
            else:
                raise ValueError, "Unsupported QT mouse event button: %s" % ( qtBtn )
            mX = evt.x()
            mY = evt.y()
            mods = Event.NO_MODS
            eMods = evt.modifiers()
            if ( eMods & QtCore.Qt.ShiftModifier ):
                mods = mods & Event.SHIFT
            if ( eMods & QtCore.Qt.AltModifier ):
                mods = mods & Event.ALT
            if ( eMods & QtCore.Qt.ControlModifier ):
                mods = mods & Event.CTRL
            return MouseEvent( eType, button=eBtn, x=mX, y=mY, modifiers=mods )
        else:
            raise ValueError, "Unrecognized QEvent type: %s" % ( evt.type() )

class QTFlowLineContext( QtEventProcessor, FlowLineContext ):
    def __init__( self, cancelCB=None ):
        FlowLineContext.__init__( self, cancelCB )
        
if __name__ == '__main__':
    print
    line = GLLine( Vector2( -1.0, -1.0 ), Vector2( 1.0, 1.0 ) )
    p1 = Vector2( 0.0, 0.0 )
    print "Distance should be 0.0:", line.pointDistance( p1 )
    p2 = Vector2( 1.0, 0.0 )
    print "Distance should be sqrt(2)/2:", line.pointDistance( p2 )
    p3 = Vector2( -1.0, 0.0 )
    print "Distance should be sqrt(2)/2:", line.pointDistance( p3 )
    p4 = Vector2( 2.0, 2.0 )
    print "Distance should be sqrt(2):", line.pointDistance( p4 )
    p4 = Vector2( -2.0, -2.0 )
    print "Distance should be sqrt(2):", line.pointDistance( p4 )
    p5 = Vector2( -1.0, -2.0 )
    print "Distance should be 1:", line.pointDistance( p5 )
        
