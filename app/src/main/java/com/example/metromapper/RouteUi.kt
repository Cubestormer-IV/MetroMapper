package com.example.metromapper

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.google.android.gms.maps.CameraUpdateFactory
import com.google.android.gms.maps.model.CameraPosition
import com.google.android.gms.maps.model.LatLng
import com.google.android.gms.maps.model.LatLngBounds
import com.google.maps.android.compose.GoogleMap
import com.google.maps.android.compose.Polyline
import com.google.maps.android.compose.rememberCameraPositionState

// Which screen is on display. Just three screens, so no navigation library.
sealed class Screen {
    data object Picker : Screen()
    data class Options(val routes: List<RouteResult>) : Screen()
    data class Detail(val route: RouteResult, val options: Options) : Screen()
}

private fun colorFromHex(hex: String): Color =
    Color(android.graphics.Color.parseColor(hex))

// --- Screen 1: pick a from and a to station ---------------------------------

@Composable
fun StationPickerScreen(
    stations: List<Station>,
    onSearch: (fromId: String, toId: String) -> Unit
) {
    var fromId by remember { mutableStateOf<String?>(null) }
    var toId by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Text("MetroMapper", style = MaterialTheme.typography.headlineSmall)
        Spacer(modifier = Modifier.height(16.dp))

        StationField(label = "From", stations = stations, onSelect = { fromId = it })
        Spacer(modifier = Modifier.height(12.dp))
        StationField(label = "To", stations = stations, onSelect = { toId = it })
        Spacer(modifier = Modifier.height(16.dp))

        Button(
            onClick = {
                val from = fromId
                val to = toId
                if (from != null && to != null) onSearch(from, to)
            },
            enabled = fromId != null && toId != null && fromId != toId,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Find routes")
        }
    }
}

@Composable
private fun StationField(
    label: String,
    stations: List<Station>,
    onSelect: (String) -> Unit
) {
    var query by remember { mutableStateOf("") }
    var expanded by remember { mutableStateOf(false) }

    Column {
        OutlinedTextField(
            value = query,
            onValueChange = {
                query = it
                expanded = it.isNotBlank()
            },
            label = { Text(label) },
            modifier = Modifier.fillMaxWidth()
        )

        if (expanded) {
            val matches = stations
                .filter { it.name.contains(query, ignoreCase = true) }
                .take(8)

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surfaceVariant)
            ) {
                matches.forEach { station ->
                    Text(
                        text = station.name,
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable {
                                query = station.name
                                expanded = false
                                onSelect(station.id)
                            }
                            .padding(12.dp)
                    )
                }
            }
        }
    }
}

// --- Screen 2: the list of route options -------------------------------------

@Composable
fun RouteOptionsScreen(
    routes: List<RouteResult>,
    stationsById: Map<String, Station>,
    linesById: Map<String, MetroLine>,
    onSelect: (RouteResult) -> Unit,
    onBack: () -> Unit
) {
    val first = routes.firstOrNull()
    val title = if (first != null) {
        val from = stationsById[first.stations.first()]?.name ?: first.stations.first()
        val to = stationsById[first.stations.last()]?.name ?: first.stations.last()
        "$from → $to"
    } else {
        "Routes"
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Text(title, style = MaterialTheme.typography.headlineSmall)
        Spacer(modifier = Modifier.height(8.dp))

        if (routes.isEmpty()) {
            Text("No route found between these stations.")
        }

        LazyColumn(modifier = Modifier.weight(1f)) {
            items(routes) { route ->
                val legs = splitIntoLegs(route)
                val totalMinutes = legs.sumOf { it.estimatedMinutes }
                val transfers = legs.size - 1

                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 6.dp)
                        .clickable { onSelect(route) }
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            legs.forEach { leg ->
                                LineBadge(linesById[leg.line])
                                Spacer(modifier = Modifier.size(6.dp))
                            }
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text("$totalMinutes min", fontWeight = FontWeight.Bold)
                        Text(
                            if (transfers == 0) "Direct" else "$transfers change${if (transfers > 1) "s" else ""}",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))
        Button(onClick = onBack, modifier = Modifier.fillMaxWidth()) {
            Text("Back")
        }
    }
}

@Composable
private fun LineBadge(line: MetroLine?) {
    Box(
        modifier = Modifier
            .size(16.dp)
            .clip(CircleShape)
            .background(line?.let { colorFromHex(it.color) } ?: Color.Gray)
    )
}

// --- Screen 3: the map and the step-by-step directions ------------------------

@Composable
fun RouteDetailScreen(
    route: RouteResult,
    connections: List<Connection>,
    termini: Map<String, String>,
    stationsById: Map<String, Station>,
    linesById: Map<String, MetroLine>,
    backgroundLines: List<Pair<List<LatLng>, Color>>,
    onBack: () -> Unit
) {
    val routePoints = route.stations.mapNotNull { stationsById[it]?.position }

    val delhi = LatLng(28.6139, 77.2090)
    val cameraPositionState = rememberCameraPositionState {
        position = CameraPosition.fromLatLngZoom(delhi, 11f)
    }

    // Once we know the route's points, move the camera to frame them
    LaunchedEffect(routePoints) {
        if (routePoints.size >= 2) {
            val bounds = LatLngBounds.builder().apply {
                routePoints.forEach { include(it) }
            }.build()
            cameraPositionState.animate(CameraUpdateFactory.newLatLngBounds(bounds, 100))
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(250.dp)
        ) {
            GoogleMap(
                modifier = Modifier.fillMaxSize(),
                cameraPositionState = cameraPositionState
            ) {
                backgroundLines.forEach { (points, color) ->
                    Polyline(points = points, color = color, width = 8f)
                }
                if (routePoints.isNotEmpty()) {
                    Polyline(points = routePoints, color = Color.Black, width = 16f)
                }
            }
        }

        val steps = buildSteps(route, connections, termini, stationsById, linesById)

        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .padding(horizontal = 16.dp)
        ) {
            item {
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    "%.1f km".format(route.distanceM / 1000.0),
                    style = MaterialTheme.typography.bodySmall
                )
            }
            items(steps) { step -> StepRow(step) }
            item { Spacer(modifier = Modifier.height(12.dp)) }
        }

        Button(
            onClick = onBack,
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text("Back to routes")
        }
    }
}

@Composable
private fun StepRow(step: RouteStep) {
    when (step) {
        is RouteStep.Board -> {
            HorizontalDivider()
            Row(
                modifier = Modifier.padding(vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(14.dp)
                        .clip(CircleShape)
                        .background(colorFromHex(step.lineColorHex))
                )
                Spacer(modifier = Modifier.size(8.dp))
                Column {
                    Text("Board at ${step.stationName}", fontWeight = FontWeight.Bold)
                    Text(
                        step.lineName + (step.direction?.let { " towards $it" } ?: ""),
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }

        is RouteStep.Ride -> {
            Text(
                "${step.stops} stop${if (step.stops != 1) "s" else ""} · ${step.minutes} min",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(start = 22.dp, bottom = 6.dp)
            )
        }

        is RouteStep.ChangeAt -> {
            Text("Change at ${step.stationName}", fontWeight = FontWeight.Bold)
        }

        is RouteStep.GetOffAt -> {
            HorizontalDivider()
            Text(
                "Get off at ${step.stationName}",
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(vertical = 10.dp)
            )
        }
    }
}
