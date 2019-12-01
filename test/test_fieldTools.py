#from contextlib import contextmanager
import os
#import re
#from StringIO import StringIO
import sys
import unittest

# This allows execution of this file, in this directory but gives it
# access to the parent directory (the files under test).
sys.path.insert(0, os.path.abspath(os.path.relpath('..', os.path.dirname(__file__))))

import fieldTools as dut
from vField import VectorField

class TestFieldTools(unittest.TestCase):

    def test_smoothFieldRegion(self):
        '''Tests the smoothFieldRegion() method.'''
        # This test is just a stop gap; some way of exercising code.
        field = VectorField((0,0), (10, 10), 1.0)
        field.read('test_field.txt')
        kernel_size = 1.0
        minima = [7, 16]
        maxima = [19, 27]
        # confirm the region spans valid cells.
        print 'test1'
        self.assertLessEqual(minima[0], field.data.shape[0])
        self.assertLessEqual(maxima[0], field.data.shape[0])
        self.assertLessEqual(minima[1], field.data.shape[1])
        self.assertLessEqual(maxima[1], field.data.shape[1])
        smoothed = dut.smoothFieldRegion(field, kernel_size, minima, maxima)
        self.assertEqual(smoothed.shape[0], maxima[0] - minima[0])
        self.assertEqual(smoothed.shape[1], maxima[1] - minima[1])
        
        # Shift the region -1 in each direction; the dimensions of the result should be the same.
        minima = [6, 15]
        maxima = [18, 26]
        # confirm the region spans valid cells.
        print '\ntest2'
        self.assertLessEqual(minima[0], field.data.shape[0])
        self.assertLessEqual(maxima[0], field.data.shape[0])
        self.assertLessEqual(minima[1], field.data.shape[1])
        self.assertLessEqual(maxima[1], field.data.shape[1])
        smoothed = dut.smoothFieldRegion(field, kernel_size, minima, maxima)
        self.assertEqual(smoothed.shape[0], maxima[0] - minima[0])
        self.assertEqual(smoothed.shape[1], maxima[1] - minima[1])


if __name__ == '__main__':
    unittest.main()