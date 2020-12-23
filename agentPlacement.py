# coding=utf-8
"""A collection of methods for placing blocks of disk agents."""

#TODO: Use Poisson-disk distribution to fill an area
import numpy as np
import random

import sys
OBJ_READER_PATH = '\\projects\\objreader'
if not OBJ_READER_PATH in sys.path:
    sys.path.insert(0, OBJ_READER_PATH)
from primitives import Vector2

        
def _disk_distance_for_density(target_density, radius):
    """Given the radius of an agent and the desired density, returns the
    distance between "adjacent" agent centers.

    It should be the case that:
        _disk_distance_for_density(_max_density_for_disk(radius), radius)
    is equal to 2 * radius.

        Raises:
            ValueError: if the requested target density is too high for agents
              with the given radius."""
    max_density = _max_density_for_disk(radius)
    if target_density > max_density:
        raise ValueError(
            ("For an agent with radius {}, requested density must be smaller "
             "than {}; requested density {}.").format(
                radius, max_density, target_density))
    return 2 * _effective_radius(target_density)


def _max_density_for_disk(radius):
    """Computes the maximum collision-free density for disk agents of the given
    radius.

    It should be the case that:
        _disk_distance_for_density(_max_density_for_disk(radius), radius)
    is equal to 2 * radius."""
    # The hexagonal pattern is shown below. We can draw a single box through
    # four disk centers. This box represents the tileable pattern. The box has
    # dimensions 2R x 2R⋅√3, yielding an area of 2R²√3. Inside the box, the
    # total disk area is 2 (the wholly contained center disk, and the four
    # quarter disks in each corner. Therefore, the density is:
    #  2 / 2R²√3 = 1 / R²√3
    #                          2R
    #                   ┆               ┆
    #           uuuu vvv┆vvv uuuuuuu vvv┆vvv uuuu
    #             vv    ┆    vv   vv    ┆    vv
    #            v      ┆      v v      ┆      v
    #           v       ┆       v       ┆       v
    #           v       o───────────────o┄┄┄┄┄┄┄┄┄┄┄┄┄┄
    #           v       │       v       │       v
    #            v      │      v v      │      v
    #             vv    │    vv   vv    │    vv
    #           uuuu vvv│vvv uuuuuuu vvv│vvv uuuu         R⋅√3
    #                uu │ uu         uu │ uu
    #                  u│u             u│u
    #                   │               │
    #            o      │       o┄┄┄┄┄┄┄│┄┄┄┄┄┄┄┄┄┄┄┄┄┄
    #                   │               │
    #                  u│u             u│u
    #                uu │ uu         uu │ uu
    #           uuuu vvv│vvv uuuuuuu vvv│vvv uuuu         R⋅√3
    #             vv    │    vv   vv    │    vv
    #            v      │      v v      │      v
    #           v       │       v       │       v
    #           v       o───────────────o┄┄┄┄┄┄┄┄┄┄┄┄┄┄
    #           v               v               v
    #            v             v v             v
    #             vv         vv   vv         vv
    #           uuuu vvvvvvv uuuuuuu vvvvvvv uuuu
    assert(radius > 0)
    return 1.0 / (radius * radius * 2.0 * np.sqrt(3.0))


def _effective_radius(density):
    """Given the desired density, returns the radius of the disk which, if
    maximally packed, would produce that density.

    It should be the case that:
        _effective_radius(_max_density_for_disk(radius), radius) == radius.
    is True."""
    assert(density > 0)
    return 1.0 / (np.sqrt(density * 2 * np.sqrt(3)))


