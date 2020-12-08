from math import sqrt
import re
import unittest
import warnings

if __name__ == '__main__':
    import os
    import sys
    sys.path.insert(0, os.path.abspath(
        os.path.relpath('..', os.path.dirname(__file__))))
import primitives as dut


class TestVector2(unittest.TestCase):

    def test_ValueAccess(self):
        """Tests construction, getting, and setting values."""
        # Construction.
        v = dut.Vector2(1.5, 2.5)

        # Access via properties.
        self.assertEqual(1.5, v.x)
        self.assertEqual(2.5, v.y)
        # Access via __getitem__.
        self.assertEqual(v[0], v.x)
        self.assertEqual(v[1], v.y)
        # Access as tuple.
        self.assertEqual((1.5, 2.5), v.asTuple())
        # Exception raising access.
        with self.assertRaises(IndexError, msg="list index out of range"):
            v[-1]
        with self.assertRaises(IndexError, msg="list index out of range"):
            v[3]
        with self.assertRaises(IndexError, msg="list index out of range"):
            v[-1] = 3
        with self.assertRaises(IndexError, msg="list index out of range"):
            v[3] = 4

        # Set via .set()
        v.set((3.5, 4.5))
        self.assertEqual(3.5, v.x)
        self.assertEqual(4.5, v.y)
        # Set via __setitem__.
        v[0] = -1.0
        v[1] = -2.5
        self.assertEqual(-1.0, v.x)
        self.assertEqual(-2.5, v.y)

    def test_Operators(self):
        """Tests the mathematical operators."""
        v = dut.Vector2(1.5, 2.5)
        delta = dut.Vector2(0.75, 0.25)

        self.assertFalse(v == delta)
        self.assertTrue(v != delta)
        self.assertEqual((v - delta),
                         dut.Vector2(v.x - delta.x, v.y - delta.y))
        self.assertEqual((v + delta),
                         dut.Vector2(v.x + delta.x, v.y + delta.y))
        self.assertEqual(-v, dut.Vector2(-v.x, -v.y))
        self.assertEqual(v / 2, dut.Vector2(v.x / 2, v.y / 2))
        self.assertEqual(v / 2.0, dut.Vector2(v.x / 2, v.y / 2))
        self.assertEqual(v * 4, dut.Vector2(v.x * 4, v.y * 4))
        self.assertEqual(4 * v, dut.Vector2(v.x * 4, v.y * 4))

        v2 = dut.Vector2(v.x, v.y)
        self.assertEqual(v, v2)
        v2 -= delta
        self.assertEqual(v2, v - delta)
        v2.set(v)
        v2 += delta
        self.assertEqual(v2, v + delta)
        v2.set(v)
        v2.negate()
        self.assertEqual(v2, -v)
        v2.set(v)
        v2 *= 3
        self.assertEqual(v2, v * 3)

    def test_normalize(self):
        """Tests normalization and magnitude calculation."""
        v = dut.Vector2(1.5, 2.5)
        expected_mag = sqrt(1.5 * 1.5 + 2.5 * 2.5)
        self.assertEqual(v.magnitude(), expected_mag)
        self.assertEqual(v.magSq(), expected_mag * expected_mag)
        n = v.normalize()
        self.assertEqual(v, dut.Vector2(1.5, 2.5))
        self.assertEqual(n,
                         dut.Vector2(v.x / expected_mag, v.y / expected_mag))
        self.assertAlmostEqual(n.magnitude(), 1.0, 15)

        v.normalize_ip()
        self.assertEqual(v, n)
        self.assertAlmostEqual(v.magnitude(), 1.0, 15)

        # Error condition; zero-length vector.
        v = dut.Vector2(0, 0)
        self.assertEqual(v.magnitude(), 0)
        self.assertTrue(v.isZero())
        n = v.normalize()
        self.assertEqual(n.magnitude(), 0)
        v.normalize_ip()
        self.assertEqual(v.magnitude(), 0)

    def test_Representation(self):
        """Tests str(v) and repr(v)."""
        v = dut.Vector2(1.5, 2.5)
        v_str = str(v)
        v_repr = repr(v)
        self.assertEqual(v_str, v_repr)
        m = re.compile('<(.+), (.+)>').match(v_repr)
        self.assertIsNot(m, None)
        self.assertEqual(float(m.group(1)), v.x)
        self.assertEqual(float(m.group(2)), v.y)

    def test_AdditionalMath(self):
        """Tests dot and det."""
        v = dut.Vector2(1.5, 2.5)
        self.assertEqual(v.dot(v), v.magSq())
        self.assertEqual(v.dot(dut.Vector2(-1, -1)),
                         -(v.x + v.y))
        v2 = dut.Vector2(-1, 0.5)
        expected_det = v.x * v2.y - v.y * v2.x
        self.assertEqual(v.det(v2), expected_det)
        self.assertEqual(v2.det(v), -expected_det)


