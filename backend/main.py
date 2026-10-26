from pathlib import Path
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fastapi.responses import StreamingResponse
import numpy as np
import rasterio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent.parent

DEM_PATH = ROOT / "data" / "dem" / "krishna_dem.tif"
EARLIER_PATH = ROOT / "data" / "satellite" / "opera_water_aligned.tif"
LATER_PATH = ROOT / "data" / "satellite" / "opera_water_20261014_aligned.tif"

app = FastAPI(
    title="FloodSense API",
    description="Satellite comparison and terrain data API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "online",
        "application": "FloodSense",
        "message": "Python backend is running.",
    }


@app.get("/api/summary")
def satellite_summary():
    required_files = [DEM_PATH, EARLIER_PATH, LATER_PATH]
    missing = [str(path) for path in required_files if not path.exists()]

    if missing:
        raise HTTPException(
            status_code=500,
            detail={"message": "Required data files are missing.", "files": missing},
        )

    try:
        with rasterio.open(DEM_PATH) as src:
            dem = src.read(1, masked=True).astype("float32").filled(np.nan)
            bounds = src.bounds
            crs = str(src.crs)
            shape = dem.shape

        with rasterio.open(EARLIER_PATH) as src:
            earlier = src.read(1)

        with rasterio.open(LATER_PATH) as src:
            later = src.read(1)

        if earlier.shape != dem.shape or later.shape != dem.shape:
            raise HTTPException(
                status_code=500,
                detail="DEM and satellite rasters have different dimensions.",
            )

        # OPERA classes: 0 = non-water, 1 = open water,
        # 3 = inundated vegetation. Other values are excluded.
        common = (
            np.isfinite(dem)
            & np.isin(earlier, [0, 1, 3])
            & np.isin(later, [0, 1, 3])
        )

        earlier_water = common & np.isin(earlier, [1, 3])
        later_water = common & np.isin(later, [1, 3])

        newly_water = common & ~np.isin(earlier, [1, 3]) & np.isin(
            later, [1, 3]
        )

        no_longer_water = common & np.isin(earlier, [1, 3]) & ~np.isin(
            later, [1, 3]
        )

        earlier_count = int(earlier_water.sum())
        later_count = int(later_water.sum())
        newly_count = int(newly_water.sum())
        no_longer_count = int(no_longer_water.sum())

        return {
            "status": "success",
            "dem": {
                "rows": int(shape[0]),
                "columns": int(shape[1]),
                "crs": crs,
                "bounds": {
                    "west": bounds.left,
                    "south": bounds.bottom,
                    "east": bounds.right,
                    "north": bounds.top,
                },
                "minimum_elevation_m": float(np.nanmin(dem)),
                "maximum_elevation_m": float(np.nanmax(dem)),
            },
            "satellite": {
                "earlier_date": "2026-09-15",
                "later_date": "2026-10-14",
                "common_valid_pixels": int(common.sum()),
                "earlier_water_pixels": earlier_count,
                "later_water_pixels": later_count,
                "newly_water_classified_pixels": newly_count,
                "no_longer_water_classified_pixels": no_longer_count,
                "net_pixel_difference": later_count - earlier_count,
                "earlier_water_share_percent": (
                    round(100 * earlier_count / int(common.sum()), 2)
                    if common.any() else 0
                ),
                "later_water_share_percent": (
                    round(100 * later_count / int(common.sum()), 2)
                    if common.any() else 0
                ),
            },
            "interpretation": (
                "These are satellite classification differences, not "
                "confirmation of flood expansion or a validated forecast."
            ),
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not analyze raster data: {exc}",
        ) from exc