def make_ranks_in_x(start_x, start_y, agt_distance, rank_distance, rank_count,
                    rank_length, noise=(0, 0), max_count=-1):
    """Creates a block of agents with ranks parallel with the x-axis.

                    1  2  .  .  .  rank_length
       rank_count   O  O  O  O  O  O
             .       O  O  O  O  O
             .      O  O  O  O  O  O
             .        O  O  O  O  O    _
             2      O  O  O  O  O  O   _ rank_distance
             1        O  O  O  O  O
             0      O  O  O  O  O| |O
                    ^             ^
                    |             |
           (start_x, start_y)     agt_distance

    The basic configuration of the agent positions forms a uniform block.
    The agents are organized in ranks. The ranks are parallel with the x-axis.
    Along each rank, the agent centers are `agt_distance` units apart. Each
    rank is, in turn, separated by `rank_distance` units along the y-axis.
    Furthermore, the ranks are offset such that they form a hexagonal lattice.
    There are `rank_count` total ranks. Ranks alternate between being a "major"
    and "minor" rank. Major ranks have `rank_length` agents and minor ranks
    have one fewer.

    The first agent is located at (start_x, start_y) and the direction that
    the ranks grow is based on the *signs* of `agt_distance` and
    `rank_distance`. Positive distances grow the block in the positive x- and
    y-axis directions. Negative distances in the negative directions.

    The basic configuration can be modified in two ways. Limiting the count
    (via `max_count`) such that the block is incomplete, or perturbing the
    positions of the agents using `noise`.

        Args:
            start_x: A float. The x-position of the first (aka "anchor") agent.
            start_y: A float. The y-position of the first (aka "anchor") agent.
            agt_distance: A float. The signed distance between agents on a
              rank. If negative, the agents are distributed to the left of
              the first agent.
            rank_distance: A float. The signed distance between ranks. If
              negative, the ranks are positioned in the -y direction from the
              first agent.
            rank_count: An int. The total number of ranks.
            rank_length: An int. The population of the major ranks (the minor
              ranks have one fewer).
            noise: A 2-tuple of floats. Optional specification of positional
              noise based on a gaussian distribution. noise[0] and noise[1] are
              the mean and standard deviation of the noise, respectively.
            max_count: An int. The maximum number of agents to create. If
              max_count is <= 0, there is no limit. Otherwise, no more than
              max_count number of positions are defined.

        Returns:
            An Nx2 array of agent positions. Each row is one agent position
              where the 0- and 1st columns are the x- and y-positions,
              respectively."""
    major_count = rank_count / 2 + (rank_count % 2)
    minor_count = rank_count - major_count
    full_rank_population = (major_count * rank_length +
                            minor_count * (rank_length - 1))
    # We use the full population if the limit is undefined (aka -1) or larger
    # than the full population.
    if not(0 <= max_count <= full_rank_population):
        max_count = full_rank_population

    positions = np.empty((max_count, 2), dtype=np.float32)
    
    a = 0    
    y = start_y
    for rank in range(rank_count):
        if a >= max_count:
            break
        x = start_x
        count = rank_length
        if rank % 2:
            x += agt_distance * 0.5
            count -= 1
        for pos in range(count):
            px = x
            py = y
            if noise:
                px += random.gauss(noise[0], noise[1])
                py += random.gauss(noise[0], noise[1])
            positions[a, :] = (px, py)
            a += 1
            if a >= max_count:
                break
            x += agt_distance
        y += rank_distance
    return positions


def make_ranks_in_y(start_x, start_y, agt_distance, rank_distance, rank_count,
                    rank_length, noise=(0, 0), max_count=-1):
    """Variation of make_ranks_in_y that aligns the ranks with the y-axis. In
    all other respects, it is identical."""
    row_agents = make_ranks_in_x(start_x, start_y, agt_distance, rank_distance,
                                 rank_count, rank_length, noise, max_count)
    # To translate from make_ranks_in_x to make_ranks_in_y, we *essentially*
    # want to mirror the agent positions around a line parallel to y = x.
    # However, that line passes through (startX, startY). So, the transpose is
    # achieved by swapping the x- an y-positions (modified to handle the
    # arbitrary origin).
    row_x = np.array(row_agents[:, 0]) - start_x + start_y
    row_agents[:, 0] = row_agents[:, 1] - start_y + start_x
    row_agents[:, 1] = row_x
    return row_agents


def _distances_in_ranks(radius):
    """Given the effective radius of an agent, computes the distance ALONG the
    rank between agent centers and between ranks.

        Args:
            radius: A float. The radius of the agent to pack.

        Returns:
            A 2-tuple of floats: (`agt_distance`, `rank_distance`), where
              `agt_distance` is the distance between agents on a single rank
              and `rank_distance` is the distance between ranks."""
    return 2.0 * radius, np.sqrt(3.0) * radius


