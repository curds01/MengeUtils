# Playback ability for an scb file

from PyQt4 import QtCore, QtGui
from agent_set import AgentSet

class PlayerController( QtGui.QFrame ):
    '''The playback controller for playing back scb data'''

    # Signals a change to the animation state that requires a redraw
    need3DUpdate = QtCore.pyqtSignal()

    # TODO: Have view pass itself into the drawable instead of saving it everywhere
    def __init__( self, view, parent=None ):
        super(PlayerController, self).__init__( parent )
        # internal functionality
        self.view = view
        
        self.agent_set = None
        self.player = Player()
        self.player.finished.connect( self.playFinished )
        self.player.timeChange.connect( self.setCurrTime )

        # set up GUI
        hLayout = QtGui.QHBoxLayout()
        hLayout.setMargin(0)
        
        self.playButton = QtGui.QPushButton("Play")
        self.playButton.setCheckable( True )
        hLayout.addWidget( self.playButton )
        self.playButton.clicked.connect( self.startPlay )
        
        self.timeSlider = QtGui.QSlider()
        self.timeSlider.setOrientation(QtCore.Qt.Horizontal )
        self.timeSlider.valueChanged.connect( self.player.setFrame )
        hLayout.addWidget( self.timeSlider )

        self.timeStamp = QtGui.QLabel('time')
        hLayout.addWidget( self.timeStamp )

        hLayout.setStretch( 0, 0 )
        hLayout.setStretch( 1, 1 )
        hLayout.setStretch( 2, 0 )

        self.setLayout( hLayout )

        self.setEnable( False )

    def setEnable( self, enabled ):
        self.playButton.setEnabled( enabled )
        self.timeSlider.setEnabled( enabled )
        self.timeStamp.setEnabled( enabled )
        
    def startPlay( self, checked ):
        '''Begins playback'''
        if ( checked ):
            #start play
            self.playButton.setText("Stop")
            self.player.start()
        else:
            # stop play
            self.playButton.setText("Play")
            self.player.stop()
    
    def playFinished( self ):
        self.playButton.setText("Play")
        self.playButton.setChecked( False )

    def setCurrTime( self, t ):
        '''Updates the visibile timeline and gui to arbitrary value.
        @param      t       The time to set the animation system.
        '''
        # No feedback loop between slider and player
        self.timeSlider.blockSignals( True )
        self.timeSlider.setSliderPosition( t )
        self.timeSlider.blockSignals( False )
        self.timeStamp.setText( '%d' % t )
        self.need3DUpdate.emit()

    def setFrameSet( self, frame_set ):
        if ( not self.agent_set is None ):
            try:
                self.view.removeDrawable( self.agent_set )
            except ValueError:
                print "Attempted to delete resource not in view"

        last_frame = 0
        if ( frame_set ):
            # TODO: Get the agent size from somewhere else.
            last_frame = frame_set.totalFrames() - 1
            self.timeSlider.setMaximum( last_frame )
            self.timeSlider.setSliderPosition( 0 )
            self.agent_set = AgentSet( self.view, 0.19, frame_set )
            self.view.addDrawable( self.agent_set )
            self.setEnable( True )
            self.need3DUpdate.emit()
            print "Loading scb data for playback"
            print "\t%d frames" % (last_frame + 1)
            print "\tReported playback rate: %.1f fps" % ( 1 / frame_set.simStepSize )
            print "\tReal time duration: %.1f s" % ((last_frame + 1) * frame_set.simStepSize )
        elif ( not self.agent_set is None ):
            self.agent_set = None
            self.setEnable( False )
            self.need3DUpdate.emit()
        self.player.setData( frame_set, last_frame, self.agent_set )

class Player( QtCore.QAbstractAnimation ):
    '''The player for advancing crap'''
    # Emitted to reports that the current time has changed.
    timeChange = QtCore.pyqtSignal( float )
    
    def __init__( self, parent=None ):
        '''Constructor.

        @param      parent      The optional parent node.
        '''
        super( Player, self ).__init__( parent )
        self.frame_set = None
        self.agent_set = None

    def setData( self, frame_set, last_frame, agent_set ):
        '''Sets the data for the player, resetting its state.

        @param      frame_set   The frame_set data from which to get agents and positions.
        @param      last_frame  The index of the last valid frame.
        @param      agent_set   The agent set to provide the current frame to.
        '''
        self.frame_set = frame_set
        self.agent_set = agent_set

        if ( not frame_set is None ):
            self.lastFrame = last_frame
            self.currFrame = -1
            self.lastTime = 0       # The last QT time stamp at which this was evaluated
            self._duration = 0  # total ms this lasts
            self.setFrameRate( 1.0 / self.frame_set.simStepSize )
            
            if ( self.frame_set ):
                self.setFrame(0)

    def setFrameRate( self, fps ):
        '''Sets the frame rate of the playback.

        @param  fps     Frames per second.
        '''
        # represented as milliseconds per frame for efficient computation
        self.mspf = 1000.0 / fps
        # represented as frames per milliseconds
        self.fpms = fps / 1000.0
        self._computeDuration()

    def _computeDuration( self ):
        '''Computes the duration of real-time playback relative to the *current* frame.'''
        totalFrames = self.lastFrame - self.currFrame + 1
        self._duration = int( totalFrames * self.mspf )

    def setFrame( self, frame_number):
        '''Sets the frame to the given frame.'''
        if ( frame_number != self.currFrame ):
            self.frame_set.setNext( frame_number )
            self.evalNextFrame()
            self._computeDuration()
        
    def evalNextFrame( self ):
        '''Updates the state of the player by calling for the next frame on the frame set'''
        frame, self.currFrame = self.frame_set.next()
        self.agent_set.setFrame( frame )
        self.timeChange.emit( self.currFrame )
        
    def start( self ):
        '''Start the playback'''
        if ( self.currFrame == self.lastFrame ):
            # automatically loop back to the beginning, otherwise continue from where we are.
            self.frame_set.setNext(0)
            self.currFrame = 0
        self.startTime = self.currFrame * self.mspf
        self._computeDuration()
        super( Player, self ).start()
        
    def updateCurrentTime( self, currTime ):
        '''Updates the player to the current time'''
        # Note: the "currTime" value is always relative to when the play button
        # was hit.  It starts at zero every time the animation is stopped and started.
        totalTime = self.startTime + currTime
        targetFrame = int(totalTime * self.fpms)
        if (targetFrame > self.currFrame):
            self.frame_set.setNext( targetFrame )
            try:
                self.evalNextFrame()
            except:
                self.stop()

    def duration( self ):
        return self._duration