@app.get("/api/map.png")
def satellite_map():
    try:
        with rasterio.open(DEM_PATH) as src:
            dem = src.read(1, masked=True).astype("float32").filled(np.nan)
            bounds = src.bounds

        with rasterio.open(EARLIER_PATH) as src:
            earlier = src.read(1)

        with rasterio.open(LATER_PATH) as src:
            later = src.read(1)

        if dem.shape != earlier.shape or dem.shape != later.shape:
            raise HTTPException(
                status_code=500,
                detail="Raster dimensions do not match."
            )

        valid = np.isfinite(dem)

        # Compare only cells with valid classifications in both observations.
        common = (
            valid
            & np.isin(earlier, [0, 1, 3])
            & np.isin(later, [0, 1, 3])
        )

        earlier_water = common & np.isin(earlier, [1, 3])
        later_water = common & np.isin(later, [1, 3])

        newly_water = common & ~earlier_water & later_water
        no_longer_water = common & earlier_water & ~later_water

        fig, ax = plt.subplots(figsize=(10, 7))

        extent = [
            bounds.left,
            bounds.right,
            bounds.bottom,
            bounds.top,
        ]

        terrain = ax.imshow(
            dem,
            extent=extent,
            origin="upper",
            cmap="terrain",
        )

        # RGBA overlay: blue = later water, orange = newly classified,
        # purple = no-longer-water-classified.
        overlay = np.zeros((*dem.shape, 4), dtype=np.float32)

        overlay[later_water] = [0.12, 0.43, 0.75, 0.75]
        overlay[newly_water] = [0.95, 0.48, 0.16, 0.95]
        overlay[no_longer_water] = [0.58, 0.35, 0.70, 0.95]

        ax.imshow(
            overlay,
            extent=extent,
            origin="upper",
        )

        ax.set_title(
            "FloodSense | Terrain and Satellite Classification Changes"
        )
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")

        fig.colorbar(
            terrain,
            ax=ax,
            label="DEM elevation (m)",
            shrink=0.75,
        )

        buffer = BytesIO()
        fig.savefig(
            buffer,
            format="png",
            dpi=130,
            bbox_inches="tight",
        )
        plt.close(fig)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="image/png",
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not generate satellite map: {exc}",
        ) from exc
        
        # ------------------------------------------
# FloodSense: Gauge Reading API
# ------------------------------------------

from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field


class GaugeReading(BaseModel):
    distance_cm: float = Field(ge=0, le=1000)
    sensor_height_cm: float = Field(gt=0, le=1000)
    source: str = "HC-12 receiver"


gauge_history = []


@app.post("/api/gauge")
def receive_gauge_reading(reading: GaugeReading):
    """
    Receive an ultrasonic distance measurement.

    sensor_height_cm:
        Sensor height above the chosen zero-level reference.

    distance_cm:
        Measured distance from sensor to water.

    water_level_cm:
        Calculated water level relative to the chosen reference.
    """

    water_level = reading.sensor_height_cm - reading.distance_cm

# Reject readings that imply an impossible negative water level.
    # Reject readings that imply an impossible negative water level.
    if water_level < -1.0:
        raise HTTPException(
            status_code=422,
            detail=(
                "Invalid sensor reading: measured distance exceeds "
                "the configured sensor height. Check the sensor position "
                "and SENSOR_HEIGHT_CM setting."
            ),
        )

    # Treat small negative values caused by measurement variation as zero.
    water_level = max(0.0, water_level)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": reading.source,
        "distance_cm": reading.distance_cm,
        "sensor_height_cm": reading.sensor_height_cm,
        "water_level_cm": round(water_level, 2),
    }

    gauge_history.append(record)

    # Keep the most recent 1000 readings in memory.
    if len(gauge_history) > 1000:
        del gauge_history[:-1000]

    return {
        "status": "success",
        "reading": record,
    }


@app.get("/api/gauge/latest")
def get_latest_gauge_reading():
    if not gauge_history:
        return {
            "status": "waiting",
            "message": "No gauge readings received yet.",
            "reading": None,
        }

    return {
        "status": "success",
        "reading": gauge_history[-1],
    }


@app.get("/api/gauge/history")
def get_gauge_history():
    return {
        "count": len(gauge_history),
        "readings": gauge_history,
    }
    
