import { Search, ExternalLink, Sparkles, Briefcase, Loader2 } from 'lucide-react';
import { DEFAULT_JOB_AREAS } from '../lib/api';

function isSafeHttpUrl(url) {
  return typeof url === 'string' && /^https?:\/\//i.test(url.trim());
}

export function JobsPanel({
  selectedAreas,
  onToggleArea,
  customQuery,
  onCustomQueryChange,
  onSearchJobs,
  isSearching,
  jobResults,
  onAdaptResumeForJob,
  onAdaptFromReport,
}) {
  const { jobs = [], report = '', sources = [] } = jobResults || {};

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isSearching) return;
    onSearchJobs();
  };

  return (
    <div className="tab-pane jobs-pane">
      <div className="pane-header">
        <div>
          <h3>Pesquisar Vagas</h3>
          <p>Software, Automações de IA, Automação Industrial e Robótica</p>
        </div>
        {jobs.length > 0 && <span className="count-pill">{jobs.length}</span>}
      </div>

      <form className="jobs-search-box" onSubmit={handleSubmit}>
        <div className="jobs-areas" role="group" aria-label="Áreas de interesse">
          {DEFAULT_JOB_AREAS.map((area) => {
            const active = selectedAreas.includes(area);
            return (
              <button
                key={area}
                type="button"
                className={`area-chip ${active ? 'active' : ''}`}
                onClick={() => onToggleArea(area)}
                disabled={isSearching}
              >
                {area}
              </button>
            );
          })}
        </div>

        <div className="jobs-input-row">
          <input
            type="text"
            value={customQuery}
            onChange={(e) => onCustomQueryChange(e.target.value)}
            placeholder="Filtre por cargo, senioridade, cidade ou modalidade"
            disabled={isSearching}
          />
          <button type="submit" className="btn btn-primary" disabled={isSearching}>
            {isSearching ? <Loader2 size={15} className="spin" /> : <Search size={15} />}
            {isSearching ? 'Buscando...' : 'Pesquisar'}
          </button>
        </div>
      </form>

      <div className="list-scroll">
        {isSearching && (
          <div className="empty-state">
            Agentes Pesquisador e Verificador buscando vagas reais via Tavily...
          </div>
        )}

        {!isSearching && !jobResults && (
          <div className="empty-state">
            Clique em <strong>Pesquisar</strong> para buscar vagas nas áreas selecionadas.
          </div>
        )}

        {!isSearching && jobs.length > 0 && (
          <div className="jobs-list">
            {jobs.map((job, idx) => {
              const badgeClass = (job.eligibility || '').toUpperCase().includes('ELEGÍVEL') &&
                !(job.eligibility || '').toUpperCase().includes('INELEGÍVEL')
                ? 'ok'
                : (job.eligibility || '').toUpperCase().includes('INELEGÍVEL')
                  ? 'warn'
                  : 'neutral';

              return (
                <article key={`${job.title}-${idx}`} className="job-card">
                  <div className="job-card-top">
                    <span className="job-title">
                      <Briefcase size={14} />
                      {job.title}
                    </span>
                    <span className={`job-eligibility ${badgeClass}`}>
                      {job.eligibility || 'VERIFICAÇÃO_PENDENTE'}
                    </span>
                  </div>

                  <div className="job-meta">
                    <strong>{job.company}</strong>
                    {job.seniority ? ` · ${job.seniority}` : ''}
                    {job.modality ? ` · ${job.modality}` : ''}
                    {job.salary ? ` · ${job.salary}` : ''}
                  </div>

                  {job.justification && <p className="job-justification">{job.justification}</p>}

                  <div className="job-actions">
                    {isSafeHttpUrl(job.url) && (
                      <a
                        href={job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary btn-sm"
                      >
                        <ExternalLink size={13} />
                        Abrir vaga
                      </a>
                    )}
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => onAdaptResumeForJob(job)}
                    >
                      <Sparkles size={13} />
                      Adaptar Currículo
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}

        {!isSearching && jobResults && (
          <div className="job-report-box">
            <div className="job-report-header">
              <strong>Relatório Auditado</strong>
              {jobs.length === 0 && report && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => onAdaptFromReport(report)}
                >
                  <Sparkles size={13} />
                  Adaptar Currículo
                </button>
              )}
            </div>

            {sources.length > 0 && (
              <div className="job-sources">
                <span>Fontes verificadas:</span>
                <ul>
                  {sources.map((url) =>
                    isSafeHttpUrl(url) ? (
                      <li key={url}>
                        <a href={url} target="_blank" rel="noopener noreferrer">
                          {url}
                        </a>
                      </li>
                    ) : null
                  )}
                </ul>
              </div>
            )}

            <pre className="job-report-text">{report}</pre>
          </div>
        )}
      </div>
    </div>
  );
}