# rank organization - rows or columns
RANK_IN_Y = 1
RANK_IN_X = 2


def fill_rectangle(radius, min_x, min_y, max_x, max_y, density, rank_dir,
                   noise=None):
    """Fills a rectangular region with agent positions.

    Agent positions are created in a hexagonal lattice contained within a given
    rectangular region. The spacing between the agents is based on the
    requested `density` value. If no noise is applied, all agents are
    guaranteed to be *completely* inside the rectangular region (the addition
    of noise breaks that guarantee).

    The ranks are aligned with either the x- or y-axis values based on the
    value of `rank_dir`. The agent lattice is *centered* in the rectangle;
    there may be space between the outer-most agents and the rectangle
    boundary.

    If we compute the average density in the rectangular region (total
    population divided by rectangle area) it will *always* be less than the
    requested density. The `density` value only serves as a *guideline* for
    spacing.

    The image below illustrates such a configuration with the ranks aligned
    along the x-axis.

                                        (max_x, max_y)
                                       ╱
                   ┌──────────────────┐
                   │ O    O    O    O │
                   │    O    O    O   │
                   │ O    O    O    O │
                   │    O    O    O   │
                   │ O    O    O    O │         y
                   │    O    O    O   │         ^
                   │ O    O    O    O │         │
                   │    O    O    O   │         │
                   │ O    O    O    O │         │
                   └──────────────────┘         └──────>  x
                  ╱
    (min_x, min_y)

        Args:
            radius: A float. The physical radius of the agents.
            min_x: A float. The value of the minimum extent of the rectangle
              along the x-axis.
            min_y: A float. The value of the minimum extent of the rectangle
              along the y-axis.
            max_x: A float. The value of the maximum extent of the rectangle
              along the x-axis.
            max_y: A float. The value of the maximum extent of the rectangle
              along the y-axis.
            density: A float. The targeted density of the population.
            rank_dir: An int. A Value from the set {RANK_IN_Y, RANK_IN_X}. It
              specifies the axis along which ranks are defined.
            noise: A 2-tuple of floats. Optional specification of positional
              noise based on a gaussian distribution. noise[0] and noise[1] are
              the mean and standard deviation of the noise, respectively.

        Returns:
            An Nx2 array of agent positions. Where N is the number of agents
            required to fill the space. The ith row consists of the x- and
            y-positions of the ith agent.

        Raises:
            ValueError: if a) the requested density is too high for agents of
              the given radius, b) the box's measures aren't at least equal
              to an agent's diameter, or c) in the rank direction, the box is
              too narrow to fit two agents at the given density."""
    R = _effective_radius(density)
    if R < radius:
        raise ValueError(("The requested density {} is too high for the given "
                          "agent radius {}").format(density, radius))

    # Shrink the rectangular domain by radius, so we know that the regular
    # lattice keeps all agents inside the rectangle.
    max_x -= radius
    max_y -= radius
    min_y += radius
    min_x += radius
    # We'll define ranks in the "width" direction. We initially assume ranks
    # in the x-direction.
    width = max_x - min_x
    height = max_y - min_y
    if rank_dir == RANK_IN_Y:
        # Reverse the meaning of "width" and "height" if ranks go in the
        # y-direction.
        width, height = (height, width)

    if width < 0 or height < 0:
        raise ValueError(("The rectangle dimensions ({}, {}) are too small to "
                          "contain agents with radius {}").format(
            width + 2 * radius, height + 2 * radius, radius))

    agt_distance, rank_distance = _distances_in_ranks(R)
    if width < agt_distance:
        raise ValueError(
            ("Rectangle is too small in the rank direction ({}) to support "
             "the requested density: {}; minor ranks would have no agents.")
                .format(width, density))
    rank_population = int(width / agt_distance) + 1
    rank_count = int(height / rank_distance) + 1

    # We need to center the lattice. So, compute the size of the bounding box
    # in each direction and offset the starting position of the lattice by
    # that amount.
    lattice_width = agt_distance * (rank_population - 1)
    lattice_height = rank_distance * (rank_count - 1)
    rank_offset = (width - lattice_width) / 2
    row_offset = (height - lattice_height) / 2

    if rank_dir == RANK_IN_X:
        return make_ranks_in_x(min_x + rank_offset, min_y + row_offset,
                               agt_distance, rank_distance, rank_count,
                               rank_population, noise)
    elif rank_dir == RANK_IN_Y:
        return make_ranks_in_y(min_x + row_offset, min_y + rank_offset,
                               agt_distance, rank_distance, rank_count,
                               rank_population, noise)


