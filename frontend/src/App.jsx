import { useState, useEffect } from 'react'
import {
Activity,
MapPinned,
TrendingUp,
Radio,
Clock3,
AlertTriangle,
CheckCircle2,
Droplets,
} from 'lucide-react'
import './App.css'

const scenarios = {
stable: {
label: 'Stable Conditions',
level: 2.4,
rate: 0.0,
change: 0.2,
status: 'Stable',
description: 'Water level and satellite observations show no significant increase.',
},
rising: {
label: 'Rising Water',
level: 320,
rate: 18,
change: 12.6,
status: 'Rising',
description: 'Simulated water-level rise. Review the latest satellite evidence and terrain scenario.',
},
}

function MetricCard({ label, value, unit, icon: Icon, note }) {
return ( <article className="metric-card"> <div className="metric-heading"> <span>{label}</span> <span className="metric-icon"><Icon size={19} /></span> </div> <div className="metric-value">{value}<small>{unit}</small></div> <div className="metric-note">{note}</div> </article>
)
}

function WaterChart({ history, trend }) {
  const data = history
    .filter((item) =>
      item &&
      item.timestamp &&
      Number.isFinite(Date.parse(item.timestamp)) &&
      Number.isFinite(Number(item.water_level_cm))
    )
    .slice(-30)
    .map((item) => ({
      timestamp: item.timestamp,
      time: new Date(item.timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }),
      level: Number(item.water_level_cm),
    }))

  const width = 620
  const height = 225
  const left = 52
  const right = 14
  const top = 20
  const bottom = 42
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom

  // Fit the vertical axis to real measurements, with breathing room when
  // measurements are flat so a constant level still appears clearly.
  const values = data.map((item) => item.level)
  const observedMin = values.length ? Math.min(...values) : 0
  const observedMax = values.length ? Math.max(...values) : 1
  const observedRange = observedMax - observedMin
  const padding = observedRange > 0 ? observedRange * 0.2 : Math.max(Math.abs(observedMax) * 0.03, 0.5)
  const min = observedMin - padding
  const max = observedMax + padding || min + 1

  const points = data.map((item, index) => ({
    x: left + (data.length <= 1 ? plotWidth / 2 : (index / (data.length - 1)) * plotWidth),
    y: top + ((max - item.level) / (max - min)) * plotHeight,
    ...item,
  }))

  const line = points.map((point) => `${point.x},${point.y}`).join(' ')
  const area = points.length > 1
    ? `${left},${height - bottom} ${line} ${points[points.length - 1].x},${height - bottom}`
    : ''
  const chartStyle = trend === 'RISING' ? 'rising' : 'stable'
  const tickValues = [0, 1, 2, 3].map((step) => max - (step / 3) * (max - min))
  const labelIndexes = data.length <= 6
    ? data.map((_, index) => index)
    : Array.from({ length: 6 }, (_, index) => Math.round((index / 5) * (data.length - 1)))

  return (
    <div className="chart-wrap">
      {data.length === 0 ? (
        <div style={{ minHeight: 205, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, textAlign: 'center', color: '#73849a' }}>
          <Radio size={24} />
          <strong>Waiting for live sensor readings</strong>
          <span>The chart will begin plotting when VELOR receives measurements from the gauge.</span>
        </div>
      ) : (
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Live ultrasonic water-level history in centimetres">
          {tickValues.map((value, index) => {
            const y = top + (index / 3) * plotHeight
            return (
              <g key={`${value}-${index}`}>
                <line x1={left} y1={y} x2={width - right} y2={y} className="grid-line" />
                <text x={left - 9} y={y + 4} textAnchor="end" className="axis-label">{value.toFixed(1)}</text>
              </g>
            )
          })}
          {points.length > 1 && <polygon points={area} className={`chart-area ${chartStyle}`} />}
          {points.length > 1 && <polyline points={line} className={`chart-line ${chartStyle}`} />}
          {points.map((point) => (
            <circle key={point.timestamp} cx={point.x} cy={point.y} r="4" className={`chart-point ${chartStyle}`}>
              <title>{`${point.time}: ${point.level.toFixed(2)} cm`}</title>
            </circle>
          ))}
          {labelIndexes.map((index) => {
            const point = points[index]
            return (
              <text key={`${point.timestamp}-label`} x={point.x} y={height - 12} textAnchor="middle" className="axis-label">
                {point.time}
              </text>
            )
          })}
        </svg>
      )}
      <div className="chart-disclaimer">
        {data.length > 0
          ? `Live sensor readings · ${data.length} latest point${data.length === 1 ? '' : 's'} plotted · water level in cm`
          : 'No sample values are shown; live measurements will appear here.'}
      </div>
    </div>
  )
}

