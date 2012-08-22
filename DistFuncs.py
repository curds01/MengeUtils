import numpy as np
import pylab as plt

AGENTRADIUS = 1.0

# Functions to estimate density used in Kernel class
def uniformFunc( dispX, dispY, radius ):
    """ Density Estimation using uniform function -> square in 2D """
    maskX = dispX <= radius
    maskY = dispY <= radius
    maskXY = maskX & maskY
    return maskXY/ float(radius *radius)

def linearFunc( dispX, dispY, radius):
    """ Density Esitmation using linear function -> cone in 2D """
    distXY = np.sqrt( dispX * dispX + dispY * dispY )
    maskXY = distXY <= radius
    valueXY = (radius - distXY) * maskXY
    ## For testing by ploting gradient or value of the function
    if ( False ):
        gradX, gradY = np.gradient(valueXY)
        gradMag = np.sqrt( gradX * gradX + gradY * gradY )
        plt.contour( valueXY )
        plt.axis('equal')
        plt.show()
    return valueXY

def biweightFunc( dispX, dispY, radius):
    rSqd = radius * radius
    dispYSqd = dispY * dispY
    distXY = dispX * dispX + dispYSqd
    maskXY = np.sqrt(distXY) <= radius
    valueXY = -( distXY )/rSqd
    valueXY += 1.0
    # Normalize the biweight function
    valueXY /= (4. * rSqd)/ 3.
    valueXY *= maskXY
    ##For testing by ploting gradient or value of the function
    if ( False ):
        gradX, gradY = np.gradient( valueXY )
        gradMag = np.sqrt( gradX * gradX + gradY * gradY )
        plt.contour( valueXY )
        plt.axis( 'equal' )
        plt.show()
    return valueXY
        
def gaussianFunc( dispX, dispY, radiusSqd ):
    """ Density Estimation  using gaussian function """
    return np.exp( -(dispX * dispX + dispY * dispY) / (2.0 * radiusSqd ) ) / ( 2.0 * np.pi * radiusSqd )

def variableGaussianFunc( dispX, dispY, smooth_sqrd ):
    """ Density Estimation  using gaussian function with varied radius"""
    # Have to be seperated from normal Gaussian for function pointer testing in Kernel and Grid file
    return np.exp( -(dispX * dispX + dispY * dispY) / (2.0 * radiusSqd * smooth_sqrd ) ) / ( 2.0 * np.pi *
                                                                radiusSqd * smooth_sqrd )

UNIFORM     = lambda X, Y, S: uniformFunc( X, Y, S ) 
GAUSS       = lambda X, Y, S: gaussianFunc( X, Y, S * S )
LINEAR      = lambda X, Y, S: linearFunc( X, Y, S * S )
BIWEIGHT    = lambda X, Y, S: biweightFunc( X, Y, S )
VARGAUSS    = lambda X, Y, S: variableGaussianFunc( X, Y, S * S)
VORONOI_UNI = lambda X, Y, S: uniformFunc( X, Y, S )

FUNCS_MAP = { "uniform": UNIFORM,
              "gaussian": GAUSS,
              "variable-gaussian":VARGAUSS,
              "linear": LINEAR,
              "biweight": BIWEIGHT,
              "voronoi-uniform": VORONOI_UNI
              }