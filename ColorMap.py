# The basic color map class
# responsible for mapping scalar value [0,1] to a color
#   specifically, designed to work on numpy arrays

import pygame
import numpy as np

def clip( value, minVal, maxVal ):
    if ( value < minVal ):
        return minVal
    elif ( value > maxVal ):
        return maxVal
    else:
        return value
    
class ColorMap:
    BAR_HEIGHT = 200    # height of the bar in pixels
    BAR_WIDTH = 20      # width of the bar
    LABEL_COUNT = 11     # number of numerical labels to apply to bar
    LABEL_PAD = 4       # the number of pixels between bar and labels
    FONT = None
    def __init__( self, dataRange=None ):
        if ( dataRange == None ):
            self.dataRange = [0.0, 10.0]
            self.fixedRange = False
        else:
            self.dataRange = dataRange
            self.fixedRange = True
        if ( ColorMap.FONT == None ):
            ColorMap.FONT = pygame.font.Font( 'arialn.ttf', 12 )

    def getColor( self, value, (minVal, maxVal) ):
        '''Given a range of values (minVal and maxVal) and a single value, returns
        an RGB value for that value'''
        raise AttributeError, "getColor not instantiated for this class: %s" % ( str( self.__class__ ) )

    def colorOnSurface( self, dataRange, data ):
        """Creates a surface with the data colored onto it"""
        raise AttributeError, "ColorMap class can't be called"

    def mapBar( self, dataRange, labelCount=LABEL_COUNT ):
        '''Create a bar map for the given range'''
        data = np.zeros( ( ColorMap.BAR_WIDTH, ColorMap.BAR_HEIGHT ), dtype=np.float32 )
        vals = np.arange( ColorMap.BAR_HEIGHT, dtype=np.float32 ) / ( ColorMap.BAR_HEIGHT - 1 )
        domain = dataRange[1] - dataRange[0] 
        vals = ( vals * domain ) + dataRange[0]
        data += vals
        bar = self.colorOnSurface( dataRange, data[ :, ::-1] )
        barRect = bar.get_rect()
        labelDelta = domain / ( labelCount - 1 )
        labels = [ '%.2g' % ( i * labelDelta + dataRange[0] ) for i in range( labelCount - 1 ) ]
        labels.append( '>= %.2g' % dataRange[1] )
        labelSrf = [ ColorMap.FONT.render( x, True, (255, 255, 255) ) for x in labels ]
        labelHeight = labelSrf[0].get_rect().height
        labelWidth = max( [ srf.get_rect().width for srf in labelSrf ] )
        barRect.top = labelHeight / 2
        map = pygame.Surface( ( ColorMap.BAR_WIDTH + ColorMap.LABEL_PAD + labelWidth, ColorMap.BAR_HEIGHT + labelHeight ) )
        map.fill( (128, 128, 128 ) )
        map.blit( bar, barRect )
        labelLeft = ColorMap.BAR_WIDTH + ColorMap.LABEL_PAD
        labelTop = 0
        labelDistance = ColorMap.BAR_HEIGHT / ( labelCount - 1 )
        for srf in labelSrf:
            srfRect = srf.get_rect()
            srfRect.left = labelLeft
            srfRect.top = labelTop
            map.blit( srf, srfRect )
            labelTop += labelDistance
        
        return map
        
    def lastMapBar( self, labelCount=LABEL_COUNT ):
        """Draws the bar for the last mapped data"""
        return self.mapBar( self.dataRange, labelCount )

    def _normalize( self, data, (minVal, maxVal) ):
        """Returns an affine mapped version of the data based on the data range provided"""
        assert( maxVal > minVal )
        return ( data - minVal ) / ( maxVal - minVal )
    
    def bgMask( self, data, dataRange ):
        """Creates a mask on the data for the background"""
        # the background is detected by values less than the minimum data range
        return data < dataRange[0]
    
class GreyScaleMap( ColorMap ):
    """Maps the data to a grey scale map"""
    def __init__( self, dataRange=None ):
        ColorMap.__init__( self, dataRange )

    def colorOnSurface( self, dataRange, data ):
        """Creates a greyscale map the same size as the data"""
        assert( len( data.shape ) == 2 )
        if ( not self.fixedRange ):
            self.dataRange = dataRange
        normData = self._normalize( data, self.dataRange )
        color = np.zeros( ( data.shape[0], data.shape[1], 3 ), dtype=np.uint8 )
        color[:,:,0] = normData * 255
        color[:,:,1] = normData * 255
        color[:,:,2] = normData * 255
        
        return pygame.surfarray.make_surface( color[:,::-1,:] )
    
