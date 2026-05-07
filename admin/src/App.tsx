import { useEffect, useMemo, useRef, useState } from 'react';
import {
  getAgentConfig,
  getDatabaseStatus,
  getDocuments,
  getKnowledgeRebuildJob,
  getOverview,
  getSessions,
  rebuildKnowledge,
  updateAgentConfig,
  uploadDocument,
} from './api';

type JobProgress = {
  stage?: string;
  message?: string;
  percent?: number;
  processed_documents?: number;
  total_documents?: number;
  current_document?: string | null;
  current_document_chunks_done?: number;
  current_document_chunks_total?: number;
  vectorized_chunks?: number;
  persisted_chunks?: number;
};

type DatabaseStatus = {
  connected?: boolean;
  last_checked_at?: string;
  database?: {
    database?: string;
    host?: string;
    port?: number;
    charset?: string;
    tables?: string[];
  };
  counts?: Record<string, number>;
};

const overviewLabelMap: Record<string, string> = {
  agent_count: 'Agent',
  session_count: '会话',
  message_count: '消息',
  document_count: '文档',
  feedback_count: '反馈',
  retrieval_count: '检索',
  job_count: '任务',
  running_job_count: '运行中',
  last_updated_at: '更新时间',
};

export default function App() {
  const [overview, setOverview] = useState<Record<string, unknown>>({});
  const [database, setDatabase] = useState<DatabaseStatus>({});
  const [sessions, setSessions] = useState<Array<Record<string, unknown>>>([]);
  const [documents, setDocuments] = useState<Array<Record<string, unknown>>>([]);
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [modelName, setModelName] = useState('gpt-4.1-mini');
  const [temperature, setTemperature] = useState('0.5');
  const [uploadTitle, setUploadTitle] = useState('四大名著资料');
  const [uploadCorpus, setUploadCorpus] = useState('四大名著');
  const [rebuildStatus, setRebuildStatus] = useState('idle');
  const [rebuildJobId, setRebuildJobId] = useState('');
  const [jobProgress, setJobProgress] = useState<JobProgress>({});
  const pollRef = useRef<number | null>(null);

  async function refresh() {
    const [ov, db, ss, ds, cg] = await Promise.all([getOverview(), getDatabaseStatus(), getSessions(), getDocuments(), getAgentConfig()]);
    setOverview(ov);
    setDatabase(db as DatabaseStatus);
    setSessions(ss.items);
    setDocuments(ds.items);
    setConfig(cg);
    setModelName(String(cg.model_name ?? 'gpt-4.1-mini'));
    setTemperature(String(cg.temperature ?? 0.5));
  }

  useEffect(() => {
    refresh().catch(() => undefined);
    return () => {
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
      }
    };
  }, []);

  function stopPolling() {
    if (pollRef.current) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  function startPolling(jobId: string) {
    stopPolling();
    pollRef.current = window.setInterval(() => {
      if (!jobId) {
        stopPolling();
        return;
      }
      getKnowledgeRebuildJob(jobId)
        .then((detail) => {
          const status = String(detail.status ?? 'running');
          setRebuildStatus(status);
          setJobProgress((detail.progress ?? {}) as JobProgress);
          if (status !== 'running') {
            stopPolling();
            refresh().catch(() => undefined);
          }
        })
        .catch(() => {
          stopPolling();
          setRebuildStatus('failed');
        });
    }, 2000);
  }

  const metricCards = useMemo(
    () =>
      Object.entries(overview).map(([key, value]) => ({
        key,
        label: overviewLabelMap[key] ?? key.replace(/_/g, ' '),
        value: String(value),
      })),
    [overview],
  );

  const progressPercent = Number(jobProgress.percent ?? 0);
  const currentDb = database.database ?? {};
  const counts = database.counts ?? {};

  return (
    <div className="admin-shell">
      <header className="hero-card">
        <div>
          <p className="eyebrow">Administration · Kongming Agent</p>
          <h1>孔明运筹台</h1>
          <p className="hero-copy">
            这里负责看数据库、盯重建、查会话和文档。向量库继续放在 Milvus，基础信息由本地 MySQL 持久化。
          </p>
        </div>
        <div className="hero-status">
          <article>
            <span>数据库</span>
            <strong>{String(database.connected ?? false)}</strong>
          </article>
          <article>
            <span>任务</span>
            <strong>{String(rebuildStatus)}</strong>
          </article>
          <article>
            <span>文档</span>
            <strong>{String(counts.documents ?? 0)}</strong>
          </article>
        </div>
      </header>

      <section className="metrics-grid">
        {metricCards.map((metric) => (
          <article className="metric-card" key={metric.key}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </section>

      <section className="main-grid">
        <div className="stack">
          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>数据库状态</h2>
                <p className="muted">本地 MySQL 的连接和表结构一目了然。</p>
              </div>
              <button className="secondary-btn" onClick={() => refresh().catch(() => undefined)}>
                刷新
              </button>
            </div>

            <div className="db-grid">
              <article>
                <span>库名</span>
                <strong>{String(currentDb.database ?? '-')}</strong>
              </article>
              <article>
                <span>主机</span>
                <strong>
                  {String(currentDb.host ?? '-') }:{String(currentDb.port ?? '-')}
                </strong>
              </article>
              <article>
                <span>字符集</span>
                <strong>{String(currentDb.charset ?? '-')}</strong>
              </article>
              <article>
                <span>最后检查</span>
                <strong>{String(database.last_checked_at ?? '-')}</strong>
              </article>
            </div>

            <div className="table-cloud">
              {(currentDb.tables ?? []).map((table) => (
                <span key={table}>{table}</span>
              ))}
            </div>

            <div className="count-grid">
              {Object.entries(counts).map(([key, value]) => (
                <article key={key}>
                  <span>{overviewLabelMap[key] ?? key}</span>
                  <strong>{String(value)}</strong>
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>Agent 配置</h2>
                <p className="muted">保留现有人格，只允许调模型参数和温度。</p>
              </div>
            </div>

            <div className="form-grid">
              <label>
                <span>模型名称</span>
                <input value={modelName} onChange={(e) => setModelName(e.target.value)} />
              </label>
              <label>
                <span>Temperature</span>
                <input value={temperature} onChange={(e) => setTemperature(e.target.value)} />
              </label>
            </div>

            <button
              className="primary-btn"
              onClick={() =>
                updateAgentConfig({ 模型名称: modelName, 温度: Number(temperature) }).then(() => refresh()).catch(() => undefined)
              }
            >
              保存配置
            </button>

            <pre>{JSON.stringify(config, null, 2)}</pre>
          </section>
        </div>

        <div className="stack">
          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>知识库重建</h2>
                <p className="muted">DashScope 向量化完成后，会一次性写入 Milvus。</p>
              </div>
              <button
                className="primary-btn"
                onClick={() => {
                  setRebuildStatus('running');
                  setRebuildJobId('');
                  setJobProgress({});
                  rebuildKnowledge()
                    .then((job) => {
                      const jobId = String(job.job_id ?? '');
                      setRebuildJobId(jobId);
                      setRebuildStatus(String(job.status ?? 'running'));
                      setJobProgress((job.progress ?? {}) as JobProgress);
                      startPolling(jobId);
                    })
                    .catch(() => setRebuildStatus('failed'));
                }}
              >
                {rebuildStatus === 'running' ? '重建中' : '立即重建'}
              </button>
            </div>

            <div className="progress-shell">
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${Math.min(100, Math.max(0, progressPercent))}%` }} />
              </div>
              <div className="progress-line">
                <span>进度 {progressPercent.toFixed(2)}%</span>
                <span>{String(jobProgress.stage ?? 'idle')}</span>
              </div>
            </div>

            <div className="detail-list">
              <div>
                <span>状态</span>
                <strong>{rebuildStatus}</strong>
              </div>
              <div>
                <span>任务</span>
                <strong>{rebuildJobId || '-'}</strong>
              </div>
              <div>
                <span>当前文档</span>
                <strong>{String(jobProgress.current_document ?? '-')}</strong>
              </div>
              <div>
                <span>文档进度</span>
                <strong>
                  {String(jobProgress.processed_documents ?? 0)} / {String(jobProgress.total_documents ?? 0)}
                </strong>
              </div>
              <div>
                <span>当前文档切片</span>
                <strong>
                  {String(jobProgress.current_document_chunks_done ?? 0)} / {String(jobProgress.current_document_chunks_total ?? 0)}
                </strong>
              </div>
              <div>
                <span>累计向量化</span>
                <strong>{String(jobProgress.vectorized_chunks ?? 0)}</strong>
              </div>
              <div>
                <span>累计入库</span>
                <strong>{String(jobProgress.persisted_chunks ?? 0)}</strong>
              </div>
            </div>

            <p className="muted">{String(jobProgress.message ?? '等待任务启动')}</p>
          </section>

          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>文档登记</h2>
                <p className="muted">录入新增资料，后续可按文档推进重建和管理。</p>
              </div>
            </div>

            <div className="form-grid">
              <label>
                <span>语料名称</span>
                <input value={uploadCorpus} onChange={(e) => setUploadCorpus(e.target.value)} />
              </label>
              <label>
                <span>文档标题</span>
                <input value={uploadTitle} onChange={(e) => setUploadTitle(e.target.value)} />
              </label>
            </div>

            <button
              className="secondary-btn"
              onClick={() =>
                uploadDocument({ 语料名称: uploadCorpus, 文档标题: uploadTitle }).then(() => refresh()).catch(() => undefined)
              }
            >
              登记文档
            </button>

            <div className="list-grid">
              {documents.map((doc) => (
                <article key={String(doc.doc_id)} className="mini-card">
                  <strong>{String(doc.doc_title)}</strong>
                  <span>{String(doc.corpus_name)}</span>
                  <p>{String(doc.parse_status ?? 'pending')}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <h2>会话列表</h2>
            <div className="list-grid">
              {sessions.map((session) => (
                <article key={String(session.session_id)} className="mini-card">
                  <strong>{String(session.session_title ?? session.session_id)}</strong>
                  <span>{String(session.user_id ?? 'anonymous')}</span>
                  <p>{String(session.status ?? 'active')}</p>
                </article>
              ))}
            </div>
          </section>
        </div>
      </section>
    </div>
  );
}
