import datetime
import math

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from solar_exposure import (
    CEST,
    CRITICAL_HOURS,
    arpa_solar_to_cest,
    is_in_building_shadow,
    required_height_at_distance,
    search_radius_for,
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
            stop_x, stop_y, azimuth_deg=0, elevation_deg=30, raster=raster, band=band, nodata=nodata,
            search_radius_m=80,
        )
        assert in_shadow is True


def test_no_shadow_when_sun_too_high_for_the_same_building(synthetic_raster):
    with rasterio.open(synthetic_raster) as raster:
        band = raster.read(1)
        nodata = raster.nodata
        stop_x, stop_y = raster.xy(10, 10)

        # Same building, but sun high enough that its shadow doesn't reach.
        in_shadow = is_in_building_shadow(
            stop_x, stop_y, azimuth_deg=0, elevation_deg=70, raster=raster, band=band, nodata=nodata,
            search_radius_m=80,
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
            stop_x, stop_y, azimuth_deg=180, elevation_deg=30, raster=raster, band=band, nodata=nodata,
            search_radius_m=80,
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


def test_search_radius_for_high_and_low_sun():
    # 45 degrees: radius equals the max height, already a multiple of the step.
    assert 100 <= search_radius_for(45, 100, 10) <= 110
    # Low sun -> long shadows -> larger radius; rounded up to the step.
    low = search_radius_for(10, 100, 10)
    high = search_radius_for(65, 100, 10)
    assert low > high
    assert low % 10 == 0 and high % 10 == 0
    assert low >= 100 / math.tan(math.radians(10))
    assert high >= 100 / math.tan(math.radians(65))
    with pytest.raises(ValueError):
        search_radius_for(0, 100)


def test_tall_building_beyond_80m_casts_shadow(tmp_path):
    width, height = 60, 60
    data = np.zeros((height, width), dtype=np.uint16)
    data[10, 30] = 200  # 200 m tall, 200 m north of the stop at row 30
    path = tmp_path / "big.tif"
    with rasterio.open(
        path, "w", driver="GTiff", height=height, width=width, count=1,
        dtype=data.dtype, crs="EPSG:3035", transform=from_origin(0, 600, 10, 10), nodata=65535,
    ) as dst:
        dst.write(data, 1)

    with rasterio.open(path) as raster:
        band = raster.read(1)
        stop_x, stop_y = raster.xy(30, 30)
        elevation = 45
        radius = search_radius_for(elevation, float(band.max()))
        assert radius >= 200
        kwargs = dict(azimuth_deg=0, elevation_deg=elevation, raster=raster, band=band, nodata=raster.nodata)
        assert is_in_building_shadow(stop_x, stop_y, search_radius_m=80, **kwargs) is False
        assert is_in_building_shadow(stop_x, stop_y, search_radius_m=radius, **kwargs) is True


def test_arpa_solar_time_maps_to_cest_plus_one_hour():
    assert arpa_solar_to_cest(datetime.datetime(2026, 6, 28, 12, 0)) == datetime.datetime(2026, 6, 28, 13, 0)
    assert arpa_solar_to_cest(datetime.datetime(2026, 6, 28, 23, 30)) == datetime.datetime(2026, 6, 29, 0, 30)


def test_critical_hours_are_arpa_window_in_cest():
    assert list(CRITICAL_HOURS) == [13, 14, 15, 16, 17, 18, 19]


def test_sun_still_high_at_19_cest_on_study_day():
    _, elevation = solar_position(datetime.datetime(2026, 6, 28, 19, 0, tzinfo=CEST))
    assert elevation > 15