function calculateGaugeTrend(history) {
  const now = Date.now()
  const recent = history
    .map((reading) => ({
      time: Date.parse(reading.timestamp),
      level: Number(reading.water_level_cm),
    }))
    .filter(
      (reading) =>
        Number.isFinite(reading.time) &&
        Number.isFinite(reading.level) &&
        now - reading.time >= 0 &&
        now - reading.time <= 60000
    )
    .sort((a, b) => a.time - b.time)

  // Wait for at least four distinct readings spanning 10 seconds.
  if (recent.length < 4) return null

  const firstTime = recent[0].time
  const elapsedSeconds = (recent[recent.length - 1].time - firstTime) / 1000
  if (elapsedSeconds < 10) return null

  // Least-squares slope smooths small ultrasonic sensor fluctuations.
  const times = recent.map((reading) => (reading.time - firstTime) / 1000)
  const levels = recent.map((reading) => reading.level)
  const meanTime = times.reduce((sum, value) => sum + value, 0) / times.length
  const meanLevel = levels.reduce((sum, value) => sum + value, 0) / levels.length

  let numerator = 0
  let denominator = 0
  for (let index = 0; index < times.length; index += 1) {
    numerator += (times[index] - meanTime) * (levels[index] - meanLevel)
    denominator += (times[index] - meanTime) ** 2
  }

  if (denominator === 0) return null

  const rateCmPerMinute = (numerator / denominator) * 60
  const trend = rateCmPerMinute > 0.3
    ? 'RISING'
    : rateCmPerMinute < -0.3
      ? 'FALLING'
      : 'STABLE'

  return {
    rateCmPerMinute,
    // 1 cm/min = 0.6 m/hour.
    rateMetersPerHour: rateCmPerMinute * 0.6,
    trend,
    sampleCount: recent.length,
    windowSeconds: elapsedSeconds,
  }
}

