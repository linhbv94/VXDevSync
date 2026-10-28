# VXDevSync 1.0.5 — Tự động nhận diện Git Remote URL & Onboarding Central Library

## 1. Tổng quan Bản phát hành
- **Tính năng mới:**
  - Bổ sung trường nhập Git Remote URL cho Central Skills Library trong Onboarding Wizard (Bước 1) và cài đặt Skills Sync.
  - Tự động nhận diện URL remote `origin` qua API `get_git_remote_url(folder_path)` khi người dùng chọn thư mục Central Skills Library.
  - Đồng bộ thuật ngữ và nhận diện hệ sinh thái VXUtilities trên toàn bộ giao diện và hệ thống tài liệu đặc tả.
- **Mục tiêu:**
  - Nâng version lên `1.0.5` trong `src/version.py`, `installer/windows_installer.nsi`, `docs/release_notes/1.0.5.md`.
  - Kiểm thử tự động: 41 unit tests + Node frontend security test PASS 100%.
  - Đóng gói và phát hành multi-platform release.

## 2. Kiểm thử Tự động & Bằng chứng Nghiệm thu
- `python -m scripts.run_tests`: 41/41 tests PASS (100%).
  - Bổ sung `test_get_git_remote_url` kiểm tra nhận diện remote URL của Git repo.
  - Bổ sung `test_save_config_with_skills_git_repo` kiểm tra lưu cấu hình `git_repo` đồng bộ từ GUI và Onboarding.
- `node scripts/test_frontend_security.mjs`: PASS (100%).
- `python src/main.py --self-test`: PASS (`version: 1.0.5`, `self_test: ok`).

## 3. Bản phát hành Multi-platform
- Windows x64 NSIS setup EXE: `vxdevsync_1.0.5_windows_x64_setup.exe`
- macOS Apple Silicon DMG: `vxdevsync_1.0.5_macos_silicon.dmg`
- macOS Apple Silicon updater archive: `vxdevsync_1.0.5_macos_silicon.app.tar.gz`
- macOS Intel DMG: `vxdevsync_1.0.5_macos_intel.dmg`
- macOS Intel updater archive: `vxdevsync_1.0.5_macos_intel.app.tar.gz`
- Manifest cập nhật tự động: `latest.json`
