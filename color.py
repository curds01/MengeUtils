'''Color utilities'''
import numpy as np

def hsvToRgb( h, s, v, dtype=int ):
    '''Convert hue, saturation and lightness to r, g, b values.
    Hue in [0, 360], s in [0, 1], l in [0, 1].
    If dtype is int, then values are in the range [0, 255]
    otherwise in the range [0,1]'''
    r = g = b = 0.0
    c = s * v
    h /= 60.0
    x = c * (1 - abs( ( h % 2 ) - 1 ) )
    
    if ( h >= 0 and h < 1 ):
        r = c
        g = x
    elif ( h >= 1 and h < 2 ):
        r = x
        g = c
    elif ( h >= 2 and h < 3 ):
        g = c
        b = x
    elif ( h >= 3 and h < 4 ):
        g = x
        b = c
    elif ( h >= 4 and h < 5 ):
        r = x
        b = c
    else:
        r = c
        b = x
    m = v - c
    r += m
    g += m
    b += m

    if ( dtype == int ):
        r = int( round( r * 255 ) )
        g = int( round( g * 255 ) )
        b = int( round( b * 255 ) )
    return r, g, b

def hsvToRgbNP( hues, datatype=np.uint8 ):
    '''Convert hue, saturation and lightness to r, g, b values.
    The colors are defined by an N X 3 array of HSV tuples such
    that H is [0], S is [1] and V is [2]'''
    H = 0
    S = 1
    V = 2
    nColor = np.zeros( hues.shape, dtype=np.float32 ) 
    c = hues[:,S] * hues[:,V]
    h = hues[:,H] / 60

    x = c * (1 - abs( ( h % 2 ) - 1 ) )
    # six masks
    mask1 = ( h >= 0 ) & ( h < 1 )
    nColor[ mask1, 0 ] = c[ mask1 ]
    nColor[ mask1, 1 ] = x[ mask1 ]

    mask1 = ( h >= 1 ) & ( h < 2 )
    nColor[ mask1, 0 ] = x[ mask1 ]
    nColor[ mask1, 1 ] = c[ mask1 ]
        
    mask1 = ( h >= 2 ) & ( h < 3 )
    nColor[ mask1, 1 ] = c[ mask1 ]
    nColor[ mask1, 2 ] = x[ mask1 ]
        
    mask1 = ( h >= 3 ) & ( h < 4 )
    nColor[ mask1, 1 ] = x[ mask1 ]
    nColor[ mask1, 2 ] = c[ mask1 ]
        
    mask1 = ( h >= 4 ) & ( h < 5 )
    nColor[ mask1, 0 ] = x[ mask1 ]
    nColor[ mask1, 2 ] = c[ mask1 ]
        
    mask1 = ( h >= 5 )
    nColor[ mask1, 0 ] = c[ mask1 ]
    nColor[ mask1, 2 ] = x[ mask1 ]

    m = hues[:,V] - c
    m.shape = (-1, 1 )

    nColor += m

    if ( datatype == np.uint8 ):
        colors = np.empty( hues.shape, dtype=np.uint8 )
        colors[:, :] = np.round( nColor * 255 )
    else:
        colors = hues

    return colors

if __name__ == '__main__':
    colors = (
        ( ( 0, 1.0, 1.0 ),      (255, 0, 0) ) ,
        ( ( 120, 1.0, 1.0 ),    (0, 255, 0 ) ),
        ( ( 120, 0.5, 1.0 ),    (128, 255, 128) ),
        ( ( 120, 0, 1.0 ),      (255, 255, 255) ),
        ( ( 120, 1.0, 0.5 ),    (0, 128, 0 ) ),
        ( ( 120, 1.0, 0.0 ),    (0, 0, 0) ),
        ( ( 240, 1.0, 1.0 ),    (0, 0, 255) ),
        ( ( 149, 0.82001, 0.62 ),    (28, 158, 91) ),
        )

    HSL = np.array( [hsl for hsl, rgb in colors] )
    RGB = np.array( [rgb for hsl, rgb in colors] )

    allValid = True
    for i in xrange( len( colors ) ):
        converted = np.array( hsvToRgb( HSL[i,0], HSL[i,1], HSL[i,2] ) )
        delta = np.sum( converted - RGB[i,:] )
        if ( delta > 0 ):
            allValid = False
            print "\t", HSL[ i, : ], "should be", RGB[i,:], "produced", converted
    if ( allValid ):
        print "All colors valid for float representation"

    converted = hsvToRgbNP( HSL )
    matches = converted == RGB
    valid = matches[:,0] & matches[:,1] & matches[:,2]
    validCount = sum( valid )
    if ( validCount == len( colors ) ):
        print "All np colors match!"
    else:
        print "Following colors were wrong:"
        bad = np.where( ~valid )
        for i in bad:
            print "\t", HSL[ i, : ], "should be", RGB[i,:], "produced", converted[i,:]