import unittest

from clock_skew_detector import SkewEstimator, SkewEstimate, estimate_offset


class TestSkewEstimator(unittest.TestCase):
    def test_empty_returns_zero_n(self):
        est = SkewEstimator()
        result = est.estimate()
        self.assertIsInstance(result, SkewEstimate)
        self.assertEqual(result.n, 0)
        self.assertEqual(result.offset_ms, 0.0)

    def test_single_probe_returns_zero_n(self):
        est = SkewEstimator()
        est.add_probe(1000.0, 1500.0, 1510.0)
        result = est.estimate()
        self.assertEqual(result.n, 0)

    def test_two_probes_constant_offset(self):
        est = SkewEstimator()
        # sync probe (discarded)
        est.add_probe(1000.0, 1500.0, 1510.0)
        # real probe: remote midpoint is 500 ms ahead of local send
        # midpoint = (2500 + 2510) / 2 = 2505; offset = 2505 - 2000 = 505
        est.add_probe(2000.0, 2500.0, 2510.0)
        result = est.estimate()
        self.assertEqual(result.n, 1)
        self.assertAlmostEqual(result.offset_ms, 505.0)

    def test_negative_offset(self):
        est = SkewEstimator()
        est.add_probe(1000.0, 500.0, 510.0)   # discarded
        # midpoint = (1500 + 1510) / 2 = 1505; offset = 1505 - 2000 = -495
        est.add_probe(2000.0, 1500.0, 1510.0)
        result = est.estimate()
        self.assertEqual(result.n, 1)
        self.assertAlmostEqual(result.offset_ms, -495.0)

    def test_median_with_outlier(self):
        est = SkewEstimator()
        est.add_probe(1000.0, 1500.0, 1510.0)  # discarded
        est.add_probe(2000.0, 2500.0, 2510.0)  # offset +505
        est.add_probe(3000.0, 3500.0, 3510.0)  # offset +505
        est.add_probe(4000.0, 9999.0, 9999.0)  # outlier offset +5999
        result = est.estimate()
        self.assertEqual(result.n, 3)
        self.assertAlmostEqual(result.offset_ms, 505.0)

    def test_functional_api(self):
        probes = [
            (1000.0, 1500.0, 1510.0),
            (2000.0, 2500.0, 2510.0),
            (3000.0, 3500.0, 3510.0),
        ]
        result = estimate_offset(probes)
        self.assertEqual(result.n, 2)
        self.assertAlmostEqual(result.offset_ms, 505.0)


if __name__ == '__main__':
    unittest.main()
