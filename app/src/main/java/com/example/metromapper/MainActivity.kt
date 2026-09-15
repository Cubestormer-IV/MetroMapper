package com.example.metromapper

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import com.example.metromapper.ui.theme.MetroMapperTheme
import androidx.compose.ui.graphics.Color

import com.google.android.gms.maps.model.CameraPosition
import com.google.android.gms.maps.model.LatLng
import com.google.maps.android.compose.GoogleMap
import com.google.maps.android.compose.MapProperties
import com.google.maps.android.compose.MapUiSettings
import com.google.maps.android.compose.Polyline
import com.google.maps.android.compose.rememberCameraPositionState
import java.io.BufferedReader
import java.io.InputStreamReader


data class ShapePoint(
    val lat: Double,
    val lon: Double,
    val sequence: Int
)
class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)


        setContent {
            val delhi = LatLng(28.6139, 77.2090)

            val cameraPositionState = rememberCameraPositionState {
                position = CameraPosition.fromLatLngZoom(delhi, 11f)
            }

            val metroLines = listOf(
                "0" to Color.Red,
                "29" to Color.Magenta,
                "31" to Color.Gray,
                "33" to Color.Green
            )


            GoogleMap(
                modifier = Modifier.fillMaxSize(),
                cameraPositionState = cameraPositionState
            ) {

                val redLine = loadColorLine("0")

                Polyline(
                    points = redLine,
                    color = Color.Red,
                    width = 8f
                )
            }
        }
    }

    private fun loadColorLine(
        routeId: String
    ) : List<LatLng> {

        // Find a trip belonging to this route
        val trips = assets.open("trips.txt")
            .bufferedReader()
            .readLines()

        val trip = trips
            .drop(1)
            .map { it.split(",") }
            .firstOrNull { it[0] == routeId }

        if (trip == null) return emptyList()

        val shapeId = trip[7]   // shape_id

        // Get the shape points
        val shapes = assets.open("shapes.txt")
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