class TestVector3(unittest.TestCase):

    def test_ValueAccess(self):
        """Tests construction, getting, and setting values."""
        # Construction.
        v = dut.Vector3(1.5, 2.5, 3.5)

        # Access via properties.
        self.assertEqual(1.5, v.x)
        self.assertEqual(2.5, v.y)
        self.assertEqual(3.5, v.z)
        # Access via __getitem__.
        self.assertEqual(v[0], v.x)
        self.assertEqual(v[1], v.y)
        self.assertEqual(v[2], v.z)
        # Access as tuple.
        self.assertEqual((1.5, 2.5, 3.5), v.asTuple())
        # Exception raising access.
        with self.assertRaises(IndexError, msg="list index out of range"):
            v[-1]
        with self.assertRaises(IndexError, msg="list index out of range"):
            v[4]
        with self.assertRaises(IndexError, msg="list index out of range"):
            v[-1] = 3
        with self.assertRaises(IndexError, msg="list index out of range"):
            v[4] = 4

        # Set via .set()
        v.set((3.5, 4.5, 5.5))
        self.assertEqual(3.5, v.x)
        self.assertEqual(4.5, v.y)
        self.assertEqual(5.5, v.z)
        # Set via __setitem__.
        v[0] = -1.0
        v[1] = -2.5
        v[2] = -3.5
        self.assertEqual(-1.0, v.x)
        self.assertEqual(-2.5, v.y)
        self.assertEqual(-3.5, v.z)

    def test_Operators(self):
        """Tests the mathematical operators."""
        v = dut.Vector3(1.5, 2.5, 3.5)
        d = dut.Vector3(0.75, 0.25, 0.5)

        self.assertFalse(v == d)
        self.assertTrue(v != d)
        self.assertEqual((v - d), dut.Vector3(v.x - d.x, v.y - d.y, v.z - d.z))
        self.assertEqual((v + d), dut.Vector3(v.x + d.x, v.y + d.y, v.z + d.z))
        self.assertEqual(-v, dut.Vector3(-v.x, -v.y, -v.z))
        self.assertEqual(v / 2, dut.Vector3(v.x / 2, v.y / 2, v.z / 2))
        self.assertEqual(v / 2.0, dut.Vector3(v.x / 2, v.y / 2, v.z / 2))
        self.assertEqual(v * 4, dut.Vector3(v.x * 4, v.y * 4, v.z * 4))
        self.assertEqual(4 * v, dut.Vector3(v.x * 4, v.y * 4, v.z * 4))

        with warnings.catch_warnings(record=True) as w:
            # We currently allow V3 - V2 --> V2. That's crap. I've put a
            # deprecation warning there; let's make sure it happens.
            warnings.simplefilter("always")
            v - dut.Vector2(1, 1)
            self.assertEqual(len(w), 1)

        v2 = dut.Vector3(v.x, v.y, v.z)
        self.assertEqual(v, v2)
        v2 -= d
        self.assertEqual(v2, v - d)
        v2.set(v)
        v2 += d
        self.assertEqual(v2, v + d)
        v2.set(v)
        v2.negate()
        self.assertEqual(v2, -v)
        v2.set(v)
        v2 *= 3
        self.assertEqual(v2, v * 3)

    def test_normalize(self):
        """Tests normalization and magnitude calculation."""
        v = dut.Vector3(1.5, 2.5, 3.5)
        expected_mag = sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
        self.assertEqual(v.magnitude(), expected_mag)
        self.assertEqual(v.length(), expected_mag)
        self.assertEqual(v.lengthSquared(), expected_mag * expected_mag)
        n = v.normalize()
        self.assertEqual(v, dut.Vector3(1.5, 2.5, 3.5))
        recip_mag = 1.0 / expected_mag
        self.assertEqual(n, dut.Vector3(v.x * recip_mag,
                                        v.y * recip_mag,
                                        v.z * recip_mag))
        self.assertAlmostEqual(n.magnitude(), 1.0, 15)

        v.normalize_ip()
        self.assertEqual(v, n)
        self.assertAlmostEqual(v.magnitude(), 1.0, 15)

        # Error condition; zero-length vector.
        v = dut.Vector3(0, 0, 0)
        self.assertEqual(v.magnitude(), 0)
        self.assertTrue(v.isZero())
        n = v.normalize()
        self.assertEqual(n.magnitude(), 0)
        v.normalize_ip()
        self.assertEqual(v.magnitude(), 0)

    def test_Representation(self):
        """Tests str(v) and repr(v)."""
        v = dut.Vector3(1.5, 2.5, 3.5)
        v_str = str(v)
        v_repr = repr(v)
        self.assertEqual(v_str, v_repr)
        m = re.compile('<(.+), (.+), (.+)>').match(v_repr)
        self.assertIsNot(m, None)
        self.assertEqual(float(m.group(1)), v.x)
        self.assertEqual(float(m.group(2)), v.y)
        self.assertEqual(float(m.group(3)), v.z)

    def test_AdditionalMath(self):
        """Tests dot, cross, minAxis, minAbsAxis."""
        v = dut.Vector3(1.5, 2.5, 3.5)
        # self.assertEqual(v.dot(v), v.magSq())
        self.assertEqual(v.dot(dut.Vector3(-1, -1, -1)),
                         -(v.x + v.y + v.z))
        v2 = dut.Vector3(-1, 0.5, -2.25)
        expected_cross = dut.Vector3(v.y * v2.z - v.z * v2.y,
                                     v.z * v2.x - v.x * v2.z,
                                     v.x * v2.y - v.y * v2.x)
        self.assertEqual(v.cross(v2), expected_cross)
        self.assertEqual(v2.cross(v), -expected_cross)


