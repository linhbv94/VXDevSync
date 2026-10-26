#!/usr/bin/env bash
# VXDevSync macOS .app Build Script
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================="
echo "[Build] Đang đóng gói VXDevSync thành macOS .app"
echo "=========================================="

# 1. Kiểm tra Python Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[Error] Không tìm thấy .venv! Hãy chạy ./run.sh trước."
    exit 1
fi

# 2. Đảm bảo pyinstaller đã cài đặt
./.venv/bin/pip show pyinstaller >/dev/null 2>&1 || {
    echo "[Install] Đang cài đặt pyinstaller..."
    ./.venv/bin/pip install pyinstaller
}

# 3. Dọn dẹp thư mục build/dist cũ
echo "[Clean] Dọn dẹp bản build cũ..."
rm -rf build dist

# 4. Chạy PyInstaller
echo "[Package] Đang thực thi PyInstaller đóng gói bundle..."
./.venv/bin/pyinstaller --clean --noconfirm VXDevSync.spec

APP_PATH="dist/VXDevSync.app"
if [ ! -d "$APP_PATH" ]; then
    echo "[Error] Không tạo được $APP_PATH!"
    exit 1
fi

# 4.1. Chuẩn hóa Mach-O LC_BUILD_VERSION sang SDK 15.5 tương thích AppKit (khớp chuẩn VXMedia/VXmp3)
EXE_PATH="$APP_PATH/Contents/MacOS/VXDevSync"
if [ -f "$EXE_PATH" ]; then
    echo "[SDK] Đang chuẩn hóa SDK metadata sang 15.5 (khớp chuẩn AppKit VXMedia/VXmp3 bezel 12pt)..."
    vtool -set-build-version macos 11.0 15.5 -replace -output "$EXE_PATH" "$EXE_PATH"
fi

# 5. Ký ad-hoc codesign để macOS chạy mượt mà
echo "[Sign] Đang ký ad-hoc codesign cho bundle..."
codesign --force --deep --sign - "$APP_PATH"

# 6. Kiểm tra chữ ký
codesign --verify --deep --strict "$APP_PATH"
if [ $? -eq 0 ]; then
    echo "[OK] Chữ ký ad-hoc hợp lệ."
else
    echo "[Warning] Cảnh báo xác minh chữ ký."
fi

# 7. Hiển thị thông tin kết quả
echo ""
echo "=========================================="
echo "[Success] Đóng gói thành công: $APP_PATH"
echo "Icon: icon.icns (đã nhúng vào bundle)"
du -sh "$APP_PATH"
echo "=========================================="
echo "Để chạy thử app, bạn có thể thực thi:"
echo "open dist/VXDevSync.app"
