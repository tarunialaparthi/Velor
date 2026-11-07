import rasterio
import numpy as np
from pathlib import Path

earlier_path = Path("data/satellite/opera_water_aligned.tif")
later_path = Path("data/satellite/opera_water_20261014_aligned.tif")

for path in [earlier_path, later_path]:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

with rasterio.open(earlier_path) as earlier_src, \
     rasterio.open(later_path) as later_src:

    earlier = earlier_src.read(1)
    later = later_src.read(1)

    if earlier.shape != later.shape:
        raise ValueError("The two rasters have different dimensions.")

    if earlier_src.transform != later_src.transform:
        raise ValueError("The two rasters do not share the same grid transform.")

    if earlier_src.crs != later_src.crs:
        raise ValueError("The two rasters use different coordinate systems.")

    # OPERA classes: 0 = non-water, 1 = open water,
    # 3 = inundated vegetation, 255 = no data.
    earlier_valid = np.isin(earlier, [0, 1, 3])
    later_valid = np.isin(later, [0, 1, 3])

    # Only compare pixels valid in BOTH observations.
    common = earlier_valid & later_valid

    earlier_water = np.isin(earlier, [1, 3])
    later_water = np.isin(later, [1, 3])

    persistent = common & earlier_water & later_water
    newly_water = common & (earlier == 0) & later_water
    no_longer_water = common & earlier_water & (later == 0)

    common_count = int(np.count_nonzero(common))
    persistent_count = int(np.count_nonzero(persistent))
    newly_count = int(np.count_nonzero(newly_water))
    no_longer_count = int(np.count_nonzero(no_longer_water))

    earlier_count = int(np.count_nonzero(common & earlier_water))
    later_count = int(np.count_nonzero(common & later_water))

    print("\n========== SATELLITE WATER-CLASSIFICATION COMPARISON ==========")
    print("Earlier observation: 15 September 2026")
    print("Later observation:   14 October 2026")
    print(f"Pixels valid in both observations: {common_count:,}")

    if common_count == 0:
        raise ValueError("No common valid pixels available for comparison.")

    print("\n--- PIXEL COUNTS ---")
    print(f"Water in both observations: {persistent_count:,}")
    print(f"Newly water-classified: {newly_count:,}")
    print(f"No-longer-water-classified: {no_longer_count:,}")
    print(f"Water pixels in earlier observation: {earlier_count:,}")
    print(f"Water pixels in later observation: {later_count:,}")

    print("\n--- CHANGE METRICS ---")
    print(f"Net change in water-classified pixels: {later_count - earlier_count:+,}")
    print(f"Newly classified share of common pixels: {newly_count / common_count * 100:.2f}%")
    print(f"No-longer-classified share of common pixels: {no_longer_count / common_count * 100:.2f}%")

    print("\nIMPORTANT:")
    print("These are changes in satellite water classification, not confirmed flood expansion.")
    print("Ordinary water bodies, seasonal changes, and observation differences may contribute.")
    print("Pixel counts are not converted to area in this step.")

print("\nComparison complete.")
