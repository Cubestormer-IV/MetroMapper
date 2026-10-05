package com.example.metromapper

import java.util.PriorityQueue

data class Connection(
    val from: String,
    val to: String,
    val line: String,
    val distanceM: Int
)

data class RouteResult(
    val stations: List<String>,
    val hops: List<Connection>,
    val distanceM: Int
)

private data class QueueNode(
    val station: String,
    val distance: Int
)

fun findShortestRoute(
    connections: List<Connection>,
    start: String,
    destination: String,
    excluded: Set<Connection> = emptySet()
): RouteResult? {

    // Build the graph
    val graph = mutableMapOf<String, MutableList<Connection>>()

    for (connection in connections) {
        if (connection in excluded) continue

        graph
            .getOrPut(connection.from) { mutableListOf() }
            .add(connection)
    }

    // Shortest known distance to each station
    val distances = mutableMapOf<String, Int>()

    // The connection we used to reach each station
    val previous = mutableMapOf<String, Connection>()

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
                previous[connection.to] = connection

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

    // Reconstruct the route, one connection at a time
    val hops = mutableListOf<Connection>()
    var current = destination

    while (current != start) {
        val hop = previous[current] ?: return null
        hops.add(hop)
        current = hop.from
    }

    hops.reverse()

    return RouteResult(
        stations = listOf(start) + hops.map { it.to },
        hops = hops,
        distanceM = distances[destination]!!
    )
}

// Returns up to maxRoutes different routes, shortest first.
// Alternatives come from blocking each connection of the best route in turn.
fun findRoutes(
    connections: List<Connection>,
    start: String,
    destination: String,
    maxRoutes: Int = 3
): List<RouteResult> {

    val best = findShortestRoute(connections, start, destination) ?: return emptyList()

    val routes = mutableListOf(best)

    for (hop in best.hops) {
        val alternative = findShortestRoute(
            connections,
            start,
            destination,
            excluded = setOf(hop)
        ) ?: continue

        if (routes.none { it.hops == alternative.hops }) {
            routes.add(alternative)
        }
    }

    return routes
        .sortedBy { it.distanceM }
        .take(maxRoutes)
}