@app.get("/api/gauge/rate")
def get_gauge_rate():
    if len(gauge_history) < 2:
        return {
            "rate_cm_per_min": None,
            "trend": "WAITING",
            "sample_count": len(gauge_history)
        }

    now = datetime.now(timezone.utc)
    readings = []

    # Use readings from the last 60 seconds
    for record in gauge_history:
        try:
            timestamp = datetime.fromisoformat(
                record["timestamp"].replace("Z", "+00:00")
            )

            if (now - timestamp).total_seconds() <= 60:
                readings.append((
                    timestamp.timestamp(),
                    float(record["water_level_cm"])
                ))
        except (KeyError, ValueError, TypeError):
            continue

    if len(readings) < 2:
        return {
            "rate_cm_per_min": None,
            "trend": "WAITING",
            "sample_count": len(readings)
        }

    readings.sort(key=lambda item: item[0])

    times = np.array([r[0] for r in readings], dtype=float)
    levels = np.array([r[1] for r in readings], dtype=float)

    elapsed = times[-1] - times[0]

    # Collect enough readings before estimating a rate
    if elapsed < 10:
        return {
            "rate_cm_per_min": None,
            "trend": "WAITING",
            "sample_count": len(readings)
        }

    # Linear regression reduces the effect of small sensor fluctuations
    times = times - times[0]
    rate_cm_per_min = float(np.polyfit(times, levels, 1)[0] * 60)

    if rate_cm_per_min > 0.3:
        trend = "RISING"
    elif rate_cm_per_min < -0.3:
        trend = "FALLING"
    else:
        trend = "STABLE"

    return {
        "rate_cm_per_min": round(rate_cm_per_min, 2),
        "trend": trend,
        "sample_count": len(readings),
        "window_seconds": round(elapsed, 1)
    }
    
    # ---------------------------------------------------
# FloodSense: Potential Inundation Analysis
# ---------------------------------------------------

from scipy import ndimage
from pyproj import Geod
from fastapi import Query


def load_inundation_data():
    """Load the DEM and latest satellite classification."""

    with rasterio.open(DEM_PATH) as src:
        dem = src.read(1, masked=True).astype("float32").filled(np.nan)
        transform = src.transform
        bounds = src.bounds
        crs = str(src.crs)

    with rasterio.open(LATER_PATH) as src:
        water = src.read(1)

    if dem.shape != water.shape:
        raise HTTPException(
            status_code=500,
            detail="DEM and satellite raster dimensions do not match."
        )

    if crs != "EPSG:4326":
        raise HTTPException(
            status_code=500,
            detail=f"Expected EPSG:4326 DEM coordinates; found {crs}."
        )

    return dem, water, transform, bounds


@app.get("/api/water-components")
def get_water_components():
    """
    Identify the largest contiguous water-classified regions
    and return representative coordinates for selecting a seed.
    """

    dem, water, transform, bounds = load_inundation_data()

    water_mask = np.isin(water, [1, 3]) & np.isfinite(dem)

    if not water_mask.any():
        raise HTTPException(
            status_code=404,
            detail="No valid satellite water-classified pixels found."
        )

    labels, component_count = ndimage.label(
        water_mask,
        structure=np.ones((3, 3), dtype=np.uint8)
    )

    sizes = np.bincount(labels.ravel())
    sizes[0] = 0

    largest_labels = np.argsort(sizes[1:])[-10:][::-1] + 1

    components = []

    for label_id in largest_labels:
        if sizes[label_id] == 0:
            continue

        rows, cols = np.where(labels == label_id)

        # Select an actual pixel near the component's centre.
        mean_row = np.mean(rows)
        mean_col = np.mean(cols)

        nearest = np.argmin(
            (rows - mean_row) ** 2 + (cols - mean_col) ** 2
        )

        row = int(rows[nearest])
        col = int(cols[nearest])

        lon, lat = rasterio.transform.xy(
            transform, row, col, offset="center"
        )

        components.append({
    "component_id": int(label_id),
    "pixel_count": int(sizes[label_id]),
    "seed_latitude": float(lat),
    "seed_longitude": float(lon),
    "seed_dem_elevation_m": round(float(dem[row, col]), 2),
    "median_dem_elevation_m": round(
        float(np.median(dem[labels == label_id])), 2
    )
})

    return {
        "status": "success",
        "component_count": int(component_count),
        "components": components,
        "note": (
            "Coordinates identify satellite-classified water pixels. "
            "The median DEM elevation is terrain elevation, not a "
            "measured river water-surface elevation."
        )
    }


