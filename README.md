# VELOR | River Monitoring & Flood Inundation Screening

**Connecting live water-level monitoring with satellite observations and terrain analysis to support flood-risk assessment.**

VELOR is a hydrological monitoring prototype that combines sensor readings, satellite-derived water classifications, and Digital Elevation Model (DEM) data to explore how changing water levels could affect surrounding terrain.

The idea behind VELOR is simple: monitoring water levels is useful, but understanding what those changes could mean for the surrounding area is equally important. VELOR brings these elements together in one dashboard.


## What VELOR Does

* **Monitors water levels:** Used to measure the distance between the sensor and the water surface.
* **Tracks water-level changes:** Displays incoming measurements and estimates the rate of rise when sufficient recent readings are available.
* **Compares satellite observations:** Examines water-classification data from two OPERA DSWx-S1 observations to identify changes between observation dates.
* **Analyses surrounding terrain:** Uses a DEM to estimate connected low-lying terrain below a selected hypothetical water-surface elevation.
* **Visualises potential impact:** Presents preliminary terrain-area and distance estimates through an interactive web dashboard.
* **Supports wireless monitoring:** Includes an experimental HC-12 communication design for transmitting measurements from a remote gauge node to a receiver.


## Technology Stack

| Component              | Technologies                             |
| ---------------------- | ---------------------------------------- |
| Frontend               | React, Vite, JavaScript, CSS             |
| Backend                | Python, FastAPI, Uvicorn                 |
| Geospatial processing  | Rasterio, NumPy, PyProj                  |
| Gauge controller       | ESP32                                    |
| Wireless communication | HC-12 modules — experimental integration |
| Terrain data           | Digital Elevation Model (DEM)            |
| Satellite observations | OPERA DSWx-S1                            |


## Backend API

The FastAPI backend provides endpoints for gauge readings, satellite statistics, and terrain analysis.

| Endpoint                      | Purpose                                                            |
| ----------------------------- | ------------------------------------------------------------------ |
| `GET /api/health`             | Check backend availability                                         |
| `GET /api/summary`            | Retrieve DEM and satellite summary statistics                      |
| `GET /api/gauge/latest`       | Retrieve the latest accepted gauge reading                         |
| `GET /api/gauge/history`      | Retrieve stored gauge readings                                     |
| `POST /api/gauge`             | Submit a gauge measurement                                         |
| `GET /api/water-components`   | Retrieve satellite-classified water regions                        |
| `GET /api/inundation`         | Estimate connected terrain below a selected hypothetical elevation |
| `GET /api/map.png`            | Retrieve the terrain and satellite overview map                    |
| `GET /api/inundation-map.png` | Retrieve the terrain-scenario map, where supported                 |

The exact response formats depend on the current backend implementation.


## Hardware Overview

### Gauge Node

The gauge node is designed around:

* ESP32 microcontroller
* HC-SR04 ultrasonic sensor
* HC-12 transmitter for the experimental wireless route
* Appropriate power supply and supporting circuitry

The ultrasonic sensor is mounted above the water surface. As the water level rises, the distance measured by the sensor decreases.

The approximate water depth in the demonstration container is calculated using:

```text
Water Level = Sensor Height - Measured Distance
```

The HC-SR04 is not waterproof, so it is suitable for a controlled demonstration rather than direct exposure to river conditions.

### Receiver Node

The proposed wireless receiver consists of:

* HC-12 receiver module
* ESP8266 NodeMCU
* Wi-Fi connection to the laptop running FastAPI

The receiver is intended to read incoming radio packets and forward valid measurements to the backend over HTTP.

The HC-12 link is still experimental. Its range, reliability, and end-to-end data delivery need to be tested before the communication path can be described as operational.

## Satellite Analysis

VELOR compares two OPERA DSWx-S1 water-classification observations:

* **15 September 2026**
* **14 October 2026**

The comparison examines pixels classified as water in both observations, pixels newly classified as water, and pixels no longer classified as water.

These differences help show how water classification changed between the two observation dates.

Satellite classification changes should not automatically be interpreted as confirmed flood expansion. The observations represent specific acquisition dates rather than continuous live monitoring.

## DEM-Based Terrain Analysis

One of VELOR's main features is the use of a Digital Elevation Model to explore potential terrain inundation.

The backend starts from a selected satellite-classified water region and estimates connected terrain below a chosen hypothetical water-surface elevation.

The current model produces preliminary estimates of:

* Connected terrain area in square kilometres
* Maximum straight-line distance from the selected seed location
* Number of connected terrain cells

The dashboard can compare different hypothetical water-level scenarios and display their calculated results.

### What the Results Mean

The model identifies connected terrain under a selected elevation threshold. It does not establish that every identified location will flood.

The current demonstration can also map the water depth measured in the test container to a hypothetical elevation change in the DEM. This is an illustrative scaling assumption, not a calibrated conversion to actual river elevation.

A DEM alone cannot determine which buildings are occupied, how many people could be affected, or which locations must officially be evacuated.

The results should therefore be treated as preliminary terrain-screening estimates, not confirmed flood boundaries or evacuation instructions.


## Future Improvements

The next stage of development could focus on making VELOR more reliable and useful through better field calibration, validated hydrological inputs, clearer impact mapping, and more robust wireless communication.

The longer-term goal is to connect reliable water-level observations with meaningful spatial context so that changes at a monitoring point can be evaluated alongside the surrounding terrain.

## Safety and Intended Use

VELOR is a prototype for learning, demonstration, and preliminary terrain analysis. It is not a certified flood-forecasting or public-warning system.

Real-world deployment would require field-validated measurements, calibrated elevation references, validated flood models, reliable communications, and coordination with the relevant authorities.

## About

VELOR is an electronics and geospatial engineering project exploring how embedded sensing, wireless communication, satellite observations, and terrain modelling can work together in a flood-monitoring workflow.