function App() {
  const [scenario, setScenario] = useState('stable')
  const [activeNav, setActiveNav] = useState('overview')

function navigateTo(page) {
  setActiveNav(page)

  document.getElementById(page)?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}
  const [gaugeData, setGaugeData] = useState(null)
  const [gaugeHistory, setGaugeHistory] = useState([])

const [gaugeApiError, setGaugeApiError] = useState('')
const [waterComponents, setWaterComponents] = useState([])
const [selectedComponentId, setSelectedComponentId] = useState('')
const [inundationResult, setInundationResult] = useState(null)
const [inundationLoading, setInundationLoading] = useState(false)
const [inundationError, setInundationError] = useState('')

const selectedWaterComponent = waterComponents.find(
  (component) =>
    String(component.component_id) === selectedComponentId
)

// LIVE-TO-DEM DEMONSTRATION MAPPING
// The ultrasonic sensor measures depth in the demo container, not absolute
// river elevation. For this prototype only, map the full measured sensor-height
// range to a 0–3 m terrain-stage range above the selected DEM water-region seed.
// This scale is adjustable and is NOT a calibrated real-river conversion.
const DEMO_MAX_STAGE_RISE_M = 3.0
const liveReadingTimestamp = gaugeData?.timestamp
  ? Date.parse(gaugeData.timestamp)
  : NaN
const liveSensorHeightRaw = Number(gaugeData?.sensor_height_cm)
const liveWaterLevelRaw = Number(gaugeData?.water_level_cm)
const hasFreshLiveWaterLevel = Boolean(
  gaugeData &&
  Number.isFinite(liveReadingTimestamp) &&
  Date.now() - liveReadingTimestamp >= 0 &&
  Date.now() - liveReadingTimestamp <= 15000 &&
  Number.isFinite(liveSensorHeightRaw) &&
  liveSensorHeightRaw > 0 &&
  Number.isFinite(liveWaterLevelRaw)
)
const liveSensorHeightCm = hasFreshLiveWaterLevel ? liveSensorHeightRaw : null
const liveWaterLevelCm = hasFreshLiveWaterLevel
  ? Math.max(0, Math.min(liveWaterLevelRaw, liveSensorHeightRaw))
  : null
const liveStageRiseM = liveWaterLevelCm !== null
  ? Math.round((liveWaterLevelCm / liveSensorHeightCm) * DEMO_MAX_STAGE_RISE_M * 2) / 2
  : null

// Use the live, demo-scaled stage whenever a fresh measurement exists.
// If no fresh reading is available, retain the Stable/Rising scenario buttons.
const terrainStageRiseM = liveStageRiseM !== null
  ? liveStageRiseM
  : scenario === 'rising'
    ? DEMO_MAX_STAGE_RISE_M
    : 0.5
const selectedSeedElevationM = selectedWaterComponent
  ? Number(selectedWaterComponent.seed_dem_elevation_m)
  : NaN
const scenarioLevel = selectedWaterComponent && Number.isFinite(selectedSeedElevationM)
  ? selectedSeedElevationM + terrainStageRiseM
  : null

  const current = scenarios[scenario]
  const liveTrend = calculateGaugeTrend(gaugeHistory)

  const statusTitle = liveTrend
    ? liveTrend.trend === 'RISING'
      ? 'Rising Water Conditions'
      : liveTrend.trend === 'FALLING'
        ? 'Falling Water Conditions'
        : 'Stable Conditions'
    : gaugeData
      ? 'Collecting Live Readings'
      : current.label

  const statusDescription = liveTrend
    ? liveTrend.trend === 'RISING'
      ? 'Live ultrasonic readings indicate that the measured water level is increasing.'
      : liveTrend.trend === 'FALLING'
        ? 'Live ultrasonic readings indicate that the measured water level is decreasing.'
        : 'Live ultrasonic readings show no significant change in water level.'
    : gaugeData
      ? 'Sensor data is arriving. Collecting enough distinct readings to estimate the live trend.'
      : current.description

  const statusClass = liveTrend
    ? liveTrend.trend === 'RISING'
      ? 'rising'
      : 'stable'
    : scenario

  // 2. Poll the latest gauge reading every three seconds
useEffect(() => {
  let active = true

  async function loadGaugeData() {
    try {
      const response = await fetch(
        'http://127.0.0.1:8000/api/gauge/latest',
        { cache: 'no-store' }
      )

      if (!response.ok) {
        throw new Error(`Gauge API returned HTTP ${response.status}`)
      }

      const result = await response.json()
      const reading = result.status === 'success' ? result.reading : null

      // Fetch the backend's stored readings as well as the latest reading,
      // so faster sensor transmissions are not skipped by the browser poll.
      let serverHistory = []
      try {
        const historyResponse = await fetch(
          'http://127.0.0.1:8000/api/gauge/history',
          { cache: 'no-store' }
        )
        if (historyResponse.ok) {
          const historyPayload = await historyResponse.json()
          if (Array.isArray(historyPayload)) {
            serverHistory = historyPayload
          } else if (Array.isArray(historyPayload.history)) {
            serverHistory = historyPayload.history
          } else if (Array.isArray(historyPayload.readings)) {
            serverHistory = historyPayload.readings
          } else if (Array.isArray(historyPayload.data)) {
            serverHistory = historyPayload.data
          } else if (Array.isArray(historyPayload.records)) {
            serverHistory = historyPayload.records
          } else if (Array.isArray(historyPayload.items)) {
            serverHistory = historyPayload.items
          }
        }
      } catch (historyError) {
        console.warn('Gauge history endpoint unavailable; using latest readings:', historyError)
      }

      if (active) {
        setGaugeData(reading)

        setGaugeHistory((previous) => {
          const merged = new Map()
          ;[...previous, ...serverHistory, ...(reading ? [reading] : [])].forEach((item) => {
            if (
              item &&
              item.timestamp &&
              Number.isFinite(Date.parse(item.timestamp)) &&
              Number.isFinite(Number(item.water_level_cm))
            ) {
              merged.set(item.timestamp, {
                timestamp: item.timestamp,
                water_level_cm: Number(item.water_level_cm),
              })
            }
          })

          return Array.from(merged.values())
            .sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp))
            .slice(-120)
        })

        setGaugeApiError('')
      }
    } catch (error) {
      if (active) {
        setGaugeApiError(error.message)
      }
    }
  }

  loadGaugeData()

  const timer = setInterval(loadGaugeData, 3000)

  return () => {
    active = false
    clearInterval(timer)
  }
}, [])


