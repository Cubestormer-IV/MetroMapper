package com.example.metromapper

import android.content.Context
import com.google.android.gms.maps.model.LatLng
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName

// Matches the fields in stations.json
private data class StationJson(
    val id: String,
    val name: String,
    val latitude: Double,
    val longitude: Double,
    val lines: List<String>
)

// Station ID -> map position, e.g. "rithala" -> LatLng(28.7, 77.1)
fun loadStationCoordinates(context: Context): Map<String, LatLng> {
    val json = context.assets
        .open("data/canonical/stations.json")
        .bufferedReader()
        .use { it.readText() }

    return Gson()
        .fromJson(json, Array<StationJson>::class.java)
        .associate { it.id to LatLng(it.latitude, it.longitude) }
}

private data class ConnectionJson(
    val from: String,
    val to: String,
    val line: String,
    @SerializedName("distance_m") val distanceM: Int
)

fun loadConnections(context: Context): List<Connection> {
    val json = context.assets
        .open("data/canonical/connections.json")
        .bufferedReader()
        .use { it.readText() }

    return Gson()
        .fromJson(json, Array<ConnectionJson>::class.java)
        .map { Connection(it.from, it.to, it.line, it.distanceM) }
}

// Matches the fields in termini.json
private data class TerminusJson(
    val line: String,
    val stationId: String,
    val towards: String
)

// Keyed by "line:stationId", e.g. "red:rithala" -> "Rithala"
fun loadTermini(context: Context): Map<String, String> {
    val json = context.assets
        .open("data/canonical/termini.json")
        .bufferedReader()
        .use { it.readText() }

    return Gson()
        .fromJson(json, Array<TerminusJson>::class.java)
        .associate { "${it.line}:${it.stationId}" to it.towards }
}