# Data model — design decisions

Status: design only. Not yet implemented — the app and `CanonicalData.kt` still use
the simpler schema described in the main README. This document exists so the
reasoning behind the next schema isn't lost before it's built.

## Source of truth: two tiers, not one

- **Tier 1 — a maintained, corrected copy of the raw feeds** (DMRC/DIMTS/DTC GTFS,
  eventually OSM, eventually manual additions), kept in standard GTFS shape,
  intended to be published as its own thing. Every hand correction (a fixed
  distance, a filled-in transfer time, a corrected branch) is made *here*.
- **Tier 2 — the canonical JSON the app reads**, always a regenerated build
  artifact produced from tier 1 by a deterministic converter script. Never
  hand-edited directly. If canonical data is ever wrong, the fix goes into
  tier 1 and the converter is re-run — canonical JSON and its source are never
  allowed to drift apart.

This mirrors how larger transit apps and aggregators (Transitland, Google's
transit ingestion) handle the same problem: official feeds are inconsistent
and often wrong, so a cleaning/normalization layer sits between raw sources
and anything that actually does routing.

## Node model

Two kinds of node, not one:

- **Place** — the human-facing concept: what search results, map markers, and
  "lines serving this stop" badges are built from. Roughly what `stations.json`
  does today.
- **Stop** — the actual node the routing graph runs on: a physically distinct
  boardable point. Every Stop has a `placeId` pointing at its Place.

**The splitting rule for Stops:** a Stop is justified only when reaching it
costs a real, different amount of walking than reaching some other Stop at
the same Place. This is *not* the same as "one Stop per line" or "one Stop
per direction" — those are common *reasons* two platforms end up physically
separate, not the rule itself:

- Two directions of the *same* line usually share one physical platform — no
  walk between them — so they're normally the same Stop. (Exception: a
  station that genuinely has separate up/down platforms would need a real
  split — check before assuming either way.)
- Two different *lines* at an interchange are usually genuinely separate
  platforms — normally different Stops.
- Bus stops don't split by route at all: one physical pole serving 40 routes
  is one Stop. Splitting by route would multiply the already-large bus stop
  count (10,559, see below) for no routing benefit.

**Open / not decided:**
- Exact node ID scheme (a proposal was made — prefix by source/mode, e.g.
  `bus:dtc:0`, `metro:rajiv_chowk:blue`, keep the raw GTFS id as its own field
  — but this was explicitly not committed to).
- Whether `Place` is its own JSON file, or collapsed into the Stop record for
  bus (where Place and Stop are ~1:1 anyway).
- How to determine actual metro platform topology. The source GTFS has no
  `location_type`/`parent_station` columns — there is currently **no data
  source** telling us how many physically distinct platforms a given metro
  station really has. This will likely need manual correction, OSM, or
  physical/anecdotal knowledge, station by station.

## Edge model

Two kinds, not four — transfer-at-a-station, cross-station interchange walks,
and future POI-to-entrance access are all the same *kind* of edge:

- **Ride** — board a vehicle. Fields: `from`, `to`, `mode` (METRO/BUS/...),
  `lineId`/`routeId`, a time weight.
- **Walk** — any pedestrian connection between two Stops, regardless of
  whether they're on the same platform, different stations, or (later) a Stop
  and a POI. Fields: `from`, `to`, a time weight. No mode/line field.

**Weight strategy:** Ride edges should carry a time weight (minutes) as the
primary routing cost, not raw distance. Metro's current distance-plus-constant-speed
approximation is fine, since trains run at roughly constant speed, but it
should still resolve to a time. Buses must not reuse that approach — distance
is a bad proxy for bus travel time under real traffic, so bus Ride edges need
an honest estimated time per hop. `distance_m` can stay as a secondary,
display-only field where available.

**Open / not decided:** where interchange-walk times (e.g. the Hauz
Khas pink/yellow walk) actually come from. The raw metro feed has no
`transfers.txt`/`pathways.txt`/`levels.txt` — this data does not exist in the
source and will likely require manual entry. If/when it is entered, GTFS has
a standard shape for exactly this (the GTFS-Pathways extension: `pathways.txt`,
`levels.txt`) — worth using that shape rather than inventing a bespoke one,
even though it means filling it in by hand.

## Branch handling

A line's branches are a normalized canonical concept, independent of how the
raw source happens to encode them. Confirmed from inspecting the real feed:
DMRC splits Blue Line into two separate `route_id`s for its two branches
(`Delhi3`/`Delhi4`), but does not do the same for Green Line's branch — Green
stays one `route_id` with multiple trip/shape patterns. Both are valid GTFS;
the spec's own definition of "route" (a group of trips shown to riders as one
service) actually favors Green's approach, but GTFS doesn't enforce
consistency, and DMRC's feed uses both conventions. The converter must treat
both the same way and must not use "is this a separate `route_id`" as its
branch-detection signal — `termini.json`'s existing approach (keyed by
line + station, not by route row) already does this correctly for Blue and
should extend to Green.

## Real-time — a seam, not a feature

Not building this now. The only thing worth doing now: route every weight
lookup through one function (e.g. `weightOf(edge, atTime)`) instead of
reading `.distanceM`/`.minutes` directly at call sites. A future live-data
layer can then check live predictions first and fall back to the static
weight — additive, no graph redesign required later.

## Storage

JSON files remain the right choice for the app at current scale — the app
only ever does point lookups by id, which `Map<String, X>` built at load time
handles with no friction. A database would earn its place if: ad-hoc queries/joins
become necessary, data needs to update without rebuilding the app, or the
planned dev-playground tool wants to explore data interactively. If that
happens, SQLite is the natural fit for the app (GTFS's shape is already
relational), and the *converter* might benefit from a throwaway local
database even before the app does, since doing real joins across
`stops`/`routes`/`trips`/`stop_times` by hand in a script is painful.

## What inspecting the real source data confirmed

- Metro `stops.txt`: no `location_type`/`parent_station` — station-level only,
  confirming the open platform-topology question above.
- Metro `trips.txt`: `direction_id` and `trip_headsign` are both empty for
  every trip — `termini.json` + `directionOf()` are filling a real gap, not
  duplicating something the source already had.
- Metro `routes.txt`: 12 routes. Confirms the Blue-line branch-as-route-split
  described above.
- Bus (DTC + DIMTS): 2 agencies, 2,403 routes, 10,559 stops — an order of
  magnitude more nodes than the metro network, which is why bus Stops must
  not be split per-route.
