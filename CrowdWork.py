# Class for performing the work of crowd analysis

from PyQt4 import QtGui, QtCore

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