// 3. Load satellite-classified water regions
useEffect(() => {
  let active = true

  async function loadWaterComponents() {
    try {
      const response = await fetch(
        'http://127.0.0.1:8000/api/water-components'
      )

      if (!response.ok) {
        throw new Error(
          `Could not load water regions: HTTP ${response.status}`
        )
      }

      const data = await response.json()

      if (!active) return

      const components = Array.isArray(data.components)
        ? data.components
        : []

      setWaterComponents(components)

      if (components.length > 0) {
        setSelectedComponentId(
          String(components[0].component_id)
        )
        setInundationError('')
      } else {
        setInundationError('No satellite water regions were found.')
      }
    } catch (error) {
      if (active) {
        setInundationError(error.message)
      }
    }
  }

  loadWaterComponents()

  return () => {
    active = false
  }
}, [])


// 4. Calculate the selected terrain scenario
useEffect(() => {
  if (!selectedWaterComponent || scenarioLevel === null) {
    return
  }

  let active = true
  const controller = new AbortController()

  async function calculateScenario() {
    setInundationLoading(true)
    setInundationError('')

    try {
      const params = new URLSearchParams({
        water_surface_elevation_m: String(scenarioLevel),
        seed_latitude: String(
          selectedWaterComponent.seed_latitude
        ),
        seed_longitude: String(
          selectedWaterComponent.seed_longitude
        ),
      })

      const response = await fetch(
        `http://127.0.0.1:8000/api/inundation?${params}`,
        { signal: controller.signal }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : JSON.stringify(data.detail || 'Scenario calculation failed')
        )
      }

      if (active) {
        setInundationResult(data)
      }
    } catch (error) {
      if (active && error.name !== 'AbortError') {
        setInundationError(error.message)
      }
    } finally {
      if (active) {
        setInundationLoading(false)
      }
    }
  }

  calculateScenario()

  return () => {
    active = false
    controller.abort()
  }
}, [scenarioLevel, selectedWaterComponent])


