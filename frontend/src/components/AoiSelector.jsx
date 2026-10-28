import { useState } from 'react'
import shp from 'shpjs'
import { kml as kmlToGeoJSON } from '@tmcw/togeojson'
import AoiMap from './AoiMap'
import { getDefaultAoi } from '../services/api'

const METHODS = [
  ['map', 'Desenhar no mapa'],
  ['bbox', 'Coordenadas'],
  ['file', 'Carregar arquivo'],
  ['saved', 'Área cadastrada'],
]

export default function AoiSelector({ geometry, onChange }) {
  const [method, setMethod] = useState('map')
  const [bbox, setBbox] = useState({ west: -44.14, south: -20.045, east: -44.08, north: -19.995 })
  const [error, setError] = useState('')

  const applyBbox = () => {
    const { west, south, east, north } = Object.fromEntries(Object.entries(bbox).map(([k, v]) => [k, Number(v)]))
    if (!(west < east && south < north)) return setError('Coordenadas inválidas.')
    setError('')
    onChange({ type: 'Polygon', coordinates: [[[west,south],[east,south],[east,north],[west,north],[west,south]]] })
  }

  const loadSaved = async () => {
    try {
      const data = await getDefaultAoi()
      onChange(data.geometry)
      setError('')
    } catch (e) { setError(e.message) }
  }

  const loadFile = async (file) => {
    try {
      const ext = file.name.toLowerCase().split('.').pop()
      let geo
      if (ext === 'zip') {
        const parsed = await shp(await file.arrayBuffer())
        geo = Array.isArray(parsed) ? parsed[0] : parsed
      } else if (ext === 'kml') {
        const xml = new DOMParser().parseFromString(await file.text(), 'text/xml')
        geo = kmlToGeoJSON(xml)
      } else {
        geo = JSON.parse(await file.text())
      }
      if (geo.type === 'FeatureCollection') onChange(geo)
      else if (geo.type === 'Feature') onChange(geo.geometry)
      else onChange(geo)
      setError('')
    } catch (e) { setError(`Não foi possível ler o arquivo: ${e.message}`) }
  }

  return (
    <div className="aoi-selector">
      <div className="tabs">
        {METHODS.map(([id, label]) => <button key={id} className={method === id ? 'active' : ''} onClick={() => setMethod(id)}>{label}</button>)}
      </div>

      {method === 'map' && <AoiMap geometry={geometry} onChange={onChange} />}

      {method === 'bbox' && (
        <div className="bbox-grid">
          {['west','south','east','north'].map(k => (
            <label key={k}>{({west:'Longitude oeste',south:'Latitude sul',east:'Longitude leste',north:'Latitude norte'})[k]}
              <input type="number" step="0.000001" value={bbox[k]} onChange={e => setBbox({ ...bbox, [k]: e.target.value })} />
            </label>
          ))}
          <button className="primary" onClick={applyBbox}>Aplicar coordenadas</button>
        </div>
      )}

      {method === 'file' && (
        <div className="upload-box">
          <strong>GeoJSON, KML ou Shapefile (.zip)</strong>
          <p>Para Shapefile, compacte .shp, .shx, .dbf e .prj no mesmo ZIP.</p>
          <input type="file" accept=".geojson,.json,.kml,.zip" onChange={e => e.target.files?.[0] && loadFile(e.target.files[0])} />
        </div>
      )}

      {method === 'saved' && (
        <div className="upload-box">
          <strong>Lagoa REGAP</strong>
          <p>Área de estudo utilizada durante a validação do projeto.</p>
          <button className="primary" onClick={loadSaved}>Usar Lagoa REGAP</button>
        </div>
      )}
      {error && <div className="error">{error}</div>}
      {geometry && <div className="success-line">✓ AOI definida</div>}
    </div>
  )
}
