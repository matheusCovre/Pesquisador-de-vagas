import { useState } from 'react';
import {
  FileText,
  FileCode2,
  Download,
  Send,
  Building2,
  MapPin,
  Mail,
  Phone,
  Globe,
  Sparkles,
  Copy,
  Check,
  HardDrive,
  Pencil,
  Eye,
  ShieldCheck,
  AlertTriangle,
  Plus,
  Trash2,
} from 'lucide-react';

function StringListEditor({ label, items = [], onChange, placeholder }) {
  const updateAt = (index, value) => {
    const next = [...items];
    next[index] = value;
    onChange(next);
  };

  const removeAt = (index) => {
    onChange(items.filter((_, i) => i !== index));
  };

  const addItem = () => {
    onChange([...items, '']);
  };

  return (
    <div className="cv-section">
      <div className="editor-section-header">
        <h3>{label}</h3>
        <button type="button" className="btn btn-secondary btn-sm" onClick={addItem}>
          <Plus size={13} />
          Adicionar
        </button>
      </div>
      <div className="editor-stack">
        {items.map((item, idx) => (
          <div key={idx} className="editor-inline-row">
            <input
              type="text"
              value={item}
              placeholder={placeholder}
              onChange={(e) => updateAt(idx, e.target.value)}
            />
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => removeAt(idx)}
              title="Remover item"
            >
              <Trash2 size={13} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ResumeViewer({
  resume,
  onChangeResume,
  isEditing = false,
  onToggleEdit,
  onVerifyResume,
  isVerifying = false,
  verificationState = null,
  onOpenSendModal,
  onDownload,
  onSaveToDrive,
  isSavingDrive = false,
}) {
  const [viewMode, setViewMode] = useState('document');
  const [copied, setCopied] = useState(false);

  const handleCopyJson = async () => {
    await navigator.clipboard.writeText(JSON.stringify(resume, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const updateField = (field, value) => {
    onChangeResume?.({ ...resume, [field]: value });
  };

  const updateCandidate = (field, value) => {
    onChangeResume?.({
      ...resume,
      candidate: { ...resume.candidate, [field]: value },
    });
  };

  const updateExperience = (index, patch) => {
    const next = (resume.experiences || []).map((exp, i) =>
      i === index ? { ...exp, ...patch } : exp
    );
    updateField('experiences', next);
  };

  const addExperience = () => {
    updateField('experiences', [
      ...(resume.experiences || []),
      { role: '', company: '', period: '', location: '', highlights: [''] },
    ]);
  };

  const removeExperience = (index) => {
    updateField(
      'experiences',
      (resume.experiences || []).filter((_, i) => i !== index)
    );
  };

  const updateProject = (index, patch) => {
    const next = (resume.projects || []).map((proj, i) =>
      i === index ? { ...proj, ...patch } : proj
    );
    updateField('projects', next);
  };

  const addProject = () => {
    if ((resume.projects || []).length >= 3) return;
    updateField('projects', [
      ...(resume.projects || []),
      { title: '', technologies: [], description: '', status: null, url: null },
    ]);
  };

  const removeProject = (index) => {
    updateField(
      'projects',
      (resume.projects || []).filter((_, i) => i !== index)
    );
  };

  const updateEducation = (index, patch) => {
    const next = (resume.education || []).map((edu, i) =>
      i === index ? { ...edu, ...patch } : edu
    );
    updateField('education', next);
  };

  return (
    <section className="resume-panel">
      <div className="panel-toolbar">
        <div className="toolbar-meta">
          <span className="badge-ai">
            <Sparkles size={13} />
            {resume.targetRole}
          </span>
          <span className="target-company">
            <Building2 size={14} />
            {resume.targetCompany}
          </span>
          <span className="updated-tag">Atualizado: {resume.updatedAt}</span>
        </div>

        <div className="toolbar-actions">
          <div className="segmented-control">
            <button
              type="button"
              className={viewMode === 'document' && !isEditing ? 'active' : ''}
              onClick={() => {
                setViewMode('document');
                if (isEditing) onToggleEdit?.();
              }}
            >
              <FileText size={14} />
              Documento
            </button>
            <button
              type="button"
              className={viewMode === 'json' ? 'active' : ''}
              onClick={() => setViewMode('json')}
            >
              <FileCode2 size={14} />
              JSON
            </button>
          </div>

          {onToggleEdit && (
            <button
              type="button"
              className={`btn ${isEditing ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => {
                setViewMode('document');
                onToggleEdit();
              }}
              title="Editar conteúdo diretamente no documento"
            >
              {isEditing ? <Eye size={15} /> : <Pencil size={15} />}
              {isEditing ? 'Visualizar' : 'Editar'}
            </button>
          )}

          {onVerifyResume && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onVerifyResume}
              disabled={isVerifying}
              title="Verificar documento contra a base local revisada"
            >
              <ShieldCheck size={15} />
              {isVerifying ? 'Verificando...' : 'Verificar'}
            </button>
          )}

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onDownload('DOCX')}
            title="Exportar em Word (.docx)"
          >
            <Download size={15} />
            DOCX
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onDownload('PDF')}
            title="Exportar em PDF (.pdf)"
          >
            <Download size={15} />
            PDF
          </button>

          {onSaveToDrive ? (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onSaveToDrive}
              disabled={isSavingDrive}
              title="Salvar PDF verificado no Google Drive"
            >
              <HardDrive size={15} />
              {isSavingDrive ? 'Salvando...' : 'Salvar no Drive'}
            </button>
          ) : null}

          <button
            type="button"
            className="btn btn-primary"
            onClick={onOpenSendModal}
          >
            <Send size={15} />
            Enviar E-mail
          </button>
        </div>
      </div>

      {verificationState && (
        <div
          className={`verification-banner ${
            verificationState.status === 'approved' ? 'is-approved' : 'is-blocked'
          }`}
        >
          <div className="verification-banner-title">
            {verificationState.status === 'approved' ? (
              <>
                <ShieldCheck size={15} />
                <span>Documento verificado e aprovado contra a base local.</span>
              </>
            ) : (
              <>
                <AlertTriangle size={15} />
                <span>
                  Documento bloqueado na verificação. Edite os campos apontados e clique em
                  Verificar.
                </span>
              </>
            )}
          </div>
          {verificationState.issues?.length > 0 && (
            <div className="chat-issues-list">
              {verificationState.issues.map((iss, idx) => (
                <span key={`${iss.code}-${idx}`} className="issue-pill">
                  {iss.code} ({iss.field})
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="resume-canvas">
        {viewMode === 'document' && isEditing ? (
          <article className="a4-sheet a4-editor">
            <div className="cv-section">
              <h3>Cabeçalho e Vaga-Alvo</h3>
              <div className="editor-grid">
                <label>
                  Nome completo
                  <input
                    type="text"
                    value={resume.candidate.name}
                    onChange={(e) => updateCandidate('name', e.target.value)}
                  />
                </label>
                <label>
                  Headline
                  <input
                    type="text"
                    value={resume.candidate.headline}
                    onChange={(e) => updateCandidate('headline', e.target.value)}
                  />
                </label>
                <label>
                  Cargo-alvo
                  <input
                    type="text"
                    value={resume.targetRole}
                    onChange={(e) => updateField('targetRole', e.target.value)}
                  />
                </label>
                <label>
                  Empresa-alvo
                  <input
                    type="text"
                    value={resume.targetCompany}
                    onChange={(e) => updateField('targetCompany', e.target.value)}
                  />
                </label>
                <label>
                  E-mail
                  <input
                    type="email"
                    value={resume.candidate.email}
                    onChange={(e) => updateCandidate('email', e.target.value)}
                  />
                </label>
                <label>
                  Telefone
                  <input
                    type="text"
                    value={resume.candidate.phone}
                    onChange={(e) => updateCandidate('phone', e.target.value)}
                  />
                </label>
                <label>
                  Localização
                  <input
                    type="text"
                    value={resume.candidate.location}
                    onChange={(e) => updateCandidate('location', e.target.value)}
                  />
                </label>
                <label>
                  LinkedIn
                  <input
                    type="text"
                    value={resume.candidate.linkedin}
                    onChange={(e) => updateCandidate('linkedin', e.target.value)}
                  />
                </label>
                <label>
                  GitHub
                  <input
                    type="text"
                    value={resume.candidate.github || ''}
                    onChange={(e) => updateCandidate('github', e.target.value)}
                  />
                </label>
              </div>
            </div>

            <div className="cv-section">
              <h3>Perfil Profissional</h3>
              <textarea
                rows={4}
                className="editor-textarea"
                value={resume.summary}
                onChange={(e) => updateField('summary', e.target.value)}
              />
            </div>

            <StringListEditor
              label="Competências Técnicas"
              items={resume.skills || []}
              onChange={(next) => updateField('skills', next)}
              placeholder="Categoria: competências..."
            />

            <div className="cv-section">
              <div className="editor-section-header">
                <h3>Experiência Profissional</h3>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={addExperience}
                >
                  <Plus size={13} />
                  Adicionar
                </button>
              </div>
              <div className="editor-stack">
                {(resume.experiences || []).map((exp, idx) => (
                  <div key={idx} className="editor-card">
                    <div className="editor-card-head">
                      <strong>Experiência #{idx + 1}</strong>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => removeExperience(idx)}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                    <div className="editor-grid">
                      <label>
                        Cargo
                        <input
                          type="text"
                          value={exp.role}
                          onChange={(e) => updateExperience(idx, { role: e.target.value })}
                        />
                      </label>
                      <label>
                        Empresa
                        <input
                          type="text"
                          value={exp.company}
                          onChange={(e) => updateExperience(idx, { company: e.target.value })}
                        />
                      </label>
                      <label>
                        Período
                        <input
                          type="text"
                          value={exp.period}
                          onChange={(e) => updateExperience(idx, { period: e.target.value })}
                        />
                      </label>
                      <label>
                        Local
                        <input
                          type="text"
                          value={exp.location || ''}
                          onChange={(e) => updateExperience(idx, { location: e.target.value })}
                        />
                      </label>
                    </div>
                    <label>
                      Destaques (um por linha)
                      <textarea
                        rows={3}
                        className="editor-textarea"
                        value={(exp.highlights || []).join('\n')}
                        onChange={(e) =>
                          updateExperience(idx, {
                            highlights: e.target.value.split('\n'),
                          })
                        }
                      />
                    </label>
                  </div>
                ))}
              </div>
            </div>

            <div className="cv-section">
              <div className="editor-section-header">
                <h3>Projetos Selecionados (máx. 3)</h3>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={addProject}
                  disabled={(resume.projects || []).length >= 3}
                >
                  <Plus size={13} />
                  Adicionar
                </button>
              </div>
              <div className="editor-stack">
                {(resume.projects || []).map((proj, idx) => (
                  <div key={idx} className="editor-card">
                    <div className="editor-card-head">
                      <strong>Projeto #{idx + 1}</strong>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => removeProject(idx)}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                    <div className="editor-grid">
                      <label>
                        Título
                        <input
                          type="text"
                          value={proj.title}
                          onChange={(e) => updateProject(idx, { title: e.target.value })}
                        />
                      </label>
                      <label>
                        Tecnologias (separadas por vírgula)
                        <input
                          type="text"
                          value={(proj.technologies || []).join(', ')}
                          onChange={(e) =>
                            updateProject(idx, {
                              technologies: e.target.value
                                .split(',')
                                .map((t) => t.trim())
                                .filter(Boolean),
                            })
                          }
                        />
                      </label>
                      <label>
                        Status
                        <select
                          value={proj.status || ''}
                          onChange={(e) =>
                            updateProject(idx, { status: e.target.value || null })
                          }
                        >
                          <option value="">Concluído / Padrão</option>
                          <option value="in_development">Em desenvolvimento</option>
                        </select>
                      </label>
                    </div>
                    <label>
                      Descrição
                      <textarea
                        rows={2}
                        className="editor-textarea"
                        value={proj.description}
                        onChange={(e) => updateProject(idx, { description: e.target.value })}
                      />
                    </label>
                  </div>
                ))}
              </div>
            </div>

            <div className="cv-section">
              <h3>Formação Acadêmica</h3>
              <div className="editor-stack">
                {(resume.education || []).map((edu, idx) => (
                  <div key={idx} className="editor-grid">
                    <label>
                      Curso
                      <input
                        type="text"
                        value={edu.degree}
                        onChange={(e) => updateEducation(idx, { degree: e.target.value })}
                      />
                    </label>
                    <label>
                      Instituição
                      <input
                        type="text"
                        value={edu.institution}
                        onChange={(e) => updateEducation(idx, { institution: e.target.value })}
                      />
                    </label>
                    <label>
                      Período / Previsão
                      <input
                        type="text"
                        value={edu.period}
                        onChange={(e) => updateEducation(idx, { period: e.target.value })}
                      />
                    </label>
                  </div>
                ))}
              </div>
            </div>

            <StringListEditor
              label="Pesquisa e Apresentações"
              items={resume.research || []}
              onChange={(next) => updateField('research', next)}
              placeholder="Descrição da pesquisa/apresentação..."
            />

            <StringListEditor
              label="Idiomas"
              items={resume.languages || []}
              onChange={(next) => updateField('languages', next)}
              placeholder="Idioma (Nível)"
            />
          </article>
        ) : viewMode === 'document' ? (
          <article className="a4-sheet">
            <header className="cv-header">
              <h1>{resume.candidate.name}</h1>
              <p className="cv-headline">{resume.candidate.headline}</p>
              <div className="cv-contact-row">
                <span>
                  <Mail size={13} />
                  {resume.candidate.email}
                </span>
                <span>
                  <Phone size={13} />
                  {resume.candidate.phone}
                </span>
                <span>
                  <MapPin size={13} />
                  {resume.candidate.location}
                </span>
                <span>
                  <Globe size={13} />
                  {resume.candidate.linkedin}
                </span>
                {resume.candidate.github && (
                  <span>
                    <Globe size={13} />
                    {resume.candidate.github}
                  </span>
                )}
              </div>
            </header>

            <div className="cv-section">
              <h3>Perfil Profissional</h3>
              <p className="cv-paragraph">{resume.summary}</p>
            </div>

            {resume.skills?.length > 0 && (
              <div className="cv-section">
                <h3>Competências Técnicas</h3>
                <div className="cv-tags">
                  {resume.skills.map((skill, idx) => (
                    <span key={`${skill}-${idx}`} className="cv-tag">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="cv-section">
              <h3>Experiência Profissional</h3>
              <div className="cv-list">
                {resume.experiences.map((exp, idx) => (
                  <div key={idx} className="cv-item">
                    <div className="cv-item-header">
                      <div>
                        <strong>{exp.role}</strong>
                        <span className="cv-company"> — {exp.company}</span>
                      </div>
                      <span className="cv-period">
                        {exp.period}
                        {exp.location ? ` · ${exp.location}` : ''}
                      </span>
                    </div>
                    <ul className="cv-bullets">
                      {exp.highlights.map((bullet, bIdx) => (
                        <li key={bIdx}>{bullet}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>

            {resume.projects?.length > 0 && (
              <div className="cv-section">
                <h3>Projetos Selecionados</h3>
                <div className="cv-list">
                  {resume.projects.map((proj, idx) => (
                    <div key={`${proj.title}-${idx}`} className="cv-item">
                      <div className="cv-item-header">
                        <div>
                          <strong>{proj.title}</strong>
                          {proj.technologies?.length > 0 && (
                            <span className="cv-company">
                              {' '}
                              | {proj.technologies.join(' · ')}
                            </span>
                          )}
                        </div>
                        {proj.status === 'in_development' && (
                          <span className="cv-period">em desenvolvimento</span>
                        )}
                      </div>
                      <ul className="cv-bullets">
                        <li>{proj.description}</li>
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="cv-section">
              <h3>Formação Acadêmica</h3>
              <div className="cv-list">
                {resume.education.map((edu, idx) => (
                  <div key={idx} className="cv-item-header">
                    <div>
                      <strong>{edu.degree}</strong>
                      <span className="cv-company"> — {edu.institution}</span>
                    </div>
                    <span className="cv-period">{edu.period}</span>
                  </div>
                ))}
              </div>
            </div>

            {resume.research?.length > 0 && (
              <div className="cv-section">
                <h3>Pesquisa e Apresentações</h3>
                <ul className="cv-bullets">
                  {resume.research.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="cv-section">
              <h3>Idiomas</h3>
              <ul className="cv-bullets">
                {resume.languages.map((lang, idx) => (
                  <li key={`${lang}-${idx}`}>{lang}</li>
                ))}
              </ul>
            </div>
          </article>
        ) : (
          <div className="json-viewer">
            <div className="json-viewer-bar">
              <span>Payload estruturado retornado pelo agente (CrewAI)</span>
              <button type="button" className="btn btn-secondary btn-sm" onClick={handleCopyJson}>
                {copied ? <Check size={13} /> : <Copy size={13} />}
                {copied ? 'Copiado' : 'Copiar JSON'}
              </button>
            </div>
            <pre>{JSON.stringify(resume, null, 2)}</pre>
          </div>
        )}
      </div>
    </section>
  );
}