class BlackBodyMap( ColorMap ):
    """Maps the data to a black-body color map"""
    def __init__( self, red=0.4, yellow=0.75, dataRange=None ):
        """Allows configuration of the red and yellow points of the map"""
        ColorMap.__init__( self, dataRange )
        assert( yellow > red )
        self.red = red
        self.yellow = yellow

    def colorOnSurface( self, dataRange, data ):
        """Creates a greyscale map the same size as the data"""
        assert( len( data.shape ) == 2 )
        if ( not self.fixedRange ):
            self.dataRange = dataRange
        normData = self._normalize( data, self.dataRange )
        color = np.zeros( ( data.shape[0], data.shape[1], 3 ), dtype=np.uint8 )
        color[:,:,0] = ( normData * 2.0 ).clip( 0.0, 1.0 ) * 255
        color[:,:,1] = ( ( normData - 0.25 ) * 2 ).clip( 0.0, 1.0 ) * 255
        color[:,:,2] = ( ( normData - 0.5 ) * 2 ).clip( 0.0, 1.0 ) * 255
        # use grey as the default bg color
        bgMask = self.bgMask( data, dataRange )
        color[ bgMask ] = 128
        
        return pygame.surfarray.make_surface( color[:,::-1,:] )

class FlameMap( ColorMap ):
    """Maps the data to a black-body color map"""
    def __init__( self, dataRange=None ):
        """Color map goes from black->blue->red->orange->yellow"""
        ColorMap.__init__( self, dataRange )
        
    def getColor( self, value, (minVal, maxVal) ):
        '''Given a range of values (minVal and maxVal) and a single value, returns
        an RGB value for that value'''
        normData = self._normalize( value, (minVal, maxVal ) )
        color = [0, 0, 0]
        color[0] = int( clip( ( ( normData - 0.25 ) * 4.0 ), 0.0, 1.0 ) * 255 )
        color[1] = int( clip( ( ( normData - 0.5 ) * 4.0 ), 0.0, 1.0 ) * 255 )
        if ( normData < 0.25 ):
            color[2] = int( clip( normData * 4.0, 0.0, 1.0 ) * 255 )
        elif ( normData > 0.75 ):
            color[2] = int( clip( ( normData - 0.75 ) * 4.0, 0.0, 1.0 ) * 255 )
        else:
            color[2] = int( clip( 1.0 - ( normData - 0.25 ) * 4.0, 0.0, 1.0 ) * 255 )
        return color

    def colorOnSurface( self, dataRange, data ):
        """Creates a greyscale map the same size as the data"""
        assert( len( data.shape ) == 2 )
        if ( not self.fixedRange ):
            self.dataRange = dataRange
        normData = self._normalize( data, self.dataRange )
        color = np.zeros( ( data.shape[0], data.shape[1], 3 ), dtype=np.uint8 )
        color[:,:,0] = ( ( normData - 0.25 ) * 4.0 ).clip( 0.0, 1.0 ) * 255
        color[:,:,1] = ( ( normData - 0.5 ) * 4.0 ).clip( 0.0, 1.0 ) * 255
        b1Mask = normData < 0.25
        b3Mask = normData > 0.75
        b2Mask = ~( b1Mask | b3Mask )
        blueValues = np.zeros_like( normData )
        blueValues[b1Mask] = ( normData[ b1Mask ] * 4.0 )
        blueValues[b3Mask ]= ( normData[ b3Mask ] - 0.75 ) * 4.0
        blueValues[b2Mask ] = 1.0 - ( normData[ b2Mask ] - 0.25 ) * 4.0
        color[:,:,2] = blueValues.clip( 0.0, 1.0 ) * 255
        # use grey as the default bg color
        
        bgMask = self.bgMask( data, dataRange )
        color[ bgMask ] = 128
        return pygame.surfarray.make_surface( color[:,::-1,:] )
    
