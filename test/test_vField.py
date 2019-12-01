import os
import sys
import unittest

import numpy as np

# This allows execution of this file, in this directory but gives it
# access to the parent directory (the files under test).
sys.path.insert(0, os.path.abspath(os.path.relpath('..', os.path.dirname(__file__))))

import vField as dut

class TestVectorField(unittest.TestCase):

    def make_field(self):
        '''Creates the default vector field, storing the parameters that created it.'''
        self.min_point = (0.0, -1.0)
        self.size = (10.0, 9.0)
        self.cell_size = 1.0
        return dut.VectorField(self.min_point, self.size, self.cell_size)

    def default_shape(self):
        '''Reports the expected shape of the default vector field.'''
        return (int(self.size[0]), int(self.size[1]), 2)

    def test_Constructor(self):
        field = self.make_field()
        self.assertEqual(tuple(field.minPoint),  self.min_point)
        self.assertEqual(field.cellSize,  self.cell_size)
        # Note: this resolution works because I know cell size is 1.0.
        self.assertEqual(tuple(field.resolution), self.size)
        shape = self.default_shape()
        self.assertEqual(field.data.shape, shape)
        # The field is 2D vectors, so it's (w x h x 2)
        self.assertEqual(field.data.size, 180)

    def test_SetMinPoint(self):
        field = self.make_field()

        new_X = self.min_point[0] + 10.0
        self.assertEqual(field.minPoint[0], self.min_point[0])
        field.setMinX(new_X)
        self.assertEqual(field.minPoint[0], new_X)

        new_Y = self.min_point[1] + 10.0
        self.assertEqual(field.minPoint[1], self.min_point[1])
        field.setMinY(new_Y)
        self.assertEqual(field.minPoint[1], new_Y)

    def test_SetSize(self):
        field = self.make_field()
        orig_shape = self.default_shape()

        new_W = self.size[1] * 2
        self.assertEqual(field.data.shape[1], orig_shape[1])
        field.setWidth(new_W)
        self.assertEqual(field.data.shape[1], new_W)  # because cell size = 1.0

        new_H = self.size[0] * 2
        self.assertEqual(field.data.shape[0], orig_shape[0])
        field.setHeight(new_H)
        self.assertEqual(field.data.shape[0], new_H)  # because cell size = 1.0

    def test_Corners(self):
        field = self.make_field()
        expected_corners = ((self.min_point[0], self.min_point[1]),
                            (self.min_point[0] + self.size[1], self.min_point[1]),
                            (self.min_point[0] + self.size[1], self.min_point[1] + self.size[0]),
                            (self.min_point[0], self.min_point[1] + self.size[0]))
        corners = field.getCorners()
        for actual, expected in zip(corners, expected_corners):
            self.assertEqual(tuple(actual), tuple(expected))

    def test_subRegion(self):
        '''Test the subregion access'''
        field = self.make_field()
        # populate the field; the x-value of each cell is equal to the cell center's position and
        # similary the y-value.
        data = np.empty_like(field.data)
        min_center = np.array(self.min_point) + (self.cell_size * 0.5)
        x_values = min_center[0] + np.arange(self.size[1])
        y_values = min_center[1] + np.arange(self.size[0])
        y_values.shape = (-1, 1)
        data[:, :, 0] = x_values.T
        data[:, :, 1] = y_values
        self.assertEqual(tuple(data[3, 4, :]), (min_center[0] + 4, min_center[1] + 3))
        field.data[:, :, :] = data

        # Case: A single cell.
        value = field.subRegion((3, 4), (4, 5))
        self.assertEqual(value.size, 2) # simply two floats
        self.assertEqual(tuple(value[0, 0, :]), (min_center[0] + 4, min_center[1] + 3))

        # Case: A region of fully contained cells.
        value = field.subRegion((3, 4), (5, 7))
        self.assertEqual(value.size, 2 * 2 * 3)  # a 2x3 region of two floats each
        for r in xrange(2):
            global_r = 3 + r
            for c in xrange(3):
                global_c = 4 + c
                expected_value = (min_center[0] + global_c, min_center[1] + global_r)
                self.assertEqual(tuple(value[r, c, :]), expected_value)
        # TODO(curds01): when it is completely contained, I should have a slice into the data and
        # should be able to edit it directly; test this.

        # Case: region extends beyond boundary (in negative direction)
        value = field.subRegion((-1, -2), (2, 3))
        self.assertEqual(value.size, 3 * 5 * 2)
        for r in xrange(3):
            global_r = -1 + r
            for c in xrange(5):
                global_c = -2 + c
                expected_value = [0, 0]
                if field.isValidCell(global_r, global_c):
                    expected_value = (min_center[0] + global_c, min_center[1] + global_r)
                self.assertEqual(tuple(value[r, c, :]), tuple(expected_value))

        # Case: region extends beyond boundary (in positive direction)
        max_r = int(self.size[0] - 1)
        max_c = int(self.size[1] - 1)
        value = field.subRegion((max_r - 1, max_c - 2), (max_r + 2, max_c + 3))
        self.assertEqual(value.size, 3 * 5 * 2)
        for r in xrange(3):
            global_r = max_r - 1 + r
            for c in xrange(5):
                global_c = max_c - 2 + c
                expected_value = [0, 0]
                if field.isValidCell(global_r, global_c):
                    expected_value = (min_center[0] + global_c, min_center[1] + global_r)
                self.assertEqual(tuple(value[r, c, :]), tuple(expected_value))

        # Case: region lies completely outside of the field; negative direction.
        value = field.subRegion((-6,-3), (-3, -2))
        self.assertEqual(value.size, 3 * 1 * 2)
        for r in xrange(3):
            for c in xrange(1):
                expected_value = (0, 0)
                self.assertEqual(tuple(value[r, c, :]), expected_value)

        # Case: region lies completely outside of the field; positive direction.
        value = field.subRegion((max_r + 2, max_c + 3), (max_r + 4, max_c + 4))
        self.assertEqual(value.size, 2 * 1 * 2)
        for r in xrange(2):
            for c in xrange(1):
                expected_value = (0, 0)
                self.assertEqual(tuple(value[r, c, :]), expected_value)

        # Case: region lies completely outside of the field; mixed directions.
        value = field.subRegion((-4, max_c + 3), (-1, max_c + 5))
        self.assertEqual(value.size, 3 * 2 * 2)
        for r in xrange(3):
            for c in xrange(2):
                expected_value = (0, 0)
                self.assertEqual(tuple(value[r, c, :]), expected_value)

        # Case: region is larger all around.
        value = field.subRegion((-2, -3), (max_r + 2, max_c + 3))
        self.assertEqual(value.size, (max_r + 4) * (max_c + 6) * 2)
        for r in xrange(max_r + 4):
            global_r = -2 + r
            for c in xrange(max_c + 6):
                global_c = -3 + c
                expected_value = [0, 0]
                if field.isValidCell(global_r, global_c):
                    expected_value = (min_center[0] + global_c, min_center[1] + global_r)
                self.assertEqual(tuple(value[r, c, :]), tuple(expected_value))


    # TODO(curds01): Test the following:
    #  - setCellSize()
    #  - setDimensions()
    #  - getCell()
    #  - getCells()
    #  - getMagnitudes()
    #  - cellCenters()
    #  - cellSegmentDistance()
    #  - cellDistances()
    #  - fieldChanged()
    #  - write()
    #  - gridChange()
    #  - writeAscii()
    #  - read()
    #  - readAscii()
    #  - readBinary()


if __name__ == '__main__':
    unittest.main()