def corridor_mob(radius, p_FQ, p_FR, density, agent_count, noise=None):
    """Populates a "corridor" with a requested number of agents.

    A "corridor" is an unbounded rectangular region. The width of the region
    is defined by the line segment QR. Furthermore, the line segment defines
    the "front" of the rectangular region. The corresponding "back" boundary is
    however far it needs to be to encompass the requested number of agents.

    The corridor is defined in a local frame: C. The +x direction of Frame C
    (Cx) is parallel with p_QR. The +y direction of Frame C (Cy) is:
    [-p_QR.y, p_QR.x] (i.e., the direction of p_QR rotated counter-clockwise).

    The agents are placed in the corridor forming a "block" of agents such
    that:
      1. The block fills the width of the corridor to the maximum possible
         amount based on the requested `density`.
      2. The block touches the front edge of the region, and extends in the +Cy
         direction.
      3. The ranks are oriented parallel with the front line segment
      4. The block is centered on the front edge.
      5. The ranks are filled in the +Cx direction, adding rows to reach the
         requested `agent_count` number of agents. The last rank may not be
         filled.

       Q
        ┌─────────────────┄┄┄┄┄┄              ┌─────> Cx
        │O   O   O   O   O   O                │
        │  O   O   O   O   O                  v
        │O   O   O   O   O   O                Cy
        └─────────────────┄┄┄┄┄┄
       R

        Args:
            radius: A float. The physical radius of the agents.
            p_FQ: A Vector2. The point Q, measured and expressed in Frame F.
            p_FR: A Vector2. The point R, measured and expressed in Frame F.
            density: A float. The targeted density of the positions.
            noise: A 2-tuple of floats. Optional specification of positional
              noise based on a gaussian distribution. noise[0] and noise[1] are
              the mean and standard deviation of the noise, respectively.
            agent_count: An int. The total number of agents to create.

        Returns:
            An Nx2 array of agent positions. N is the number of agents required
              to fill the space. The ith row consists of the x- and y-positions
              of the ith agent, measured and expressed in Frame F.

        Raise:
            ValueError: If a) the density is too high for the given agent
              radius, or b) the corridor is too narrow to accommodate an agent.
    """
    R = _effective_radius(density)
    if R < radius:
        raise ValueError(("The requested density {} is too high for the given "
                          "agent radius {}").format(density, radius))
    agt_distance, rank_distance = _distances_in_ranks(R)

    # We'll compute the agent positions in frame C (the corridor extends
    # into the +Cy direction and the front segment is centered on Co).
    p_QR_F = p_FR - p_FQ
    width = p_QR_F.magnitude()
    if width < 2 * radius:
        raise ValueError(
            ("The corridor width ({}) is too small to contain agents with "
             "radius {}").format(width, radius))

    rank_population = int(width / agt_distance) + 1
    rank_width = (rank_population - 1) * agt_distance
    min_x = -rank_width / 2
    rank_count = (agent_count / (2 * rank_population - 1) + 1) * 2
    pos_C = make_ranks_in_x(start_x=min_x, start_y=radius,
                            agt_distance=agt_distance,
                            rank_distance=rank_distance,
                            rank_count=rank_count,
                            rank_length=rank_population, noise=noise,
                            max_count=agent_count)

    # Now transform from C to F.
    Cx_F = p_QR_F.normalize()
    Cy_F = Vector2(-Cx_F.y, Cx_F.x)
    # Build rotation matrix from rows.
    R_CF = np.array((Cx_F.asTuple(), Cy_F.asTuple()))
    p_FM = (p_FQ + p_FR) * 0.5

    # Ordinarily, we'd want to write: pos_F = R_FC * pos_C (as
    # pos_F = np.dot(R_FC, pos_C)) but for numpy's broadcasting to work, we
    # have to *right* multiply as: pos_C * R_CF.
    pos_F = np.dot(pos_C, R_CF) + p_FM.asTuple()

    return pos_F


