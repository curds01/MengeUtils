# Given the root of a skeleton, and a file name, exports an asf file of the skeleton

from maya.OpenMaya import *
from maya.OpenMayaAnim import *
import maya.cmds as cmds
import maya.mel as MEL
import asfReader as asf
from math import sqrt, pi
import os

# This is a naive exporter it makes the following assumptions:
#   1. All children of a single node are at the same place

VERSION = '1.0'
ROT_ORDER = ['invalid', 'xyz', 'yzx', 'zxy', 'xzy', 'yxz', 'zyx' ]

def ERROR( msg ):
    '''Prints an error message'''
    print "***", msg

def confirmRoot():
    '''Confirms that the root is selected and returns....
    ... currently returns None, if not a valid root or
    the MDagPath to the root if valid.
    '''
    # if nothing is selected, return None
    selected = MSelectionList()
    MGlobal.getActiveSelectionList( selected )
    if ( selected.length() == 0 ):
        ERROR( "Nothing selected!  Please select the root node" )
        return None
    if ( selected.length() > 1 ):
        ERROR( "Too many objects selected!  Please select ONLY the root node" )
        return None
    path = MDagPath()
    selected.getDagPath( 0, path )
    objName = path.partialPathName()
    # confirm it is a joint
    if ( not path.node().hasFn( MFn.kJoint ) ):
        ERROR( "The root must be a joint object" )
        return None
    # confirm it has no joint parents
    if ( path.length() > 1):
        print "Path length:", path.length()
        path.pop(0)
        print "PARENT:", path.partialPathName()
        if ( path.node().hasFn( MFn.kJoint ) ):
            ERROR( "The root node cannot have any joint parents.  All other parents will be ignored" )
            return None
        selected.getDagPath( 0, path )
    return path

def getJointPosition( dagPath ):
    '''Returns a tuple of the joint's position'''
    return MEL.eval( 'getAttr %s.t' % dagPath.fullPathName() )
    
def getJointOrientation( dagPath ):
    '''Returns a tuple of the joint's orientation'''
    return MEL.eval( 'getAttr %s.r' % dagPath.fullPathName() )
    
def initASF( rootDagPath, tgtLen=1.0 ):
    '''Creates an ASFFile object and initializes very components'''
    asfFile = asf.ASFFile()
    asfFile.name = rootDagPath.partialPathName()
    u = asf.ASFUnits()
    u.addUnit( 'mass', '1.0' )
    u.addUnit( 'length', '%.4f' % tgtLen )
    u.addUnit( 'angle', 'deg' )
    asfFile.units = u
    asfFile.doc = '\tExported via exportASF version %s\n\tThe unit length value of 0.0245 indicates that the exported units are already meters.\n' % VERSION
    r = asf.ASFRoot()
    asfFile.root = r
    r.order = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz' ]
    r.axis = getBoneRotOrder( rootDagPath )
    r.pos = getJointPosition( rootDagPath )
    r.orient = getJointOrientation( rootDagPath )
    asfFile.version = '1.10'
    return asfFile

def getBoneRotOrder( path ):
    '''Returns a string representing the rotation order of the joint'''
    return 'XYZ'
    j = MFnTransform( path.node() )
    rotOrder = j.rotationOrder()
    return ROT_ORDER[ rotOrder ]  # TODO: Get the real order

def getBoneDimensions( path ):
    '''Returns the direction and length of the bone'''
    for i in xrange( path.childCount() ):
        c = path.child( i )
        if ( c.hasFn( MFn.kJoint ) ):
            child = MFnTransform( c )
            cPath = MDagPath()
            child.getPath( cPath )
            dx, dy, dz = getBoneDisplacement( path, cPath )
            l = sqrt( dx * dx + dy * dy + dz * dz )
            return ( dx / l, dy / l, dz / l ), l
    raise ValueError, "Can't get bone length for a joint that has no joint children"

def getBoneDirection( parentPath, childPath ):
    '''Computes the direction vector from the parent towards the child'''
    dx, dy, dz = getBoneDisplacement( parentPath, childPath )
    mag = sqrt( dx * dx + dy * dy + dz * dz )
    if ( mag > 0.0 ):
        dx /= mag
        dy /= mag
        dz /= mag
    return ( dx, dy, dz )

def getBoneDisplacement( parentPath, childPath ):
    '''Computes the displacement from the parent to the child node in world coordinates'''
    pPos = cmds.xform( parentPath.partialPathName(), q=True, ws=True, t=True )
    cPos = cmds.xform( childPath.partialPathName(), q=True, ws=True, t=True )
    dx = cPos[0] - pPos[0]
    dy = cPos[1] - pPos[1]
    dz = cPos[2] - pPos[2]
    
    return dx, dy, dz

