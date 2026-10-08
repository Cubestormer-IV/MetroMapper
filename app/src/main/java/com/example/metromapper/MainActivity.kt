package com.example.metromapper

import android.content.res.AssetManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.Color

import com.google.android.gms.maps.model.LatLng

// The old GTFS route IDs we draw as background lines on the map,
// with a color each. This predates the canonical data and can be
// retired once shapes.json is wired up instead.
private val LEGACY_LINE_COLORS = listOf(
    "0" to Color.Red,
    "2" to Color.Yellow,
    "5" to Color.Blue,
    "7" to Color.Green,
    "12" to Color.Magenta
)

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Load the canonical data once, not on every recomposition
        val stations = loadStations(this)
        val stationsById = stations.associateBy { it.id }
        val connections = loadConnections(this)
        val termini = loadTermini(this)
        val linesById = loadLines(this).associateBy { it.id }

        val backgroundLines = LEGACY_LINE_COLORS.map { (routeId, color) ->
            loadColorLine(assets, routeId) to color
        }

        setContent {
            var screen by remember { mutableStateOf<Screen>(Screen.Picker) }

            when (val current = screen) {
                is Screen.Picker -> StationPickerScreen(
                    stations = stations,
                    onSearch = { fromId, toId ->
                        screen = Screen.Options(findRoutes(connections, fromId, toId))
                    }
                )

                is Screen.Options -> RouteOptionsScreen(
                    routes = current.routes,
                    stationsById = stationsById,
                    linesById = linesById,
                    onSelect = { route -> screen = Screen.Detail(route, current) },
                    onBack = { screen = Screen.Picker }
                )

                is Screen.Detail -> RouteDetailScreen(
                    route = current.route,
                    connections = connections,
                    termini = termini,
                    stationsById = stationsById,
                    linesById = linesById,
                    backgroundLines = backgroundLines,
                    onBack = { screen = current.options }
                )
            }
        }
    }
}

// Reads a GTFS route's shape points, to draw it on the map.
private fun loadColorLine(assets: AssetManager, routeId: String): List<LatLng> {

    // Find a trip belonging to this route
    val trips = assets.open("data/gtfs/trips.txt")
        .bufferedReader()
        .readLines()

    val trip = trips
        .drop(1)
        .map { it.split(",") }
        .firstOrNull { it[0] == routeId }
        ?: return emptyList()

    val shapeId = trip[7] // shape_id

    // Get the shape points
    val shapes = assets.open("data/gtfs/shapes.txt")
        .bufferedReader()
        .readLines()

    return shapes
        .drop(1)
        .map { it.split(",") }
        .filter { it[0] == shapeId }
        .sortedBy { it[3].toInt() } // shape_pt_sequence
        .map { LatLng(it[1].toDouble(), it[2].toDouble()) }
}
