package com.example.metromapper

// One continuous ride on a single line, or a walk between two platforms
// (line == "walk"). stations[0] is where you board/start, the last station
// is where you get off/arrive.
data class Leg(
    val line: String,
    val stations: List<String>,
    val distanceM: Int,
    val durationS: Int
) {
    val boardAt: String get() = stations.first()
    val alightAt: String get() = stations.last()
    val isWalk: Boolean get() = line == "walk"

    // Stations you pass through without getting on or off
    val intermediateStops: Int get() = stations.size - 2

    val estimatedMinutes: Int get() = Math.round(durationS / 60.0).toInt()
}


// All stations you can reach from `from`, staying on the given line,
// without turning back along the way you came in.
private fun reachableOnLine(
    from: String,
    line: String,
    connections: List<Connection>,
    visited: MutableSet<String> = mutableSetOf()
): Set<String> {
    if (!visited.add(from)) return visited

    for (connection in connections) {
        if (connection.line == line && connection.from == from && connection.to !in visited) {
            reachableOnLine(connection.to, line, connections, visited)
        }
    }

    return visited
}

// Works out where the train is heading: walk along the line from the station
// you get off at, away from where you boarded, until the line ends.
// At a branch, take the fork that actually leads towards where you're going.
// Returns the terminus name, or null if the line ends somewhere we have no
// terminus for — or if this leg is a walk, which has no direction to name.
fun directionOf(
    leg: Leg,
    destination: String,
    connections: List<Connection>,
    termini: Map<String, String>
): String? {
    if (leg.isWalk) return null

    var previous = leg.boardAt
    var current = leg.alightAt

    while (true) {
        val options = connections.filter {
            it.from == current && it.line == leg.line && it.to != previous
        }

        if (options.isEmpty()) break

        val next = if (options.size == 1) {
            options.first()
        } else {
            options.firstOrNull { destination in reachableOnLine(it.to, leg.line, connections) }
                ?: options.first()
        }

        previous = current
        current = next.to
    }

    return termini["${leg.line}:$current"]
}

// Groups the hops of a route into legs. A new leg starts whenever the line
// changes — which includes switching into or out of a walk.
fun splitIntoLegs(route: RouteResult): List<Leg> {
    val legs = mutableListOf<Leg>()

    for (hop in route.hops) {
        val last = legs.lastOrNull()

        if (last != null && last.line == hop.line) {
            legs[legs.lastIndex] = last.copy(
                stations = last.stations + hop.to,
                distanceM = last.distanceM + hop.distanceM,
                durationS = last.durationS + hop.durationS
            )
        } else {
            legs.add(Leg(hop.line, listOf(hop.from, hop.to), hop.distanceM, hop.durationS))
        }
    }

    return legs
}
