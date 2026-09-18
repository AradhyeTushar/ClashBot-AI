# -*- coding: utf-8 -*-
"""Unit tests for coordinate geometry and tile transformations."""
import unittest

class TestScreenGeometry(unittest.TestCase):
    def test_aspect_ratio_normalization(self):
        target_res = (860, 480)
        scale_x = target_res[0] / 860.0
        scale_y = target_res[1] / 480.0
        self.assertEqual((scale_x, scale_y), (1.0, 1.0))

    def test_bounding_box_clamping(self):
        def clamp(val, min_v, max_v):
            return max(min_v, min(val, max_v))
        self.assertEqual(clamp(-10, 0, 860), 0)
        self.assertEqual(clamp(900, 0, 860), 860)
        self.assertEqual(clamp(450, 0, 860), 450)

if __name__ == "__main__":
    unittest.main()
