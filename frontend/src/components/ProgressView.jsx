const STEPS = [
  ['aoi', 'Validando parâmetros e AOI'],
  ['acquisition', 'Buscando imagem de satélite'],
  ['inference', 'Executando modelo de IA'],
  ['outputs', 'Gerando métricas e mapas'],
  ['done', 'Concluído'],
]

export default function ProgressView({ job }) {
  const current = Math.max(0, STEPS.findIndex(([id]) => id === job.stage))
  return (
    <section className="panel progress-panel">
      <h2>Executando análise...</h2>
      <div className="progress-bar"><span style={{ width: `${job.progress || 0}%` }} /></div>
      {STEPS.map(([id, label], i) => (
        <div className={`progress-step ${i < current || job.stage === 'done' ? 'done' : i === current ? 'current' : ''}`} key={id}>
          <span>{i < current || job.stage === 'done' ? '✓' : i === current ? '●' : '○'}</span>
          <div><strong>{label}</strong>{i === current && <small>{job.message}</small>}</div>
        </div>
      ))}
      {job.error && <div className="error">{job.error}</div>}
    </section>
  )
}
