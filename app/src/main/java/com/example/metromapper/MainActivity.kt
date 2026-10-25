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
import com.google.maps.android.compose.Marker
import com.google.maps.android.compose.rememberMarkerState
import com.google.android.gms.maps.model.Dot
import com.google.android.gms.maps.model.Gap

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        enableEdgeToEdge()

        // Load the canonical data once, not on every recomposition
        val stations = loadStations(this)
        val stationsById = stations.associateBy { it.id }
        val connections = loadConnections(this) + loadTransfers(this)
        val termini = loadTermini(this)
        val linesById = loadLines(this).associateBy { it.id }

        val backgroundLines = loadMetroLineShapes(assets)

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

                        when (val current = screen) {
                            is Screen.Options -> {
                                val fromPos = current.routes.firstOrNull()?.stations?.firstOrNull()
                                    ?.let {stationsById[it]?.position }
                                val toPos = current.routes.firstOrNull()?.stations?.lastOrNull()
                                    ?.let {stationsById[it]?.position }
                                if (fromPos != null) Marker(state = rememberMarkerState(position = fromPos))
                                if (toPos != null) Marker(state = rememberMarkerState(position = toPos))

                                if (fromPos != null && toPos != null) {
                                    Polyline(
                                        points = listOf(fromPos, toPos),
                                        color = Color.Black,
                                        pattern = listOf(Dot(), Gap(10f))
                                    )
                                }
                            }

                            is Screen.Detail -> {
                                val routePoints = current.route.stations.mapNotNull { stationsById[it]?.position }
                                if (routePoints.isNotEmpty()) {
                                    Polyline(points = routePoints, color = Color.Black, width = 16f)
                                }
                            }

                            else -> {}
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

// A shape's bounding box, used to tell a route's genuinely distinct
// physical branches apart from short-turn trip variants that just trace
// part of a path we're already drawing.
private data class BBox(val minLat: Double, val maxLat: Double, val minLng: Double, val maxLng: Double)

private fun boundingBoxOf(points: List<LatLng>): BBox = BBox(
    minLat = points.minOf { it.latitude },
    maxLat = points.maxOf { it.latitude },
    minLng = points.minOf { it.longitude },
    maxLng = points.maxOf { it.longitude },
)

// True if `inner` doesn't meaningfully extend beyond `outer` -- i.e. inner
// is a short-turn/truncated variant of a path we're already drawing, not a
// genuinely distinct branch.
private fun isRedundant(inner: BBox, outer: BBox, tolerance: Double = 0.002): Boolean =
    inner.minLat >= outer.minLat - tolerance &&
    inner.maxLat <= outer.maxLat + tolerance &&
    inner.minLng >= outer.minLng - tolerance &&
    inner.maxLng <= outer.maxLng + tolerance

// Reads every metro route's shapes, colored with that route's own GTFS
// color. A route can have several distinct shape_ids across its trips --
// not just Blue's and Green's branch routes, but any short-turn trip
// pattern -- so every distinct shape is considered, and only the ones that
// aren't just a smaller subset of a shape we're already drawing survive.
private fun loadMetroLineShapes(assets: AssetManager): List<Pair<List<LatLng>, Color>> {
    val routeRows = assets.open("data/gtfs/metro/routes.txt")
        .bufferedReader().readLines().drop(1).map { it.split(",") }
    val tripRows = assets.open("data/gtfs/metro/trips.txt")
        .bufferedReader().readLines().drop(1).map { it.split(",") }
    val shapeRows = assets.open("data/gtfs/metro/shapes.txt")
        .bufferedReader().readLines().drop(1).map { it.split(",") }

    val pointsByShapeId = shapeRows
        .groupBy { it[0] }
        .mapValues { (_, rows) ->
            rows.sortedBy { it[3].toInt() }.map { LatLng(it[1].toDouble(), it[2].toDouble()) }
        }

    val shapeIdsByRoute = tripRows
        .groupBy { it[0] } // route_id
        .mapValues { (_, trips) -> trips.map { it[7] }.filter { it.isNotBlank() }.distinct() }

    return routeRows.flatMap { route ->
        val routeId = route[0]
        val colorHex = route[7] // route_color
        val color = Color(android.graphics.Color.parseColor("#$colorHex"))

        val shapes = shapeIdsByRoute[routeId].orEmpty()
            .mapNotNull { shapeId -> pointsByShapeId[shapeId]?.takeIf { it.isNotEmpty() } }
            .sortedByDescending { it.size }

        val kept = mutableListOf<List<LatLng>>()
        for (shape in shapes) {
            val bbox = boundingBoxOf(shape)
            val redundant = kept.any { isRedundant(bbox, boundingBoxOf(it)) }
            if (!redundant) kept.add(shape)
        }

        kept.map { it to color }
    }
}
