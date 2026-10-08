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

        assertEquals("Station C", directionOf(leg, "C", connections, termini))
    }

    @Test
    fun alightingAtTerminusGivesThatTerminus() {

        // Ride A -> C: you get off at the end of the line
        val leg = Leg("red", listOf("A", "B", "C"), 200)

        assertEquals("Station C", directionOf(leg, "C", connections, termini))
    }

    @Test
    fun returnsNullWhenNoTerminusIsKnown() {

        val leg = Leg("red", listOf("A", "B"), 100)

        assertNull(directionOf(leg, "C", connections, emptyMap()))
    }

    @Test
    fun choosesBranchThatLeadsToDestination() {

        // M -> J, then J splits into two branches: J -> X and J -> Y
        val branchingConnections = listOf(
            Connection("M", "J", "red", 100),
            Connection("J", "X", "red", 100),
            Connection("J", "Y", "red", 100)
        )

        val branchingTermini = mapOf(
            "red:X" to "Station X",
            "red:Y" to "Station Y"
        )

        // This leg ends at J. Beyond J, the line splits into two directions.
        val leg = Leg("red", listOf("M", "J"), 100)

        assertEquals(
            "Station X",
            directionOf(leg, "X", branchingConnections, branchingTermini)
        )

        assertEquals(
            "Station Y",
            directionOf(leg, "Y", branchingConnections, branchingTermini)
        )
    }

}
