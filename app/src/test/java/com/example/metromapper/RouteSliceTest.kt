package com.example.metromapper

import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import org.junit.Test
import org.junit.Assert.assertEquals
import java.io.File

class RouteSliceTest {

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
    fun rithalaToRajivChowkCrossesFromRedToYellowAtKashmereGate() {

        val connections = loadConnections()
        val route = findShortestRoute(connections, "rithala", "rajiv_chowk")!!

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
                "kashmere_gate",
                "kashmere_gate",
                "chandni_chowk",
                "chawri_bazar",
                "new_delhi",
                "rajiv_chowk"
            ),
            route.stations
        )

        assertEquals(19019, route.distanceM)

        val legs = splitIntoLegs(route)

        // red -> walk (change platforms at Kashmere Gate) -> yellow
        assertEquals(3, legs.size)
        assertEquals("red", legs[0].line)
        assertEquals("kashmere_gate:red", legs[0].alightAt)
        assertEquals("walk", legs[1].line)
        assertEquals("yellow", legs[2].line)
        assertEquals("rajiv_chowk:yellow", legs[2].alightAt)
    }
}