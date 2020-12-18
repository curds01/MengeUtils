# Strategy for adding missing unit tests

## Files and what they import

o agent.py
o agent_set.py
  - ObjSlice.AABB
  - primitives.Vector3
o agentPlacement
  - primitives.Vector2
o AnalysisTasks.py
  - primitives.(Vector2, Segment, segmentsFromString)
  - trajectory.scbData.NPFrameSet
  - Crowd
  - Kernels
  - Signals
  - GFSVis.visualizeGFS
  - Grid.makeDomain
  - ColorMap
  - domains.RectDomain
o analyzeCrowd.py
  - GLWidget
  - anaylzeWidgets.(AnalaysisWidget, SystemResource)
  - AnalysisTask.readAnalysisProject
  - scb_qt_playback.PlayerController
o analyzeWidgets.py
  - ColorMap
  - obstacles.readObstacles
  - qtcontext
  - AnalysisTask
  - CrowdWork.CrowdAnalyzeThread
  - trajectory.scbData.NPFrameSet
o bound.py
  - primitives.Vector2
o color.py
o ColorMap.py
  - color
o commandline.py
o ComputeNorms.py
  - Grid.Grid
  - GridFileSequence.GridFileSequence
  - primitives.Vector2
o Context.py
o Crowd.py
  - ColorMap
  - Grid
  - Signals
  - Kernels
  - GridFileSequence
  - flow
  - primtives.(Vector2, Segment)
  - trace.renderTraces
  - ObjSlice.Polygon
  - obstacles
  - GFSVis.visualizeGFS
  - stats.StatRecord
o crowdConsistency.py
  - trajectory.scbData.NPFrameSet
o CrowdWork.py
o denseTest.py
o distance.py
o DistFuncs.py
o domains.py
  - primitives.Vector2
o drawVoronoi.py
  - primitives.Vector2
  - GFSVis.(drawObstacles, drawSites)
o exportASF.py
  - maya
o fakeRotation.py
  - trajectory.scbData.(NPPFrameSet, writeNPSCB)
o fieldTools.py
  - vField
o flow.py
  - primitives.Vector3, Vector2, Segment
o flowContext.py
  - Context
  - primitives.Vector2, Segment
o GFSVis.py
  - GridFileSequence GFS
  - ColorMap
  - trajectory.loadTrajectory
o glPrimitives
  - primitives.Segment
o GLWidget.py
  - Context
  - ObjSlice.AABB
o GoalContext.py
  - RoadContext.PGContext, MouseEnabled, PGMouse
  - Context.BaseContext, ContextResult
  - GoalEditor
  - Goals
  - paths
o GoalEditor.py
  - Goals
o Goals
  - primitives.Vector2
o graph.py
o Grid.py 
  - domains.RectDomain
  - primitives.Vector2
o GridFileSequence.py
  - stats.StatRecord
  - Grid
  - RasterGrid.RasterGrid
  - primitives.Vector2
  - ThreadRasterization
  - Kernels
  - Signals (Signals.PedestrianSignal for "splatting agents")
o HeightFIeld.py
  - trajectory.gaussian1D (actually, trajectory.smoothTrajectory.gaussian1D)
o IncludeHeader.py
o KDTree.py
  - ObstacleStructure
  - primitives.Vector2
o Kernels
  - primitives.Vector2
  - domains
  - Signals
o ktest.py (move to unit tests)
  - Grid
  - Kernels
  - Signals
  - primitives.Vector2
  - ColorMap.BlackBodyMap
  - obstacles
  - ObstacleHandler
  - Voronoi
  - trajectory.loadTrajectory
o navMesh.py
  - primitives.Vector2
o navMeshToObst.py
  - navMesh.Obstacle
o ObjReader.py
  - primitives
o ObjSlice.py
  - ObjReader.ObjFile
  - primitives.Vector3, Vector2
o objToH3D.py
  - ObjReader
o objToNavMesh.py
  - ObjReader.ObjFile
  - navMesh.Node, Edge, Obstacle, NavMesh
  - primitives.Vector2
o obst2XML.py
  - ObjSlice.Segment, Polygon, buildPolygons
  - primitives.Vector3
o ObstacleHandler.py
  - IncludeHeader
  - KDTree
  - ObstacleList
  - obstacles
  - primitives
o ObstacleList.py
  - IncludeHeader
  - ObstacleStructure.ObstacleStructure
o obstacles.py
  - ObjSlice.AABB, Segment, Polygon
  - primitives.Vector3, Vector2
o ObstacleStructure
  - primitives.Vector2
o paths.py
o pilgrims.py
  - obstacles
  - primitives.Vector2
o primitives.py
o qtcontext.py
  - Context
  - flowContext.FlowLineContext
  - rectContext.RectContext
  - vFieldContext.FieldComainContext
  - Kernels
o RasterGrid
  - Grid.DataGrid
  - primitives.Vector2
o rectContext.py
  - Context
  - primitives.Vector2
  - domains.RectDomain
o RoadContext.py
  - Context.BaseContext, ContextResult
  - fieldTools
  - trajectory.scbData
  - primitives.Vector2
  - obstacles.GLPoly
  - paths
o roadmapBuilder.py
  - primitives.Vector3
  - view.View
  - paths
  - agent
  - graph
  - obstacles
  - vField.GLVectorField
  - RoadContext
  - GoalContext
  - GoalEditor
  - Goals
  - Context
o scb_qt_playback.py
  - agent_set.AgentSet
o scbData.py
  - trajectory.scbData
o scbMetric.py
  - trajectory.scbdata
