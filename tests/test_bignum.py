import unittest
import _path  # noqa
from pixel_td.bignum import fmt, safe_pow, to_int, MAXF


class BigNum(unittest.TestCase):
    def test_small(self):
        self.assertEqual(fmt(0), "0")
        self.assertEqual(fmt(5), "5")
        self.assertEqual(fmt(12.5), "12.5")
        self.assertEqual(fmt(999), "999")

    def test_suffixes(self):
        self.assertEqual(fmt(1000), "1K")
        self.assertEqual(fmt(1500), "1.5K")
        self.assertEqual(fmt(2_500_000), "2.5M")
        self.assertEqual(fmt(3 * 10 ** 9), "3B")
        self.assertEqual(fmt(4 * 10 ** 12), "4T")
        self.assertEqual(fmt(999_999), "1M")             # rounds up into next tier

    def test_huge_int_and_float(self):
        self.assertTrue(fmt(10 ** 100).endswith("e100"))
        self.assertTrue(fmt(10 ** 5000).endswith("e5000"))
        self.assertTrue("e" in fmt(1.5e250))
        self.assertEqual(fmt(float("inf")), "INF")

    def test_negative(self):
        self.assertEqual(fmt(-2000), "-2K")

    def test_safe_pow_clamps(self):
        self.assertEqual(safe_pow(1.2, 1e9), MAXF)
        self.assertEqual(safe_pow(2, 3), 8)
        self.assertEqual(to_int(float("nan")), 0)
        self.assertGreater(to_int(1e305), 0)


if __name__ == "__main__":
    unittest.main()
