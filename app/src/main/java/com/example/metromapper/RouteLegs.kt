package com.example.metromapper

// Rough assumptions until we have real timetable data
private const val METRES_PER_MINUTE = 583.0   // about 35 km/h
private const val MINUTES_PER_STOP = 1.0

// One continuous ride on a single line.
// stations[0] is where you board, the last station is where you get off.
data class Leg(
    val line: String,
    val stations: List<String>,
    val distanceM: Int
) {
    val boardAt: String get() = stations.first()
    val alightAt: String get() = stations.last()

    // Stations you pass through without getting on or off
    val intermediateStops: Int get() = stations.size - 2

    // Estimated ride time: travel time plus a little for each stop
    val estimatedMinutes: Int
        get() = Math.round(
            distanceM / METRES_PER_MINUTE + intermediateStops * MINUTES_PER_STOP
        ).toInt()
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
// Returns the terminus name, or null if the line ends somewhere we have no terminus for.
fun directionOf(
    leg: Leg,
    destination: String,
    connections: List<Connection>,
    termini: Map<String, String>
): String? {
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

// Groups the hops of a route into legs. A new leg starts whenever the line changes.
fun splitIntoLegs(route: RouteResult): List<Leg> {
    val legs = mutableListOf<Leg>()

    for (hop in route.hops) {
        val last = legs.lastOrNull()

        if (last != null && last.line == hop.line) {
            legs[legs.lastIndex] = last.copy(
                stations = last.stations + hop.to,
                distanceM = last.distanceM + hop.distanceM
            )
        } else {
            legs.add(Leg(hop.line, listOf(hop.from, hop.to), hop.distanceM))
        }
    }

    return legs
}