class TestFace(unittest.TestCase):

    def test_Construction(self):
        v_indices = [1, 2, 3, 4]
        n_indices = [5, 6, 7, 8]
        uv_indices = [9, 10, 11, 12]

        # Vertices only.
        f = dut.Face(v_indices)
        self.assertEqual(f.verts, v_indices)
        self.assertFalse(f.verts is v_indices)
        self.assertEqual(f.norms, [])
        self.assertEqual(f.uvs, [])

        # Vertices and normals.
        f = dut.Face(v_indices, vn=n_indices)
        self.assertEqual(f.verts, v_indices)
        self.assertFalse(f.verts is v_indices)
        self.assertEqual(f.norms, n_indices)
        self.assertFalse(f.norms is n_indices)
        self.assertEqual(f.uvs, [])

        # Vertices and texture coordinates.
        f = dut.Face(v_indices, vt=uv_indices)
        self.assertEqual(f.verts, v_indices)
        self.assertFalse(f.verts is v_indices)
        self.assertEqual(f.norms, [])
        self.assertEqual(f.uvs, uv_indices)
        self.assertFalse(f.uvs is uv_indices)

        # All vertex data.
        f = dut.Face(v_indices, vn=n_indices, vt=uv_indices)
        self.assertEqual(f.verts, v_indices)
        self.assertFalse(f.verts is v_indices)
        self.assertEqual(f.norms, n_indices)
        self.assertFalse(f.norms is n_indices)
        self.assertEqual(f.uvs, uv_indices)
        self.assertFalse(f.uvs is uv_indices)

    def test_Triangulation(self):
        v_indices = [1, 2, 3, 4]
        n_indices = [5, 6, 7, 8]
        uv_indices = [9, 10, 11, 12]

        expected_triangles = (
            dut.Face(v_indices[:3], n_indices[:3], uv_indices[:3]),
            dut.Face([v_indices[0]] + v_indices[-2:],
                     [n_indices[0]] + n_indices[-2:],
                     [uv_indices[0]] + uv_indices[-2:]))

        f = dut.Face(v_indices, n_indices, uv_indices)
        triangles = f.triangulate()

        self.assertEqual(len(triangles), len(expected_triangles))
        for i in range(2):
            self.assertEqual(triangles[i].verts, expected_triangles[i].verts)
            self.assertEqual(triangles[i].norms, expected_triangles[i].norms)
            self.assertEqual(triangles[i].uvs, expected_triangles[i].uvs)

    def test_ObjFormat(self):
        v_indices = [1, 2, 3]
        n_indices = [5, 6, 7]
        uv_indices = [9, 10, 11]

        # Vertex only.
        f = dut.Face(v_indices)
        self.assertEqual(f.OBJFormat(), "f 1 2 3")

        # Vertices and normals.
        f = dut.Face(v_indices, vn=n_indices)
        self.assertEqual(f.OBJFormat(), "f 1//5 2//6 3//7")

        # Vertices and texture coordinates.
        f = dut.Face(v_indices, vt=uv_indices)
        self.assertEqual(f.OBJFormat(), "f 1/9 2/10 3/11")

        # All vertex data.
        f = dut.Face(v_indices, n_indices, uv_indices)
        self.assertEqual(f.OBJFormat(), "f 1/9/5 2/10/6 3/11/7")


