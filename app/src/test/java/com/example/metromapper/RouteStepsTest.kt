package com.example.metromapper

import com.google.android.gms.maps.model.LatLng
import org.junit.Assert.assertEquals
import org.junit.Test

class RouteStepsTest {

    @Test
    fun buildsBoardRideChangeRideGetOff() {

        // A -> B -> C on red, then C -> D on yellow
        val connections = listOf(
            Connection("A", "B", "red", 100),
            Connection("B", "C", "red", 100),
            Connection("C", "D", "yellow", 100)
        )

        val stationsById = listOf(
            Station("A", "Alpha", LatLng(0.0, 0.0), listOf("red")),
            Station("B", "Beta", LatLng(0.0, 0.0), listOf("red")),
            Station("C", "Gamma", LatLng(0.0, 0.0), listOf("red", "yellow")),
            Station("D", "Delta", LatLng(0.0, 0.0), listOf("yellow"))
        ).associateBy { it.id }

        val linesById = listOf(
            MetroLine("red", "Red Line", "#E53935"),
            MetroLine("yellow", "Yellow Line", "#FDD835")
        ).associateBy { it.id }

        val termini = mapOf("red:C" to "Gamma", "yellow:D" to "Delta")

        val route = findShortestRoute(connections, "A", "D")!!
        val steps = buildSteps(route, connections, termini, stationsById, linesById)

        assertEquals(
            listOf(
                RouteStep.Board("Alpha", "Red Line", "#E53935", "Gamma"),
                RouteStep.Ride(stops = 1, minutes = 1),
                RouteStep.ChangeAt("Gamma"),
                RouteStep.Board("Gamma", "Yellow Line", "#FDD835", "Delta"),
                RouteStep.Ride(stops = 0, minutes = 0),
                RouteStep.GetOffAt("Delta")
            ),
            steps
        )
    }
}
