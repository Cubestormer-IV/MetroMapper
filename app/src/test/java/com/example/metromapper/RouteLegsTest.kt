package com.example.metromapper

import org.junit.Assert.assertEquals
import org.junit.Test

class RouteLegsTest {

    @Test
    fun splitsRouteIntoLegsAtLineChange() {

        // A -red- B -red- C -yellow- D -yellow- E
        val connections = listOf(
            Connection("A", "B", "red", 100),
            Connection("B", "C", "red", 100),
            Connection("C", "D", "yellow", 100),
            Connection("D", "E", "yellow", 100)
        )

        val route = findShortestRoute(connections, "A", "E")!!
        val legs = splitIntoLegs(route)

        assertEquals(2, legs.size)

        assertEquals("red", legs[0].line)
        assertEquals(listOf("A", "B", "C"), legs[0].stations)
        assertEquals(200, legs[0].distanceM)
        assertEquals(1, legs[0].intermediateStops)

        assertEquals("yellow", legs[1].line)
        assertEquals(listOf("C", "D", "E"), legs[1].stations)
        assertEquals("C", legs[1].boardAt)
        assertEquals("E", legs[1].alightAt)
    }

    @Test
    fun estimatesMinutesFromDistanceAndStops() {

        // A -> B -> C on one line: 5830 m total, one stop in the middle
        val connections = listOf(
            Connection("A", "B", "red", 2915),
            Connection("B", "C", "red", 2915)
        )

        val route = findShortestRoute(connections, "A", "C")!!
        val leg = splitIntoLegs(route).single()

        // 5830 / 583 = 10 minutes travel, plus 1 minute for the stop
        assertEquals(11, leg.estimatedMinutes)
    }
}
