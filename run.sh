#!/usr/bin/env bash
# VXDevSync Launch Script

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Tạo .venv nếu chưa có
if [ ! -d ".venv" ]; then
    echo "[Setup] Đang khởi tạo môi trường ảo Python .venv..."
    python3 -m venv .venv
    ./.venv/bin/pip install --upgrade pip
    ./.venv/bin/pip install -r requirements.txt
fi

echo "[Launch] Đang khởi chạy VXDevSync..."
exec ./.venv/bin/python src/main.py "$@"
