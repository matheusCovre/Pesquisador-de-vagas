import { Clock, Mail, FileText, CheckCircle2, Eye, RefreshCw } from 'lucide-react';

const STATUS_LABELS = {
  enviado_sem_resposta: 'Enviado',
  enviado_com_resposta: 'Respondido',
  confirmacao: 'Confirmado',
  entrevista: 'Entrevista',
  rejeicao: 'Rejeitado',
  aprovacao: 'Aprovado',
  cancelamento: 'Cancelado',
};

export function HistoryPanel({ history, activeResumeId, onSelectHistory, onRefresh, isLoading }) {
  return (
    <div className="tab-pane history-pane">
      <div className="pane-header">
        <div>
          <h3>Histórico de Envios</h3>
          <p>Últimas candidaturas registradas no Supabase</p>
        </div>
        <div className="pane-actions-row">
          <span className="count-pill">{history.length}</span>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onRefresh}
            disabled={isLoading}
            title="Atualizar histórico do Supabase"
          >
            <RefreshCw size={13} className={isLoading ? 'spin' : ''} />
          </button>
        </div>
      </div>

      <div className="list-scroll">
        {history.length === 0 ? (
          <div className="empty-state">
            Nenhuma candidatura registrada no Supabase ainda.
          </div>
        ) : (
          history.map((item) => {
            const isSelected = item.resumeData?.id && item.resumeData.id === activeResumeId;
            const statusText = STATUS_LABELS[item.status] || item.status;
            const statusClass = statusText.toLowerCase().replace(/[^a-z0-9]/g, '');

            return (
              <button
                key={item.id}
                type="button"
                className={`history-card ${isSelected ? 'selected' : ''}`}
                onClick={() => onSelectHistory(item)}
              >
                <div className="history-card-top">
                  <span className="history-title">
                    <FileText size={14} />
                    {item.resumeTitle}
                  </span>
                  <span className={`status-badge status-${statusClass}`}>
                    {statusText === 'Visualizado' || statusText === 'Respondido' ? (
                      <Eye size={11} />
                    ) : (
                      <CheckCircle2 size={11} />
                    )}
                    {statusText}
                  </span>
                </div>

                <div className="history-recipient">
                  <strong>Empresa:</strong> {item.company}
                  {item.recipientName ? ` · ${item.recipientName}` : ''}
                </div>

                {item.recipientEmail && (
                  <div className="history-email">
                    <Mail size={12} />
                    {item.recipientEmail}
                  </div>
                )}

                <div className="history-card-footer">
                  <span>
                    <Clock size={12} />
                    {item.sentAt}
                  </span>
                  <span className="format-badge">{item.format}</span>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
