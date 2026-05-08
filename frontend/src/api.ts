type Json = Record<string, unknown>;

const API_BASE = '/kongming/api/v1';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  const payload = (await response.json()) as { data?: T; code?: number; message?: string };
  return (payload.data ?? payload) as T;
}

export async function createSession() {
  return request<{ session_id: string }>('/智能体/kongming/会话', {
    method: 'POST',
    body: JSON.stringify({ 标题: '四大名著问答', 元数据: { scene: 'four_classics_chat' } }),
  });
}

export async function getSession(sessionId: string) {
  return request<{ session_id: string; session_title?: string; summary?: string; status?: string; metadata?: Json }>(`/会话/${sessionId}`);
}

export async function getMessages(sessionId: string) {
  return request<{ session_id: string; items: Array<{ message_id: string; role: 'user' | 'assistant'; content: string; source_type?: string; source_refs?: Array<{ doc_title: string; excerpt: string; score: number }> }>; total: number }>(
    `/会话/${sessionId}/消息`,
  );
}

export async function sendMessage(sessionId: string, content: string) {
  return request<{ answer: string; sources: Array<{ doc_title: string; excerpt: string; score: number }>; usage: Json }>(
    `/会话/${sessionId}/消息`,
    {
      method: 'POST',
      body: JSON.stringify({ 内容: content, 流式: false, 选项: { top_k: 4, use_rag: true } }),
    },
  );
}

export async function* sendMessageStream(
  sessionId: string,
  content: string,
): AsyncGenerator<
  | { type: 'chunk'; content: string }
  | { type: 'done'; sources: Array<{ doc_title: string; excerpt: string; score: number }>; usage: Json }
  | { type: 'error'; message: string }
> {
  const response = await fetch(`${API_BASE}/会话/${sessionId}/消息`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 内容: content, 流式: true, 选项: { top_k: 4, use_rag: true } }),
  });

  if (!response.ok) {
    const text = await response.text();
    yield { type: 'error', message: text || response.statusText };
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    yield { type: 'error', message: '浏览器不支持流式响应' };
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events from buffer
    const lines = buffer.split('\n');
    // Keep the last incomplete line in the buffer
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        const parsed: { type: string; payload: unknown } = JSON.parse(line.slice(6));
        if (parsed.type === 'chunk' && typeof parsed.payload === 'string') {
          yield { type: 'chunk', content: parsed.payload };
        } else if (parsed.type === 'done') {
          const p = parsed.payload as { sources: Array<{ doc_title: string; excerpt: string; score: number }>; usage: Json };
          yield { type: 'done', sources: p.sources, usage: p.usage };
        } else if (parsed.type === 'error') {
          const p = parsed.payload as { message: string };
          yield { type: 'error', message: p.message };
        }
      } catch {
        // Skip malformed lines
      }
    }
  }

  // Process remaining buffer
  if (buffer.startsWith('data: ')) {
    try {
      const parsed: { type: string; payload: unknown } = JSON.parse(buffer.slice(6));
      if (parsed.type === 'chunk' && typeof parsed.payload === 'string') {
        yield { type: 'chunk', content: parsed.payload };
      } else if (parsed.type === 'done') {
        const p = parsed.payload as { sources: Array<{ doc_title: string; excerpt: string; score: number }>; usage: Json };
        yield { type: 'done', sources: p.sources, usage: p.usage };
      } else if (parsed.type === 'error') {
        const p = parsed.payload as { message: string };
        yield { type: 'error', message: p.message };
      }
    } catch {
      // Skip malformed
    }
  }
}

export async function searchKnowledge(query: string) {
  return request<{ query: string; results: Array<{ doc_title: string; excerpt: string; score: number }> }>(
    `/知识库/检索?${new URLSearchParams({ 问题: query, 数量: '4' }).toString()}`,
  );
}

export async function getDiagnostics() {
  return request<Record<string, unknown>>('/知识库/诊断');
}
