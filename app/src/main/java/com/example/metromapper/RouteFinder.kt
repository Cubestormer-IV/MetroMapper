package com.example.metromapper

import java.util.PriorityQueue

data class Connection(
    val from: String,
    val to: String,
    val line: String,
    val distanceM: Int,
    val durationS: Int
)

data class RouteResult(
    val stations: List<String>,
    val hops: List<Connection>,
    val distanceM: Int,
    val durationS: Int
)

private data class QueueNode(
    val node: String,
    val duration: Int
)

// Interchanges are modeled as one node per (place, line) — e.g. Kashmere
// Gate is "kashmere_gate:red", "kashmere_gate:yellow", "kashmere_gate:violet"
// — but a user searches by place ("kashmere_gate"). Expands a place id to
// every node that belongs to it; a non-interchange place is just itself.
private fun nodesForPlace(place: String, connections: List<Connection>): Set<String> {
    val nodes = mutableSetOf<String>()

    for (connection in connections) {
        for (node in listOf(connection.from, connection.to)) {
            if (node == place || node.startsWith("$place:")) {
                nodes.add(node)
            }
        }
    }

    return nodes.ifEmpty { setOf(place) }
}

// The place a node displays as — "kashmere_gate:red" is still "kashmere_gate"
// to a rider.
fun placeOf(node: String): String = node.substringBefore(":")

// Shortest route by time, not distance — a walk between platforms only has
// a duration, no meaningful distance, so time is the one cost every kind of
// hop (riding a line, walking a transfer) can be compared by.
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

    val startNodes = nodesForPlace(start, connections)
    val destinationNodes = nodesForPlace(destination, connections)

    // Shortest known duration to each node, in seconds
    val durations = mutableMapOf<String, Int>()

    // The connection we used to reach each node
    val previous = mutableMapOf<String, Connection>()

    val queue = PriorityQueue<QueueNode>(
        compareBy { it.duration }
    )

    for (node in startNodes) {
        durations[node] = 0
        queue.add(QueueNode(node, 0))
    }

    var reached: String? = null

    while (queue.isNotEmpty()) {

        val current = queue.poll()

        if (current.node in destinationNodes) {
            reached = current.node
            break
        }

        // Ignore outdated queue entries
        if (current.duration > (durations[current.node] ?: Int.MAX_VALUE)) {
            continue
        }

        for (connection in graph[current.node].orEmpty()) {

            val newDuration =
                current.duration + connection.durationS

            val oldDuration =
                durations[connection.to] ?: Int.MAX_VALUE

            if (newDuration < oldDuration) {

                durations[connection.to] = newDuration
                previous[connection.to] = connection

                queue.add(
                    QueueNode(
                        connection.to,
                        newDuration
                    )
                )
            }
        }
    }

    // Destination was never reached
    val reachedNode = reached ?: return null

    // Reconstruct the route, one connection at a time
    val hops = mutableListOf<Connection>()
    var current = reachedNode

    while (current !in startNodes) {
        val hop = previous[current] ?: return null
        hops.add(hop)
        current = hop.from
    }

    hops.reverse()

    return RouteResult(
        stations = listOf(placeOf(current)) + hops.map { placeOf(it.to) },
        hops = hops,
        distanceM = hops.sumOf { it.distanceM },
        durationS = durations[reachedNode]!!
    )
}

// Returns up to maxRoutes different routes, fastest first.
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
        .sortedBy { it.durationS }
        .take(maxRoutes)
}
