# VXDevSync 1.0.1 — QA và phát hành native SDK 27.0
Ngày: 2026-10-27. User giao release sau migration SDK cụm traffic lights.

- Đồng bộ giao diện cụm nút điều khiển cửa sổ macOS (traffic lights) theo tiêu chuẩn native SDK 27.0.
- Rebuild PyInstaller bootloader nguồn thật từ PyPI bằng toolchain SDK 27.0 native thay thế hoàn toàn giải pháp vá metadata vtool cũ.
- Tích hợp gate tự chứa `scripts/macos_sdk_gate.mjs` kiểm tra executable và toàn bộ Mach-O slices.
- Cập nhật CI runner macOS sang `xcode-27` để đảm bảo SDK 27.0 thật trên cả hai gói macOS Silicon và macOS Intel.
- Local QA: 33 Python unit & integration tests + 1 Node security test đạt 100% PASS. Gate SDK 27.0 trên binary bundle local và codesign verification đạt 100%.
