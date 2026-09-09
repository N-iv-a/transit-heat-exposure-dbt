import datetime
import math

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from solar_exposure import (
    CEST,
    is_in_building_shadow,
    required_height_at_distance,
    solar_position,
)


def test_solar_position_milan_summer_noon_is_high_and_south():
    dt_local = datetime.datetime(2026, 6, 28, 14, 0, tzinfo=CEST)
    azimuth, elevation = solar_position(dt_local)

    # Near summer solstice at 45.46N, solar noon elevation tops out at
    # roughly 90 - 45.46 + 23.44 = 67.98 degrees.
    assert 60 < elevation < 70
    # Sun should be roughly south-southwest in the early afternoon.
    assert 150 < azimuth < 230


def test_solar_position_is_lower_at_evening_than_at_noon():
    noon = datetime.datetime(2026, 6, 28, 14, 0, tzinfo=CEST)
    evening = datetime.datetime(2026, 6, 28, 18, 0, tzinfo=CEST)
    _, elevation_noon = solar_position(noon)
    _, elevation_evening = solar_position(evening)
    assert elevation_evening < elevation_noon


def test_required_height_at_distance_matches_trigonometry():
    # A 45-degree sun needs a building exactly as tall as the distance.
    assert required_height_at_distance(50, 45) == pytest.approx(50, rel=1e-6)
    # Higher sun -> taller building needed for the same distance.
    assert required_height_at_distance(50, 70) > required_height_at_distance(50, 45)
    # Zero distance never needs a building.
    assert required_height_at_distance(0, 45) == 0


@pytest.fixture
def synthetic_raster(tmp_path):
    """A tiny 10m-resolution raster, all zero height except one tall
    building at a known offset from the origin.
    """
    width, height = 20, 20
    transform = from_origin(0, 200, 10, 10)  # top-left at (0, 200), 10m pixels
    data = np.zeros((height, width), dtype=np.uint16)

    # Tall building 40m north of the raster's center pixel (col 10, row 10).
    data[6, 10] = 60  # row decreases northward from the raster's top edge

    path = tmp_path / "synthetic.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=data.dtype,
        crs="EPSG:3035",
        transform=transform,
        nodata=65535,
    ) as dst:
        dst.write(data, 1)

    return path


def test_shadow_detected_when_tall_building_is_between_stop_and_sun(synthetic_raster):
    with rasterio.open(synthetic_raster) as raster:
        band = raster.read(1)
        nodata = raster.nodata
        stop_x, stop_y = raster.xy(10, 10)  # center pixel, at raster row/col (10, 10)

        # Sun due north (azimuth 0) at a low-ish elevation: the 60m building
        # 40m away requires elevation <= atan(60/40) ~= 56.3 degrees to shade.
        in_shadow = is_in_building_shadow(
            stop_x, stop_y, azimuth_deg=0, elevation_deg=30, raster=raster, band=band, nodata=nodata
        )
        assert in_shadow is True


def test_no_shadow_when_sun_too_high_for_the_same_building(synthetic_raster):
    with rasterio.open(synthetic_raster) as raster:
        band = raster.read(1)
        nodata = raster.nodata
        stop_x, stop_y = raster.xy(10, 10)

        # Same building, but sun high enough that its shadow doesn't reach.
        in_shadow = is_in_building_shadow(
            stop_x, stop_y, azimuth_deg=0, elevation_deg=70, raster=raster, band=band, nodata=nodata
        )
        assert in_shadow is False


def test_no_shadow_when_building_is_in_the_wrong_direction(synthetic_raster):
    with rasterio.open(synthetic_raster) as raster:
        band = raster.read(1)
        nodata = raster.nodata
        stop_x, stop_y = raster.xy(10, 10)

        # Sun due south: the building is north of the stop, so it can't be
        # between the stop and a southern sun.
        in_shadow = is_in_building_shadow(
            stop_x, stop_y, azimuth_deg=180, elevation_deg=30, raster=raster, band=band, nodata=nodata
        )
        assert in_shadow is False


def test_no_shadow_beyond_search_radius(synthetic_raster):
    with rasterio.open(synthetic_raster) as raster:
        band = raster.read(1)
        nodata = raster.nodata
        stop_x, stop_y = raster.xy(10, 10)

        in_shadow = is_in_building_shadow(
            stop_x,
            stop_y,
            azimuth_deg=0,
            elevation_deg=30,
            raster=raster,
            band=band,
            nodata=nodata,
            search_radius_m=20,  # building is 40m away, out of range
        )
        assert in_shadow is False
