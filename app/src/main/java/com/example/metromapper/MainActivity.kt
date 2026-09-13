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

        val redLinePoints = loadRedLine()

        setContent {
            val delhi = LatLng(28.6139, 77.2090)

            val cameraPositionState = rememberCameraPositionState {
                position = CameraPosition.fromLatLngZoom(delhi, 11f)
            }

            GoogleMap(
                modifier = Modifier.fillMaxSize(),
                cameraPositionState = cameraPositionState,
                uiSettings = MapUiSettings(
                    zoomControlsEnabled = true
                )
            ) {
                Polyline(
                    points = redLinePoints,
                    color = Color.Red,
                    width = 8f
                )
            }
        }
    }

    private fun loadRedLine(): List<LatLng> {

        // Read routes.txt
        val routes = assets.open("routes.txt")
        val routeReader = BufferedReader(InputStreamReader(routes))

        var redRouteId: String? = null

        routeReader.readLine() // Skip header

        routeReader.forEachLine { line ->

            val columns = line.split(",")

            val routeId = columns[0]
            val routeShortName = columns[2]

            if (routeShortName == "R_RD") {
                redRouteId = routeId
            }
        }

        routeReader.close()

        // Read trips.txt to find the shape used by the Red Line
        val trips = assets.open("trips.txt")
        val tripReader = BufferedReader(InputStreamReader(trips))

        var redShapeId: String? = null

        tripReader.readLine() // Skip header

        tripReader.forEachLine { line ->

            val columns = line.split(",")

            val routeId = columns[0]
            val shapeId = columns[7]

            if (routeId == redRouteId) {
                redShapeId = shapeId
                return@forEachLine
            }
        }

        tripReader.close()

        // Read shapes.txt
        val shapes = assets.open("shapes.txt")
        val shapeReader = BufferedReader(InputStreamReader(shapes))

        val points = mutableListOf<ShapePoint>()

        shapeReader.readLine() // Skip header

        shapeReader.forEachLine { line ->

            val columns = line.split(",")

            val shapeId = columns[0]

            if (shapeId == redShapeId) {

                val lat = columns[1].toDouble()
                val lon = columns[2].toDouble()
                val sequence = columns[3].toInt()

                points.add(
                    ShapePoint(
                        lat = lat,
                        lon = lon,
                        sequence = sequence
                    )
                )
            }
        }

        shapeReader.close()

        return points
            .sortedBy { it.sequence }
            .map { LatLng(it.lat, it.lon) }
    }
}