o scbPlotOrient.py
  - trajectory.NPFrameSet
o scbSlice.py
o Select.py
o Signals.py
  - Grid
  - GridFileSequence.GridFileSequenceReader
    - it requires the symbol for the express purpose of testing an object against
      the GridFileSequenceReader *type*.
  - domains
o stats
o tawafField.py
  - obstacles.readObstacles
  - vField.VectorField
- test.py -- just delete me.
o ThreadRasterization.py
  - Grid
  - Voronoi
  - drawVoronoi
o trace.py
o trajectory.py
o vField.py
  - primitives.Vector2
o vFieldContext.py
  - Context
  - vField.GLVectorField
o view.py
  - Select
o Voronoi.py
  - Grid.AbstractGrid
  - primitives.Vector2
o xformVectorField.py
  - vField
o trajectory/commonData.py
o trajectory/dataLoader.py
  - trajectory.scbData, julichData
o trajectory/julichData.py
  - trajectory.commonData
o trajectory/julichToSCB.py
  - fakeRotation
  - bound.AABB2D
  - primitives.Vector2
  - trajectory.JulichData
  - trajectory.scbData
o trajectory/scbData.py
  - primitives.Vector2
  - trajectory.commonData
o trajectory/scbTruncate.py
  - trajectory.scbData
o trajectory/smoothTrajectory.py
  - trajectory.dataLoader.loadTrajectory
  - trajectory.commonData
  - trajectory.scbData.SCBDataMemory
o trajectory/xform.py
  - trajectory.commonData
  - trajectory.scbData.SCBDataMemory
o trajectory/xformTrajectory.py
  - trajectory.dataLoader.loadTrajectory
  - trajectory.xform.TrajXform

## Dependency tree

Order the files such that it is guaranteed that if I work in sequence, by the
time I get to a file to test, all of its upstream dependencies have been
tested. Note: not everything higher on the list is a dependency.

 - [ ] primitives.py
   - [ ] agentPlacement.py
   - [ ] bound.py
   - [ ] domains.py
     - [ ] Grid.py
       - [ ] RaterGrid.py
       - [ ] Voronoi.py
       - [ ] Signals.py (ignoring the dependency on GridFileSequence *type*)
         - [ ] Kernels.py
   - [ ] flow.py
   - [ ] glPrimitives.py
   - [ ] Goals.py
     - [ ] GoalEditor.py
   - [ ] navMesh.py
     - [ ] navMeshToObst.py
   - [ ] ObjReader.py
     - [ ] ObjSlice.py
       - [ ] agent_set.py
         - [ ] scb_qt_playback.py
       - [ ] obstacles.py
         - [ ] pilgrims.py
       - [ ] obst2XML.py
     - [ ] objToH3D.py
     - [ ] objToNavMesh.py
   - [ ] ObstacleStructure
     - [ ] ObstacleList.py
     - [ ] KDTree.py
       - [ ] ObstacleHandler.py
   - [ ] vField
     - [ ] xformVectorField.py
     - [ ] fieldTools.py
     - [ ] tawafField.py
 - [ ] trajectory/commonData.py
   - [ ] trajectory/julichData.py
   - [ ] trajectory/scbData.py
     - [ ] trajectory/scbTruncate.py
     - [ ] trajectory/xform.py
     - [ ] fakeRotation.py
       - [ ] trajectory/julichToSCB.py
     - [ ] scbMetric.py
     - [ ] scbPlotOrient.py
     - [ ] crowdConsistency.py
   - [ ] trajectory/dataLoader.py
     - [ ] trajectory/smoothTrajectory.py
       - [ ] HeightField.py
     - [ ] trajectory.xformTrajectory.py
 - [ ] Blob of GFS interdependencies
   - [ ] drawVoroni.py
   - [ ] GFSVis.py
   - [ ] GridFileSequence.py
     - [ ] ComputeNorms.py
   - [ ] ThreadRasterization.py
 - [ ] Context.py
   - [ ] RoadContext.py
     - [ ] GoalContext.py
   - [ ] flowContext.py
   - [ ] GLWidget.py
   - [ ] rectContext.py
     - [ ] qtcontext.py
   - [ ] vFieldContext.py
 - [ ] color.py
   - [ ] ColorMap.py
 - [ ] Select.py
   - [ ] view.py
     - [ ] roadmapBuilder.py
 - [ ] stats.py
 - [ ] agent.py
 - [ ] CrowdWork.py
 - [ ] distance.py
 - [ ] DistFuncs.py
 - [ ] graph.py
 - [ ] paths.py
 - [ ] scbSlice.py
 - [ ] trace.py
   - [ ] Crowd.py
     - [ ] AnalysisTasks.py
       - [ ] analyzeWidgets.py
         - [ ] analyzeCrowd.py
 - [ ] trajectory.py
 
### Files that require no tests
 - scbData.py
 - ktest.py
 - IncludeHeader.py
 - exportASF.py
 - commandline.py

## Outstanding questions
  - this needs *huge* amounts of reorganization! More submodules would be good.
  - agent.py and agent_set.py both have AgentSet classes; reconcile them.
  - commandline.py should simply be eliminated in favor of `argparse`.
  - denseTest.py is a testing utility that should go into tests.
  - exportASF.py is probably no longer usable; it should be mothballed and
    updated to blender.
  - IncludeHeader.py seems *highly* disturbing and most likely unneccessary.
    Delete it!
  - obstacles: there are *lots* of definitions of obstacles. THey need to all
    be unified.
    
## Reorganization
  - I should separate core funtionality from executables
    - just as I have trajectory, I should also have other sub modules.
  