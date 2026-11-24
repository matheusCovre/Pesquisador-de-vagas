import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, FileEdit } from 'lucide-react';

const QUICK_PROMPTS = [
  'Adaptar resumo para vaga de Backend FastAPI',
  'Pesquisar cultura da empresa via Tavily',
  'Destacar projetos com CrewAI e PDF/Word',
];

export function ChatPanel({
  messages,
  onSendMessage,
  isThinking,
  onOpenDraftInEditor,
}) {
  const [input, setInput] = useState('');
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isThinking) return;
    onSendMessage(trimmed);
    setInput('');
  };

  return (
    <div className="tab-pane chat-pane">
      <div className="pane-header">
        <div>
          <h3>Chat com Agentes (CrewAI)</h3>
          <p>Pesquisa de vagas, revisão e estruturação em tempo real</p>
        </div>
      </div>

      <div className="quick-prompts">
        {QUICK_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className="chip-btn"
            onClick={() => onSendMessage(prompt)}
            disabled={isThinking}
          >
            <Sparkles size={12} />
            {prompt}
          </button>
        ))}
      </div>

      <div className="chat-messages">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`chat-bubble-row ${msg.sender === 'user' ? 'is-user' : 'is-assistant'}`}
          >
            <div className="chat-avatar">
              {msg.sender === 'user' ? <User size={15} /> : <Bot size={15} />}
            </div>
            <div className="chat-bubble">
              <p>{msg.text}</p>
              {msg.blocked && onOpenDraftInEditor && (
                <div className="chat-draft-actions">
                  {msg.verificationIssues?.length > 0 && (
                    <div className="chat-issues-list">
                      {msg.verificationIssues.map((iss, idx) => (
                        <span key={`${iss.code}-${idx}`} className="issue-pill">
                          {iss.code} ({iss.field})
                        </span>
                      ))}
                    </div>
                  )}
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() =>
                      onOpenDraftInEditor(msg.draftResume || null, msg.verificationIssues || [])
                    }
                  >
                    <FileEdit size={13} />
                    {msg.draftResume
                      ? 'Ver e Editar Rascunho no Documento'
                      : 'Editar Documento Atual'}
                  </button>
                </div>
              )}
              <span className="chat-time">{msg.time}</span>
            </div>
          </div>
        ))}

        {isThinking && (
          <div className="chat-bubble-row is-assistant">
            <div className="chat-avatar">
              <Bot size={15} />
            </div>
            <div className="chat-bubble thinking">
              Agente pesquisando e estruturando resposta...
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Descreva a vaga, peça pesquisa ou ajuste no currículo..."
          disabled={isThinking}
        />
        <button type="submit" className="btn btn-primary" disabled={!input.trim() || isThinking}>
          <Send size={15} />
        </button>
      </form>
    </div>
  );
}
