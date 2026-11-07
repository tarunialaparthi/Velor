import os
import rasterio

dem_path = os.path.join("data", "dem", "krishna_dem.tif")

print("=" * 50)
print("FLOODSENSE - DEM INSPECTION")
print("=" * 50)

if not os.path.exists(dem_path):
    print("\nERROR: DEM file was not found!")
    print("Expected location:", os.path.abspath(dem_path))
    print("Check that the DEM file is inside data/dem/")
else:
    with rasterio.open(dem_path) as dataset:
        print("\nDEM successfully opened!")

        print("\n--- RASTER INFORMATION ---")
        print("File:", os.path.abspath(dem_path))
        print("Width (pixels):", dataset.width)
        print("Height (pixels):", dataset.height)
        print("Number of bands:", dataset.count)
        print("Coordinate reference system:", dataset.crs)
        print("Geographic/projected bounds:", dataset.bounds)
        print("Pixel resolution:", dataset.res)
        print("No-data value:", dataset.nodata)

        elevation = dataset.read(1, masked=True)
        valid_elevation = elevation.compressed()

        print("\n--- ELEVATION STATISTICS ---")
        if valid_elevation.size > 0:
            print("Minimum elevation:", round(float(valid_elevation.min()), 2))
            print("Maximum elevation:", round(float(valid_elevation.max()), 2))
            print("Mean elevation:", round(float(valid_elevation.mean()), 2))
            print("Number of valid pixels:", valid_elevation.size)
        else:
            print("ERROR: No valid elevation pixels were found.")

print("\nInspection script finished.")