def getBoneLength( path ):
    '''Compute the length of bone at path'''
    # it's the magnitude of the displacement of THIS node to its child
    for i in xrange( path.childCount() ):
        c = path.child( i )
        if ( c.hasFn( MFn.kJoint ) ):
            child = MFnTransform( c )
            cPath = MDagPath()
            child.getPath( cPath )
            dx, dy, dz = getBoneDisplacement( path, cPath )
            return sqrt( dx * dx + dy * dy + dz * dz )
    raise ValueError, "Can't get bone length for a joint that has no joint children"

def getBoneDofs( path ):
    '''Create a list of dof values for this bone'''
    # only test rotation dofs
    dofs = []
    jName = path.partialPathName()
    if ( cmds.getAttr( '%s.jointTypeX' % jName ) ):
        dofs.append( 'rx' )
    if ( cmds.getAttr( '%s.jointTypeY' % jName ) ):
        dofs.append( 'ry' )
    if ( cmds.getAttr( '%s.jointTypeZ' % jName ) ):
        dofs.append( 'rz' )
    return dofs

def isASFBone( obj ):
    '''Determines if the MObject points to a valid asfbone joint.  Returns
    a MDagPath if it is valid, none otherwise'''
    if ( obj.hasFn( MFn.kJoint ) ):
        joint = MFnTransform( obj )
        path = MDagPath()
        joint.getPath( path )
        for i in xrange( path.childCount() ):
            c = path.child( i )
            if ( c.hasFn( MFn.kJoint ) ):
                return path            
    return None

def getJointOrient( path ):
    '''Return the joint orientation (as a quaternion) of the joint pointed to at the path'''
    j = MFnIkJoint( path.node() )
    q = MQuaternion()
    j.getOrientation( q )
    return q

def buildSkeletonRec( parentData, asfFile, hMap, posScale ):
    '''Recursively (depth-first) build the skeleton rooted at path'''
    RAD_TO_DEG = 180.0 / pi
    pNode, pPath, pJO = parentData
    pName = pPath.partialPathName()
    childCount = pPath.childCount()
    for i in xrange( childCount ):
        childObj = pPath.child( i )
        path = isASFBone( childObj )
        if ( path ):
            cName = path.partialPathName()
            bone = asf.ASFBone()
            bone.name = cName
            d, l = getBoneDimensions( path )
            bone.direction = d
            bone.length = l * posScale
            bone.dof = getBoneDofs( path )
            asfFile.bones.append( bone )
            bone.id = len( asfFile.bones )
            childJO = pJO * getJointOrient( path )
            euler = childJO.asEulerRotation()
            bone.axis = ( euler.x * RAD_TO_DEG, euler.y * RAD_TO_DEG, euler.z * RAD_TO_DEG, getBoneRotOrder( path ) )
            # TODO: include limits
            cName = path.partialPathName()
            if ( hMap.has_key( pName ) ):
                hMap[ pName ].append( cName )
            else:
                hMap[ pName ] = [ cName ]
            buildSkeletonRec( ( bone, path, childJO ), asfFile, hMap, posScale )
            
def buildSkeleton( rootDagPath, asfFile, tgtLen ):
    '''Builds the skeleton from the root.
    Returns a dictionary outlining the hierarchy'''
    posScale = 100.0 * tgtLen / 2.54
    hierarchyMap = {} # a dictionary mapping node name to list of children
    buildSkeletonRec( ( asfFile.root, rootDagPath, getJointOrient( rootDagPath ) ), asfFile, hierarchyMap, posScale )
    asfFile.hierarchy = asf.ASFHierarchy( asfFile.root, asfFile.bones )
    # use the hierarchyMap to build the hierarchy
    asfFile.hierarchy.buildFromMap( hierarchyMap )
    # count up the dofs
    dofCount = 6
    for b in asfFile.bones:
        dofCount += len( b.dof )
    print "Found %d degrees of freedom" % dofCount
                
    
def makeDofList( fileName, asfFile ):
    '''Createas a dof file for the accompnaying asffile'''
    base, ext = os.path.splitext( fileName )
    dofFileName = base + '.dof'
    
    dofs = asfFile.enumerateDofs()
    f = open( dofFileName, 'w' )
    for d in dofs:
        f.write( '%s\n' % d )
    f.close()
    

def exportASF( fileName, tgtLen=0.0254 ):
    '''Exports the selected skeleton to the given asfFile.  The length units value is
    based on the meterSize'''
    print "Exporting to asf file:", fileName
    root = confirmRoot()
    if ( root ):
        print "Now doing the work"
        asfFile = initASF( root, tgtLen )
        # find all the bones
        buildSkeleton( root, asfFile, tgtLen )
        # build the hierarchy
        # output the formatted asf file
        f = open( fileName, 'w' )
        f.write( asfFile.format() )
        f.close()
        makeDofList( fileName, asfFile )
        

exportASF( 'k:/footstep/motion_capture/mayaConvert/test02.asf', 0.45 )        