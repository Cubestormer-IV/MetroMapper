package com.example.metromapper

// One line of the step-by-step directions. No Android or Compose types here,
// on purpose: that keeps this file plain Kotlin, so it can be unit tested
// the same way RouteFinder.kt and RouteLegs.kt are.
sealed class RouteStep {
    data class Board(
        val stationName: String,
        val lineName: String,
        val lineColorHex: String,
        val direction: String?
    ) : RouteStep()

    data class Ride(val stops: Int, val minutes: Int) : RouteStep()
    data class ChangeAt(val stationName: String) : RouteStep()
    data class GetOffAt(val stationName: String) : RouteStep()
}

// Turns a route into the steps a rider actually needs:
// board, ride, (change, board, ride, ...), get off.
fun buildSteps(
    route: RouteResult,
    connections: List<Connection>,
    termini: Map<String, String>,
    stationsById: Map<String, Station>,
    linesById: Map<String, MetroLine>
): List<RouteStep> {
    val legs = splitIntoLegs(route)
    val destination = route.stations.last()
    val steps = mutableListOf<RouteStep>()

    fun nameOf(stationId: String) = stationsById[stationId]?.name ?: stationId

    legs.forEachIndexed { index, leg ->
        val line = linesById[leg.line]
        val direction = directionOf(leg, destination, connections, termini)

        steps.add(
            RouteStep.Board(
                stationName = nameOf(leg.boardAt),
                lineName = line?.name ?: leg.line,
                lineColorHex = line?.color ?: "#9E9E9E",
                direction = direction
            )
        )

        steps.add(RouteStep.Ride(stops = leg.intermediateStops, minutes = leg.estimatedMinutes))

        steps.add(
            if (index == legs.lastIndex) {
                RouteStep.GetOffAt(nameOf(leg.alightAt))
            } else {
                RouteStep.ChangeAt(nameOf(leg.alightAt))
            }
        )
    }

    return steps
}
