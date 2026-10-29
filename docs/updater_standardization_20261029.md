# Chuẩn hóa engine updater VXDevSync

Version: 1.1.0 — Ngày update: 2026-10-29

Track chỉnh sửa sau update/release, độc lập với các app khác. Theo [contract chung](../../_summary/standard_docs/auto_update_standards.md). Chưa release, không đổi appID/key/version.

## Owner và luồng
- Một AppUpdater qua BridgeApi._get_updater với creation lock; RLock single-flight bảo vệ check/install. get_update_status đọc snapshot/progress thật trong khi RPC install chạy; check_updates/install_update dùng cùng owner. Startup UI chỉ check, không tự install.
- Check15s, download request30s/tổng300s theo monotonic; signed Ed25519 manifest giữ public key hiện tại, stable version/đúng platform/URL/size/hash; stale pending bị xóa khi recheck. Download có byte progress, verifying/installing/handed_off là trạng thái thật.
- install_update giữ exclusive mutation và shutdown_pending; chỉ delayed exit sau helper/installer ready ACK. Không chờ frontend Promise sống qua quá trình app thoát.
- macOS: stage cùng volume, identity/version/plan/ready path validation, helper parent wait30s, old bundle backup. Swap hoặc relaunch exit-error/timeout có rollback giữ hai bản và receipt; không báo completed chỉ từ open exit0. App mới xác nhận receipt ở startup; không ghi đè fast-child confirmation.
- Helper đọc snapshot identity/content của target và staging trước ACK; kiểm lại sau parent-exit ngay trước swap. Target thay inode hoặc staging đổi nội dung thì từ chối, không đè app. Hai test race sauACK đã tái hiện lỗi cũ và đạt sau sửa.
- Windows source: truyền chính thư mục executable đang chạy; NSIS ready receipt trước parent wait30s, giữ backup, kiểm lỗi launch và rollback. Receipt UTF16 INI để giữ đường dẫn Unicode, version từ VERSION. **Chưa compile NSIS hoặc chạy native Windows trong đợt này**.

## Checks và giới hạn
18 updater tests PASS (signed/tamper/package/path/swap/rollback/ready escape/fast launch ack/single-flight); đây là fixture/mock, không thay E2E update production. UI Anti cần bind get_update_status, card Update trực tiếp và một store. Không cài vào /Applications hoặc sửa dữ liệu Git/Skills để QA. Cần native Mac/Win cũ→mới có chữ ký và readback cấu hình trước báo AU-09…AU-12 đạt.

## Lịch sử cập nhật

- 1.1.0 (2026-10-29): Revalidate bundle đích/staging sau ACK và trước swap, thêm2regression,18tests đạt.
- 1.0.0 (2026-10-29): Controller/bridge chung, signed package, helper ACK/receipt/rollback.