@app.get("/api/inundation")
def calculate_inundation(
    water_surface_elevation_m: float = Query(
        ..., gt=0, lt=10000,
        description=(
            "Water-surface elevation in metres, referenced to the "
            "same vertical datum as the DEM."
        )
    ),
    seed_latitude: float = Query(
        ..., ge=-90, le=90,
        description="Latitude of a selected water-classified pixel."
    ),
    seed_longitude: float = Query(
        ..., ge=-180, le=180,
        description="Longitude of a selected water-classified pixel."
    )
):
    """
    Calculate low terrain connected to a selected satellite water pixel.

    This is a simplified terrain scenario, not a hydraulic flood model.
    """

    dem, water, transform, bounds = load_inundation_data()

    # Verify that the coordinate lies inside the DEM.
    if not (
        bounds.left <= seed_longitude <= bounds.right
        and bounds.bottom <= seed_latitude <= bounds.top
    ):
        raise HTTPException(
            status_code=400,
            detail="The selected coordinates fall outside the DEM."
        )

    row, col = rasterio.transform.rowcol(
        transform, seed_longitude, seed_latitude
    )

    if not (
        0 <= row < dem.shape[0]
        and 0 <= col < dem.shape[1]
    ):
        raise HTTPException(
            status_code=400,
            detail="The selected coordinate has no valid DEM pixel."
        )

    # Require the seed pixel to be classified as water in the
    # latest satellite observation.
    if water[row, col] not in [1, 3]:
        raise HTTPException(
            status_code=400,
            detail=(
                "The selected pixel is not classified as water in the "
                "latest satellite raster. Use /api/water-components "
                "to find candidate coordinates."
            )
        )

    valid = np.isfinite(dem)

    if dem[row, col] > water_surface_elevation_m:
        raise HTTPException(
            status_code=422,
            detail=(
                "The selected seed terrain is above the supplied "
                "water-surface elevation. Check the elevation and "
                "vertical datum."
            )
        )

    # Simplified scenario:
    # include cells below the water-surface elevation, then retain
    # only those connected to the selected seed using 8-neighbour
    # connectivity.
    eligible = valid & (dem <= water_surface_elevation_m)

    seed = np.zeros(dem.shape, dtype=bool)
    seed[row, col] = True

    connected = ndimage.binary_propagation(
        seed & eligible,
        structure=np.ones((3, 3), dtype=bool),
        mask=eligible
    )

    rows, cols = np.where(connected)

    if len(rows) == 0:
        raise HTTPException(
            status_code=422,
            detail="No connected terrain pixels were found."
        )

    pixel_count = int(len(rows))

    # Approximate area using the geographic grid resolution and
    # latitude-adjusted pixel width.
    row_counts = np.bincount(rows, minlength=dem.shape[0])

    pixel_height_m = abs(transform.e) * 110574.0

    row_latitudes = np.array([
        rasterio.transform.xy(
            transform, r, 0, offset="center"
        )[1]
        for r in range(dem.shape[0])
    ])

    pixel_widths_m = (
        abs(transform.a)
        * 111320.0
        * np.cos(np.radians(row_latitudes))
    )

    approximate_area_km2 = float(
        np.sum(row_counts * pixel_widths_m * pixel_height_m) / 1e6
    )

    # Calculate maximum straight-line geodesic distance from the
    # selected seed pixel to the connected terrain pixels.
    seed_lon, seed_lat = rasterio.transform.xy(
        transform, row, col, offset="center"
    )

    pixel_lons, pixel_lats = rasterio.transform.xy(
        transform, rows.tolist(), cols.tolist(), offset="center"
    )

    geod = Geod(ellps="WGS84")

    pixel_lons = np.asarray(pixel_lons, dtype=np.float64)
    pixel_lats = np.asarray(pixel_lats, dtype=np.float64)

    # Repeat the seed coordinate for every destination pixel.
    seed_lons = np.full(pixel_lons.shape, float(seed_lon))
    seed_lats = np.full(pixel_lats.shape, float(seed_lat))

    _, _, distances_m = geod.inv(
        seed_lons,
        seed_lats,
        pixel_lons,
        pixel_lats
    )

    max_distance_km = float(np.max(distances_m) / 1000.0)

    return {
        "status": "success",
        "scenario": {
            "water_surface_elevation_m": water_surface_elevation_m,
            "seed_latitude": seed_latitude,
            "seed_longitude": seed_longitude
        },
        "results": {
            "connected_terrain_pixels": pixel_count,
            "approximate_area_km2": round(approximate_area_km2, 4),
            "maximum_straight_line_distance_km": round(
                max_distance_km, 3
            )
        },
        "limitations": [
            "The water-surface elevation must match the DEM vertical datum.",
            "The area is a terrain-scenario estimate, not confirmed inundation.",
            "Distance is measured in a straight line, not along the river.",
            "The method does not simulate flow, discharge, flood timing, "
            "river hydraulics, or barriers not adequately represented by "
            "the terrain data."
        ]
    }
