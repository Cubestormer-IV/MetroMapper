package com.example.metromapper

import org.junit.Test
import org.junit.Assert.assertEquals

class RouteFinderTest {

    @Test
    fun findsShortestRoute() {

        val connections = listOf(
            Connection("rithala", "rohini_west", "red", 1228),
            Connection("rohini_west", "rohini_east", "red", 1251),
            Connection("rohini_east", "pitampura", "red", 835)
        )

        val result = findShortestRoute(
            connections,
            "rithala",
            "pitampura"
        )

        assertEquals(
            listOf(
                "rithala",
                "rohini_west",
                "rohini_east",
                "pitampura"
            ),
            result?.stations
        )

        assertEquals(3314, result?.distanceM)
    }
}