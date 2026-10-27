# Migration native chrome — macOS SDK27.0
Version: 1.0.0 — Ngày update: 2026-10-27

User đã chốt baseline27.0 cho suite VX. Tài liệu này áp dụng riêng repo, không phụ thuộc source repo khác khi build CI. Không đổi minimum deployment target, app identity, updater key hoặc OS permissions.

- `scripts/macos_sdk_gate.mjs`: preflight SDK chính xác27.0, kiểm SDKROOT, metadata mọi slice của executable, chọn toolchain trong CI theo từng job; thiếu27.0 thì fail, không fallback hoặc patch metadata.
- CI gọi `--select-ci` trước native build/test. Tên runner không thay SDK pin; runner phải được provision Xcode/CLT có27.0. Chưa chạy CI trong lượt migration local này.
- App Tauri: `npm run tauri` qua wrapper pin SDKROOT và kiểm executable sau build trước khi trả về uploader; build.rs chặn direct cargo native bằng cùng gate. Windows/Linux giữ CLI nguyên hành vi, bỏ qua SDK gate macOS. Mỗi repo giữ bản gate tự chứa.
- PyInstaller: build bootloader từ source bằng SDK27.0; kiểm bootloader và bundle executable, không dùng vtool để ghi SDK giả. Không đổi deployment target11.0 của packaging hiện có.
- Traffic lights giữ frame/bounds/controlSize chuẩn AppKit27.0, không ép về12pt của profile SDK15.5. Tâm cách20pt; align theo content toolbar và flipped coordinates. VXShot đã chuyển từ superview titlebar sang content coordinates.
- Lượt này tạo build local để kiểm SDK, không tự cài vào Applications hoặc commit/push/release. Build/metadata không thay visual runtime/resize/focus/fullscreen/Spaces; ghi các phần đó riêng trong báo cáo root.
