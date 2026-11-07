import rasterio
import numpy as np
from pathlib import Path

satellite_path = Path("data/satellite/opera_water.tif")

with rasterio.open(satellite_path) as src:
    water = src.read(1)

    transform = src.transform
    crs = src.crs

    pixel_width = abs(transform.a)
    pixel_height = abs(transform.e)

    # This product uses a projected coordinate system.
    # Pixel dimensions are expressed in the CRS units.
    pixel_area_m2 = pixel_width * pixel_height

    # Valid classifications exclude masks and missing data.
    valid = np.isin(water, [0, 1, 3])

    # Open water plus inundated vegetation.
    observed_water = np.isin(water, [1, 3])

    valid_pixels = int(np.count_nonzero(valid))
    water_pixels = int(np.count_nonzero(observed_water))

    valid_area_km2 = valid_pixels * pixel_area_m2 / 1_000_000
    water_area_km2 = water_pixels * pixel_area_m2 / 1_000_000

    water_percentage = (
        100 * water_pixels / valid_pixels
        if valid_pixels > 0 else 0
    )

    print("\nFLOODSENSE: SATELLITE WATER ANALYSIS")
    print("-" * 45)
    print(f"CRS: {crs}")
    print(f"Raster dimensions: {water.shape[1]} x {water.shape[0]}")
    print(f"Pixel size: {pixel_width:.2f} x {pixel_height:.2f} CRS units")
    print(f"Valid classified pixels: {valid_pixels:,}")
    print(f"Observed water pixels: {water_pixels:,}")
    print(f"Valid classified area: {valid_area_km2:.3f} km²")
    print(f"Observed water area: {water_area_km2:.3f} km²")
    print(f"Water percentage of valid area: {water_percentage:.2f}%")

    print("\nInterpretation:")
    print("This is the water extent classified in one satellite observation.")
    print("It does not establish whether flooding is expanding.")
    print("Masked and missing pixels are excluded from the calculation.")
