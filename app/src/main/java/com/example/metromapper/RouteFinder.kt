package com.example.metromapper

import kotlin.math.min
import java.util.PriorityQueue

data class Connection(
    val from: String,
    val to: String,
    val line: String,
    val distanceM: Int
)

data class RouteResult(
    val stations: List<String>,
    val distanceM: Int
)

private data class QueueNode(
    val station: String,
    val distance: Int
)

fun findShortestRoute(
    connections: List<Connection>,
    start: String,
    destination: String
): RouteResult? {

    // Build the graph
    val graph = mutableMapOf<String, MutableList<Connection>>()

    for (connection in connections) {
        graph
            .getOrPut(connection.from) { mutableListOf() }
            .add(connection)
    }

    // Shortest known distance to each station
    val distances = mutableMapOf<String, Int>()
    val previous = mutableMapOf<String, String>()

    val queue = PriorityQueue<QueueNode>(
        compareBy { it.distance }
    )

    distances[start] = 0
    queue.add(QueueNode(start, 0))

    while (queue.isNotEmpty()) {

        val current = queue.poll()

        if (current.station == destination) {
            break
        }

        // Ignore outdated queue entries
        if (current.distance > (distances[current.station] ?: Int.MAX_VALUE)) {
            continue
        }

        for (connection in graph[current.station].orEmpty()) {

            val newDistance =
                current.distance + connection.distanceM

            val oldDistance =
                distances[connection.to] ?: Int.MAX_VALUE

            if (newDistance < oldDistance) {

                distances[connection.to] = newDistance
                previous[connection.to] = current.station

                queue.add(
                    QueueNode(
                        connection.to,
                        newDistance
                    )
                )
            }
        }
    }

    // Destination was never reached
    if (destination !in distances) {
        return null
    }

    // Reconstruct the route
    val route = mutableListOf<String>()
    var current = destination

    while (current != start) {
        route.add(current)
        current = previous[current] ?: return null
    }

    route.add(start)
    route.reverse()

    return RouteResult(
        stations = route,
        distanceM = distances[destination]!!
    )
}