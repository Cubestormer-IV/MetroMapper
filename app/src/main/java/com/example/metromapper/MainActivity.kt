package com.example.metromapper

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.ui.Alignment
import com.google.android.gms.maps.model.CameraPosition
import com.google.maps.android.compose.GoogleMap
import com.google.maps.android.compose.Polyline
import com.google.maps.android.compose.rememberCameraPositionState
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.foundation.layout.height
import androidx.compose.material3.Surface
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import android.content.res.AssetManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.Color
import androidx.compose.material3.Scaffold
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.ui.Modifier
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.runtime.LaunchedEffect
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

        enableEdgeToEdge()

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

            val delhi = LatLng(28.6139, 77.2090)
            val cameraPositionState = rememberCameraPositionState {
                position = CameraPosition.fromLatLngZoom(delhi, 11f)
            }

            val cardHeight = 640.dp
            val restingVisibleHeight = 180.dp
            val maxOffset = cardHeight - restingVisibleHeight
            val density = LocalDensity.current

            var offsetY by remember {mutableStateOf(maxOffset)}

            LaunchedEffect(offsetY) {
                cameraPositionState.position = CameraPosition.fromLatLngZoom(delhi, 11f)
            }

            LaunchedEffect(screen) {
                offsetY = when (screen) {
                    is Screen.Picker -> maxOffset
                    else -> 0.dp
                }
            }

            Scaffold { innerPadding ->
                Box(modifier = Modifier
                    .padding(innerPadding)
                    .fillMaxSize()
                ) {
                    GoogleMap(
                        modifier = Modifier.fillMaxSize(),
                        cameraPositionState = cameraPositionState,
                        contentPadding = PaddingValues(bottom = cardHeight - offsetY)
                    ) {
                        backgroundLines.forEach { (points, color) ->
                            Polyline(points = points, color = color, width = 8f)
                        }
                    }
                    Surface(
                        tonalElevation = 4.dp,
                        shadowElevation = 8.dp,
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .fillMaxWidth()
                            .height(cardHeight)
                            .offset(y = offsetY)
                            .pointerInput(Unit) {
                                detectVerticalDragGestures { change, dragAmount ->
                                    change.consume()
                                    offsetY = (offsetY + with(density) { dragAmount.toDp() })
                                        .coerceIn(0.dp, maxOffset)
                                }
                            }
                    ) {
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
                                onBack = { screen = current.options }
                            )
                        }
                    }
                }
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
