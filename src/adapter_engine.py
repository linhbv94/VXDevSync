from src import safe_sync_io
from src.skills_engine import AgentPresence, SkillItem
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import hashlib

CLAUDE_HEADER_METADATA = """# Claude Code Project & Global Instructions

> **Source:** Synchronized automatically by VXDevSync from AGENTS.md
> **Note:** Follow these global rules and guidelines strictly.

"""

class AdapterEngine:
    """Chịu trách nhiệm chuyển đổi và đồng bộ quy tắc chung: AGENTS.md ↔ CLAUDE.md."""

    @staticmethod
    def get_file_hash(filepath: Path) -> str:
        return safe_sync_io.file_hash(filepath.parent, filepath.name)

    @staticmethod
    def strip_claude_header(text: str) -> str:
        """Bóc tách phần header CLAUDE_HEADER_METADATA ở đầu tệp, hỗ trợ cả CRLF và LF."""
        normalized = text.replace("\r\n", "\n")
        norm_header = CLAUDE_HEADER_METADATA.replace("\r\n", "\n").strip()
        trimmed = normalized.lstrip()
        if trimmed.startswith(norm_header):
            return trimmed[len(norm_header):].lstrip()
        return normalized

    def get_rules_status(
        self,
        library_path: Path,
        agent_paths: Dict[str, str],
        active_agents: List[str]
    ) -> SkillItem:
        """
        Kiểm tra trạng thái file rule tổng (AGENTS.md tại Central Library và từng Agent,
        CLAUDE.md tại Claude Code sau khi bóc tách header).
        """
        lib_root_file = library_path / "AGENTS.md"
        lib_exists = lib_root_file.exists() and lib_root_file.is_file() and lib_root_file.stat().st_size > 0
        lib_text = ""
        lib_mtime = 0.0
        if lib_exists:
            try:
                lib_text = safe_sync_io.read_text(lib_root_file.parent, lib_root_file.name).replace("\r\n", "\n").strip()
                lib_mtime = lib_root_file.stat().st_mtime
            except Exception:
                lib_exists = False

        agents_dict: Dict[str, AgentPresence] = {}
        for agent_name in ["anti", "codex", "claude"]:
            agent_dir_str = agent_paths.get(agent_name, "")
            if not agent_dir_str:
                agents_dict[agent_name] = AgentPresence(exists=False, is_synced=False)
                continue

            agent_dir = Path(agent_dir_str)
            if agent_name in ["anti", "codex", "antigravity"]:
                target_file = agent_dir.parent / "AGENTS.md" if agent_dir.name == "skills" else agent_dir / "AGENTS.md"
            elif agent_name == "claude":
                target_file = agent_dir / "CLAUDE.md"
            else:
                target_file = agent_dir / "AGENTS.md"

            if not target_file.exists() or not target_file.is_file() or target_file.stat().st_size == 0:
                agents_dict[agent_name] = AgentPresence(exists=False, is_synced=False, status="missing")
                continue

            try:
                raw_text = safe_sync_io.read_text(target_file.parent, target_file.name)
                clean_text = self.strip_claude_header(raw_text).replace("\r\n", "\n").strip() if agent_name == "claude" else raw_text.replace("\r\n", "\n").strip()
                is_synced = bool(lib_exists and clean_text == lib_text and len(lib_text) > 0)
                mtime = target_file.stat().st_mtime

                if is_synced:
                    status = "synced"
                elif not lib_exists:
                    status = "new"
                elif mtime > lib_mtime:
                    status = "modified"
                else:
                    status = "outdated"

                agents_dict[agent_name] = AgentPresence(
                    exists=True,
                    is_synced=is_synced,
                    mtime=mtime,
                    file_count=1,
                    status=status
                )
            except Exception:
                agents_dict[agent_name] = AgentPresence(exists=False, is_synced=False, status="missing")

        return SkillItem(
            name="AGENTS.md",
            in_library=lib_exists,
            agents=agents_dict,
            is_tombstoned=False,
            is_pinned=True,
            is_rules=True
        )

    def get_agent_rules_files(self, agent_name: str, agent_dir_str: str) -> List[Path]:
        if not agent_dir_str:
            return []
        agent_dir = Path(agent_dir_str)
        files = []

        if agent_name in ["anti", "codex", "antigravity"]:
            if agent_dir.name == "skills":
                files.append(agent_dir.parent / "AGENTS.md")
            else:
                files.append(agent_dir / "AGENTS.md")
        elif agent_name == "claude":
            files.append(agent_dir / "CLAUDE.md")

        return [f for f in files if f.exists()]

    def sync_rules_upstream(
        self,
        library_path: Path,
        agent_paths: Dict[str, str],
        selected_agents: List[str]
    ) -> Tuple[bool, str]:
        """
        [Upstream Rules Sync]: Phát hiện nếu AGENTS.md hoặc CLAUDE.md ở bất kỳ Agent nào mới hơn
        bản trong Central Library (AGENTS.md), tự động gom về Library.
        Chống xung đột (Conflict Guard): Nếu nhiều agent cùng sửa đổi với nội dung khác nhau,
        từ chối tự ý ghi đè và dừng để bảo vệ an toàn dữ liệu.
        """
        lib_root_file = library_path / "AGENTS.md"
        lib_exists = lib_root_file.exists() and lib_root_file.stat().st_size > 0
        lib_mtime = lib_root_file.stat().st_mtime if lib_exists else 0.0
        lib_text = ""
        if lib_exists:
            try:
                lib_text = safe_sync_io.read_text(lib_root_file.parent, lib_root_file.name).replace("\r\n", "\n").strip()
            except Exception as e:
                return False, f"Lỗi đọc AGENTS.md Thư viện trung tâm: {e}"

        # Thu thập các agent có rules khác với Central Library
        modified_agents: Dict[str, Tuple[Path, str, float]] = {}

        for agent_name in selected_agents:
            agent_dir_str = agent_paths.get(agent_name, "")
            rules_files = self.get_agent_rules_files(agent_name, agent_dir_str)

            for rf in rules_files:
                if not rf.exists() or rf.stat().st_size == 0:
                    continue

                try:
                    content = safe_sync_io.read_text(rf.parent, rf.name)
                    if rf.name == "CLAUDE.md":
                        clean_content = self.strip_claude_header(content)
                    else:
                        clean_content = content

                    norm_clean = clean_content.replace("\r\n", "\n").strip()
                    # Bỏ qua nếu nội dung thực tế giống hệt Central Library
                    if lib_exists and norm_clean == lib_text:
                        continue

                    rf_mtime = rf.stat().st_mtime
                    modified_agents[agent_name] = (rf, clean_content, rf_mtime)
                except ValueError:
                    raise
                except Exception as e:
                    return False, f"Lỗi đọc rules từ {agent_name}: {e}"

        # Trường hợp 1: Không có Agent nào thay đổi nội dung so với Library
        if not modified_agents:
            return True, ""

        # Trường hợp 2: Đúng 1 Agent có thay đổi
        if len(modified_agents) == 1:
            agent_name, (rf, clean_content, rf_mtime) = next(iter(modified_agents.items()))
            if not lib_exists or rf_mtime >= lib_mtime:
                try:
                    safe_sync_io.ensure_directory(library_path)
                    safe_sync_io.write_text(lib_root_file.parent, lib_root_file.name, clean_content, mtime=rf_mtime)
                    action_desc = "Khởi tạo" if not lib_exists else "Gom cập nhật"
                    return True, f"{action_desc} AGENTS.md từ {agent_name} ({rf.name}) về Thư viện trung tâm."
                except ValueError:
                    raise
                except Exception as e:
                    return False, f"Lỗi ghi rules vào Thư viện từ {agent_name}: {e}"
            else:
                # rf_mtime < lib_mtime: Library có bản mới hơn, Library sẽ deploy downstream xuống agent này
                return True, ""

        # Trường hợp 3: Nhiều Agent có sửa đổi
        # Kiểm tra xem tất cả các agent có cùng một nội dung mới không
        distinct_contents = {v[1].replace("\r\n", "\n").strip() for v in modified_agents.values()}
        if len(distinct_contents) == 1:
            # Nội dung đồng nhất, chọn timestamp mới nhất
            latest_agent = max(modified_agents.items(), key=lambda x: x[1][2])
            agent_name, (rf, clean_content, rf_mtime) = latest_agent
            if not lib_exists or rf_mtime >= lib_mtime:
                try:
                    safe_sync_io.ensure_directory(library_path)
                    safe_sync_io.write_text(lib_root_file.parent, lib_root_file.name, clean_content, mtime=rf_mtime)
                    return True, f"Gom cập nhật AGENTS.md đồng nhất từ {', '.join(modified_agents.keys())} về Thư viện trung tâm."
                except ValueError:
                    raise
                except Exception as e:
                    return False, f"Lỗi ghi rules vào Thư viện: {e}"
            else:
                return True, ""
        else:
            # XUNG ĐỘT THỰC SỰ: Các agent có nội dung sửa đổi khác biệt nhau
            conflict_names = ", ".join(sorted(modified_agents.keys()))
            return False, f"Xung đột rules: Các Agent [{conflict_names}] có nội dung sửa đổi khác nhau. Tạm dừng đồng bộ rules để tránh mất dữ liệu."

    def deploy_rules_downstream(
        self,
        library_path: Path,
        agent_paths: Dict[str, str],
        selected_agents: List[str]
    ) -> List[str]:
        """
        [Downstream Rules Deploy]: Phân bổ AGENTS.md từ Central Library sang các Agent đang active.
        Tự động tạo CLAUDE.md có header tương thích cho Claude Code.
        """
        lib_root_file = library_path / "AGENTS.md"
        if not lib_root_file.exists():
            return []

        try:
            base_content = safe_sync_io.read_text(lib_root_file.parent, lib_root_file.name)
            lib_mtime = lib_root_file.stat().st_mtime
        except ValueError:
            raise
        except Exception:
            return []

        claude_content = CLAUDE_HEADER_METADATA + base_content
        deployed = []

        for agent_name in selected_agents:
            agent_dir_str = agent_paths.get(agent_name, "")
            if not agent_dir_str:
                continue

            agent_dir = Path(agent_dir_str)
            safe_sync_io.ensure_directory(agent_dir)

            if agent_name in ["anti", "codex", "antigravity"]:
                target_file = agent_dir.parent / "AGENTS.md" if agent_dir.name == "skills" else agent_dir / "AGENTS.md"
                target_hash = self.get_file_hash(target_file)
                if self.get_file_hash(lib_root_file) != target_hash:
                    safe_sync_io.write_text(target_file.parent, target_file.name, base_content, mtime=lib_mtime)
                    deployed.append(f"{agent_name} (AGENTS.md)")

            elif agent_name == "claude":
                target_file = agent_dir / "CLAUDE.md"
                # So sánh nội dung
                current_text = ""
                if target_file.exists():
                    try:
                        current_text = safe_sync_io.read_text(target_file.parent, target_file.name)
                    except ValueError:
                        raise
                    except Exception:
                        pass
                if current_text != claude_content:
                    safe_sync_io.write_text(target_file.parent, target_file.name, claude_content, mtime=lib_mtime)
                    deployed.append("claude (CLAUDE.md)")

        return deployed
