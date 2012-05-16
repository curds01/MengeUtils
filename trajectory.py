# Various utilities for playing with trajectories

import numpy as np

def firstDerivForward( x, dt, k=1 ):
    '''Given a time-dependent value, x, computes the first derivative.
    It uses the first-order forward-difference approach

    @param x: an Nx1 numpy array.  The uniformly sampled time-dependent value.
    @param dt: a float.  The time elapsed between samples in x.
    @param k: an int. The sample rate at which to compute the derivative.  Bigger --> smoother.
    @return: an (N-k)x1 numpy array of derivatives.'''
    DT = k * dt
    return ( x[k:] - x[:-k] ) / DT

def firstDerivCenter( x, dt, k=1 ):
    '''Given a time-dependent value, x, computes the first derivative.
    It uses the second-order center-differences approach

    @param x: an Nx1 numpy array.  The uniformly sampled time-dependent value.
    @param dt: a float.  The time elapsed between samples in x.
    @param k: an int. The sample rate at which to compute the derivative.  Bigger --> smoother.
    @return: an (N-2k)x1 numpy array of derivatives.'''
    DT = k * dt
    k2 = 2 * k
    return ( x[k2:] - x[:-k2] ) / ( 2 * DT )

firstDeriv = firstDerivCenter

def secondDeriv( x, dt, k=1 ):
    '''Given a time-dependent value, x, computes the second derivative.
    Uses a simple, second-order center-differences method.

    @param x: an Nx1 numpy array.  The uniformly sampled time-dependent value.
    @param dt: a float.  The time elapsed between samples in x.
    @param k: an int. The sample rate at which to compute the derivative.  Bigger --> smoother.
    @return: an (N-2k)x1 numpy array of derivatives.'''
    DT = k * dt
    dt2 = DT * DT 
    k2 = 2 * k
    return ( x[ k2: ] - 2 * x[ k:-k ] + x[ :-k2 ] ) / dt2

def curvature( x, y, dt, k=1 ):
    '''Given two time-varying parameters (x, y), computes the curvature of the
    space-time curve w.r.t. time.'''
    # THIS IS THE SIGNED CURVATURE
    # KAPPA = \frac{ x'y'' - y'x'' }{ (x'^2 + y'^2)^(3/2)}
    x1 = firstDerivCenter( x, dt, k )
    x2 = secondDeriv( x, dt, k )
    y1 = firstDerivCenter( y, dt, k )
    y2 = secondDeriv( y, dt, k )
    
    num = x1 * y2 - y1 * x2
    denom = x1 * x1 + y1 * y1
    badDenom = np.nonzero( denom < 0.01 )[0] # velocity falls to zero
    for bad in badDenom:
        if ( bad == 0 ):
            denom[ bad ] = denom[1]
        elif ( bad == denom.size - 1 ):
            denom[ bad ] = denom[-2]
        else:
            denom[ bad ] = ( denom[ bad - 1 ] + denom[ bad + 1 ] ) / 2.0
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