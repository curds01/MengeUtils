# Class for performing the work of crowd analysis

import time
from PyQt4 import QtGui, QtCore
from primitives import Vector2, Segment
import flowUtils
from trajectory.scbData import FrameSet, NPFrameSet

import Crowd
import os, sys
from GFSVis import visualizeGFS
import Kernels
import Signals
from Grid import makeDomain

class CrowdAnalyzeThread( QtCore.QThread ):
    '''Class to perform the crowd analysis'''
    def __init__( self, data, parent=None ):
        '''Constructor.

        @param      data        A list of AnalysisTasks.  
        '''
        QtCore.QThread.__init__( self, parent )
        self.tasks = data

    def run( self ):
        '''Execute the task list'''
        for task in self.tasks:
            task.execute()
