from dataclasses import dataclass


@dataclass
class GaugeReading:
    previous_level_m: float
    current_level_m: float
    elapsed_minutes: float


@dataclass
class SatelliteEvidence:
    earlier_area_km2: float
    later_area_km2: float
    earlier_date: str
    later_date: str


def assess_flood_evidence(gauge, satellite):
    if gauge.elapsed_minutes <= 0:
        raise ValueError("Elapsed time must be positive.")

    if gauge.previous_level_m < 0 or gauge.current_level_m < 0:
        raise ValueError("Gauge levels cannot be negative.")

    if satellite.earlier_area_km2 < 0 or satellite.later_area_km2 < 0:
        raise ValueError("Satellite areas cannot be negative.")

    change_m = gauge.current_level_m - gauge.previous_level_m
    rate_m_per_hour = change_m / gauge.elapsed_minutes * 60

    # Demonstration threshold only; calibrate with real gauge accuracy.
    threshold_m = 0.02

    if change_m > threshold_m:
        trend = "RISING"
    elif change_m < -threshold_m:
        trend = "FALLING"
    else:
        trend = "STABLE"

    area_change = (
        satellite.later_area_km2 - satellite.earlier_area_km2
    )

    if satellite.earlier_area_km2 > 0:
        area_change_percent = (
            area_change / satellite.earlier_area_km2
        ) * 100
    else:
        area_change_percent = None

    # Satellite observations are historical, so this is a comparison
    # of evidence rather than confirmation of current flooding.
    if area_change > 0.01:
        satellite_trend = "INCREASED"
    elif area_change < -0.01:
        satellite_trend = "DECREASED"
    else:
        satellite_trend = "LITTLE_CHANGE"

    if trend == "RISING" and satellite_trend == "INCREASED":
        interpretation = (
            "Both indicators show an increasing trend, but the satellite "
            "observations are historical. Current flood expansion is "
            "not confirmed."
        )
    elif trend == "RISING" and satellite_trend != "INCREASED":
        interpretation = (
            "The river gauge is rising, but the historical satellite "
            "comparison does not show a corresponding increase. Continue "
            "monitoring and check official local warnings."
        )
    elif trend == "FALLING":
        interpretation = (
            "The river gauge is falling. This does not establish that "
            "previously inundated locations are safe."
        )
    else:
        interpretation = (
            "The gauge is approximately stable. Historical satellite "
            "evidence alone cannot establish current flood conditions."
        )

    return {
        "gauge_change_m": change_m,
        "gauge_rate_m_per_hour": rate_m_per_hour,
        "gauge_trend": trend,
        "satellite_area_change_km2": area_change,
        "satellite_area_change_percent": area_change_percent,
        "satellite_trend": satellite_trend,
        "interpretation": interpretation,
    }


if __name__ == "__main__":
    # Illustrative test values, not live measurements.
    gauge = GaugeReading(
        previous_level_m=4.20,
        current_level_m=4.50,
        elapsed_minutes=30,
    )

    satellite = SatelliteEvidence(
        earlier_area_km2=3.64,
        later_area_km2=5.21,
        earlier_date="2026-09-15",
        later_date="2026-10-14",
    )

    result = assess_flood_evidence(gauge, satellite)

    print("\n========== FLOODSENSE EVIDENCE ASSESSMENT ==========")
    print(f"Gauge trend: {result['gauge_trend']}")
    print(f"Gauge change: {result['gauge_change_m']:+.3f} m")
    print(
        "Gauge rate: "
        f"{result['gauge_rate_m_per_hour']:+.3f} m/hour"
    )
    print(f"Satellite trend: {result['satellite_trend']}")
    print(
        "Satellite area change: "
        f"{result['satellite_area_change_km2']:+.3f} km²"
    )

    percent = result["satellite_area_change_percent"]
    if percent is not None:
        print(f"Satellite area change: {percent:+.2f}%")

    print("\nInterpretation:")
    print(result["interpretation"])
    print("\nNote: Test values are illustrative; this is not a validated forecast.")