class StephenBlackBodyMap( BlackBodyMap ):
    """This is stephen's black body map which clamps the data range to a
    maximum value of 6.0"""
    def __init__( self, maxValue=6.0, red=0.4, yellow=0.75, dataRange=None ):
        BlackBodyMap.__init__( self, red, yellow, dataRange )
        self.maxVal = maxValue

    def colorOnSurface( self, dataRange, data ):
        """Creates a greyscale map the same size as the data"""
        if ( dataRange[1] > self.maxVal ):
            dataRange = [ dataRange[0], self.maxVal ]
        return BlackBodyMap.colorOnSurface( self, dataRange, data )
    
class LogBlackBodyMap( BlackBodyMap ):
    """First takes the log of the data before performing a black body
    coloring of the data"""
    def __init__( self, maxValue=6.0, red=0.4, yellow=0.75, dataRange=None ):
        BlackBodyMap.__init__( self, red, yellow, dataRange )
        
    def colorOnSurface( self, dataRange, data ):
        """Creates a greyscale map the same size as the data"""
        # NOTE: This is wrong for the color bar
        dRange = ( np.log( dataRange[0] + 0.001 ), np.log( dataRange[1] + 0.001 ) )
        print "Log BlackBodyMap", dRange
        s =  BlackBodyMap.colorOnSurface( self, dRange, np.log( data + 0.001 ) )
        if ( not self.fixedRange ):
            self.dataRange = dataRange
        return s
    
class BandedBlackBodyMap( BlackBodyMap ):
    """Maps the data to a black-body color map"""
    def __init__( self, bandCount=10, red=0.4, yellow=0.75, dataRange=None ):
        BlackBodyMap.__init__( self, red, yellow, dataRange )
        self.bandCount = bandCount

    def colorOnSurface( self, dataRange, data ):
        """Creates a greyscale map the same size as the data"""
        assert( len( data.shape ) == 2 )
        if ( not self.fixedRange ):
            self.dataRange = dataRange
        normData = self._normalize( data, self.dataRange )
        normData = np.ceil( normData * self.bandCount ) / self.bandCount
        
        color = np.zeros( ( data.shape[0], data.shape[1], 3 ), dtype=np.uint8 )
        color[:,:,0] = ( normData * 2.5 ).clip( 0.0, 1.0 ) * 255
        color[:,:,1] = ( ( normData - 0.4 ) / 0.35 ).clip( 0.0, 1.0 ) * 255
        color[:,:,2] = ( ( normData - 0.75 ) / 0.25 ).clip( 0.0, 1.0 ) * 255
        return pygame.surfarray.make_surface( color[:,::-1,:] )

class RedBlueMap( ColorMap ):
    '''Color map which is white at 0 and verges to red and blue at the extreme values.  The map is
    symmetric.  So, the range at which the colors reach red and blue is the maximum( min, max).'''
    def __init__( self, dataRange=None ):
        """Color map goes from blue->white->red"""
        ColorMap.__init__( self, dataRange )

    def bipolarRange( self, (minVal, maxVal) ):
        '''Normalizes this for the bipolar map.  Remaps the values such that 0.0 -> 0.5, abs( maxVal, minVal) maps
        to 1 and -abs(maxVal, minVal) maps to 0.'''
        maxVal = max( abs( minVal ), abs( maxVal ) )
        minVal = -maxVal
        return minVal, maxVal
        
    def colorOnSurface( self, dataRange, data ):
        """Creates a greyscale map the same size as the data"""
        assert( len( data.shape ) == 2 )
        if ( not self.fixedRange ):
            self.dataRange = self.bipolarRange( dataRange )
        normData = self._normalize( data, self.dataRange )
        color = np.ones( ( data.shape[0], data.shape[1], 3 ), dtype=np.uint8 ) * 255

        redMask = normData > 0.5
        blueMask = normData < 0.5

        vals = ( 2.0 * normData[ blueMask ] ) * 255
        color[ blueMask, 0 ] = vals
        color[ blueMask, 1 ] = vals
        vals = ( 1.0 - 2.0 * normData[ redMask ] ) * 255
        color[ redMask, 1 ] = vals
        color[ redMask, 2 ] = vals
        
        # use balck as the default bg color
        bgMask = self.bgMask( data, dataRange )
        color[ bgMask ] = 0
        return pygame.surfarray.make_surface( color[:,::-1,:] )

# a dictionary from available color map namess to color map classes
COLOR_MAPS = { "Grey scale":GreyScaleMap,
               "Black body":BlackBodyMap,
               "Flame":FlameMap,
               "Log Black body":LogBlackBodyMap,
               "Red Blue":RedBlueMap
               }

            