#! /usr/bin/env python
import unittest

import noaa_wildfires


class MyUnitTest(unittest.TestCase):
    def test_fires(self):
        noaa_wildfires.get_hms_fires()

    def test_smoke(self):
        noaa_wildfires.get_hms_smoke()


if __name__ == "__main__":
    unittest.main()
