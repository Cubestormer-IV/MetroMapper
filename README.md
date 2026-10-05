# MetroMapper

An Android app for getting around Delhi by public transport. The long-term goal is a Citymapper-style app that routes from any address to any address across walking, Delhi Metro, buses, and other modes.

The current focus is Delhi Metro: finding routes between stations and showing them step by step.

## Status

Early development. Working today:

- Shortest-route search (Dijkstra) over the Metro network
- Up to three alternative routes between two stations
- Grouping a route into legs (one per line ridden)
- Loading stations and connections from bundled JSON data
- A Google Map showing stations and the Metro lines (drawn from GTFS shapes)

Not yet built: the route-picker and step-by-step UI, directions and times, exits within stations, and walking.

## How the data works

Raw transit data (GTFS, OpenStreetMap, manual corrections) is converted into a single format the app uses. The app never reads the raw sources directly.

```
GTFS / OSM / manual data
        ↓  conversion and cleaning
MetroMapper canonical data  (app/src/main/assets/data/canonical/)
        ↓
routing engine (RouteFinder.kt)
        ↓
Android app
```

Canonical files:

| File | Contents |
|---|---|
| `stations.json` | Physical stations with coordinates and the lines they serve |
| `lines.json` | Metro lines and their colors |
| `connections.json` | The routing graph: which stations link directly, on which line, and the distance in metres |
| `shapes.json` | Geometry for drawing lines on the map (planned; the app currently reads GTFS shapes) |

The canonical data is maintained by hand where the source data is wrong or out of date.

## Project layout

```
app/src/main/java/com/example/metromapper/
    MainActivity.kt     Screen and map setup
    RouteFinder.kt      Routing: connections, search, alternatives
    RouteLegs.kt        Groups a route into legs by line
    CanonicalData.kt    Loads stations and connections from assets
app/src/main/assets/data/   Bundled data files
app/src/test/               Unit tests (run on your computer, no phone needed)
```

## Building and running

Requirements: Android Studio, JDK 11 or newer.

1. Add your Google Maps API key to `local.properties`:
   ```
   MAPS_API_KEY=your_key_here
   ```
2. Open the project in Android Studio and let Gradle sync.
3. Run the app on a device or emulator, or run tests with:
   ```
   ./gradlew test
   ```

`local.properties` is for your machine only. Don't commit it.

## Tech stack

- Kotlin and Jetpack Compose
- Google Maps SDK and Maps Compose
- Gson for reading JSON
- JUnit for tests
- Min SDK 28, target SDK 37

## Roadmap

Open work is tracked in [GitHub Issues](https://github.com/Cubestormer-IV/MetroMapper/issues), not in this file. Issues can be linked to pull requests and closed when the fix is merged.

## Contributing

Work on a branch and open a pull request into `main`. Reference the issue it fixes in the description (for example, `Closes #12`).
