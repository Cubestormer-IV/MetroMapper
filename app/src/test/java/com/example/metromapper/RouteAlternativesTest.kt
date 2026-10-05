package com.example.metromapper

import org.junit.Assert.assertEquals
import org.junit.Test

class RouteAlternativesTest {

    @Test
    fun returnsBothPathsShortestFirst() {

        // Path 1: A -> B -> D (200 m)
        // Path 2: A -> C -> D (300 m)
        val connections = listOf(
            Connection("A", "B", "red", 100),
            Connection("B", "D", "red", 100),
            Connection("A", "C", "yellow", 150),
            Connection("C", "D", "yellow", 150)
        )

        val routes = findRoutes(connections, "A", "D")

        assertEquals(2, routes.size)

        assertEquals(listOf("A", "B", "D"), routes[0].stations)
        assertEquals(200, routes[0].distanceM)

        assertEquals(listOf("A", "C", "D"), routes[1].stations)
        assertEquals(300, routes[1].distanceM)
    }

    @Test
    fun returnsEmptyWhenUnreachable() {

        val connections = listOf(
            Connection("A", "B", "red", 100)
        )

        assertEquals(emptyList<RouteResult>(), findRoutes(connections, "B", "A"))
    }
}
