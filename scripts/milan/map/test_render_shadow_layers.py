"""The vectorized shadow mask must agree with solar_exposure.is_in_building_shadow
(the scalar reference) on a small synthetic raster. Fake data only."""

import sys
from pathlib import Path

import numpy as np
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_shadow_layers as rsl  # noqa: E402
import solar_exposure as se  # noqa: E402

NODATA = -9999.0


class FakeRaster:
    def __init__(self, transform):
        self.transform = transform

    def index(self, x, y):
        col, row = ~self.transform @ (x, y)
        return int(np.floor(row)), int(np.floor(col))


def synthetic():
    band = np.zeros((60, 60), dtype=np.float32)
    band[20:24, 30:34] = 45.0   # a tower
    band[40:44, 10:30] = 12.0   # a low slab
    band[0:5, 0:5] = NODATA     # a hole
    return band, from_origin(4_000_000.0, 2_500_600.0, 10.0, 10.0)


def test_matches_scalar_reference():
    band, transform = synthetic()
    raster = FakeRaster(transform)
    rng = np.random.default_rng(0)
    xs = 4_000_000.0 + rng.uniform(-50, 650, 400)
    ys = 2_500_600.0 - rng.uniform(-50, 650, 400)
    for azimuth, elevation in [(164.1, 67.2), (247.5, 51.9), (282.4, 20.9)]:
        radius = se.search_radius_for(elevation, 45.0)
        fast = rsl.shadow_mask(band, transform, NODATA, xs, ys, azimuth, elevation, radius)
        slow = np.array(
            [se.is_in_building_shadow(x, y, azimuth, elevation, raster, band, NODATA, radius) for x, y in zip(xs, ys)]
        )
        assert (fast == slow).all()
        assert fast.any() and not fast.all()


def test_shadow_falls_away_from_the_sun():
    band, transform = synthetic()
    # sun due west (azimuth 270), low: the shadow of the tower lies east of it
    xs = np.array([4_000_000.0 + 32 * 10 + 15.0, 4_000_000.0 + 25 * 10])
    ys = np.array([2_500_600.0 - 22 * 10, 2_500_600.0 - 22 * 10])
    mask = rsl.shadow_mask(band, transform, NODATA, xs, ys, 270.0, 30.0, se.search_radius_for(30.0, 45.0))
    assert mask[0] and not mask[1]
