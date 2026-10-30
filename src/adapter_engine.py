from src import safe_sync_io
from pathlib import Path
from typing import List, Dict, Tuple, Optional

CLAUDE_HEADER_METADATA = """# Claude Code Project & Global Instructions

> **Source:** Synchronized automatically by VXDevSync from AGENTS.md
> **Note:** Follow these global rules and guidelines strictly.

"""

class AdapterEngine:
    """Chịu trách nhiệm chuyển đổi và đồng bộ quy tắc chung: AGENTS.md ↔ CLAUDE.md."""

    @staticmethod
    def get_file_hash(filepath: Path) -> str:
        return safe_sync_io.file_hash(filepath.parent, filepath.name)


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
        """
        lib_root_file = library_path / "AGENTS.md"
        
        # Nếu Central Library đã có AGENTS.md, Central Library là Single Source of Truth
        if lib_root_file.exists() and lib_root_file.stat().st_size > 0:
            return False, "Central Library AGENTS.md là Single Source of Truth."

        # Nếu Central Library chưa có AGENTS.md, nạp từ Agent có rules hợp lệ
        for agent_name in selected_agents:
            agent_dir_str = agent_paths.get(agent_name, "")
            rules_files = self.get_agent_rules_files(agent_name, agent_dir_str)

            for rf in rules_files:
                if rf.exists() and rf.stat().st_size > 0:
                    try:
                        content = safe_sync_io.read_text(rf.parent, rf.name)

                        if rf.name == "CLAUDE.md" and CLAUDE_HEADER_METADATA.strip() in content:
                            content = content.replace(CLAUDE_HEADER_METADATA, "").strip()

                        safe_sync_io.ensure_directory(library_path)
                        safe_sync_io.write_text(lib_root_file.parent, lib_root_file.name, content)

                        return True, f"Khởi tạo AGENTS.md cho Central Library từ {agent_name} ({rf.name})."
                    except ValueError:
                        raise
                    except Exception as e:
                        return False, f"Lỗi đọc rules từ {agent_name}: {e}"

        return False, "Chưa tìm thấy rules nào để khởi tạo."

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
                    safe_sync_io.write_text(target_file.parent, target_file.name, base_content)
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
                    safe_sync_io.write_text(target_file.parent, target_file.name, claude_content)
                    deployed.append("claude (CLAUDE.md)")

        return deployed
