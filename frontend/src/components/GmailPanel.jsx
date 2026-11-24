import { useState } from 'react';
import {
  Inbox,
  Send,
  RefreshCw,
  Search,
  ArrowLeft,
  MailOpen,
  Mail,
  Link2,
} from 'lucide-react';

export function GmailPanel({
  emails,
  gmailConnected,
  isLoading,
  onConnectGmail,
  onRefresh,
  onMarkRead,
}) {
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [selectedEmailId, setSelectedEmailId] = useState(null);

  const filteredEmails = emails.filter((mail) => {
    const matchesFilter = filter === 'all' || mail.direction === filter;
    const term = search.toLowerCase();
    const matchesSearch =
      !term ||
      mail.subject.toLowerCase().includes(term) ||
      mail.from.toLowerCase().includes(term) ||
      mail.to.toLowerCase().includes(term) ||
      mail.snippet.toLowerCase().includes(term);
    return matchesFilter && matchesSearch;
  });

  const selectedEmail = emails.find((e) => e.id === selectedEmailId);

  const handleOpenEmail = (mail) => {
    setSelectedEmailId(mail.id);
    if (mail.unread) {
      onMarkRead(mail.id);
    }
  };

  if (selectedEmail) {
    return (
      <div className="tab-pane gmail-pane">
        <div className="pane-header">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setSelectedEmailId(null)}
          >
            <ArrowLeft size={14} />
            Voltar
          </button>
          <span className={`gmail-status-dot ${gmailConnected ? 'connected' : 'disconnected'}`}>
            {gmailConnected ? 'Gmail Conectado' : 'Modo Local'}
          </span>
        </div>

        <div className="email-detail">
          <h4>{selectedEmail.subject}</h4>
          <div className="email-detail-meta">
            <div>
              <strong>De:</strong> {selectedEmail.from}
            </div>
            <div>
              <strong>Para:</strong> {selectedEmail.to}
            </div>
            <div>
              <strong>Data:</strong> {selectedEmail.date}
            </div>
          </div>
          <div className="email-detail-body">{selectedEmail.body}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="tab-pane gmail-pane">
      <div className="pane-header">
        <div>
          <h3>Mensagens Gmail</h3>
          <p>{gmailConnected ? 'Conectado via OAuth2' : 'Aguardando conexão OAuth2'}</p>
        </div>
        <div className="pane-actions-row">
          {!gmailConnected && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={onConnectGmail}
            >
              <Link2 size={13} />
              Conectar
            </button>
          )}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onRefresh}
            disabled={isLoading}
            title="Sincronizar com Gmail API"
          >
            <RefreshCw size={13} className={isLoading ? 'spin' : ''} />
            Atualizar
          </button>
        </div>
      </div>

      <div className="gmail-controls">
        <div className="search-box">
          <Search size={14} />
          <input
            type="text"
            placeholder="Buscar assunto ou remetente..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="filter-pills">
          <button
            type="button"
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            Todos
          </button>
          <button
            type="button"
            className={filter === 'received' ? 'active' : ''}
            onClick={() => setFilter('received')}
          >
            <Inbox size={12} />
            Recebidos
          </button>
          <button
            type="button"
            className={filter === 'sent' ? 'active' : ''}
            onClick={() => setFilter('sent')}
          >
            <Send size={12} />
            Enviados
          </button>
        </div>
      </div>

      <div className="list-scroll">
        {!gmailConnected ? (
          <div className="empty-state">
            <p>Gmail ainda não conectado.</p>
            <button type="button" className="btn btn-primary btn-sm" onClick={onConnectGmail}>
              <Link2 size={13} />
              Autorizar acesso ao Gmail
            </button>
          </div>
        ) : filteredEmails.length === 0 ? (
          <div className="empty-state">Nenhuma mensagem encontrada.</div>
        ) : (
          filteredEmails.map((mail) => (
            <button
              key={mail.id}
              type="button"
              className={`email-card ${mail.unread ? 'unread' : ''}`}
              onClick={() => handleOpenEmail(mail)}
            >
              <div className="email-card-top">
                <span className="email-sender">
                  {mail.unread ? <Mail size={13} /> : <MailOpen size={13} />}
                  {mail.direction === 'sent' ? `Para: ${mail.to}` : mail.from}
                </span>
                <span className="email-date">{mail.date}</span>
              </div>
              <div className="email-subject">{mail.subject}</div>
              <div className="email-snippet">{mail.snippet}</div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
