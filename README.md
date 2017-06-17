# MengeUtils
Collection of utilities for working with Menge configuration and output files

My own personal collection of utilities for working with Menge. The documentation is sporadic and incomplete. 
To gain access to the full documentation, message me (@curds01) and I can get you access.  The text below is the
initial text contained in the documentation.


# Guide to the Unofficial Menge Utilities
 
This provides some documentation on how to use the unofficial menge-slightly-affiliated python utilities.  These utilities 
are a bunch of hacked-together processes and applications to facilitate various aspects the crowd simulation process.  They 
are not supported and most likely have bugs and are definitely, on the whole, haphazardly architected.  So, as with all 
things caveat emptor.
 
For your assistance, a glossary is provided to define various terms.  Those terms which can be found in the glossary will 
appear like this.
 
## What is in the Utility Set?
These are, more or less, the independent components
  - `analyzeCrowd.py`: A tool for performing post hoc analysis on the results of Menge simulation.  It consumes scb files
  and scene descriptions (particularly the obstacle definitions) and provides tools for performing various types of 
  analysis on the movement of the crowd.
  - `fakeRotation.py`: Replaces orientation information in an scb file with a vector pointing in the direction travelled 
  from time i to time i + 1.
  - `ObjSlice.py`: Consumes an obj file and the definition of a plane.  Slices the 3D file with the plane, creating 
  obstacles of all of the intersecting edges.
  - `objToNavMesh.py`: Consumes an obj file and attempts to create a Menge-style navigation mesh.  The code is very 
  fragile and requires a well-conditioned mesh to function properly.
  - `roadmapBuilder.py`: A tool for authoring various aspects of a Menge scene including defining obstacles, placing 
  agents, defining goal sets, building roadmaps and navigation fields.
  - `scbMetric.py`: Scans an scb file and computes and prints a number of metrics about the file.
  - `scbPlotOrient.py`: Creates a graph of the orientation of an agent based on its scb file with respect to time.
  - `scbSlice.py`: Creates a new scb file from an input scb file by truncating and sampling the time steps.

## Dependencies
  - Python 2.7
  - Numpy
  - Matplotlib
  - Pygame
  - pyopengl
  - pyqt4
