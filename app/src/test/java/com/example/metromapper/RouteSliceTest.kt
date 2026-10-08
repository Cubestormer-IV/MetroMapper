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
        @SerializedName("distance_m") val distanceM: Int
    )

    private fun loadConnections(): List<Connection> {
        val json = File("src/main/assets/data/canonical/connections.json").readText()

        return Gson()
            .fromJson(json, Array<ConnectionJson>::class.java)
            .map { Connection(it.from, it.to, it.line, it.distanceM) }
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
                "chandni_chowk",
                "chawri_bazar",
                "new_delhi",
                "rajiv_chowk"
            ),
            route.stations
        )

        assertEquals(18486, route.distanceM)

        val legs = splitIntoLegs(route)

        assertEquals(2, legs.size)
        assertEquals("red", legs[0].line)
        assertEquals("kashmere_gate", legs[0].alightAt)
        assertEquals("yellow", legs[1].line)
        assertEquals("rajiv_chowk", legs[1].alightAt)
    }
}