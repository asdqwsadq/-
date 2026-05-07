const API_BASE = '/api/v1';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  const payload = (await response.json()) as { data?: T };
  return (payload.data ?? payload) as T;
}

export function getOverview() {
  return request<Record<string, unknown>>('/管理/概览');
}

export function getDatabaseStatus() {
  return request<Record<string, unknown>>('/管理/数据库');
}

export function getSessions() {
  return request<{ items: Array<Record<string, unknown>>; total: number }>('/管理/会话');
}

export function getDocuments() {
  return request<{ items: Array<Record<string, unknown>>; total: number }>('/管理/文档');
}

export function getAgentConfig() {
  return request<Record<string, unknown>>('/智能体/kongming/配置');
}

export function updateAgentConfig(payload: Record<string, unknown>) {
  return request<Record<string, unknown>>('/智能体/kongming/配置', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function uploadDocument(payload: Record<string, unknown>) {
  return request<Record<string, unknown>>('/知识库/文档', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}


export function rebuildKnowledge() {
  return request<Record<string, unknown>>('/知识库/重建', {
    method: 'POST',
  });
}

export function getKnowledgeRebuildJob(jobId: string) {
  return request<Record<string, unknown>>(`/知识库/重建/${jobId}`);
}
