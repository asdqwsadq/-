#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="/Users/wuliang/miniconda3/envs/myenv/bin/python"
PIP="/Users/wuliang/miniconda3/envs/myenv/bin/pip"

echo "=== 1. 启动 Milvus ==="
cd "$ROOT_DIR/docker/milvus"
docker compose up -d
echo "Milvus 已启动"

echo "=== 2. 安装/检查后端依赖 ==="
cd "$ROOT_DIR/backend"
if ! $PYTHON -c "import uvicorn" 2>/dev/null; then
  echo "安装后端依赖..."
  $PIP install -r requirements.txt
fi

echo "=== 3. 启动后端 ==="
$PYTHON run_backend.py &
BACKEND_PID=$!
echo "后端启动中 (PID: $BACKEND_PID)"

# 等待后端就绪
echo "等待后端就绪..."
for i in $(seq 1 30); do
  if curl -s http://127.0.0.1:8000/api/v1/health > /dev/null 2>&1; then
    echo "后端已就绪"
    break
  fi
  sleep 1
done

echo "=== 4. 安装/检查前端依赖 ==="
cd "$ROOT_DIR/frontend"
if [ ! -d node_modules ]; then
  echo "安装前端依赖..."
  npm install
fi

echo "=== 5. 启动前端 ==="
npm run dev
