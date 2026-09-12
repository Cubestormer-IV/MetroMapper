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

import com.google.android.gms.maps.model.CameraPosition
import com.google.android.gms.maps.model.LatLng
import com.google.maps.android.compose.GoogleMap
import com.google.maps.android.compose.MapProperties
import com.google.maps.android.compose.MapUiSettings
import com.google.maps.android.compose.rememberCameraPositionState

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            val delhi = LatLng(28.6139, 77.2090)

            val cameraPositionState = rememberCameraPositionState {
                position = CameraPosition.fromLatLngZoom(delhi, 11f)
            }

            GoogleMap(
                modifier = androidx.compose.ui.Modifier.fillMaxSize(),
                cameraPositionState = cameraPositionState,
                properties = MapProperties(
                    isBuildingEnabled = true
                ),
                uiSettings = MapUiSettings(
                    zoomControlsEnabled = true
                ),
                onMapLoaded = {
                    android.util.Log.d("MetroMapper", "MAP LOADED!")
                }
            )
        }
    }
}