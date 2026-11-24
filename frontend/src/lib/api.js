const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

async function parseErrorResponse(response) {
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (response.status === 422 && payload?.issues?.length) {
    const issueList = payload.issues.map((i) => `${i.code} (${i.field})`).join(', ');
    const err = new Error(`${payload.detail || 'Bloqueado pelo guardrail'}: ${issueList}`);
    err.status = 422;
    err.issues = payload.issues;
    return err;
  }

  const err = new Error(payload?.detail || `Erro HTTP ${response.status}`);
  err.status = response.status;
  return err;
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }
  return response.json();
}

export function getHealth() {
  return requestJson('/health');
}

export function getStarterResume() {
  return requestJson('/api/documents/starter');
}

export function verifyResume(resume) {
  return requestJson('/api/documents/verify', {
    method: 'POST',
    body: JSON.stringify(resume),
  });
}

export async function exportResumeFile(resume, format) {
  const normalizedFormat = format.toLowerCase();
  const response = await fetch(`${API_BASE}/api/documents/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ format: normalizedFormat, resume }),
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const blob = await response.blob();
  const documentId = response.headers.get('X-Document-Id') || `curriculo.${normalizedFormat}`;
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `curriculo.${normalizedFormat}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
  return { documentId };
}

export function sendChatMessage(message, resume, useSearch = true) {
  return requestJson('/api/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      resume,
      use_search: useSearch,
    }),
  });
}

export const DEFAULT_JOB_AREAS = [
  'Desenvolvimento de Software',
  'Automações de IA',
  'Automação Industrial',
  'Robótica',
];

export function searchJobs(payload = {}) {
  return requestJson('/api/jobs/search', {
    method: 'POST',
    body: JSON.stringify({
      areas: payload.areas,
      custom_query: payload.customQuery || '',
      seniority: payload.seniority,
      location: payload.location,
    }),
  });
}

export function getHistory(limit = 20) {
  return requestJson(`/api/history?limit=${limit}`);
}

export function getGmailStatus() {
  return requestJson('/api/gmail/status');
}

export function getGmailAuthUrl() {
  return requestJson('/api/gmail/auth-url');
}

export function getGmailMessages(limit = 15) {
  return requestJson(`/api/gmail/messages?limit=${limit}`);
}

export function sendGmailResume(payload) {
  return requestJson('/api/gmail/send', {
    method: 'POST',
    body: JSON.stringify({
      reviewed_by_user: Boolean(payload.reviewed_by_user),
      recipient_name: payload.recipientName || '',
      recipient_email: payload.recipientEmail,
      company: payload.company || '',
      subject: payload.subject,
      body: payload.body,
      format: (payload.format || 'pdf').toLowerCase(),
      resume: payload.resume,
    }),
  });
}

export function getDriveStatus() {
  return requestJson('/api/drive/status');
}

export function uploadResumeToDrive(resume, format = 'pdf') {
  return requestJson('/api/drive/upload', {
    method: 'POST',
    body: JSON.stringify({
      format: (format || 'pdf').toLowerCase(),
      resume,
    }),
  });
}
