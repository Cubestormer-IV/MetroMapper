package com.example.metromapper

import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import org.junit.Test
import org.junit.Assert.assertEquals
import java.io.File

class RouteFinderTest {

    // Matches the field names in connections.json
    private data class ConnectionJson(
        val from: String,
        val to: String,
        val line: String,
        @SerializedName("distance_m") val distanceM: Int,
        @SerializedName("duration_s") val durationS: Int
    )

    private data class TransferJson(
        val from: String,
        val to: String,
        @SerializedName("duration_s") val durationS: Int
    )

    private fun loadConnections(): List<Connection> {
        // Gradle runs unit tests with the app/ module as the working directory
        val json = File("src/main/assets/data/canonical/connections.json").readText()
        val transferJson = File("src/main/assets/data/canonical/transfers.json").readText()

        val rides = Gson()
            .fromJson(json, Array<ConnectionJson>::class.java)
            .map { Connection(it.from, it.to, it.line, it.distanceM, it.durationS) }

        val walks = Gson()
            .fromJson(transferJson, Array<TransferJson>::class.java)
            .map { Connection(it.from, it.to, "walk", 0, it.durationS) }

        return rides + walks
    }

    @Test
    fun findsShortestRoute() {

        val connections = loadConnections()

        val result = findShortestRoute(
            connections,
            "rithala",
            "kashmere_gate"
        )

        assertEquals(
            listOf(
                "rithala",
                "rohini_west",
                "rohini_east",
                "pitampura",
                "kohat_enclave",
                "netaji_subhash_place",
                "keshav_puram",
                "kanhaiya_nagar",
                "inderlok",
                "shastri_nagar",
                "pratap_nagar",
                "pul_bangash",
                "tis_hazari",
                "kashmere_gate"
            ),
            result?.stations
        )

        assertEquals(14896, result?.distanceM)
    }
}
