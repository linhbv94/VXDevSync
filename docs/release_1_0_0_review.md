# VXDevSync1.0.0 — QA độc lập và checkpoint release
Ngày:2026-10-26. User giao QA và phát hành đầu tiên1.0.0 Win/Mac, cho phép khóa updater riêng vào Secrets đúng repo public VXDevSync.

## QA và sửa lỗi trước tag

Baseline ef175e5 có14test cũ đạt, nhưng6fixture mới tái hiện lỗi: Smart Sync không push ahead; explicit pull vẫn chạy khi dirty; inventory tự xóa theo tombstone; skill name có thể thoát thư mục; library rỗng thành cwd; Skills Sync gom file ngoài phạm vi vào commit.

Đã sửa các lỗi trên, thêm kiểm tra staged changes trước khi đổi library, fetch/pull ff-only theo nhánh thật; giữ file ngoài phạm vi untracked. Chỉ inventory đọc, tombstones áp dụng khi Sync. Tên/path skill bị giới hạn, cấm .system/.git và symlink ở đích xóa. Tombstone được ghi nguyên tử trước khi xóa; lỗi xóa không báo thành công giả. Không chỉnh hai CLI cũ hoặc skills/Git thật để QA.

Cấu hình đọc lỗi giữ file gốc, tắt auto-scan; lưu atomically và giữ config_previous.json. Bridge ẩn các engine nội bộ, serialize các mutation và updater; frontend escape tên repo/skill/path để không trở thành HTML có quyền gọi bridge.

## Phân phối và updater

Python/pywebview/PyInstaller, không ép sang template Tauri. Win x64 NSIS currentUser + macOS Silicon/Intel DMG/app.tar.gz; cùng engine Python. Gói updater được xác minh bằng manifest Ed25519 ký riêng, URL tag-pinned thuộc repo và digest/size trước install. Key public trong app; private key không nằm Git/release.

Check khi mở app và tab Updates; không tự cài giữa tác vụ. Install chặn khi sync/busy, không cài từ source/dev. Mac staging cạnh app, helper chờ app đóng rồi đổi bundle và rollback khi rename thất bại, giữ bản cũ. Win installer chờ PID app cũ, stage/backup trước thay app rồi mở lại. Không thay config/skills/Git của user qua updater. Cài đầu cần cho phép OS nếu cảnh báo; app cần Git được cài sẵn.

Tests mới kiểm signature/tamper/wrong key/wrong repo/app, corruption/traversal, semver, Mac swap/rollback, mutation guard, config recovery và frontend escaping. First-release old→new E2E chưa thể chứng minh chỉ bằng build; ghi rõ khi có kết quả thực.

Đang QA package/GUI và chuẩn bị CI; chưa tag/publish tại checkpoint này. Không lấy14test ban đầu hoặc mô tả100% trong bàn giao làm nghiệm thu độc lập.

## Checkpoint trước CI

33 Python tests và 1 frontend security test PASS trong môi trường fixture cô lập. Local Mac ARM64 đóng gói, self-test frozen, codesign strict, giải nén tar thật và kiểm chữ ký bundle PASS. Native GUI mở đúng fixture workspace/library, inventory hiển thị sample, Settings/Updates không tràn; kiểm tra trước publish nhận 404 và nút retry hoạt động. Chưa test GUI Windows/Intel, chưa test update 1.0.0→bản tiếp theo. Một lỗi retry push library khi không có thay đổi mới cũng đã có regression test và sửa. CI sẽ build/test package thật cho cả ba target trước publish.

## Phục hồi CI Windows

Run40364109041: fixture clone bare remote mặc định HEAD khác main trên Windows; sửa fixture chỉ rõ clone -b main, cleanup Git readonly files và báo lỗi đầy đủ. Workflow dispatch từ main dùng đúng fixture của workflow SHA, chỉ overlay tests/setup_mock_env.py. Source runtime/frontend/spec/installer/package inputs vẫn nguyên tag27b7c76; không dời tag hoặc sửa binary đã public.
