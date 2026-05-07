from __future__ import annotations

import os
import sys
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip().strip("'").strip('"')
        os.environ[key] = value


if __name__ == "__main__":
    backend_root = Path(__file__).resolve().parent
    _load_env_file(backend_root.parent / ".env")
    _load_env_file(backend_root / ".env")
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    try:
        import uvicorn  # noqa: F401
    except ModuleNotFoundError:
        print(
            "错误：缺少 uvicorn，请先安装依赖：\n"
            f"  cd {backend_root} && pip install -r requirements.txt",
            flush=True,
        )
        sys.exit(1)

    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
