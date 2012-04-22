# Various utilities for playing with trajectories

import numpy as np

def firstDeriv( x, dt, k=1 ):
    '''Given a time-dependent value, x, computes the first derivative.

    @param x: an Nx1 numpy array.ArrayType
    @return: an (N-1)x1 numpy array of derivatives.'''
    return ( x[k:] - x[:-k] ) / dt
##    return np.diff( x, n=k ) / dt    
    

def curvature( x, y, dt, k=1 ):
    '''Given two time-varying parameters (x, y), computes the curvature of the
    space-time curve w.r.t. time.'''
    # THIS IS THE SIGNED CURVATURE
    # KAPPA = \frac{ x'y'' - y'x'' }{ (x'^2 + y'^2)^(3/2)}
    x1 = firstDeriv( x, dt, k )
    x2 = firstDeriv( x1, dt, k )
    x1 = x1[:-k]
    y1 = firstDeriv( y, dt, k )
    y2 = firstDeriv( y1, dt, k )
    y1 = y1[:-k]
    
    num = x1 * y2 - y1 * x2
    denom = x1 * x1 + y1 * y1
    denom = denom * np.sqrt( denom )
    return num / denom

def findZeros( vec, tol = 0.00001 ):
    """Given a vector of a data, finds all the zeros
       returns a Nx2 array of data

       each row is a zero, first column is the time of the zero, second column indicates increasing
       or decreasing (+1 or -1 respectively)"""
    zeros = []
    for i in range( vec.size - 1 ):
        a = float( vec[ i ] )
        b = float( vec[ i + 1] )
        increasing = 1
        if ( b < a ):
            increasing = -1
        if ( a * b < 0 ):
            t = -a / ( b - a )
            zeros.append( ( i + t, increasing ) )
    if ( abs( vec[ -1 ] ) < tol ):
         if ( vec[-1] > vec[-2] ):
             zeros.append( ( vec.size - 1, 1 ) )
         else:
             zeros.append( ( vec.size - 1, -1 ) )            
    return np.array( zeros, dtype=np.int )