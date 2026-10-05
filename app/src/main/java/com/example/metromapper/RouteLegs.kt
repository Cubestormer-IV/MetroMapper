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

// Works out where the train is heading: walk along the line from the station
// you get off at, away from where you boarded, until the line ends.
// At a branch this takes the first option. That's a known gap, to fix later.
// Returns the terminus name, or null if the line ends somewhere we have no terminus for.
fun directionOf(
    leg: Leg,
    connections: List<Connection>,
    termini: Map<String, String>
): String? {
    var previous = leg.boardAt
    var current = leg.alightAt

    while (true) {
        val next = connections.firstOrNull {
            it.from == current && it.line == leg.line && it.to != previous
        } ?: break

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
