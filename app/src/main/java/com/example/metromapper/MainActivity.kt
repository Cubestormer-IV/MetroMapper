package com.example.metromapper

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color

import com.google.android.gms.maps.model.CameraPosition
import com.google.android.gms.maps.model.LatLng
import com.google.maps.android.compose.GoogleMap
import com.google.maps.android.compose.Polyline
import com.google.maps.android.compose.rememberCameraPositionState


data class ShapePoint(
    val lat: Double,
    val lon: Double,
    val sequence: Int
)
class MainActivity : ComponentActivity() {

    val metroLines = listOf(
        "0" to Color.Red,
        "2" to Color.Yellow,
        "5" to Color.Blue,
        "7" to Color.Green,
        "12" to Color.Magenta,
//        "31" to Color.Gray,
//        "33" to Color.Green
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)


        setContent {
            val delhi = LatLng(28.6139, 77.2090)

            val cameraPositionState = rememberCameraPositionState {
                position = CameraPosition.fromLatLngZoom(delhi, 11f)
            }

            val stationCoords = loadStationCoordinates(this)
            val route = findShortestRoute(loadConnections(this), "rithala", "kashmere_gate")
            val routePoints = route?.stations?.mapNotNull { stationCoords[it] }.orEmpty()

            GoogleMap(
                modifier = Modifier.fillMaxSize(),
                cameraPositionState = cameraPositionState
            ) {

                metroLines.forEach { (routeId, color) ->
                    val line = loadColorLine(routeId)

                    Polyline(
                        points = line,
                        color = color,
                        width = 8f
                    )
                }

                if (routePoints.isNotEmpty()) {
                    Polyline(
                        points = routePoints,
                        color = Color.Black,
                        width = 16f
                    )
                }

            }
        }
    }

    private fun loadColorLine(
        routeId: String
    ) : List<LatLng> {

        // Find a trip belonging to this route
        val trips = assets.open("data/gtfs/trips.txt")
            .bufferedReader()
            .readLines()

        val trip = trips
            .drop(1)
            .map { it.split(",") }
            .firstOrNull { it[0] == routeId }

        if (trip == null) return emptyList()

        val shapeId = trip[7]   // shape_id

        // Get the shape points
        val shapes = assets.open("data/gtfs/shapes.txt")
            .bufferedReader()
            .readLines()

        val points = shapes
            .drop(1)
            .map { it.split(",") }
            .filter { it[0] == shapeId }
            .sortedBy { it[3].toInt() }   // shape_pt_sequence
            .map {
                LatLng(
                    it[1].toDouble(),     // latitude
                    it[2].toDouble()      // longitude
                )
            }

        return points
    }
}