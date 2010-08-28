# The basic color map class
# responsible for mapping scalar value [0,1] to a color
#   specifically, designed to work on numpy arrays

import pygame
import numpy as np

class ColorMap:
    BAR_HEIGHT = 200    # height of the bar in pixels
    BAR_WIDTH = 20      # width of the bar
    LABEL_COUNT = 11     # number of numerical labels to apply to bar
    LABEL_PAD = 4       # the number of pixels between bar and labels
    FONT = None
    def __init__( self ):
        self.dataRange = [0.0, 10.0]
        if ( ColorMap.FONT == None ):
            ColorMap.FONT = pygame.font.Font( 'arialn.ttf', 12 )

    def colorOnSurface( self, dataRange, data ):
        """Creates a surface with the data colored onto it"""
        raise AttributeError, "ColorMap class can't be called"

    def lastMapBar( self, labelCount=LABEL_COUNT ):
        """Draws the bar for the last mapped data"""
        data = np.zeros( ( ColorMap.BAR_WIDTH, ColorMap.BAR_HEIGHT ), dtype=np.float32 )
        vals = np.arange( ColorMap.BAR_HEIGHT, dtype=np.float32 ) / ( ColorMap.BAR_HEIGHT - 1 )
        domain = self.dataRange[1] - self.dataRange[0] 
        vals = ( vals * domain ) + self.dataRange[0]
        data += vals
        bar = self.colorOnSurface( self.dataRange, data )
        barRect = bar.get_rect()
        labelDelta = domain / ( labelCount - 1 )
        labels = [ '%.2g' % ( i * labelDelta + self.dataRange[0] ) for i in range( labelCount - 1 ) ]
        labels.append( '>= %.2g' % self.dataRange[1] )
        labelSrf = [ ColorMap.FONT.render( x, True, (255, 255, 255) ) for x in labels ]
        labelHeight = labelSrf[0].get_rect().height
        labelWidth = max( [ srf.get_rect().width for srf in labelSrf ] )
        barRect.top = labelHeight / 2
        map = pygame.Surface( ( ColorMap.BAR_WIDTH + ColorMap.LABEL_PAD + labelWidth, ColorMap.BAR_HEIGHT + labelHeight ) )
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

    def _normalize( self, data, (minVal, maxVal) ):
        """Returns an affine mapped version of the data based on the data range provided"""
        assert( maxVal > minVal )
        return ( data - minVal ) / ( maxVal - minVal )

class GreyScaleMap( ColorMap ):
    """Maps the data to a grey scale map"""
    def __init__( self ):
        ColorMap.__init__( self )

    def colorOnSurface( self, dataRange, data ):
        """Creates a greyscale map the same size as the data"""
        assert( len( data.shape ) == 2 )
        self.dataRange = dataRange
        normData = self._normalize( data, dataRange )
        color = np.zeros( ( data.shape[0], data.shape[1], 3 ), dtype=np.uint8 )
        color[:,:,0] = normData * 255
        color[:,:,1] = normData * 255
        color[:,:,2] = normData * 255
        return pygame.surfarray.make_surface( color )
    
class BlackBodyMap( ColorMap ):
    """Maps the data to a black-body color map"""
    def __init__( self, red=0.4, yellow=0.75 ):
        """Allows configuration of the red and yellow points of the map"""
        ColorMap.__init__( self )
        assert( yellow > red )
        self.red = red
        self.yellow = yellow

    def colorOnSurface( self, dataRange, data ):
        """Creates a greyscale map the same size as the data"""
        assert( len( data.shape ) == 2 )
        self.dataRange = dataRange
        normData = self._normalize( data, dataRange )
        color = np.zeros( ( data.shape[0], data.shape[1], 3 ), dtype=np.uint8 )
        color[:,:,0] = ( normData * 2.0 ).clip( 0.0, 1.0 ) * 255
        color[:,:,1] = ( ( normData - 0.25 ) * 2 ).clip( 0.0, 1.0 ) * 255
        color[:,:,2] = ( ( normData - 0.5 ) * 2 ).clip( 0.0, 1.0 ) * 255
##        rScale = 1.0 / self.red
##        color[:,:,0] = ( normData * rScale ).clip( 0.0, 1.0 ) * 255
##        gScale = 1.0 / ( self.yellow - self.red )
##        color[:,:,1] = ( ( normData - self.red ) * gScale ).clip( 0.0, 1.0 ) * 255
##        bScale = 1.0 / ( 1.0 - self.yellow )
##        color[:,:,2] = ( ( normData - self.yellow ) * bScale ).clip( 0.0, 1.0 ) * 255
        return pygame.surfarray.make_surface( color )

class FlameMap( ColorMap ):
    """Maps the data to a black-body color map"""
    def __init__( self ):
        """Color map goes from black->blue->red->orange->yellow"""
        ColorMap.__init__( self )
        
    def colorOnSurface( self, dataRange, data ):
        """Creates a greyscale map the same size as the data"""
        assert( len( data.shape ) == 2 )
        self.dataRange = dataRange
        normData = self._normalize( data, dataRange )
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
        return pygame.surfarray.make_surface( color )
    
class StephenBlackBodyMap( BlackBodyMap ):
    """This is stephen's black body map which clamps the data range to a
    maximum value of 6.0"""
    def __init__( self, maxValue=6.0, red=0.4, yellow=0.75 ):
        BlackBodyMap.__init__( self, red, yellow )
        self.maxVal = maxValue

    def colorOnSurface( self, dataRange, data ):
        """Creates a greyscale map the same size as the data"""
        if ( dataRange[1] > self.maxVal ):
            dataRange = [ dataRange[0], self.maxVal ]
        return BlackBodyMap.colorOnSurface( self, dataRange, data )
    
class LogBlackBodyMap( BlackBodyMap ):
    """First takes the log of the data before performing a black body
    coloring of the data"""
    def __init__( self, maxValue=6.0, red=0.4, yellow=0.75 ):
        BlackBodyMap.__init__( self, red, yellow )
        
    def colorOnSurface( self, dataRange, data ):
        """Creates a greyscale map the same size as the data"""
        # NOTE: This is wrong for the color bar
        dRange = ( np.log( dataRange[0] + 0.001 ), np.log( dataRange[1] + 0.001 ) )
        print "Log BlackBodyMap", dRange
        s =  BlackBodyMap.colorOnSurface( self, dRange, np.log( data + 0.001 ) )
        self.dataRange = dataRange
        return s
    
class BandedBlackBodyMap( BlackBodyMap ):
    """Maps the data to a black-body color map"""
    def __init__( self, bandCount=10, red=0.4, yellow=0.75 ):
        BlackBodyMap.__init__( self, red, yellow )
        self.bandCount = bandCount

    def colorOnSurface( self, dataRange, data ):
        """Creates a greyscale map the same size as the data"""
        assert( len( data.shape ) == 2 )
        self.dataRange = dataRange
        normData = self._normalize( data, dataRange )
        normData = np.ceil( normData * self.bandCount ) / self.bandCount
        
        color = np.zeros( ( data.shape[0], data.shape[1], 3 ), dtype=np.uint8 )
        color[:,:,0] = ( normData * 2.5 ).clip( 0.0, 1.0 ) * 255
        color[:,:,1] = ( ( normData - 0.4 ) / 0.35 ).clip( 0.0, 1.0 ) * 255
        color[:,:,2] = ( ( normData - 0.75 ) / 0.25 ).clip( 0.0, 1.0 ) * 255
        return pygame.surfarray.make_surface( color )
            