return ( <div className="app-shell">
  <style>{`
    /* Responsive layout correction: prevent the dashboard from being wider than the viewport. */
    html, body, #root { width: 100%; max-width: 100%; margin: 0; box-sizing: border-box; }
    *, *::before, *::after { box-sizing: border-box; }
    .app-shell { display: flex; width: 100%; max-width: 100%; min-width: 0; overflow-x: hidden; }
    .sidebar { flex: 0 0 auto; min-width: 0; }
    .main-content { flex: 1 1 0%; width: 0; min-width: 0; max-width: 100%; overflow-x: hidden; box-sizing: border-box; }
    .topbar, .scenario-section, .scenario-description, .metrics-grid, .content-grid, .bottom-grid,
    .community-impact-section, .community-impact-header, .community-impact-grid, .community-advisory,
    .panel, .chart-panel, .map-panel { min-width: 0; max-width: 100%; box-sizing: border-box; }
    .community-impact-section { width: 100%; min-width: 0; max-width: 100%; overflow: hidden; }
    .community-impact-header { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 16px; }
    .community-impact-header > div { flex: 1 1 280px; min-width: 0; }
    .impact-status { max-width: 100%; white-space: normal; overflow-wrap: anywhere; }
    .community-impact-grid { display: grid !important; grid-template-columns: repeat(3, minmax(0, 1fr)) !important; gap: 18px; width: 100%; min-width: 0; }
    .community-impact-card { width: 100%; min-width: 0; max-width: 100%; overflow-wrap: anywhere; }
    .community-impact-card p, .community-advisory p, .advisory-footnote { max-width: 100%; white-space: normal; overflow-wrap: anywhere; word-break: normal; line-height: 1.6; }
    .impact-card-value { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px; min-width: 0; overflow-wrap: anywhere; }
    .community-advisory { width: 100%; min-width: 0; max-width: 100%; overflow-wrap: anywhere; }
    .content-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .real-map-wrap, .real-map-image { width: 100%; max-width: 100%; min-width: 0; }
    .real-map-image { height: auto; object-fit: contain; }
    @media (max-width: 1100px) {
      .community-impact-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
      .content-grid { grid-template-columns: minmax(0, 1fr); }
    }
    @media (max-width: 650px) {
      .community-impact-grid, .metrics-grid, .content-grid { grid-template-columns: minmax(0, 1fr) !important; }
      .main-content { padding: 16px !important; }
      .topbar, .scenario-section, .scenario-description { flex-wrap: wrap; }
      .impact-status { justify-self: start; }
    }
  `}</style> <aside className="sidebar"> <div className="brand">  <div> <div className="brand-name">VELOR</div> <div className="brand-caption">HYDROLOGICAL INTELLIGENCE</div> </div> </div>

    <div className="sidebar-label">WORKSPACE</div>
    <button
  type="button"
  className={`nav-item ${activeNav === 'overview' ? 'active' : ''}`}
  onClick={() => navigateTo('overview')}
>
  <Activity size={18} />
  Overview
</button>

<button
  type="button"
  className={`nav-item ${activeNav === 'inundation-map' ? 'active' : ''}`}
  onClick={() => navigateTo('inundation-map')}
>
  <MapPinned size={18} />
  Inundation Map
</button>

<button
  type="button"
  className={`nav-item ${activeNav === 'community-impact' ? 'active' : ''}`}
  onClick={() => navigateTo('community-impact')}
>
  <AlertTriangle size={18} />
  Impact Assessment
</button>

<button
  type="button"
  className={`nav-item ${activeNav === 'sensor-monitoring' ? 'active' : ''}`}
  onClick={() => navigateTo('sensor-monitoring')}
>
  <Radio size={18} />
  Sensor Monitoring
</button>

    <div className="sidebar-bottom">
      <div className="connection-indicator"><span /> Prototype interface</div>
      <p>{gaugeData ? 'Live gauge data received' : 'Waiting for sensor data'}</p>
      <div className="sidebar-version">FLOODSENSE · DEVELOPMENT BUILD</div>
    </div>
  </aside>

  <main className="main-content">
    <header className="topbar" id="overview">
      <div>
        <div className="eyebrow">MONITORING CENTRE / OVERVIEW</div>
        <h1>River Monitoring Dashboard</h1>
        <p className="page-subtitle">Water-level trends, satellite evidence and terrain scenarios.</p>
      </div>
      <div className="prototype-badge"><span /> DEMO MODE</div>
    </header>

    <section className="scenario-section">
      <div>
        <div className="section-kicker">SCENARIO SIMULATOR</div>
        <h2>Explore river conditions</h2>
        <p>With a fresh sensor reading, the DEM threshold follows a demonstration-scaled stage derived from the container level. Without fresh readings, use the Stable and Rising Water scenarios.</p>
      </div>
      <div className="scenario-toggle">
        <button
          className={scenario === 'stable' ? 'scenario-button selected' : 'scenario-button'}
          onClick={() => setScenario('stable')}
        >
          <CheckCircle2 size={17} /> Stable
        </button>
        <button
          className={scenario === 'rising' ? 'scenario-button selected rising-button' : 'scenario-button'}
          onClick={() => setScenario('rising')}
        >
          <TrendingUp size={17} /> Rising Water
        </button>
      </div>
    </section>

    <div className="scenario-description">
      <span className={`status-dot ${statusClass}`} />
      <div>
        <strong>{statusTitle}</strong>
        <p>{statusDescription}</p>
      </div>
      <span className="simulated-tag">
        {hasFreshLiveWaterLevel
          ? 'LIVE SENSOR · DEMO SCALE'
          : gaugeData
            ? 'STALE / WAITING'
            : 'SIMULATED'}
      </span>
    </div>

    <section className="metrics-grid">
      <MetricCard
  label="Water Level"
  value={
    gaugeData
      ? (Number(gaugeData.water_level_cm) / 100).toFixed(2)
      : '—'
  }
  unit="m"
  icon={Droplets}
  note={
    gaugeData
      ? `Received from: ${gaugeData.source}`
      : gaugeApiError
        ? 'Backend connection failed'
        : 'Waiting for a gauge reading'
  }
/>
      <MetricCard
        label="Rate of Rise"
        value={
          liveTrend
            ? liveTrend.rateMetersPerHour.toFixed(2)
            : gaugeData
              ? '—'
              : current.rate.toFixed(2)
        }
        unit="m/h"
        icon={TrendingUp}
        note={
          liveTrend
            ? `Live sensor · ${liveTrend.trend}`
            : gaugeData
              ? 'Collecting recent sensor readings'
              : 'Simulated trend · No live gauge data'
        }
      />
      <MetricCard
  label="Water Level"
  value={
    gaugeData &&
    Number.isFinite(Number(gaugeData.water_level_cm))
      ? Number(gaugeData.water_level_cm).toFixed(1)
      : '—'
  }
  unit="cm"
  icon={Droplets}
  note={
    gaugeData
      ? `Received from: ${gaugeData.source}`
      : 'Waiting for a gauge reading'
  }
/>
      <MetricCard
  label="Gauge Data"
  value={gaugeData ? 'Received' : 'Waiting'}
  unit=""
  icon={Radio}
  note={
    gaugeData
      ? `Source: ${gaugeData.source}`
      : gaugeApiError
        ? 'Cannot reach the Python API'
        : 'No readings received yet'
  }
/>
    </section>

    <section className="content-grid">
      <article className="panel chart-panel" id="sensor-monitoring">
        <div className="panel-header">
          <div>
            <div className="section-kicker">SENSOR HISTORY</div>
            <h3>Water-level trend</h3>
          </div>
          <span className="subtle-badge"><Clock3 size={14} /> {gaugeData ? 'Live readings' : 'Waiting for sensor'}</span>
        </div>
        <WaterChart history={gaugeHistory} trend={liveTrend?.trend} />
      </article>

      <article className="panel map-panel" id="inundation-map">
        <div className="panel-header">
          <div>
            <div className="section-kicker">GEOSPATIAL ANALYSIS</div>
            <h3>Selected study area</h3>
          </div>
          <MapPinned size={19} className="muted-icon" />
        </div>
        <div className="real-map-wrap">
  <img
    src="http://127.0.0.1:8000/api/map.png"
    alt="Terrain elevation and satellite water classification map"
    className="real-map-image"
  />

  <div className="real-map-legend">
    <span>
      <i className="legend-blue" />
      Water-classified pixels
    </span>

    <span>
      <i className="legend-orange" />
      Newly classified as water
    </span>

    <span>
      <i className="legend-purple" />
      No longer classified as water
    </span>
  </div>
</div>
        <div className="map-footer">
          <span>Study area: Krishna DEM extent</span>
          <span className="pending-label">Map integration pending</span>
        </div>
      </article>
    </section>

    <section className="community-impact-section" id="community-impact">
  <div className="community-impact-header">
    <div>
      <div className="section-kicker">COMMUNITY SAFETY</div>
      <h2>Impact Assessment</h2>
      <p>DEM-based screening of terrain that may need evacuation assessment under the selected water-level scenario.</p>
    </div>

    <span className={`impact-status ${statusClass}`}>
      {liveTrend
        ? liveTrend.trend === 'RISING'
          ? 'Live water level rising'
          : liveTrend.trend === 'FALLING'
            ? 'Live water level falling'
            : 'Live water level stable'
        : gaugeData
          ? 'Collecting live trend'
          : scenario === 'rising'
            ? 'Rising-water scenario'
            : 'Stable scenario'}
    </span>
  </div>

  <div className="community-impact-grid">

    {/* Card 1: DEM-based area for evacuation assessment */}
    <article className="community-impact-card">
      <span className="impact-card-label">
        Potential area for evacuation assessment
      </span>

      <div className="impact-card-value">
        {inundationLoading
          ? '...'
          : inundationResult
            ? Number(
                inundationResult.results.approximate_area_km2
              ).toFixed(3)
            : '—'}

        <small>km²</small>
      </div>

      <p>
        {hasFreshLiveWaterLevel
          ? `Live container depth ${liveWaterLevelCm.toFixed(1)} cm maps to a demo stage rise of ${liveStageRiseM.toFixed(1)} m; current DEM threshold ${scenarioLevel !== null ? scenarioLevel.toFixed(2) : '—'} m. The scale is illustrative, not a calibrated river elevation.`
          : `DEM-connected terrain under the selected ${scenario === 'rising' ? 'rising' : 'stable'} fallback scenario; current threshold ${scenarioLevel !== null ? scenarioLevel.toFixed(2) : '—'} m. This is not a confirmed evacuation boundary.`}
      </p>
    </article>

    {/* Card 2: Maximum modelled reach */}
    <article className="community-impact-card">
      <span className="impact-card-label">
        Maximum modelled reach
      </span>

      <div className="impact-card-value">
        {inundationLoading
          ? '...'
          : inundationResult
            ? (
                Number(
                  inundationResult.results.maximum_straight_line_distance_km
                ) * 1000
              ).toLocaleString('en-IN', {
                maximumFractionDigits: 0
              })
            : '—'}

        <small>m</small>
      </div>

      <p>
        Straight-line distance from the selected satellite water pixel,
        not a verified river boundary.
      </p>
    </article>

    {/* Card 3: Latest ultrasonic measurement */}
    <article className="community-impact-card">
      <span className="impact-card-label">
        Live sensor distance
      </span>

      <div className="impact-card-value">
        {gaugeData &&
        Number.isFinite(Number(gaugeData.distance_cm))
          ? Number(gaugeData.distance_cm).toFixed(1)
          : '—'}

        <small>cm</small>
      </div>

      <p>
        {gaugeData
          ? 'Latest distance measured between the sensor and water surface.'
          : 'Waiting for an ultrasonic sensor reading.'}
      </p>
    </article>

  </div>

  <div className="community-advisory">
    <div className="advisory-heading">Assessment summary</div>

    {inundationLoading ? (
      <p>Calculating the selected terrain scenario...</p>
    ) : inundationError ? (
      <p>
        The terrain calculation is unavailable. Check the selected
        water region and elevation reference.
      </p>
    ) : !inundationResult ? (
      <p>
        Terrain results will appear when a valid scenario calculation succeeds.
      </p>
    ) : (
      <p>
        The DEM screening estimates that{' '}
        <strong>
          {Number(inundationResult.results.approximate_area_km2).toLocaleString('en-IN', {
            minimumFractionDigits: 3,
            maximumFractionDigits: 3,
          })} km²
        </strong>{' '}
        of connected terrain falls below the selected hypothetical water-surface elevation of{' '}
        <strong>{scenarioLevel !== null ? `${scenarioLevel.toFixed(2)} m` : 'the selected threshold'}</strong>.
        {hasFreshLiveWaterLevel
          ? ` The latest measured container water depth is ${liveWaterLevelCm.toFixed(1)} cm. For demonstration only, the sensor's 0–${liveSensorHeightCm.toFixed(1)} cm range is mapped to a 0–${DEMO_MAX_STAGE_RISE_M.toFixed(1)} m stage rise above the selected DEM seed elevation.`
          : ' No fresh gauge measurement is available, so the selected Stable/Rising scenario is being used.'}
        {' '}Prioritise this area for assessment; do not treat it as an instruction to evacuate every part of the area.
      </p>
    )}

    <div className="advisory-footnote">
      DEM-only screening: this estimates low terrain connected to the selected satellite water-region seed. A DEM alone cannot confirm actual flood extent, identify occupied buildings, or determine an official evacuation boundary. Validate the elevation reference and scenario against river observations and local authorities before issuing evacuation instructions.
    </div>
  </div>
</section>



    <footer className="page-footer">
      <span>FloodSense · Hydrological Mapping Prototype</span>
      <span><i /> {gaugeData ? 'Live gauge readings connected · Terrain scenarios remain hypothetical' : 'Waiting for live gauge readings · Terrain scenarios are hypothetical'}</span>
    </footer>
  </main>
</div>
)
}

export default App
