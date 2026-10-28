function SourceAttempts({ attempts = [] }) {
  if (!attempts.length) return null
  return <div className="attempts"><strong>Tentativas de fonte</strong>{attempts.map((x, i) => <span key={i} className={x.status}>{x.source}: {x.status === 'success' ? 'sucesso' : 'fallback'}</span>)}</div>
}

export default function ResultView({ result, onNew }) {
  const acq = result.acquisition || {}
  const analysis = result.analysis || {}
  const macro = result.analysis_type === 'macrophytes'

  return (
    <section className="panel result-panel">
      <div className="result-head">
        <div><span className="eyebrow">Análise concluída</span><h2>{macro ? 'Macrófitas' : 'Qualidade da água'}</h2></div>
        <button onClick={onNew}>Nova análise</button>
      </div>

      <div className="metadata-grid">
        <div><small>Fonte utilizada</small><strong>{acq.source_label || acq.source}</strong></div>
        <div><small>Data da imagem</small><strong>{(acq.datetime || '').slice(0,10)}</strong></div>
        <div><small>Satélite</small><strong>{macro ? 'Sentinel-1' : 'Sentinel-2'}</strong></div>
        {acq.orbit_state && <div><small>Órbita</small><strong>{acq.orbit_state}</strong></div>}
        {acq.cloud_cover != null && <div><small>Nuvens</small><strong>{Number(acq.cloud_cover).toFixed(1)}%</strong></div>}
      </div>
      <SourceAttempts attempts={acq.source_attempts} />

      {macro ? (
        <div className="result-grid">
          <div className="metrics">
            <div className="metric highlight"><small>Macrófitas</small><strong>{analysis.plant_pct?.toFixed(2)}%</strong></div>
            <div className="metric"><small>Área de macrófitas</small><strong>{Math.round(analysis.plant_area_m2 || 0).toLocaleString('pt-BR')} m²</strong></div>
            <div className="metric"><small>Pixels de água</small><strong>{analysis.water_pixels?.toLocaleString('pt-BR')}</strong></div>
            <div className="downloads">
              {analysis.classification_aoi_url && <a href={analysis.classification_aoi_url} download>Baixar GeoTIFF</a>}
              {analysis.preview_url && <a href={analysis.preview_url} download>Baixar PNG</a>}
            </div>
          </div>
          {analysis.preview_url && <img className="preview" src={analysis.preview_url} alt="Mapa de macrófitas" />}
        </div>
      ) : (
        <div>
          <div className="parameter-grid">
            {Object.entries(analysis.parameters || {}).map(([id, p]) => (
              <article className="parameter-card" key={id}>
                <small>{p.label}</small><strong>{Number(p.mean).toFixed(3)}</strong><span>média na AOI</span>
                {p.preview_url && <img src={p.preview_url} alt={p.label} />}
                <div className="downloads mini">
                  {p.raster_url && <a href={p.raster_url}>GeoTIFF</a>}
                  {p.preview_url && <a href={p.preview_url}>PNG</a>}
                </div>
              </article>
            ))}
          </div>
          {Object.keys(analysis.parameter_errors || {}).length > 0 && (
            <details className="warnings"><summary>Alguns parâmetros não puderam ser executados</summary><pre>{JSON.stringify(analysis.parameter_errors, null, 2)}</pre></details>
          )}
        </div>
      )}
    </section>
  )
}
