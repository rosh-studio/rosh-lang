# Rosh Airspace Demo - Scotland

Real-time airspace visualization over Scotland using public ADS-B data.

**Purpose:** Demonstration showing how Rosh can make aviation data explorable via voice and console commands.

## Data Source

- **Live data:** [OpenSky Network](https://opensky-network.org/) public API
- **Coverage:** Scotland bounding box (54.5°N to 60.5°N, 8°W to 0.5°W)
- **Update interval:** 10 seconds
- **Fallback:** Sample data when API is rate-limited

## Running the Demo

```bash
# From rosh-lang directory
cd demos/rosh-airspace/threejs
python3 -m http.server 8080
# Open http://localhost:8080
```

Or view the live demo at: https://rosh.cloud/demos/rosh-airspace/

## Commands

| Command | Description |
|---------|-------------|
| `list flights` | Show all tracked flights |
| `list airlines` | Show airline counts |
| `follow BAW123` | Follow a specific flight |
| `unfollow` | Stop following |
| `select EZY548` | Select flight for info panel |
| `pause` | Pause data updates |
| `resume` | Resume data updates |
| `refresh` | Force immediate update |
| `zoom in/out` | Adjust view |
| `help` | Show all commands |

## Controls

- **Drag:** Pan the map
- **Scroll:** Zoom in/out
- **Click:** Select a flight
- **Voice:** Click mic button or Ctrl+Space

## Flight Colors

| Color | Airline |
|-------|---------|
| Blue | British Airways (BAW) |
| Orange | EasyJet (EZY) |
| Yellow | Ryanair (RYR) |
| Purple | Loganair (LOG) |
| Dark Blue | Lufthansa (DLH) |
| Red | Air France (AFR) |
| Teal | Other UK flights |
| Gray | Unknown |

## Data Adapter

The data adapter (`fetchFlights()`) is designed for drop-in replacement with other aviation data sources:

1. Replace OpenSky endpoint with alternative API
2. Map response format to internal flight structure
3. No changes to visualization or commands

## Files

```
rosh-airspace/
├── threejs/
│   ├── index.html    # Demo page
│   └── game.js       # Visualization + commands
├── data/
│   └── scotland-sample.json  # Cached sample data
└── README.md
```
