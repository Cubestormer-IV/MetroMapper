package com.example.metromapper

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RouteDirectionTest {

    // A -> B -> C on red, where C is the terminus
    private val connections = listOf(
        Connection("A", "B", "red", 100),
        Connection("B", "C", "red", 100)
    )

    private val termini = mapOf("red:C" to "Station C")

    @Test
    fun headsTowardsTerminusBeyondAlightingStation() {

        // Ride A -> B: the train carries on past B to C
        val leg = Leg("red", listOf("A", "B"), 100)

        assertEquals("Station C", directionOf(leg, connections, termini))
    }

    @Test
    fun alightingAtTerminusGivesThatTerminus() {

        // Ride A -> C: you get off at the end of the line
        val leg = Leg("red", listOf("A", "B", "C"), 200)

        assertEquals("Station C", directionOf(leg, connections, termini))
    }

    @Test
    fun returnsNullWhenNoTerminusIsKnown() {

        val leg = Leg("red", listOf("A", "B"), 100)

        assertNull(directionOf(leg, connections, emptyMap()))
    }
}
