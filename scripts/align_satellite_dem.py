import rasterio
import numpy as np
from rasterio.warp import reproject, Resampling
from pathlib import Path

satellite_path = Path("data/satellite/opera_water.tif")
dem_path = Path("data/dem/krishna_dem.tif")
output_path = Path("data/satellite/opera_water_aligned.tif")

output_path.parent.mkdir(parents=True, exist_ok=True)

print("Loading satellite raster and DEM...")

with rasterio.open(satellite_path) as sat, rasterio.open(dem_path) as dem:
    # Read source satellite classifications.
    satellite = sat.read(1)

    # Create an output raster on exactly the same grid as the DEM.
    aligned = np.full(
        (dem.height, dem.width),
        255,
        dtype=np.uint8
    )

    reproject(
        source=satellite,
        destination=aligned,
        src_transform=sat.transform,
        src_crs=sat.crs,
        src_nodata=255,
        dst_transform=dem.transform,
        dst_crs=dem.crs,
        dst_nodata=255,
        resampling=Resampling.nearest
    )

    # Read elevation values.
    elevation = dem.read(1).astype(np.float32)
    dem_valid = np.isfinite(elevation)

    if dem.nodata is not None:
        dem_valid &= dem.read(1) != dem.nodata

    # Only retain known water classes and valid non-water pixels.
    satellite_valid = np.isin(aligned, [0, 1, 3])
    common_valid = dem_valid & satellite_valid

    observed_water = np.isin(aligned, [1, 3]) & common_valid

    # Report alignment and comparison coverage.
    print("\nALIGNMENT RESULTS")
    print("-" * 45)
    print(f"Satellite CRS: {sat.crs}")
    print(f"DEM CRS: {dem.crs}")
    print(f"Aligned raster shape: {aligned.shape}")
    print(f"DEM shape: {(dem.height, dem.width)}")
    print(f"Valid DEM pixels: {int(dem_valid.sum()):,}")
    print(f"Valid satellite pixels on DEM grid: {int(satellite_valid.sum()):,}")
    print(f"Pixels valid in both datasets: {int(common_valid.sum()):,}")
    print(f"Observed water pixels in overlap: {int(observed_water.sum()):,}")

    if common_valid.sum() > 0:
        overlap_water_percentage = (
            observed_water.sum() / common_valid.sum()
        ) * 100

        water_elevations = elevation[observed_water]

        print(f"Water percentage in valid overlap: {overlap_water_percentage:.2f}%")

        if water_elevations.size > 0:
            print(f"Elevation range of classified water pixels: "
                  f"{water_elevations.min():.2f} to "
                  f"{water_elevations.max():.2f} m")
            print(f"Median elevation of classified water pixels: "
                  f"{np.median(water_elevations):.2f} m")
        else:
            print("No classified water pixels were found in the valid overlap.")
    else:
        print("WARNING: No valid overlapping pixels were found.")

    # Save the aligned classification raster.
    profile = dem.profile.copy()
    profile.update(
        driver="GTiff",
        count=1,
        dtype="uint8",
        nodata=255,
        compress="lzw"
    )

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(aligned, 1)

    print(f"\nAligned raster saved to: {output_path}")
    print("Alignment finished.")
