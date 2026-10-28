import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import '@geoman-io/leaflet-geoman-free'
import 'leaflet/dist/leaflet.css'
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css'

function DrawingController({ geometry, onChange }) {
  const map = useMap()
  const layerRef = useRef(null)

  useEffect(() => {
    map.pm.addControls({
      position: 'topleft',
      drawMarker: false,
      drawCircleMarker: false,
      drawPolyline: false,
      drawCircle: false,
      drawText: false,
      drawPolygon: true,
      drawRectangle: true,
      editMode: true,
      dragMode: false,
      cutPolygon: false,
      removalMode: true,
      rotateMode: false,
    })

    const setLayer = (layer) => {
      if (layerRef.current && map.hasLayer(layerRef.current)) map.removeLayer(layerRef.current)
      layerRef.current = layer
      layer.addTo(map)
      const gj = layer.toGeoJSON()
      onChange(gj.geometry)
    }

    const created = (e) => setLayer(e.layer)
    const changed = (e) => {
      const layer = e.layer || layerRef.current
      if (layer) onChange(layer.toGeoJSON().geometry)
    }
    map.on('pm:create', created)
    map.on('pm:edit', changed)
    map.on('pm:remove', () => { layerRef.current = null; onChange(null) })

    return () => {
      map.off('pm:create', created)
      map.off('pm:edit', changed)
      map.pm.removeControls()
    }
  }, [map, onChange])

  useEffect(() => {
    if (!geometry) return
    if (layerRef.current && map.hasLayer(layerRef.current)) map.removeLayer(layerRef.current)
    const layer = L.geoJSON(geometry, { style: { color: '#0b74de', weight: 3, fillOpacity: 0.2 } })
    layerRef.current = layer
    layer.addTo(map)
    try { map.fitBounds(layer.getBounds(), { padding: [24, 24] }) } catch (_) {}
  }, [geometry, map])

  return null
}

export default function AoiMap({ geometry, onChange }) {
  return (
    <MapContainer center={[-20.02, -44.11]} zoom={13} className="map">
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <DrawingController geometry={geometry} onChange={onChange} />
    </MapContainer>
  )
}
