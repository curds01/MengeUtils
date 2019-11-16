# Guide to the Unofficial Menge Utilities

This provides some documentation on how to use the unofficial menge-slightly-affiliated python
utilities. These utilities are a bunch of hacked-together processes and applications to facilitate
various aspects the crowd simulation process. They are not supported and most likely have bugs and
are definitely, on the whole, haphazardly architected. So, as with all things _caveat emptor_.

<!--
For your assistance, a [glossary](glossary.md) is provided to define various terms.
-->

## What is in the set of utilties?

There are two large-scale, richly featured tools for authoring and analysis:
  - [Crowd analysis](docs/analyze_crowd.md): A tool for performing _post hoc_ analysis on the
  results of Menge simulation. It consumes `scb` files and scene descriptions (particularly the
  obstacle definitions) and provides tools for performing various types of analysis on the movement
  of the crowd.
  - [Scenario Authoring](docs/roadmap_builder.md): A tool for authoring various aspects of a Menge
  scene including defining obstacles, placing  agents, defining goal sets, and building roadmaps and
  navigation fields.

And then a number of simpler utilities for facilitating authoring scenarios and analyzing results:
These are, more or less, the independent components
  - [Adding orientation to SCB data](docs/fake_rotation.md): Replaces orientation information in an
    `scb` file with a vector pointing in the direction travelled from time i to time i + 1.
  - [Creating 2D obstacles from 3D OBJ files](docs/obj_slice.md): Consumes an obj file and the
    definition of a plane. Slices the 3D file with the plane, creating obstacles of all of the
	intersecting edges.
  - [Creating a navigation mesh from an OBJ file](docs/obj_to_navmesh.md): Consumes an obj file and
    attempts to create a Menge-style navigation mesh.  The code is very fragile and requires a 
	well-conditioned mesh to function properly.
  - [Querying properties of SCB file](docs/scb_metric.md): Scans an `scb` file and computes and
    prints a number of metrics about the file.
  - [Plotting the time-dependent orietnation of an agent in an SCB file](docs/scb_plot_orient.md):
    Creates a graph of the orientation of an agent based on its `scb` file with respect to time.
  - [Sampling an SCB file -- reducing frames, agents, etc.](docs/scb_slice.md): Creates a new `scb`
    file from an input `scb` file by truncating and sampling the time steps.
  
## Dependencies

_Note: There is an active effort to modernize these utilities to Python 3._

  - Python 2.7
  - Numpy
  - Matplotlib
  - Pygame
  - PyOpenGL
  - PyQt4
  
