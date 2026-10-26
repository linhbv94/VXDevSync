# VXDevSync — cài đặt và phát hành

App Python/pywebview, chung backend Windows/macOS. Bản đầu1.0.0. Windows chạy bộ cài NSIS x64; Mac kéo app từ DMG vào Applications. Cần cài Git. Các bản sau mở Cài đặt → Cập nhật; chỉ cài sau khi công việc đồng bộ hoàn tất. OS có thể yêu cầu cho phép app lần đầu.

## Agent release

Đọc AGENTS/spec và [QA/checkpoint](release_1_0_0_review.md). Không dùng repo/agents thật để test; `python -m scripts.run_tests` tạo fixture riêng và bare remotes cục bộ. Node regression: `node --test scripts/test_frontend_security.mjs`. Build native: `python -m scripts.build_release`, dependencies `requirements_release.txt`. Source/dev không được cài updater.

Version nằm `src/version.py`, metadata `VXDevSync.spec` và installer NSIS phải đồng bộ trước tag. Giữ appID/public key. Không gom file chưa review hoặc đưa khóa private vào Git. Native artifacts:6file gồm3installers,2tar updates vàlatest.json. Manifest riêng cho app Python, không phải schema Tauri; ký metadata canonical JSON Ed25519 và digest từng gói.

Workflow release.yml tạo draft, test/build từng OS và ký/verify manifest. Chỉ dispatch publish_release.yml trên đúng tag với local_qa_passed=true khi QA thực sự đạt; workflow kiểm CI đúng commit, version/layout/signature rồi publish và public checks. Không force-move tag hoặc thay package public. Chưa runtime Win/Intel thì báo giới hạn, không gọi compile là GUI PASS.

Cài updater giữ backup app cũ để phục hồi; không xóa backup nếu chưa xác nhận bản mới chạy ổn. Cascade delete skills là thao tác xóa; gỡ tombstone không tự khôi phục nội dung file đã xóa. Không dùng các ca destructive trên dữ liệu thật để QA.
