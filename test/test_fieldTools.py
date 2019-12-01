import os
import sys
import unittest

# This allows execution of this file, in this directory but gives it
# access to the parent directory (the files under test).
sys.path.insert(0, os.path.abspath(os.path.relpath('..', os.path.dirname(__file__))))

import fieldTools as dut
from vField import VectorField

class TestFieldTools(unittest.TestCase):

    def test_smoothFieldRegionSize(self):
        '''Tests the smoothFieldRegion() method; particularly that even as the region we want to
        smooth gets near the boundary, we still get the region back.'''
        # The *values* of the vector field don't matter. So, a simple grid [0, 0] X [10, 10] is
        # sufficient.
        field = VectorField((0,0), (10, 10), 1.0)
        kernel_size = 1.0
        minima = [4, 4]
        maxima = [6, 6]
        # confirm the region spans valid cells.
        self.assertLessEqual(minima[0], field.data.shape[0])
        self.assertLessEqual(maxima[0], field.data.shape[0])
        self.assertLessEqual(minima[1], field.data.shape[1])
        self.assertLessEqual(maxima[1], field.data.shape[1])
        smoothed = dut.smoothFieldRegion(field, kernel_size, minima, maxima)
        self.assertEqual(smoothed.shape[0], maxima[0] - minima[0])
        self.assertEqual(smoothed.shape[1], maxima[1] - minima[1])

        # This new region is the same size, but it moves the full work space off the domain of the
        # field. It should still produce a result of the expected size. We know the kernel size
        # will require data from outside the domain of the field (because the region lies on the
        # boundary.
        minima = [0, 0]
        maxima = [2, 2]
        # confirm the region spans valid cells.
        self.assertLessEqual(minima[0], field.data.shape[0])
        self.assertLessEqual(maxima[0], field.data.shape[0])
        self.assertLessEqual(minima[1], field.data.shape[1])
        self.assertLessEqual(maxima[1], field.data.shape[1])
        smoothed = dut.smoothFieldRegion(field, kernel_size, minima, maxima)
        self.assertEqual(smoothed.shape[0], maxima[0] - minima[0])
        self.assertEqual(smoothed.shape[1], maxima[1] - minima[1])


if __name__ == '__main__':
    unittest.main()
