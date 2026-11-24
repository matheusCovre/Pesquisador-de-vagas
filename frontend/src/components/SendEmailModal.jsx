import { useState } from 'react';
import { X, Send } from 'lucide-react';

export function SendEmailModal({ resume, onClose, onConfirmSend }) {
  const [recipientName, setRecipientName] = useState('Recrutamento');
  const [recipientEmail, setRecipientEmail] = useState('');
  const [company, setCompany] = useState(resume.targetCompany || '');
  const [subject, setSubject] = useState(
    `Candidatura — ${resume.targetRole} (${resume.candidate.name})`
  );
  const [format, setFormat] = useState('PDF');
  const [reviewed, setReviewed] = useState(false);
  const [body, setBody] = useState(
    `Olá,\n\nSegue em anexo meu currículo em ${format} estruturado para a vaga de ${resume.targetRole}.\n\nAtenciosamente,\n${resume.candidate.name}`
  );

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!recipientEmail.trim() || !reviewed) return;
    onConfirmSend({
      recipientName: recipientName.trim() || recipientEmail,
      recipientEmail: recipientEmail.trim(),
      company: company.trim() || 'Empresa',
      subject: subject.trim(),
      format,
      body,
      reviewed_by_user: reviewed,
    });
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        <div className="modal-header">
          <h3>Enviar Currículo via Gmail</h3>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Fechar">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-row">
            <label>
              Nome do Destinatário
              <input
                type="text"
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
                placeholder="Ex: Ana Paula (RH)"
              />
            </label>
            <label>
              Empresa
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="Ex: TechNova"
              />
            </label>
          </div>

          <div className="form-row">
            <label>
              E-mail de Destino *
              <input
                type="email"
                required
                value={recipientEmail}
                onChange={(e) => setRecipientEmail(e.target.value)}
                placeholder="recrutamento@empresa.com"
              />
            </label>
            <label>
              Formato do Anexo
              <select value={format} onChange={(e) => setFormat(e.target.value)}>
                <option value="PDF">PDF (.pdf)</option>
                <option value="DOCX">Word (.docx)</option>
              </select>
            </label>
          </div>

          <label>
            Assunto
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </label>

          <label>
            Mensagem
            <textarea
              rows={5}
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
          </label>

          <label className="checkbox-row">
            <input type="checkbox" required checked={reviewed}
              onChange={(e) => setReviewed(e.target.checked)} />
            <span>Revisei o currículo, a mensagem e o destinatário e autorizo o envio.</span>
          </label>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={!reviewed}>
              <Send size={15} />
              Enviar Agora
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
