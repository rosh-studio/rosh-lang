# Rosh Airspace Demo - Scotland

Real-time airspace visualization over Scotland using public ADS-B data.

**Purpose:** Demonstration for potential Spire partnership — showing how Rosh can make aviation data explorable via voice and console commands.

## Data Source

- **Live data:** [OpenSky Network](https://opensky-network.org/) public API
- **Coverage:** Scotland bounding box (54.5°N to 60.5°N, 8°W to 0.5°W)
- **Update interval:** 10 seconds

## Running the Demo

```bash
# From rosh-lang directory
cd demos/airspace-spire/threejs
python3 -m http.server 8080
# Open http://localhost:8080
```

Or use any local server (Live Server extension, etc.)

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

## Phase 2: Spire Integration

The data adapter (`fetchFlights()`) is designed for drop-in replacement:

1. Replace OpenSky endpoint with Spire API
2. Map Spire response format to internal flight structure
3. No changes to visualization or commands

See `/rosh-corporate/proposals/ROSH-SPIRE-PROPOSAL.md` for full proposal.

## Files

```
airspace-spire/
├── threejs/
│   ├── index.html    # Demo page
│   └── game.js       # Visualization + commands
├── data/
│   └── scotland-sample.json  # Cached sample data
└── README.md
```
