from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.v1 import router as v1_router
from app.core.config import settings
from app.core.database import init_db
from app.services.session_service import session_service


def _render_static_shell() -> str:
    return """
<div id="root">
  <div class="app-shell">
    <aside class="side-panel">
      <div class="brand">
        <div class="brand-mark">孔</div>
        <div>
          <p class="eyebrow">Kongming Agent</p>
          <h1>孔明问策</h1>
          <p>四大名著知识问答</p>
        </div>
      </div>

      <section class="panel session-panel">
        <div class="section-head">
          <h2>会话</h2>
          <span class="state-dot">加载中</span>
        </div>
        <dl class="meta-list">
          <div>
            <dt>编号</dt>
            <dd>待创建</dd>
          </div>
          <div>
            <dt>主题</dt>
            <dd>四大名著问答</dd>
          </div>
        </dl>
      </section>

      <section class="panel">
        <div class="section-head">
          <h2>四书导览</h2>
        </div>
        <div class="book-list">
          <button class="book-item" type="button">
            <span>谋略</span>
            <strong>三国演义</strong>
            <em>权谋、局势、人物决策</em>
          </button>
          <button class="book-item" type="button">
            <span>情意</span>
            <strong>红楼梦</strong>
            <em>家族、情感、命运关系</em>
          </button>
          <button class="book-item" type="button">
            <span>修行</span>
            <strong>西游记</strong>
            <em>神魔、修行、秩序隐喻</em>
          </button>
          <button class="book-item" type="button">
            <span>江湖</span>
            <strong>水浒传</strong>
            <em>江湖、群像、反抗逻辑</em>
          </button>
        </div>
      </section>

      <section class="panel">
        <h2>快捷发问</h2>
        <div class="prompt-list">
          <button class="prompt-chip" type="button">孙悟空是谁？</button>
          <button class="prompt-chip" type="button">诸葛亮的核心战略思想是什么？</button>
        </div>
      </section>
    </aside>

    <main class="workspace">
      <section class="headline-panel">
        <div>
          <p class="eyebrow">Kongming Agent</p>
          <h2>四大名著知识问答</h2>
        </div>
        <div class="headline-metrics">
          <span>三国演义</span>
          <span>红楼梦</span>
          <span>西游记</span>
          <span>水浒传</span>
        </div>
      </section>

      <section class="main-grid">
        <section class="chat-panel">
          <div class="chat-head">
            <div>
              <h2>问答记录</h2>
              <p>会话建立中</p>
            </div>
            <div class="toolbar">
              <button class="text-btn" type="button">历史</button>
              <button class="text-btn" type="button">新会话</button>
            </div>
          </div>

          <div class="message-stream">
            <article class="bubble assistant">
              <div class="bubble-top"><span>孔明</span></div>
              <div class="bubble-body">可直接提问四大名著中的人物、情节、主题或关系脉络。</div>
            </article>
          </div>

          <div class="composer">
            <textarea placeholder="输入问题，例如：孙悟空是谁？"></textarea>
            <div class="composer-row">
              <button class="text-btn" type="button">清空</button>
              <button class="primary-btn" type="button">发问</button>
            </div>
          </div>
        </section>

        <aside class="right-rail">
          <section class="search-panel">
            <div class="section-head">
              <h2>典籍检索</h2>
              <button class="text-btn" type="button">检索</button>
            </div>
            <input placeholder="诸葛亮 / 林黛玉 / 孙悟空 / 林冲" />
            <div class="search-results">
              <p class="empty-text">检索结果会显示在这里。</p>
            </div>
          </section>

          <section class="portrait-panel" aria-label="诸葛亮背景图">
            <div class="portrait-bg" aria-hidden="true"></div>
            <p>运筹帷幄之中，决胜千里之外</p>
          </section>

          <section class="status-panel">
            <h2>典籍范围</h2>
            <dl class="status-grid">
              <div><dt>谋略</dt><dd>三国演义</dd></div>
              <div><dt>情意</dt><dd>红楼梦</dd></div>
              <div><dt>修行</dt><dd>西游记</dd></div>
              <div><dt>江湖</dt><dd>水浒传</dd></div>
            </dl>
          </section>
        </aside>
      </section>
    </main>
  </div>
</div>
""".strip()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(v1_router, prefix=settings.api_prefix)

    frontend_dist = settings.project_root / "frontend" / "dist"
    frontend_index = frontend_dist / "index.html"
    frontend_assets = frontend_dist / "assets"
    portrait_svg = frontend_dist / "zhugeliang-portrait.svg"
    kongming_bg_svg = frontend_dist / "kongming-bg.svg"
    tag_image = settings.project_root / "图片" / "标签.jpg"
    portrait_image = settings.project_root / "图片" / "画像.jpeg"
    if frontend_assets.exists():
        app.mount("/assets", StaticFiles(directory=frontend_assets), name="frontend-assets")

    @app.get("/zhugeliang-portrait.svg", include_in_schema=False, response_model=None)
    def portrait_asset() -> Response:
        return FileResponse(portrait_svg, media_type="image/svg+xml")

    @app.get("/kongming-bg.svg", include_in_schema=False, response_model=None)
    def kongming_bg_asset() -> Response:
        return FileResponse(kongming_bg_svg, media_type="image/svg+xml")

    @app.get("/tag-image.jpg", include_in_schema=False, response_model=None)
    def tag_image_asset() -> Response:
        return FileResponse(tag_image, media_type="image/jpeg")

    @app.get("/portrait-image.jpeg", include_in_schema=False, response_model=None)
    def portrait_image_asset() -> Response:
        return FileResponse(portrait_image, media_type="image/jpeg")

    @app.get("/", include_in_schema=False, response_model=None)
    def root() -> Response:
        if frontend_index.exists():
            html = frontend_index.read_text(encoding="utf-8")
            html = html.replace('<div id="root"></div>', _render_static_shell())
            return HTMLResponse(
                html,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                },
            )
        return HTMLResponse(
            "<html><body><h1>Kongming Agent</h1><p>Frontend bundle not found. Run <code>cd frontend && npm run build</code>.</p></body></html>",
            status_code=503,
        )

    init_db()
    session_service.ensure_agent_profile(settings.default_agent_code)
    return app


app = create_app()
