from contextlib import contextmanager
import os
import re
from StringIO import StringIO
import sys
import unittest

# This allows execution of this file, in this directory but gives it
# access to the parent directory (the files under test).
sys.path.insert(0, os.path.abspath(os.path.relpath('..', os.path.dirname(__file__))))

import objToNavMesh as dut
import ObjReader


@contextmanager
def captured_output():
    '''Maps standard err and out to local memory buffers so broadcast messages
    can be tested.'''
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class FileBuffer:
    '''Short-term hack to spoof file contents with in-memory buffer.
    ObjReader.readFileLike() explicitly calls xreadlines(). It needs to be modernized.'''
    def __init__(self, str_data):
        self.str_data = str_data

    def xreadlines(self):
        return self.str_data.split('\n')


class TestObjAnalysis(unittest.TestCase):

    def obj_from_string(self, obj_data):
        '''Creates an ObjFile from a string containing an obj file's data'''
        obj_file = FileBuffer(obj_data)
        obj = ObjReader.ObjFile()
        obj.readFileLike(obj_file)
        return obj

    def test_good_obj(self):
        '''Analyzes trivially correct mesh'''
        obj_data = '''v 0 0 0
        v 1 0 0
        v 1 1 0
        v 0 1 0
        f 4 3 1
        f 2 1 3'''
        obj = self.obj_from_string(obj_data)
        self.assertTrue(dut.analyze_obj(obj))

    def test_bad_winding(self):
        '''Tests that adjacent faces with inconsistent winding are detected.'''
        # Creates the following simple mesh
        #
        #    v4    v3
        #    o-----o
        #    |->  /|
        # f1 |   / |
        #    |  /  | f2
        #    | / ->|
        #    o-----o
        #    v1    v2
        # Face 1 and face two have opposite winding
        obj_data = '''v 0 0 0
        v 1 0 0
        v 1 1 0
        v 0 1 0
        f 4 3 1
        f 1 2 3'''
        obj = self.obj_from_string(obj_data)
        with captured_output() as (out, err):
            result = dut.analyze_obj(obj)

        self.assertFalse(result)
        self.assertRegexpMatches(out.getvalue().strip(),
                                 re.compile(".*prevent .* mesh from being made.*"
                                            "The faces .* 6 .* 5 .* inconsistent winding",
                                            re.DOTALL))

    def test_too_many_adjacent_faces(self):
        '''Tests that a an edge with three adjacent faces is detected'''
        # Reproduces the mesh in test_bad_winding, but adds an addition vertex *above* v3
        # and a third face built on v1, v3, and v5.

        obj_data = '''v 0 0 0
        v 1 0 0
        v 1 1 0
        v 0 1 0
        v 1 1 1
        f 4 3 1
        f 1 2 3
        f 1 3 5'''
        obj = self.obj_from_string(obj_data)
        with captured_output() as (out, err):
            result = dut.analyze_obj(obj)

        self.assertFalse(result)
        self.assertRegexpMatches(out.getvalue().strip(),
                                 re.compile(".*prevent .* mesh from being made.*"
                                            "More than two faces reference the same edge.*",
                                            re.DOTALL))

    def test_duplicate_vertices(self):
        '''Tests that duplicate vertices get captured.'''
        # Obj data is the same as in test_bad_winding(), but with vertices 1 and 3
        # literally duplicated.
        obj_data = '''v 0 0 0
        v 0 1 0
        v 1 1 0
        v 0 0 0
        v 1 1 0
        v 1 0 0
        f 1 2 3
        f 4 5 6'''
        obj = self.obj_from_string(obj_data)
        with captured_output() as (out, err):
            # Duplicate is still caught with epsilon-sized tolerance.
            result = dut.analyze_obj(obj, 1e-15)

        # Duplicate vertices don't cause failure; but they do spawn warnings.
        self.assertTrue(result)
        # NOTE: There should be *two* messages about duplicate vertices.
        self.assertRegexpMatches(out.getvalue().strip(),
                                 re.compile(".* which may indicate a problem.*"
                                            "Vertices on lines .* are closer.*"
                                            "Vertices on lines .* are closer.*",
                                            re.DOTALL))

    def test_vertices_too_close(self):
        '''Tests the threshold for determining if vertices are too close.'''
        # Obj data is the same as in test_bad_winding(), but with one vertex duplicated with
        # a small perturbation.
        deviation = 1e-7
        obj_data = '''v {} 0 0
        v 0 1 0
        v 0 0 0
        v 1 1 0
        v 1 0 0
        f 1 2 4
        f 3 4 5'''.format(deviation)
        obj = self.obj_from_string(obj_data)

        # Case 1: tolerance is slightly *larger* than the deviation.
        with captured_output() as (out, err):
            result = dut.analyze_obj(obj, deviation * 1.00001)

        # Duplicate vertices don't cause failure; but they do spawn warnings.
        self.assertTrue(result)
        self.assertRegexpMatches(out.getvalue().strip(),
                                 re.compile(".* which may indicate a problem.*"
                                            "Vertices on lines .* are closer.*",
                                            re.DOTALL))

        # Case 2: tolerance is slightly *smaller* than the deviation.
        with captured_output() as (out, err):
            result = dut.analyze_obj(obj, deviation * 0.999)

        # Duplicate vertices don't cause failure; but they do spawn warnings.
        self.assertTrue(result)
        self.assertEquals(out.getvalue().strip(), "")

# TODO: Test all of the other functionality in objToNavMesh.py.

if __name__ == '__main__':
    unittest.main()