@app.get("/api/inundation-map.png")
def inundation_map(
    water_surface_elevation_m: float = Query(..., gt=0, lt=10000),
    seed_latitude: float = Query(..., ge=-90, le=90),
    seed_longitude: float = Query(..., ge=-180, le=180),
):
    """Visualize a hypothetical connected low-terrain scenario."""

    dem, water, transform, bounds = load_inundation_data()

    valid = np.isfinite(dem)

    # Confirm that the selected coordinate lies inside the DEM.
    if not (
        bounds.left <= seed_longitude <= bounds.right
        and bounds.bottom <= seed_latitude <= bounds.top
    ):
        raise HTTPException(
            status_code=400,
            detail="Selected location is outside the study area.",
        )

    row, col = rasterio.transform.rowcol(
        transform, seed_longitude, seed_latitude
    )

    if not (0 <= row < dem.shape[0] and 0 <= col < dem.shape[1]):
        raise HTTPException(
            status_code=400,
            detail="Invalid pixel coordinates.",
        )

    # The selected coordinate must be classified as water.
    water_mask = np.isin(water, [1, 3]) & valid

    if not water_mask[row, col]:
        raise HTTPException(
            status_code=400,
            detail="The selected pixel is not classified as water.",
        )

    # Identify the contiguous satellite-observed water region.
    labels, _ = ndimage.label(
        water_mask,
        structure=np.ones((3, 3), dtype=np.uint8),
    )

    component_id = labels[row, col]
    observed_component = labels == component_id

    # Identify terrain below the hypothetical elevation threshold.
    eligible = valid & (dem <= water_surface_elevation_m)

    connected_source = observed_component & eligible

    if not connected_source.any():
        raise HTTPException(
            status_code=422,
            detail=(
                "No selected water-region pixels fall below the "
                "chosen elevation threshold. Check the elevation datum."
            ),
        )

    potential = ndimage.binary_propagation(
        connected_source,
        structure=np.ones((3, 3), dtype=bool),
        mask=eligible,
    )

    # Prepare the geographic visualization.
    fig, ax = plt.subplots(figsize=(9, 6))

    extent = [
        bounds.left,
        bounds.right,
        bounds.bottom,
        bounds.top,
    ]

    terrain = ax.imshow(
        dem,
        extent=extent,
        origin="upper",
        cmap="terrain",
    )

    # Blue: satellite-observed water component.
    # Orange: additional connected terrain in the scenario.
    overlay = np.zeros((*dem.shape, 4), dtype=np.float32)

    overlay[observed_component] = [0.12, 0.43, 0.75, 0.8]

    expansion = potential & ~observed_component
    overlay[expansion] = [0.95, 0.48, 0.16, 0.8]

    ax.imshow(
        overlay,
        extent=extent,
        origin="upper",
    )

    from matplotlib.patches import Patch

    ax.legend(
        handles=[
            Patch(color="#1f6ebf", label="Satellite-observed water"),
            Patch(color="#f27929", label="Potential connected terrain"),
        ],
        loc="lower right",
        fontsize=8,
    )

    ax.set_title(
        f"Terrain scenario — threshold {water_surface_elevation_m:.2f} m"
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    fig.colorbar(
        terrain,
        ax=ax,
        label="DEM elevation (m)",
        shrink=0.75,
    )

    buffer = BytesIO()

    try:
        fig.savefig(
            buffer,
            format="png",
            dpi=120,
            bbox_inches="tight",
        )
    finally:
        plt.close(fig)

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="image/png",
    )
