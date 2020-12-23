# coding=utf-8
import agentPlacement as dut

import random
import unittest

import numpy as np

from primitives import Vector2

class TestAgentPlacement(unittest.TestCase):

    @staticmethod
    def calc_rank_stats(agents, rank_dir):
        """Returns the number of agents in the major rank (the first rank) and
        the total number of ranks."""
        if rank_dir == dut.RANK_IN_X:
            row_axis = 1
        elif rank_dir == dut.RANK_IN_Y:
            row_axis = 0
        else:
            raise ValueError("Bad value for rank_dir: {}".format(rank_dir))
        rank_population = 1
        row_value = agents[0, row_axis]
        for i in range(1, agents.shape[0]):
            if agents[i, row_axis] != row_value:
                break
            rank_population += 1
        rank_count = 0
        row_parity = 0
        agt = 0
        while agt < agents.shape[0]:
            rank_count += 1
            # There must always be at least one agent on a rank.
            agt += max(1, rank_population - row_parity)
            row_parity = row_parity ^ 1
        return rank_population, rank_count

    def test_density_and_distance(self):
        """Tests _disk_distance_for_density(), _max_density_for_disk(), and
        _effective_radius() for internal consistency."""
        # The two functions are *almost* inverses from each other. In fact,
        # _disk_distance_for_density() returns 2*R, but otherwise they should
        # be inverses of each other.
        # Other tests tests arbitrary sampled values.
        for radius in [0.25, 1.0, 2.75]:
            max_density = dut._max_density_for_disk(radius)
            center_distance = dut._disk_distance_for_density(max_density,
                                                             radius)
            self.assertAlmostEqual(center_distance / 2, radius, 5)
            self.assertAlmostEqual(
                dut._effective_radius(max_density), radius, 5)
            with self.assertRaisesRegexp(
                    ValueError,
                    "For an agent.+requested density must be smaller"):
                dut._disk_distance_for_density(max_density + 1e-5, radius)

    def test_disk_distance_for_density(self):
        # This test relies on a bunch of pre-computed values; there is no
        # reasonable alternative method for testing the code that would
        # validate the functionality.
        with self.assertRaisesRegexp(ValueError,
                                     ".+ requested density must be smaller.+"):
            dut._disk_distance_for_density(10, 1)
        # Note: as long as the density isn't too high for the given radius
        # value, the radius value has no bearing on the return value.
        self.assertEqual(dut._disk_distance_for_density(1, 0.25),
                         2 * dut._effective_radius(1))
        self.assertEqual(dut._disk_distance_for_density(0.5, 0.25),
                         2 * dut._effective_radius(0.5))

    def test_max_density_for_disk(self):
        # As with _disk_distance_for_density, the math in this function is such
        # that there is no ready alternative to test against. So, we'll have a
        # small number of curated values to detect regression.
        self.assertAlmostEqual(dut._max_density_for_disk(0.25), 4.6188, 3)
        self.assertAlmostEqual(dut._max_density_for_disk(0.35), 2.3565, 3)
        self.assertAlmostEqual(dut._max_density_for_disk(0.75), 0.5132, 3)

    def test_effective_radius(self):
        # We'll test this function with the recognition that, mathematically,
        # this is the *inverse* operation of maxDensity (but it isn't
        # implemented as such. If the implementation changes, we'll need to
        # reformulate the test.
        self.assertAlmostEqual(
            dut._effective_radius(1), 0.53728, 3)
        self.assertAlmostEqual(
            dut._effective_radius(0.5), 0.75983, 3)

    def evaluate_noise(self, agent_func):
        """Evaluates the impact of the noise 2-tuple (mean, stddev) on the
        given agent function. The `noise` parameter should be the only
        parameter."""
        # Noise; we'll test it in two parts. First, with a non-zero mean and a
        # 0 stddev, it should be a simple offset of mean in each direction.
        agents = agent_func((0, 0))
        for mean in (0.1, 0.25, 0.5):
            noise_agents = agent_func((mean, 0))
            for i in range(agents.shape[0]):
                delta = agents[i, :] - noise_agents[i, :]
                dist = np.sqrt(delta.dot(delta))
                expected_dist = np.sqrt(2) * mean
                # TODO: This is 5 places because I'm returning float32. Change
                #  it to just float (ideally double).
                self.assertAlmostEqual(dist, expected_dist, 5,
                                       "For mean {}".format(mean))
        # For non-zero standard deviation, we'll just assert that *some* of the
        # positions are not the same.
        for stddev in (0.1, 0.25, 0.5):
            noise_agents = agent_func((0, stddev))
            self.assertTrue(np.any(agents != noise_agents))
    def evaluate_agent_ranks(self, agent_func, rank_axis, row_axis):
        """Common test infrastructure for dut.make_ranks_in_x() and
        dut.make_ranks_in_y(). The two functions are closely related and this
        tests the shared properties."""
        # Confirm the "anchor" position is the position of agent 0. We're using
        # values that are perfectly represented in base 2 so that we can
        # guarantee exactitude in values.
        for x, y in ((0.25, 0.75), (-10.5, 12.25), (134.5, -22.75)):
            agents = agent_func(start_x=x, start_y=y, agt_distance=1,
                                rank_distance=1, rank_count=3, rank_length=3,
                                noise=(0, 0))
            self.assertTrue(np.all(agents[0, :] == (x, y)),
                            "{} == {}".format(agents[0, :], (x, y)))

        # Confirm agent distance (separation along the rank axis).
        for dist in (0.25, 5, -3, -0.75):
            agents = agent_func(start_x=0, start_y=0, agt_distance=dist,
                                rank_distance=1, rank_count=3, rank_length=3,
                                noise=(0, 0))
            for i in range(2):
                # For agent distance, we are defining the separation of agents
                # along the rank axis. All agents on a single rank should have
                # the same value on the row axis.
                self.assertEqual(agents[i, row_axis], agents[i + 1, row_axis])
                self.assertEqual(agents[i, rank_axis] + dist,
                                 agents[i + 1, rank_axis])

        # Confirm rank distance (separation on the row axis).
        for dist in (0.25, 5, -3, -0.75):
            agents = agent_func(start_x=0, start_y=0, agt_distance=1,
                                rank_distance=dist, rank_count=3,
                                rank_length=3, noise=(0, 0))
            # The indices of the first agent on each rank: 0, 3, 5.
            indices = (0, 3, 5)
            for i in range(2):
                # Testing the first agent in each row, we'll confirm their
                # position along the row-axis changes by the given distance.
                # The displacement along the rank-axis is more complex and is
                # left untested.
                self.assertEqual(agents[indices[i], row_axis] + dist,
                                 agents[indices[i + 1], row_axis])

        # Rank count, rank population.
        for rank_count, rank_pop, total_pop in ((1, 1, 1), (4, 3, 10)):
            agents = agent_func(start_x=0, start_y=0, agt_distance=1,
                                rank_distance=1, rank_count=rank_count,
                                rank_length=rank_pop, noise=(0, 0))
            self.assertEqual(agents.shape[0], total_pop)

        # Maximum agent count.
        # First test max_count being less than the nominal population.
        for limit in (1, 5, 7):
            for count, pop in ((10, 10), (3, 5), (8, 2)):
                agents = agent_func(start_x=0, start_y=0, agt_distance=1,
                                    rank_distance=1, rank_count=count,
                                    rank_length=pop, noise=(0, 0),
                                    max_count=limit)
                self.assertEqual(agents.shape[0], limit)
        # In the case where the maximum count is larger than the implied
        # population, we get the population.
        agents = agent_func(start_x=0, start_y=0, agt_distance=1,
                            rank_distance=1, rank_count=5, rank_length=5)
        lim_agents = agent_func(start_x=0, start_y=0, agt_distance=1,
                                rank_distance=1, rank_count=5, rank_length=5,
                                max_count=1000)
        self.assertEqual(agents.shape[0], lim_agents.shape[0])

        # Evaluate noise parameter.
        self.evaluate_noise(lambda noise: agent_func(start_x=0.25,
                                                     start_y=-0.75,
                                                     agt_distance=1,
                                                     rank_distance=1,
                                                     rank_count=3,
                                                     rank_length=3,
                                                     noise=noise))

    def test_make_ranks_in_x(self):
        self.evaluate_agent_ranks(dut.make_ranks_in_x, 0, 1)

    def test_make_ranks_in_y(self):
        self.evaluate_agent_ranks(dut.make_ranks_in_y, 1, 0)

    def test_fill_rectangle(self):
        # This implicitly tests the _distances_in_ranks() method.

        # Confirm rank direction is respected.
        # For ranks in y, adjacent agents should have a common x-value.
        agents = dut.fill_rectangle(
            radius=0.25, min_x=0, min_y=0, max_x=2, max_y=2, density=3,
            rank_dir=dut.RANK_IN_Y, noise=None)
        self.assertEqual(agents[0, 0], agents[1, 0])
        self.assertEqual(agents[1, 0], agents[2, 0])
        # For ranks in x, adjacent agents should have a common y-value.
        agents = dut.fill_rectangle(
            radius=0.25, min_x=0, min_y=0, max_x=2, max_y=2, density=3,
            rank_dir=dut.RANK_IN_X, noise=None)
        self.assertEqual(agents[0, 1], agents[1, 1])
        self.assertEqual(agents[1, 1], agents[2, 1])

        # The first agent is closest to the min corner and last agent is
        # closest to the max_corner.
        min_corner = np.array((0, 0))
        max_corner = np.array((2, 2))
        for rank_dir in (dut.RANK_IN_X, dut.RANK_IN_Y):
            agents = dut.fill_rectangle(
                radius=0.25, min_x=min_corner[0], min_y=min_corner[1],
                max_x=max_corner[0], max_y=max_corner[1], density=3,
                rank_dir=rank_dir, noise=None)
            p_CminV = agents - min_corner
            p_CmaxV = agents - max_corner
            dist_Cmin = np.sqrt(np.sum(p_CminV * p_CminV, axis=1))
            dist_Cmax = np.sqrt(np.sum(p_CmaxV * p_CmaxV, axis=1))
            self.assertEqual(dist_Cmin.argmin(), 0)
            self.assertEqual(dist_Cmax.argmin(), agents.shape[0] - 1)

        # Confirm all agents lie within the box (when there is no noise).
        min_x, min_y = (-0.25, 11.5)
        max_x, max_y = (12.3, 22.25)
        radius = 0.25
        agents = dut.fill_rectangle(
            radius=radius, min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y,
            density=0.5, rank_dir=dut.RANK_IN_Y, noise=None)
        are_inside = ((agents[:, 0] >= min_x + radius) &
                      (agents[:, 1] >= min_y + radius) &
                      (agents[:, 0] <= max_x - radius) &
                      (agents[:, 1] <= max_y - radius))
        self.assertTrue(np.all(are_inside))

        agents = dut.fill_rectangle(
            radius=radius, min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y,
            density=0.5, rank_dir=dut.RANK_IN_X, noise=None)
        are_inside = ((agents[:, 0] >= min_x + radius) &
                      (agents[:, 1] >= min_y + radius) &
                      (agents[:, 0] <= max_x - radius) &
                      (agents[:, 1] <= max_y - radius))
        self.assertTrue(np.all(are_inside))

        # In _max_density_for_disk, the maximum density is based on a box
        # with dimensions (4R X 2R√3. This function will *never* meet
        # that level of density. That level of density is based on counting
        # *portions* of agents to sum up total agent area vs rectangle area.
        # For a box of that size, the density should be half of what we
        # request. But, as we double the size of the rectangle, we should
        # converge towards the target density. We'll confirm that property.
        radius = 0.5
        density = dut._max_density_for_disk(radius)

        base_width = 4 * radius
        base_height = radius * (2 * np.sqrt(3))
        min_x, min_y = (0, 0)
        prev_avg_density = 0
        for scale in [1, 2, 4, 8, 16, 32, 128, 256]:
            # When scale = 1, we need a slight epsilon to prevent failure on
            # because the box appears too small.
            max_x, max_y = scale * base_width + 1e-15, scale * base_height
            agents = dut.fill_rectangle(
                radius=radius, min_x=min_x, min_y=min_y, max_x=max_x,
                max_y=max_y, density=density, rank_dir=dut.RANK_IN_X,
                noise=None)
            box_area = scale * scale * base_width * base_height
            avg_density = agents.shape[0] / box_area
            self.assertLess(avg_density, density)
            self.assertGreater(avg_density, prev_avg_density)
            prev_avg_density = avg_density

        # Evaluate noise parameter.
        self.evaluate_noise(
            lambda noise: dut.fill_rectangle(radius=0.25, min_x=0, min_y=0,
                                             max_x=5, max_y=6, density=1.5,
                                             rank_dir=dut.RANK_IN_X,
                                             noise=noise))

        # Error conditions.

        # Case: Density too high for given radius; raises error.
        with self.assertRaisesRegexp(ValueError,
                                     ".+ density .+ is too high.+"):
            dut.fill_rectangle(
                radius=1, min_x=0, min_y=0, max_x=10, max_y=10, density=2,
                rank_dir=dut.RANK_IN_Y, noise=None)

        # Case: Rectangle measures too small for even a single agent. The test
        # should be independent of rank direction, so we only test for one
        # direction.
        with self.assertRaisesRegexp(
                ValueError,
                "The rectangle dimensions .+ too small .+ contain .+"):
            dut.fill_rectangle(
                radius=1, min_x=0, min_y=0, max_x=1.9, max_y=5, density=0.25,
                rank_dir=dut.RANK_IN_X, noise=None)
        with self.assertRaisesRegexp(
                ValueError,
                "The rectangle dimensions .+ too small .+ contain .+"):
            dut.fill_rectangle(
                radius=1, min_x=0, min_y=0, max_x=5, max_y=1.9, density=0.25,
                rank_dir=dut.RANK_IN_X, noise=None)

        # Case: Rectangle measures too small to support requested ranks.
        with self.assertRaisesRegexp(
                ValueError,
                "Rectangle is too small .+ to support .+ density.+"):
            dut.fill_rectangle(
                radius=1, min_x=0, min_y=0, max_x=4, max_y=5, density=0.25,
                rank_dir=dut.RANK_IN_X, noise=None)
        with self.assertRaisesRegexp(
                ValueError,
                "Rectangle is too small .+ to support .+ density.+"):
            dut.fill_rectangle(
                radius=1, min_x=0, min_y=0, max_x=5, max_y=4, density=0.25,
                rank_dir=dut.RANK_IN_Y, noise=None)

    def test_corridor_mob(self):
        # This implicitly tests the _distances_in_ranks() method.

        # Confirm direction of corridor relative to front segment. We'll create
        # a *narrow* corridor (such that we get a single rank). We'll confirm
        # that the displacement vector between sequential agents lies in the
        # expected direction.
        agent_count = 3
        for segment_dir, normal_dir in ((Vector2(1, 0), Vector2(0, 1)),
                                        (Vector2(0, 1), Vector2(-1, 0)),
                                        (Vector2(-1, 0), Vector2(0, -1)),
                                        (Vector2(0, -1), Vector2(1, 0))):
            p_FQ = Vector2(0, 0)
            p_FR = p_FQ + segment_dir * 0.6
            agents = dut.corridor_mob(radius=0.25, p_FQ=p_FQ, p_FR=p_FR,
                                      density=1.0, rank_dir=dut.RANK_IN_X,
                                      agent_count=agent_count)
            agt_0 = agents[0, :]
            for i in range(1, agent_count):
                agt_i = agents[i, :]
                p_0I = agt_i - agt_0
                self.assertEqual(np.sqrt(np.dot(p_0I, p_0I)),
                                 np.dot(p_0I, normal_dir.asTuple()))

        # Confirm agent_count is respected.
        for count in (1, 2, 4, 12, 30, 157):
            p_FQ = Vector2(0, 0)
            p_FR = Vector2(1.5, 0)
            for rank_dir in (dut.RANK_IN_X, dut.RANK_IN_Y):
                agents = dut.corridor_mob(radius=0.25, p_FQ=p_FQ, p_FR=p_FR,
                                          density=1.0, rank_dir=rank_dir,
                                          agent_count=count)
                self.assertEqual(agents.shape[0], count)

        # Confirm agents are inside the corridor.
        # Create equations for three lines (the fixed boundaries of the
        # corridor) and confirm that the agents are all on the correct side of
        # the line. We pick an arbitrary, ugly line segment assuming that
        # it works for other line segments.
        p_FQ = Vector2(-1.5, 2.3)
        p_FR = Vector2(3.25, -1.7)
        p_RQ_F = p_FR - p_FQ
        norm_F = Vector2(-p_RQ_F.y, p_RQ_F.x)

        def make_line(dir_F, p_FP):
            """Creates a callable representing a line. Can be used to determine
            whether a point is "left" or "right" of the line (based on the
            line direction). A point on the left returns a positive value."""
            norm_F = Vector2(-dir_F.y, dir_F.x)
            C = -norm_F.dot(p_FP)
            return lambda pt: np.dot(pt, norm_F.asTuple()) + C

        front_line = make_line(p_RQ_F, p_FQ)
        line_R = make_line(norm_F, p_FR)
        line_Q = make_line(-norm_F, p_FQ)

        for count in (1, 15, 37):
            for rank_dir in (dut.RANK_IN_X, dut.RANK_IN_Y):
                agents = dut.corridor_mob(radius=0.25, p_FQ=p_FQ, p_FR=p_FR,
                                          density=1.0, rank_dir=rank_dir,
                                          agent_count=count)
                for i in range(agents.shape[0]):
                    self.assertGreater(front_line(agents[i,:]), 0)
                    self.assertGreater(line_R(agents[i, :]), 0)
                    self.assertGreater(line_Q(agents[i, :]), 0)

        # Confirm rank respected.
        p_FQ = Vector2(0, 0)
        p_FR = Vector2(-3, 0)
        agents = dut.corridor_mob(radius=0.25, p_FQ=p_FQ, p_FR=p_FR,
                                  density=2.0, rank_dir=dut.RANK_IN_X,
                                  agent_count=30)
        # We've selected a corridor front in the -x direction. The first few
        # agents should have fixed y-values.
        self.assertEqual(agents[0, 1], agents[1, 1])
        self.assertEqual(agents[1, 1], agents[2, 1])

        agents = dut.corridor_mob(radius=0.25, p_FQ=p_FQ, p_FR=p_FR,
                                  density=2.0, rank_dir=dut.RANK_IN_Y,
                                  agent_count=30)
        # We've selected a corridor front in the -x direction. The first few
        # agents should have fixed x-values.
        self.assertEqual(agents[0, 0], agents[1, 0])
        self.assertEqual(agents[1, 0], agents[2, 0])
        # Confirm "leading" agents touch the front line.
        p_FQ = Vector2(0, 0)
        p_FR = Vector2(-3, 0)
        agents = dut.corridor_mob(radius=0.25, p_FQ=p_FQ, p_FR=p_FR,
                                  density=2.0, rank_dir=dut.RANK_IN_X,
                                  agent_count=30)
        # The first few agents should all have y = -radius.
        for i in range(3):
            self.assertEqual(agents[i, 1], -0.25)

        agents = dut.corridor_mob(radius=0.25, p_FQ=p_FQ, p_FR=p_FR,
                                  density=2.0, rank_dir=dut.RANK_IN_Y,
                                  agent_count=30)
        rank_pop, _ = self.calc_rank_stats(agents, dut.RANK_IN_Y)
        agt = 0
        while agt < agents.shape[0]:
            self.assertEqual(agents[agt, 1], -0.25)
            # Only the first agents on the *major* ranks will touch the line.
            # So, we jump the entire major and minor ranks for the next
            # candidate.
            agt += 2 * rank_pop - 1

        # For RANK_IN_Y, confirm that the last row is not badly filled.
        # I.e., if not full, it's missing less than the number of ranks
        # positions to be full. We'll calculate the count of ranks (C) and the
        # population of the *last* rank. It is missing K agents to be full.
        # We assert that K < C.
        for count in (5, 17, 33):
            p_FQ = Vector2(0, 0)
            p_FR = Vector2(-3, 0)
            agents = dut.corridor_mob(radius=0.25, p_FQ=p_FQ, p_FR=p_FR,
                                      density=2.0, rank_dir=dut.RANK_IN_Y,
                                      agent_count=count)
            major_pop, rank_count = self.calc_rank_stats(agents, dut.RANK_IN_Y)
            # print (agents)
            # print("Major population: {}".format(major_pop))
            # print("Rank count: {}".format(rank_count))


        # Error conditions

        # Density requested is too high.
        with self.assertRaisesRegexp(ValueError,
                                     "The requested density .+ is too high+"):
            dut.corridor_mob(
                radius=1, p_FQ=Vector2(0, 0), p_FR=Vector2(1, 0),
                density=4, rank_dir=dut.RANK_IN_X, agent_count=1)

        # Corridor is too narrow.
        with self.assertRaisesRegexp(ValueError,
                                     "The corridor width .+ is too small.+"):
            dut.corridor_mob(
                radius=1.5, p_FQ=Vector2(0, 0), p_FR=Vector2(1, 0),
                density=0.01, rank_dir=dut.RANK_IN_X, agent_count=1)

    def test_rectMob(self):
        pass

    def test_getAABB(self):
        # To test, we'll create some points that definitively *define* the
        # domain of the AABB and then populate an arbitrary number of points
        # on the interior. We should consistently get the expected AABB.
        #
        # We'll use two different approaches to define points that create the
        # same AABB:
        #   1. A pair of points which uniquely define the extremal corners of
        #      the AABB
        #   2. Four points, each of which lies uniquely on the *edge* of the
        #      AABB's domain.
        # We then create an arbitrary number of interior points by randomly
        # selecting values inside the expected AABB.

        # TODO: If this ever fails, I'll need to capture the state of the
        #  inputs so I can reproduce it. This is *truly* a random test and, as
        #  such, problematic if the test ever fails. In this first pass, I'm
        #  assuming no such failure.

        # AABB defined by two corner points. (-1.75, 0.25), (10.25, 11.5)
        min_corner = np.array((-1.75, 0.25))
        max_corner = np.array((10.25, 11.5))

        minx_point = np.array((-1.75, 1.73))
        miny_point = np.array((3.8, 0.25))
        maxx_point = np.array((10.25, 0.5))
        maxy_point = np.array((8.27, 11.5))

        # Quick reality check that the two sets of points are "equivalent".
        points1 = np.array((min_corner, max_corner))
        points2 = np.array((minx_point, miny_point, maxx_point, maxy_point))
        self.assertEqual(dut.getAABB(points1), dut.getAABB(points2))

        dimensions = max_corner - min_corner
        for num_interior in [10, 100]:
            assert(num_interior > 4)
            shape = (num_interior + 2, 2)
            # Values in range [0, 1); we'll scale and transform to place inside
            # the AABB.
            samples = np.random.random(shape)
            points = samples * dimensions + min_corner
            # Shuffle the row indices so that our AABB defining vertices are
            # at arbitrary locations.
            rows = list(range(shape[0]))
            random.shuffle(rows)

            # Overwrite two rows with the corners.
            points[rows[0], :] = min_corner
            points[rows[1], :] = max_corner
            aabb_min, aabb_max = dut.getAABB(points)
            self.assertTrue(np.all(min_corner == aabb_min))
            self.assertTrue(np.all(max_corner == aabb_max))

            # Overwrite four rows with the edge points.
            points[rows[0], :] = minx_point
            points[rows[1], :] = miny_point
            points[rows[2], :] = maxx_point
            points[rows[3], :] = maxy_point
            aabb_min, aabb_max = dut.getAABB(points)
            self.assertTrue(np.all(min_corner == aabb_min))
            self.assertTrue(np.all(max_corner == aabb_max))
