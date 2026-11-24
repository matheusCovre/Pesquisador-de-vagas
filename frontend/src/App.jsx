import { useEffect, useState } from 'react';
import {
  FileText,
  MessageSquare,
  History,
  Mail,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Search,
} from 'lucide-react';
import {
  INITIAL_RESUME,
  INITIAL_CHAT_MESSAGES,
} from './data/mockData';
import {
  DEFAULT_JOB_AREAS,
  exportResumeFile,
  getGmailAuthUrl,
  getGmailMessages,
  getGmailStatus,
  getHealth,
  getHistory,
  getStarterResume,
  searchJobs,
  sendChatMessage,
  sendGmailResume,
  uploadResumeToDrive,
  verifyResume,
} from './lib/api';
import { ResumeViewer } from './components/ResumeViewer';
import { ChatPanel } from './components/ChatPanel';
import { JobsPanel } from './components/JobsPanel';
import { HistoryPanel } from './components/HistoryPanel';
import { GmailPanel } from './components/GmailPanel';
import { SendEmailModal } from './components/SendEmailModal';
import './App.css';

function mapCandidaturaToHistoryItem(item) {
  const vaga = item.vagas || {};
  const empresa = vaga.empresas || {};
  const curriculo = item.curriculos_gerados || {};
  const format = curriculo.arquivo_pdf_id
    ? 'PDF'
    : curriculo.arquivo_docx_id
      ? 'DOCX'
      : 'PDF';

  return {
    id: item.id,
    resumeTitle: vaga.titulo || 'Currículo gerado',
    recipientName: curriculo.modelos_curriculo?.nome
      ? `Modelo: ${curriculo.modelos_curriculo.nome}`
      : '',
    recipientEmail: item.comprovante_id ? `Comprovante: ${item.comprovante_id}` : '',
    company: empresa.nome || 'Empresa não informada',
    sentAt: item.data_candidatura
      ? new Date(item.data_candidatura).toLocaleString('pt-BR', {
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      : '',
    format,
    status: item.status_atual || 'enviado_sem_resposta',
    resumeData: null,
  };
}

function App() {
  const [activeResume, setActiveResume] = useState(INITIAL_RESUME);
  const [history, setHistory] = useState([]);
  const [emails, setEmails] = useState([]);
  const [chatMessages, setChatMessages] = useState(INITIAL_CHAT_MESSAGES);
  const [activeTab, setActiveTab] = useState('chat');
  const [isThinking, setIsThinking] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isLoadingGmail, setIsLoadingGmail] = useState(false);
  const [isSavingDrive, setIsSavingDrive] = useState(false);
  const [isSearchingJobs, setIsSearchingJobs] = useState(false);
  const [isEditingResume, setIsEditingResume] = useState(false);
  const [isVerifyingResume, setIsVerifyingResume] = useState(false);
  const [verificationState, setVerificationState] = useState(null);
  const [selectedAreas, setSelectedAreas] = useState(DEFAULT_JOB_AREAS);
  const [customJobQuery, setCustomJobQuery] = useState('');
  const [jobResults, setJobResults] = useState(null);
  const [isSendModalOpen, setIsSendModalOpen] = useState(false);
  const [apiOnline, setApiOnline] = useState(false);
  const [supabaseOk, setSupabaseOk] = useState(false);
  const [gmailConnected, setGmailConnected] = useState(false);
  const [toast, setToast] = useState(null);

  const unreadCount = emails.filter((e) => e.unread).length;

  const showToast = (message, isError = false) => {
    setToast({ message, isError });
    setTimeout(() => setToast(null), 3500);
  };

  const refreshHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const data = await getHistory(20);
      const mapped = (data.items || []).map(mapCandidaturaToHistoryItem);
      setHistory(mapped);
    } catch (err) {
      showToast(err.message, true);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const refreshGmail = async () => {
    setIsLoadingGmail(true);
    try {
      const statusData = await getGmailStatus();
      setGmailConnected(Boolean(statusData.connected));
      if (statusData.connected) {
        const msgData = await getGmailMessages(15);
        setEmails(msgData.messages || []);
      } else {
        setEmails([]);
      }
    } catch (err) {
      showToast(err.message, true);
    } finally {
      setIsLoadingGmail(false);
    }
  };

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const health = await getHealth();
        setApiOnline(health.status === 'ok');
        setSupabaseOk(Boolean(health.env?.supabase_configured));
      } catch {
        setApiOnline(false);
      }

      try {
        const starter = await getStarterResume();
        setActiveResume(starter);
      } catch {
        // Mantém fallback local se o backend ainda estiver subindo.
      }

      await Promise.all([refreshHistory(), refreshGmail()]);

      const params = new URLSearchParams(window.location.search);
      if (params.get('gmail') === 'connected') {
        showToast('Gmail conectado com sucesso via OAuth2!');
        window.history.replaceState({}, '', window.location.pathname);
      }
    };

    bootstrap();
  }, []);

  const handleSendChatMessage = async (text, useSearch = true) => {
    const now = new Date().toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
    });

    setChatMessages((prev) => [
      ...prev,
      { id: `msg-${Date.now()}`, sender: 'user', time: now, text },
    ]);
    setIsThinking(true);

    try {
      const result = await sendChatMessage(text, activeResume, useSearch);
      if (result.updated_resume) {
        setActiveResume(result.updated_resume);
        setVerificationState({ status: 'approved', issues: [] });
        setIsEditingResume(false);
      } else if (result.blocked) {
        setVerificationState({
          status: 'blocked',
          issues: result.verification_issues || [],
        });
      }

      const extras = [];
      if (result.generated_files?.pdf_id) extras.push(`PDF: ${result.generated_files.pdf_id}`);
      if (result.generated_files?.docx_id) extras.push(`DOCX: ${result.generated_files.docx_id}`);
      const fullReply = extras.length
        ? `${result.reply}\n\nArquivos gerados: ${extras.join(' | ')}`
        : result.reply;

      setChatMessages((prev) => [
        ...prev,
        {
          id: `msg-${Date.now() + 1}`,
          sender: 'assistant',
          time: new Date().toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit',
          }),
          text: fullReply,
          blocked: Boolean(result.blocked),
          draftResume: result.draft_resume || null,
          verificationIssues: result.verification_issues || [],
        },
      ]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: `msg-${Date.now() + 1}`,
          sender: 'assistant',
          time: new Date().toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit',
          }),
          text: `Bloqueio/Erro: ${err.message}`,
          blocked: err.status === 422,
          verificationIssues: err.issues || [],
        },
      ]);
      if (err.status === 422) {
        setVerificationState({ status: 'blocked', issues: err.issues || [] });
      }
      showToast(err.message, true);
    } finally {
      setIsThinking(false);
    }
  };

  const handleOpenDraftInEditor = (draftResume, issues = []) => {
    if (draftResume) {
      setActiveResume(draftResume);
    }
    setVerificationState({ status: 'blocked', issues });
    setIsEditingResume(true);
    showToast('Rascunho aberto no editor de documento.');
  };

  const handleChangeResume = (nextResume) => {
    setActiveResume(nextResume);
    if (verificationState?.status === 'approved') {
      setVerificationState(null);
    }
  };

  const handleVerifyResume = async () => {
    setIsVerifyingResume(true);
    try {
      const report = await verifyResume(activeResume);
      setVerificationState({
        status: report.status,
        issues: report.issues || [],
      });
      if (report.status === 'approved') {
        showToast('Documento aprovado na verificação contra a base local.');
      } else {
        showToast('Documento bloqueado. Revise os campos indicados.', true);
      }
    } catch (err) {
      showToast(err.message, true);
    } finally {
      setIsVerifyingResume(false);
    }
  };

  const handleSelectHistory = (historyItem) => {
    if (historyItem.resumeData) {
      setActiveResume(historyItem.resumeData);
      showToast(`Currículo "${historyItem.resumeTitle}" carregado.`);
    } else {
      showToast(`Candidatura em ${historyItem.company} (${historyItem.status}).`);
    }
  };

  const handleDownload = async (format) => {
    try {
      const { documentId } = await exportResumeFile(activeResume, format);
      showToast(`Arquivo ${format} gerado e baixado (${documentId}).`);
    } catch (err) {
      showToast(err.message, true);
    }
  };

  const handleSaveToDrive = async () => {
    setIsSavingDrive(true);
    try {
      const result = await uploadResumeToDrive(activeResume, 'pdf');
      const fileName = result?.drive?.name || 'Currículo PDF';
      showToast(`Salvo no Google Drive: ${fileName}`);
    } catch (err) {
      showToast(err.message, true);
    } finally {
      setIsSavingDrive(false);
    }
  };

  const handleConnectGmail = async () => {
    try {
      const data = await getGmailAuthUrl();
      if (data.auth_url) {
        window.open(data.auth_url, '_blank', 'noopener,noreferrer');
        showToast('Autorize o Gmail na janela aberta e clique em Atualizar.');
      }
    } catch (err) {
      showToast(err.message, true);
    }
  };

  const handleConfirmSendEmail = async (payload) => {
    try {
      await sendGmailResume({
        ...payload,
        resume: activeResume,
      });
      setIsSendModalOpen(false);
      showToast(`Currículo (${payload.format}) enviado via Gmail para ${payload.recipientEmail}!`);
      await Promise.all([refreshHistory(), refreshGmail()]);
    } catch (err) {
      showToast(err.message, true);
    }
  };

  const handleMarkEmailRead = (emailId) => {
    setEmails((prev) =>
      prev.map((m) => (m.id === emailId ? { ...m, unread: false } : m))
    );
  };

  const handleToggleArea = (area) => {
    setSelectedAreas((prev) => {
      if (prev.includes(area)) {
        return prev.length > 1 ? prev.filter((item) => item !== area) : prev;
      }
      return [...prev, area];
    });
  };

  const handleSearchJobs = async () => {
    setActiveTab('jobs');
    setIsSearchingJobs(true);
    try {
      const data = await searchJobs({
        areas: selectedAreas,
        customQuery: customJobQuery,
      });
      setJobResults(data);
      const count = data.jobs?.length || 0;
      showToast(
        count > 0
          ? `${count} vaga(s) estruturada(s) encontrada(s) na pesquisa.`
          : 'Pesquisa de vagas concluída. Confira o relatório auditado.'
      );
    } catch (err) {
      showToast(err.message, true);
    } finally {
      setIsSearchingJobs(false);
    }
  };

  const handleAdaptResumeForJob = async (job) => {
    setActiveTab('chat');
    const details = [
      `Adaptar o currículo para a vaga "${job.title}" na empresa "${job.company || 'Não informada'}"`,
      job.seniority ? `Senioridade: ${job.seniority}` : '',
      job.modality ? `Modalidade: ${job.modality}` : '',
      job.url ? `URL: ${job.url}` : '',
      job.justification ? `Contexto da auditoria: ${job.justification}` : '',
    ]
      .filter(Boolean)
      .join(' | ');
    await handleSendChatMessage(details, false);
  };

  const handleAdaptFromReport = async (report) => {
    setActiveTab('chat');
    const summary = report.slice(0, 1200);
    await handleSendChatMessage(
      `Adaptar o currículo com base nas vagas elegíveis encontradas:\n\n${summary}`,
      false
    );
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            <FileText size={18} />
          </div>
          <div>
            <h1>Pesquisador de Vagas</h1>
            <span>Pesquisa de vagas e adaptação de currículos</span>
          </div>
        </div>

        <div className="topbar-status">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={handleSearchJobs}
            disabled={isSearchingJobs}
            title="Pesquisar vagas em Software, Automações de IA, Automação Industrial e Robótica"
          >
            <Search size={14} className={isSearchingJobs ? 'spin' : ''} />
            {isSearchingJobs ? 'Pesquisando Vagas...' : 'Pesquisar Vagas'}
          </button>
          <span className={`pill-status ${apiOnline ? 'ok' : 'warn'}`}>
            <Sparkles size={13} />
            FastAPI: {apiOnline ? 'Online' : 'Offline'}
          </span>
          <span className={`pill-status ${supabaseOk ? 'ok' : ''}`}>
            Supabase: {supabaseOk ? 'Conectado' : 'Local'}
          </span>
          <span className={`pill-status ${gmailConnected ? 'ok' : ''}`}>
            Gmail: {gmailConnected ? 'Conectado' : 'Não autenticado'}
          </span>
        </div>
      </header>

      <main className="workspace-grid">
        <ResumeViewer
          resume={activeResume}
          onChangeResume={handleChangeResume}
          isEditing={isEditingResume}
          onToggleEdit={() => setIsEditingResume((prev) => !prev)}
          onVerifyResume={handleVerifyResume}
          isVerifying={isVerifyingResume}
          verificationState={verificationState}
          onOpenSendModal={() => setIsSendModalOpen(true)}
          onDownload={handleDownload}
          onSaveToDrive={handleSaveToDrive}
          isSavingDrive={isSavingDrive}
        />

        <aside className="side-panel">
          <nav className="side-tabs" aria-label="Navegação lateral">
            <button
              type="button"
              className={activeTab === 'chat' ? 'active' : ''}
              onClick={() => setActiveTab('chat')}
            >
              <MessageSquare size={15} />
              Chat IA
            </button>
            <button
              type="button"
              className={activeTab === 'jobs' ? 'active' : ''}
              onClick={() => setActiveTab('jobs')}
            >
              <Search size={15} />
              Vagas
              {jobResults?.jobs?.length > 0 && (
                <span className="tab-badge">{jobResults.jobs.length}</span>
              )}
            </button>
            <button
              type="button"
              className={activeTab === 'history' ? 'active' : ''}
              onClick={() => setActiveTab('history')}
            >
              <History size={15} />
              Histórico
              <span className="tab-badge">{history.length}</span>
            </button>
            <button
              type="button"
              className={activeTab === 'gmail' ? 'active' : ''}
              onClick={() => setActiveTab('gmail')}
            >
              <Mail size={15} />
              E-mails
              {unreadCount > 0 && <span className="tab-badge alert">{unreadCount}</span>}
            </button>
          </nav>

          <div className="side-content">
            {activeTab === 'chat' && (
              <ChatPanel
                messages={chatMessages}
                onSendMessage={handleSendChatMessage}
                isThinking={isThinking}
                onOpenDraftInEditor={handleOpenDraftInEditor}
              />
            )}

            {activeTab === 'jobs' && (
              <JobsPanel
                selectedAreas={selectedAreas}
                onToggleArea={handleToggleArea}
                customQuery={customJobQuery}
                onCustomQueryChange={setCustomJobQuery}
                onSearchJobs={handleSearchJobs}
                isSearching={isSearchingJobs}
                jobResults={jobResults}
                onAdaptResumeForJob={handleAdaptResumeForJob}
                onAdaptFromReport={handleAdaptFromReport}
              />
            )}

            {activeTab === 'history' && (
              <HistoryPanel
                history={history}
                activeResumeId={activeResume.id}
                onSelectHistory={handleSelectHistory}
                onRefresh={refreshHistory}
                isLoading={isLoadingHistory}
              />
            )}

            {activeTab === 'gmail' && (
              <GmailPanel
                emails={emails}
                gmailConnected={gmailConnected}
                isLoading={isLoadingGmail}
                onConnectGmail={handleConnectGmail}
                onRefresh={refreshGmail}
                onMarkRead={handleMarkEmailRead}
              />
            )}
          </div>
        </aside>
      </main>

      {isSendModalOpen && (
        <SendEmailModal
          resume={activeResume}
          onClose={() => setIsSendModalOpen(false)}
          onConfirmSend={handleConfirmSendEmail}
        />
      )}

      {toast && (
        <div className={`toast ${toast.isError ? 'toast-error' : ''}`} role="status">
          {toast.isError ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}
          <span>{toast.message}</span>
        </div>
      )}
    </div>
  );
}

export default App;
