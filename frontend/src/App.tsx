import { useEffect, useMemo, useRef, useState } from 'react';
import { createSession, getMessages, getSession, searchKnowledge, sendMessageStream } from './api';

type ChatSource = { doc_title: string; excerpt: string; score: number };
type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
};

const readingMap = [
  { title: '三国演义', prompt: '权谋、局势、人物决策', tone: '谋略' },
  { title: '红楼梦', prompt: '家族、情感、命运关系', tone: '情意' },
  { title: '西游记', prompt: '神魔、修行、秩序隐喻', tone: '修行' },
  { title: '水浒传', prompt: '江湖、群像、反抗逻辑', tone: '江湖' },
];

const welcomeMessage: ChatMessage = {
  role: 'assistant',
  content: '可直接提问四大名著中的人物、情节、主题或关系脉络。',
};

function compactSessionId(sessionId: string) {
  return sessionId ? `${sessionId.slice(0, 8)}...${sessionId.slice(-4)}` : '待创建';
}

function sourceKey(source: ChatSource, messageIndex: number, sourceIndex: number) {
  return `${messageIndex}-${sourceIndex}-${source.doc_title}-${source.score}`;
}

export default function App() {
  const [sessionId, setSessionId] = useState('');
  const [sessionTitle, setSessionTitle] = useState('四大名著问答');
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<ChatSource[]>([]);
  const [searching, setSearching] = useState(false);
  const [readyNote, setReadyNote] = useState('准备中');
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyMessages, setHistoryMessages] = useState<ChatMessage[]>([]);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const streamRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    async function bootstrap() {
      const cachedSessionId = window.localStorage.getItem('kongming_session_id') ?? '';

      if (cachedSessionId) {
        try {
          const session = await getSession(cachedSessionId);
          setSessionId(session.session_id);
          setSessionTitle(session.session_title || '四大名著问答');
          const history = await getMessages(cachedSessionId);
          const mappedHistory = history.items.map((item) => ({
            role: item.role,
            content: item.content,
            sources: item.source_refs,
          }));
          setHistoryMessages(mappedHistory);
          setMessages(mappedHistory.length ? mappedHistory.slice(-4) : [welcomeMessage]);
          setReadyNote('会话已恢复');
          return;
        } catch {
          window.localStorage.removeItem('kongming_session_id');
        }
      }

      try {
        const session = await createSession();
        window.localStorage.setItem('kongming_session_id', session.session_id);
        setSessionId(session.session_id);
        setSessionTitle('四大名著问答');
        setReadyNote('新会话已建立');
      } catch {
        window.localStorage.removeItem('kongming_session_id');
        setReadyNote('会话未建立');
      }
    }

    bootstrap().catch(() => setReadyNote('初始化失败'));
  }, []);

  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const canSend = useMemo(() => input.trim().length > 0 && !loading, [input, loading]);
  async function ensureSession() {
    if (sessionId) return sessionId;
    const session = await createSession();
    window.localStorage.setItem('kongming_session_id', session.session_id);
    setSessionId(session.session_id);
    setSessionTitle('四大名著问答');
    setReadyNote('新会话已建立');
    return session.session_id;
  }

  async function refreshSession() {
    if (!sessionId) return;
    const history = await getMessages(sessionId);
    const mappedHistory = history.items.map((item) => ({
      role: item.role,
      content: item.content,
      sources: item.source_refs,
    }));
    setHistoryMessages(mappedHistory);
    setMessages(mappedHistory.length ? mappedHistory.slice(-4) : [welcomeMessage]);
  }

  async function handleSend(raw: string) {
    const question = raw.trim();
    if (!question) return;

    setLoading(true);
    setInput('');
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: question },
      { role: 'assistant', content: '' },
    ]);

    let fullContent = '';
    let finalSources: ChatSource[] | undefined;

    try {
      const activeSessionId = await ensureSession();

      for await (const event of sendMessageStream(activeSessionId, question)) {
        if (event.type === 'chunk') {
          fullContent += event.content;
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = { ...next[next.length - 1], content: fullContent };
            return next;
          });
        } else if (event.type === 'done') {
          finalSources = event.sources;
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = { ...next[next.length - 1], sources: finalSources };
            return next;
          });
          const assistantMsg: ChatMessage = { role: 'assistant', content: fullContent, sources: finalSources };
          setHistoryMessages((prev) => [...prev, { role: 'user', content: question }, assistantMsg]);
        } else if (event.type === 'error') {
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = { ...next[next.length - 1], content: event.message };
            return next;
          });
        }
      }
    } catch {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { ...next[next.length - 1], content: '暂未拿到回答，请稍后再试。' };
        return next;
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch() {
    const query = searchQuery.trim();
    if (!query) return;
    setSearching(true);
    try {
      const data = await searchKnowledge(query);
      setSearchResults(data.results);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }

  function startNewSession() {
    window.localStorage.removeItem('kongming_session_id');
    setSessionId('');
    setHistoryMessages([]);
    setHistoryOpen(false);
    setExpandedSources(new Set());
    createSession()
      .then((data) => {
        window.localStorage.setItem('kongming_session_id', data.session_id);
        setSessionId(data.session_id);
        setSessionTitle('四大名著问答');
        setReadyNote('新会话已建立');
        setMessages([{ role: 'assistant', content: '新会话已建立。' }]);
      })
      .catch(() => setReadyNote('新会话创建失败'));
  }

  function toggleSource(key: string) {
    setExpandedSources((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  return (
    <div className="app-shell">
      <aside className="side-panel">
        <div className="brand">
          <div className="brand-mark">孔</div>
          <div>
            <p className="eyebrow">Kongming Agent</p>
            <h1>孔明问策</h1>
            <p>四大名著知识问答</p>
          </div>
        </div>

        <section className="panel session-panel">
          <div className="section-head">
            <h2>会话</h2>
            <span className="state-dot">{readyNote}</span>
          </div>
          <dl className="meta-list">
            <div>
              <dt>编号</dt>
              <dd title={sessionId}>{compactSessionId(sessionId)}</dd>
            </div>
            <div>
              <dt>主题</dt>
              <dd>{sessionTitle}</dd>
            </div>
          </dl>
        </section>

        <section className="panel">
          <div className="section-head">
            <h2>四书导览</h2>
            <button className="text-btn" onClick={() => refreshSession().catch(() => undefined)}>
              同步
            </button>
          </div>
          <div className="book-list">
            {readingMap.map((item) => (
              <button
                key={item.title}
                className="book-item"
                onClick={() => setInput(`请介绍《${item.title}》的${item.prompt}`)}
              >
                <span>{item.tone}</span>
                <strong>{item.title}</strong>
                <em>{item.prompt}</em>
              </button>
            ))}
          </div>
        </section>

      </aside>

      <main className="workspace">
        <section className="headline-panel">
          <div>
            <p className="eyebrow">Kongming Agent</p>
            <h2>四大名著知识问答</h2>
          </div>
          <div className="headline-metrics">
            <span>三国演义</span>
            <span>红楼梦</span>
            <span>西游记</span>
            <span>水浒传</span>
          </div>
        </section>

        <section className="main-grid">
          <section className="chat-panel">
            <div className="chat-head">
              <div>
                <h2>问答记录</h2>
                <p>{sessionId ? `会话 ${compactSessionId(sessionId)}` : '会话建立中'}</p>
              </div>
              <div className="toolbar">
                <button className="text-btn" onClick={() => setHistoryOpen(true)}>
                  历史
                </button>
                <button className="text-btn" onClick={startNewSession}>
                  新会话
                </button>
              </div>
            </div>

            <div className="message-stream" ref={streamRef}>
              {messages.map((item, messageIndex) => {
                const isPending = loading && item.role === 'assistant' && !item.content;
                return (
                <article key={`${item.role}-${messageIndex}`} className={`bubble ${item.role}${isPending ? ' pending' : ''}`}>
                  <div className="bubble-top">
                    <span>{item.role === 'user' ? '你' : '孔明'}</span>
                    {item.sources?.length ? <em>{item.sources.length} 条依据</em> : null}
                    {isPending ? <em>思考中</em> : null}
                  </div>
                  <div className="bubble-body">{item.content || '容我思忖片刻。'}</div>
                  {item.sources?.length ? (
                    <div className="source-list">
                      {item.sources.map((source, sourceIndex) => {
                        const key = sourceKey(source, messageIndex, sourceIndex);
                        const open = expandedSources.has(key);
                        return (
                          <button
                            key={key}
                            className={`source-row ${open ? 'open' : ''}`}
                            onClick={() => toggleSource(key)}
                          >
                            <span className="source-row-title">{source.doc_title}</span>
                            <span className="score-tag">{source.score.toFixed(2)}</span>
                            <span className="source-expand">{open ? '收起' : '展开'}</span>
                            <span className="source-excerpt">
                              {open
                                ? source.excerpt
                                : `${source.excerpt.slice(0, 36)}${source.excerpt.length > 36 ? '...' : ''}`}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  ) : null}
                </article>
                );
              })}
            </div>

            <div className="composer">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="输入问题，例如：孙悟空是谁？"
                onKeyDown={(e) => {
                  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                    e.preventDefault();
                    handleSend(input).catch(() => undefined);
                  }
                }}
              />
              <div className="composer-row">
                <button className="text-btn" onClick={() => setInput('')}>
                  清空
                </button>
                <button className="primary-btn" disabled={!canSend} onClick={() => handleSend(input)}>
                  {loading ? '回答中' : '发问'}
                </button>
              </div>
            </div>
          </section>

          <aside className="right-rail">
            <section className="search-panel">
              <div className="section-head">
                <h2>典籍检索</h2>
                <button className="text-btn" onClick={handleSearch} disabled={searching}>
                  {searching ? '检索中' : '检索'}
                </button>
              </div>
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="诸葛亮 / 林黛玉 / 孙悟空 / 林冲"
              />
              <div className="search-results">
                {searchResults.length ? (
                  searchResults.map((item, index) => (
                    <article key={`${item.doc_title}-${item.score}-${index}`} className="search-card">
                      <div>
                        <strong>{item.doc_title}</strong>
                        <span>{item.score.toFixed(2)}</span>
                      </div>
                      <p>{item.excerpt.slice(0, 86)}{item.excerpt.length > 86 ? '...' : ''}</p>
                    </article>
                  ))
                ) : (
                  <p className="empty-text">检索结果会显示在这里。</p>
                )}
              </div>
            </section>

            <section className="portrait-panel" aria-label="诸葛亮背景图">
              <div className="portrait-bg" aria-hidden="true" />
              <p>运筹帷幄之中，决胜千里之外</p>
            </section>

          </aside>
        </section>
      </main>

      {historyOpen ? (
        <div className="modal-overlay" onClick={() => setHistoryOpen(false)}>
          <section className="modal-panel" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h2>历史对话</h2>
              <button className="icon-btn" onClick={() => setHistoryOpen(false)} aria-label="关闭历史对话">
                ×
              </button>
            </div>
            <div className="history-list">
              {historyMessages.length ? (
                historyMessages.map((item, index) => (
                  <article key={`${item.role}-${index}`} className="history-item">
                    <span>{item.role === 'user' ? '你' : '孔明'}</span>
                    <p>{item.content.slice(0, 90)}{item.content.length > 90 ? '...' : ''}</p>
                  </article>
                ))
              ) : (
                <p className="empty-text">暂无历史记录。</p>
              )}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
