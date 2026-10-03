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
        @SerializedName("distance_m") val distanceM: Int
    )

    private fun loadConnections(): List<Connection> {
        // Gradle runs unit tests with the app/ module as the working directory
        val json = File("src/main/assets/data/canonical/connections.json").readText()

        return Gson()
            .fromJson(json, Array<ConnectionJson>::class.java)
            .map { Connection(it.from, it.to, it.line, it.distanceM) }
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

        assertEquals(14413, result?.distanceM)
    }
}
