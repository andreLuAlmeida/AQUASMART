import { useEffect, useMemo, useState } from 'react'
import { Droplets, Leaf, Satellite, Settings2 } from 'lucide-react'
import AoiSelector from './components/AoiSelector'
import ProgressView from './components/ProgressView'
import ResultView from './components/ResultView'
import { getCapabilities, submitJob, getJob } from './services/api'

const today = new Date().toISOString().slice(0, 10)
const monthAgo = new Date(Date.now() - 30 * 24 * 3600 * 1000).toISOString().slice(0, 10)

export default function App() {
  const [caps, setCaps] = useState(null)
  const [analysisType, setAnalysisType] = useState('macrophytes')
  const [source, setSource] = useState('auto')
  const [preferredSource, setPreferredSource] = useState('gee')
  const [startDate, setStartDate] = useState(monthAgo)
  const [endDate, setEndDate] = useState(today)
  const [aoi, setAoi] = useState(null)
  const [orbit, setOrbit] = useState('DESCENDING')
  const [cloud, setCloud] = useState(30)
  const [params, setParams] = useState(['chlorophyll_a', 'turbidity_ntu', 'secchi_cm', 'pc_rfu'])
  const [job, setJob] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => { getCapabilities().then(setCaps).catch(e => setError(e.message)) }, [])

  useEffect(() => {
    if (!job?.id || ['completed','failed'].includes(job.status)) return
    const t = setInterval(async () => {
      try {
        const fresh = await getJob(job.id)
        setJob(fresh)
      } catch (e) { setError(e.message) }
    }, 1200)
    return () => clearInterval(t)
  }, [job?.id, job?.status])

  const running = job && !['completed','failed'].includes(job.status)
  const completed = job?.status === 'completed'

  const payload = useMemo(() => ({
    analysis_type: analysisType,
    source,
    preferred_source: source === 'auto' ? preferredSource : null,
    allow_fallback: true,
    start_date: startDate,
    end_date: endDate,
    aoi,
    orbit_pass: analysisType === 'macrophytes' ? orbit : null,
    cloud_cover: Number(cloud),
    parameters: analysisType === 'water_quality' ? params : null,
  }), [analysisType, source, preferredSource, startDate, endDate, aoi, orbit, cloud, params])

  const execute = async () => {
    if (!aoi) return setError('Defina a área de estudo antes de executar.')
    if (!startDate || !endDate || startDate >= endDate) return setError('Período inválido.')
    setError('')
    try {
      const created = await submitJob(payload)
      setJob({ ...created, progress: 0, stage: 'queued', message: 'Análise enviada.' })
    } catch (e) { setError(e.message) }
  }

  if (completed) return <Shell><ResultView result={job.result} onNew={() => setJob(null)} /></Shell>
  if (running || job?.status === 'failed') return <Shell><ProgressView job={job} />{job?.status === 'failed' && <button className="primary retry" onClick={() => setJob(null)}>Voltar</button>}</Shell>

  return (
    <Shell>
      <header className="hero">
        <span className="eyebrow">Sensoriamento remoto + inteligência artificial</span>
        <h1>Análise de ambientes aquáticos</h1>
        <p>Selecione a análise, a área e o período. O AQUASMART orquestra aquisição, modelos e produtos geoespaciais.</p>
      </header>

      <div className="workspace">
        <section className="panel config-panel">
          <h2>1. Tipo de análise</h2>
          <div className="choice-grid">
            <button className={`choice ${analysisType === 'macrophytes' ? 'selected green' : ''}`} onClick={() => setAnalysisType('macrophytes')}>
              <Leaf size={24}/><strong>Macrófitas</strong><span>Sentinel-1 · U-Net</span>
            </button>
            <button className={`choice ${analysisType === 'water_quality' ? 'selected blue' : ''}`} onClick={() => setAnalysisType('water_quality')}>
              <Droplets size={24}/><strong>Qualidade da água</strong><span>Sentinel-2 · modelos .pkl</span>
            </button>
          </div>

          <h2>2. Origem dos dados</h2>
          <label className="field">Modo de aquisição
            <select value={source} onChange={e => setSource(e.target.value)}>
              <option value="auto">Automática — recomendado</option>
              <option value="gee">Google Earth Engine</option>
              <option value="copernicus">Copernicus Data Space</option>
            </select>
          </label>
          {source === 'auto' && <label className="field">Fonte preferida
            <select value={preferredSource} onChange={e => setPreferredSource(e.target.value)}>
              <option value="gee">Google Earth Engine</option>
              <option value="copernicus">Copernicus Data Space</option>
            </select>
            <small>Se falhar ou não estiver normalizada para o modelo, a outra fonte é tentada.</small>
          </label>}

          <h2>3. Período</h2>
          <div className="date-grid">
            <label className="field">Data inicial<input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} /></label>
            <label className="field">Data final<input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} /></label>
          </div>

          <details className="advanced"><summary><Settings2 size={16}/> Opções avançadas</summary>
            {analysisType === 'macrophytes' ? (
              <label className="field">Órbita Sentinel-1<select value={orbit} onChange={e => setOrbit(e.target.value)}><option>DESCENDING</option><option>ASCENDING</option></select></label>
            ) : (
              <>
                <label className="field">Cobertura máxima de nuvens (%)<input type="number" min="0" max="100" value={cloud} onChange={e => setCloud(e.target.value)} /></label>
                <div className="checks"><strong>Parâmetros</strong>{caps?.water_quality_parameters?.map(p => <label key={p.id}><input type="checkbox" checked={params.includes(p.id)} onChange={e => setParams(e.target.checked ? [...params, p.id] : params.filter(x => x !== p.id))}/>{p.label}{!p.model_available && ' (modelo ausente)'}</label>)}</div>
              </>
            )}
          </details>
        </section>

        <section className="panel map-panel">
          <h2>4. Área de estudo (AOI)</h2>
          <AoiSelector geometry={aoi} onChange={setAoi}/>
          <div className="run-row">
            <div><Satellite size={20}/><span>O processamento pode levar alguns minutos dependendo da área.</span></div>
            <button className="primary execute" onClick={execute}>Executar análise</button>
          </div>
          {error && <div className="error">{error}</div>}
        </section>
      </div>
    </Shell>
  )
}

function Shell({ children }) {
  return <div className="app-shell"><aside className="sidebar"><div className="brand">💧 <span>AQUASMART</span></div><nav><span className="active">Nova análise</span><span>Resultados</span><span>Sobre</span></nav><small>Projeto de pesquisa</small></aside><main>{children}</main></div>
}