def rectMob( radius, anchor, vertCenter, horzCenter, aspectRatio, avgDensity, rankDir, agentCount, noise=None, orient=0.0 ):
    """Creates a rectangular mob of people.  The mob is anchored on the given point and the rows
    and columns are configured based on the desired aspect ratio and average density.

    @param      radius      float - physical radius of the agents    
    @param      anchor      Vector2 - The anchor of the mob
    @param      vertCenter  float - The vertical alignment of the mob to the anchor point.  If vertCenter
                            is zero, it aligns to the bottom, 1 aligns to the top, 0.5 to the center, etc.
    @param      horzCenter  float - the horizontal alignment of the mob to the anchor point. If horzCetner
                            is zero, it aligns to the left, 1 alings to the right, 0.5 to the center, etc.
    @param      aspectRatio float - the desired aspect ratio of the mob
    @param      avgDensity  float - the average density of the positions
    @param      rankDir     int - value from the set {RANK_IN_Y, RANK_IN_X} specifies in which
                                  direction the agents form lines (y- or x-axis, respecitvely).
                                  row rank is parallel with the front line, column is perpendicular
    @param      agentCount  int - the total number of agents to create
    @param      noise       (float, float) - an optional 2-tuple representing normal
                                        distribution where noise[0] and noise[1] are the
                                        mean and standard deviation of the noise, respectively
    @param      orient      float - the orientation of the rectanble as given by the angle
                                    (in degrees).
    @returns    An Nx2 array of agent positions.  Where N is greater than or equal to agentCount
                the space.  The ith row consists of the x- and y-positions of the ith agent.
    """
    assert( horzCenter >= 0.0 and horzCenter <= 1.0 )
    assert( vertCenter >= 0.0 and vertCenter <= 1.0 )
    
    R = _effective_radius( avgDensity )
    D = 2 * R
    nbrDist, rankDist = _distances_in_ranks( R )
    if ( rankDir == RANK_IN_Y ):
        horzDist = rankDist
        vertDist = nbrDist
    elif ( rankDir == RANK_IN_X ):
        horzDist = nbrDist
        vertDist = rankDist
    else:
        raise AttributeError, "invalid rank direction: %s" % ( str( rankDir ) )

    # scale factor which, given a value for a, determines the value for b    
    bFromA = horzDist * aspectRatio / vertDist
    a = 1
    while ( True ):
        b = int( np.ceil ( bFromA * a ) )
        majorRows = b / 2 + b % 2
        minorRows = b - majorRows
        est = majorRows * a + minorRows * ( a - 1 )
        if ( est >= agentCount ):
            break
        a += 1
    # dimensions of rectangle
    W = horzDist * a + 2 * radius
    H = vertDist * b + 2 * radius
    minX = -horzCenter * W
    maxX = minX + W
    minY = ( vertCenter - 1)* H
    maxY = minY + H

    pos = fill_rectangle( radius, minX, minY, maxX, maxY, avgDensity, rankDir, noise )
    
    # transform generic positions for orientation and anchor
    xAxis = np.array( ( np.cos( orient * np.pi / 180.0 ), np.sin( orient * np.pi / 180.0 ) ) )
    yAxis = np.array( ( xAxis[1], -xAxis[0] ) )
    P_x = np.dot( pos, xAxis )
    P_y = np.dot( pos, yAxis )
    pos[:,0] = P_x + anchor[0]
    pos[:,1] = P_y + anchor[1]
    return pos


def getAABB( positions ):
    """Given the agent positions, reports the axis-aligned bounding box for the group.

    @param      positions       An Nx2 array of floats.  First and second columns are
                                the x- and y-positions, respectively.
    @returns    Two 2-tuples.  (minX, minY), (maxX, maxY)
    """
    return ( positions[:,0].min(), positions[:,1].min() ), ( positions[:,0].max(), positions[:,1].max() )