class TestVertex(unittest.TestCase):

    def test_Construct(self):
        v = dut.Vertex(1.5, 2.5, 3.5)
        self.assertEqual(v.pos[0], 1.5)
        self.assertEqual(v.pos[1], 2.5)
        self.assertEqual(v.pos[2], 3.5)

    def test_ObjFormat(self):
        """Test the OBJ representation of this vertex."""
        # We want to avoid issues of float formatting, we know the string must
        # be of the form: "v x y z", where x, y, and z are floating-point
        # values. So, we split on the white space and test the tokens for
        # value equivalency.
        v = dut.Vertex(1.5, 2.5, 3.5)
        tokens = v.formatOBJ().split()
        self.assertEqual(tokens[0], "v")
        self.assertEqual(float(tokens[1]), v.pos[0])
        self.assertEqual(float(tokens[2]), v.pos[1])
        self.assertEqual(float(tokens[3]), v.pos[2])


class TestSegment(unittest.TestCase):

    def test_ValueAccess(self):
        """Tests the constructor and flip; confirms the vectors are aliased."""
        p1 = dut.Vector2(-1, -2)
        p2 = dut.Vector2(1, 2)
        segment = dut.Segment(p1, p2)
        self.assertTrue(segment.p1 is p1)
        self.assertTrue(segment.p2 is p2)
        segment.flip()
        self.assertTrue(segment.p1 is p2)
        self.assertTrue(segment.p2 is p1)

    def test_Measures(self):
        """Tests the calculations on the Segment itself."""
        p1 = dut.Vector2(-1, -2)
        p2 = dut.Vector2(1, 2)
        segment = dut.Segment(p1, p2)
        self.assertEqual(segment.midPoint(), (p1 + p2) * 0.5)
        self.assertEqual(segment.magnitude(), (p1 - p2).magnitude())
        self.assertEqual(segment.magSq(), (p1 - p2).magSq())
        d = p2 - p1
        d_hat = d.normalize()
        self.assertEqual(segment.unit_direction(), d_hat)
        # Note: The normal could also be (d.y, -d.x). We exploit the knowledge
        #  that *this* is the normal.
        n = dut.Vector2(-d_hat.y, d_hat.x)
        self.assertEqual(segment.normal(), n)

    def test_PointDistance(self):
        p1 = dut.Vector2(-1, -2)
        p2 = dut.Vector2(1, 2)
        segment = dut.Segment(p1, p2)
        d = segment.unit_direction()
        n = segment.normal()

        # Point nearest p1 (but not the interior of the segment).
        q = p1 - 0.5 * d + 2 * n
        expected_dist = (p1 - q).magnitude()
        self.assertEqual(segment.pointDistance(q), expected_dist)

        # Point nearest p2 (but not the interior of the segment).
        q = p2 + 0.75 * d - 1.5 * n
        expected_dist = (p2 - q).magnitude()
        self.assertEqual(segment.pointDistance(q), expected_dist)

        # Point that projects onto the point 0, 0.
        q = n * 3
        expected_dist = q.magnitude()
        self.assertEqual(segment.pointDistance(q), expected_dist)

    def test_ImplicitEquation(self):
        p1 = dut.Vector2(-1, -2)
        p2 = dut.Vector2(1, 2)
        segment = dut.Segment(p1, p2)
        A, B, C = segment.implicitEquation()
        self.assertEqual(dut.Vector2(A, B), segment.normal())
        C_expected = -segment.normal().dot(p1)
        self.assertEqual(C, C_expected)

    def test_OriginDirLen(self):
        p1 = dut.Vector2(-1, -2)
        p2 = dut.Vector2(1, 2)
        segment = dut.Segment(p1, p2)
        o, d, l = segment.originDirLen()
        self.assertEqual(o, p1)
        self.assertEqual(d, dut.Vector2(1, 2).normalize())
        self.assertEqual(l, (p2 - p1).magnitude())


class TestSegmentsFromString(unittest.TestCase):

    def test_MakeSegments(self):
        s1 = dut.Segment(dut.Vector2(0.25, 0.5), dut.Vector2(1.5, -2))
        s2 = dut.Segment(dut.Vector2(-1.75, 2), dut.Vector2(2.5, -3))
        test_segments = (s1, s2)
        values = []
        for s in test_segments:
            for p in (s.p1, s.p2):
                values.append(str(p.x))
                values.append(str(p.y))
        data_str = ' '.join(values)

        segments = dut.segmentsFromString(data_str, dut.Segment)
        self.assertEqual(len(segments), len(test_segments))
        for i in range(len(segments)):
            self.assertEqual(segments[i].p1, test_segments[i].p1)
            self.assertEqual(segments[i].p2, test_segments[i].p2)


if __name__ == '__main__':
    unittest.main()
