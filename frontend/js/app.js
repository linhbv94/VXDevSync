function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
}

// VXDevSync Frontend Application Logic

const SVG_ICONS = {
  eyeOff: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>`,
  eye: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>`,
  pull: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 17V3"/><path d="m6 11 6 6 6-6"/><path d="M19 21H5"/></svg>`,
  push: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m18 9-6-6-6 6"/><path d="M12 3v14"/><path d="M5 21h14"/></svg>`,
  trash: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>`,
  arrowDown: `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="m19 12-7 7-7-7"/></svg>`,
  arrowUp: `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></svg>`,
  alertTriangle: `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  check: `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`
};

const state = {
  isReady: false,
  isFirstRun: false,
  config: null,
  activeTab: "git-sync-view",
  gitRepos: [],
  selectedRepoPaths: new Set(),
  gitFilter: "all",
  gitSearchQuery: "",
  skills: [],
  skillsSearchQuery: "",
  activeSettingsTab: "general",
  skillToDelete: "",
  isScanningGit: false,
  isSyncingGit: false,
  isSyncingSkills: false,
  lastSyncResults: {},
  currentErrorResults: []
};

// Khởi chạy khi DOM và pywebview sẵn sàng
window.addEventListener("pywebviewready", initApp);
document.addEventListener("DOMContentLoaded", () => {
  setupModeSwitcher();
  // Dự phòng nếu pywebviewready đã phát trước đó
  if (window.pywebview && window.pywebview.api) {
    initApp();
  }
});

async function initApp() {
  if (state.isReady) return;
  state.isReady = true;

  try {
    const initialState = await window.pywebview.api.get_initial_state();
    window.applyChromePlatform(initialState.platform);
    state.config = initialState;
    state.isFirstRun = initialState.is_first_run;
    if (initialState.config_error) showToast(initialState.config_error, "danger");

    setupEventListeners();
    updateUIFromConfig();
    // Startup checks never install or interrupt a sync automatically.
    window.pywebview.api.check_updates().then(result => {
      if (result.success && result.available) showToast(`Có bản ${result.version}. Mở Cài đặt → Cập nhật để cài.`, "info");
    }).catch(() => {});

    if (state.isFirstRun) {
      openOnboardingModal();
    } else {
      // Mở tab mặc định
      const defTab = state.config.general.default_tab || "git_sync";
      switchTab(defTab === "skills_sync" ? "skills-sync-view" : "git-sync-view");
      
      // Tự động quét Git nếu cấu hình cho phép
      if (state.config.general.auto_scan_on_startup) {
        triggerGitScan();
      }
    }
  } catch (err) {
    console.error("Lỗi khởi tạo ứng dụng:", err);
    showToast("Lỗi kết nối với Python backend", "danger");
  }
}

// Cập nhật các thành phần UI từ Config
function updateUIFromConfig() {
  const gitCfg = state.config.git_sync;
  const skillsCfg = state.config.skills_sync;

  // Titlebar Workspace Path
  const currentPath = gitCfg.scan_path || "Chưa chọn workspace";
  const labelElem = document.getElementById("label-current-workspace");
  if (labelElem) {
    labelElem.textContent = currentPath.split(/[\\/]/).filter(Boolean).pop() || currentPath;
    labelElem.parentElement.title = `Workspace: ${currentPath}`;
  }

  // Dropdown Recent Workspaces
  renderRecentWorkspacesDropdown();

  // Central Skills Library Header
  const libPathElem = document.getElementById("label-skills-lib-path");
  if (libPathElem) {
    libPathElem.textContent = skillsCfg.skills_lib || "Chưa cấu hình";
  }

  // Agent Toggles
  const agents = skillsCfg.agents || {};
  setCheckbox("toggle-agent-anti", agents.anti === 1);
  setCheckbox("toggle-agent-codex", agents.codex === 1);
  setCheckbox("toggle-agent-claude", agents.claude === 1);

  updateAgentCardStatus("anti", agents.anti === 1);
  updateAgentCardStatus("codex", agents.codex === 1);
  updateAgentCardStatus("claude", agents.claude === 1);
}

function setCheckbox(id, val) {
  const el = document.getElementById(id);
  if (el) el.checked = !!val;
}

function updateAgentCardStatus(agentKey, isActive) {
  const cardElem = document.getElementById(`card-agent-${agentKey}`);
  if (cardElem) {
    if (isActive) {
      cardElem.classList.remove("agent-disabled");
    } else {
      cardElem.classList.add("agent-disabled");
    }
  }
  const statusElem = document.getElementById(`status-agent-${agentKey}`);
  if (statusElem) {
    statusElem.innerHTML = `
      <span class="status-dot ${isActive ? 'active' : 'inactive'}"></span>
      <span class="status-text">${isActive ? 'Đang kích hoạt' : 'Chưa kích hoạt'}</span>
    `;
  }
}

function setupModeSwitcher() {
  // Tab Switcher
  document.getElementById("tab-btn-git").addEventListener("click", () => switchTab("git-sync-view"));
  document.getElementById("tab-btn-skills").addEventListener("click", () => switchTab("skills-sync-view"));

}

// Thiết lập toàn bộ Event Listeners
function setupEventListeners() {
  // Rescan Icon
  document.getElementById("btn-rescan-all").addEventListener("click", () => {
    if (state.activeTab === "git-sync-view") {
      triggerGitScan();
    } else {
      triggerSkillsScan();
    }
  });

  // Open Workspace Folder
  document.getElementById("btn-open-workspace").addEventListener("click", async (e) => {
    // Chỉ kích hoạt picker nếu không click vào dropdown
    if (e.target.closest(".recent-dropdown")) return;
    try {
      const res = await window.pywebview.api.pick_folder(state.config.git_sync.scan_path);
      if (!res.canceled && res.path) {
        state.config.git_sync.scan_path = res.path;
        updateUIFromConfig();
        triggerGitScan(res.path);
      }
    } catch (err) {
      console.error(err);
    }
  });

  // Change Central Skills Library Folder
  document.getElementById("btn-change-skills-lib").addEventListener("click", async () => {
    try {
      const res = await window.pywebview.api.pick_folder(state.config.skills_sync.skills_lib);
      if (!res.canceled && res.path) {
        const updateRes = await window.pywebview.api.set_skills_library_path(res.path);
        if (updateRes.success) {
          state.config.skills_sync.skills_lib = updateRes.skills_lib;
          updateUIFromConfig();
          showToast("Đã cập nhật Thư viện Kỹ năng", "success");
          triggerSkillsScan();
        } else {
          showToast(updateRes.error || "Lỗi cập nhật đường dẫn", "danger");
        }
      }
    } catch (err) {
      console.error(err);
    }
  });

  // Settings Modal Controls
  document.getElementById("btn-open-settings").addEventListener("click", openSettingsModal);
  document.getElementById("btn-close-settings").addEventListener("click", closeSettingsModal);
  document.getElementById("btn-settings-save").addEventListener("click", saveSettingsFromModal);
  document.getElementById("btn-settings-reset").addEventListener("click", resetSettingsDefault);

  // Settings Sidebar navigation
  document.querySelectorAll(".settings-nav-item").forEach(item => {
    item.addEventListener("click", (e) => {
      document.querySelectorAll(".settings-nav-item").forEach(i => i.classList.remove("active"));
      e.currentTarget.classList.add("active");
      const tab = e.currentTarget.getAttribute("data-settings-tab");
      state.activeSettingsTab = tab;
      renderSettingsTabContent(tab);
    });
  });

  // Git Search & Filter
  document.getElementById("git-search-input").addEventListener("input", (e) => {
    state.gitSearchQuery = e.target.value.toLowerCase().trim();
    renderGitReposTable();
  });

  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      e.currentTarget.classList.add("active");
      state.gitFilter = e.currentTarget.getAttribute("data-filter");
      renderGitReposTable();
    });
  });

  // Git Checkbox Select All
  document.getElementById("chk-select-all").addEventListener("change", (e) => {
    const isChecked = e.target.checked;
    const visibleRepos = getFilteredGitRepos();
    if (isChecked) {
      visibleRepos.forEach(r => state.selectedRepoPaths.add(r.path));
    } else {
      visibleRepos.forEach(r => state.selectedRepoPaths.delete(r.path));
    }
    updateSelectionUI();
    renderGitReposTable();
  });

  // Git Select Changed Only
  document.getElementById("btn-select-changed").addEventListener("click", () => {
    state.selectedRepoPaths.clear();
    state.gitRepos.forEach(r => {
      if (!r.is_ignored && (r.is_dirty || r.behind_count > 0 || r.ahead_count > 0)) {
        state.selectedRepoPaths.add(r.path);
      }
    });
    updateSelectionUI();
    renderGitReposTable();
    showToast(`Đã chọn ${state.selectedRepoPaths.size} repos có thay đổi`, "info");
  });

  // Git Smart Sync Changed Directly (One-Click Sync)
  document.getElementById("btn-smart-sync-changed").addEventListener("click", () => {
    const activeRepos = state.gitRepos.filter(r => !r.is_ignored);
    const changed = activeRepos.filter(r => r.is_dirty || r.behind_count > 0 || r.ahead_count > 0);
    if (changed.length === 0) {
      showToast("Tất cả repository đã đồng bộ!", "info");
      return;
    }
    executeGitAction("smart_sync", changed.map(r => r.path));
  });

  // Git Pull All Button
  const btnPullAll = document.getElementById("btn-pull-all");
  if (btnPullAll) {
    btnPullAll.addEventListener("click", () => {
      const activeRepos = state.gitRepos.filter(r => !r.is_ignored && r.has_remote);
      if (activeRepos.length === 0) {
        showToast("Không tìm thấy repository có remote để Pull", "info");
        return;
      }
      const behindRepos = activeRepos.filter(r => r.behind_count > 0);
      if (behindRepos.length === 0) {
        showToast("Không có repository nào cần Pull (Tất cả đã ở phiên bản mới nhất)", "info");
        return;
      }
      executeGitAction("pull", behindRepos.map(r => r.path));
    });
  }

  // Git Push All Button
  const btnPushAll = document.getElementById("btn-push-all");
  if (btnPushAll) {
    btnPushAll.addEventListener("click", () => {
      const activeRepos = state.gitRepos.filter(r => !r.is_ignored && r.has_remote);
      const aheadRepos = activeRepos.filter(r => r.ahead_count > 0);
      if (aheadRepos.length === 0) {
        showToast("Không có repository nào có commit mới cần Push", "info");
        return;
      }
      executeGitAction("push", aheadRepos.map(r => r.path));
    });
  }

  // Sync Errors Modal Controls
  const btnCloseSyncErrors = document.getElementById("btn-close-sync-errors");
  if (btnCloseSyncErrors) btnCloseSyncErrors.addEventListener("click", closeSyncErrorsModal);

  const btnDismissSyncErrors = document.getElementById("btn-dismiss-sync-errors");
  if (btnDismissSyncErrors) btnDismissSyncErrors.addEventListener("click", closeSyncErrorsModal);

  const btnCopySyncErrors = document.getElementById("btn-copy-sync-errors");
  if (btnCopySyncErrors) btnCopySyncErrors.addEventListener("click", copySyncErrorsLog);

  const btnRetryFailedSync = document.getElementById("btn-retry-failed-sync");
  if (btnRetryFailedSync) btnRetryFailedSync.addEventListener("click", retryFailedSyncRepos);

  // Git Floating Action Bar Buttons (Icon-Only Control Bar like VXPhotos)
  document.getElementById("btn-action-smart-sync").addEventListener("click", () => executeGitAction("smart_sync", Array.from(state.selectedRepoPaths)));
  document.getElementById("btn-action-pull").addEventListener("click", () => executeGitAction("pull", Array.from(state.selectedRepoPaths)));
  document.getElementById("btn-action-push").addEventListener("click", () => executeGitAction("push", Array.from(state.selectedRepoPaths)));
  document.getElementById("btn-action-clear-selection").addEventListener("click", () => {
    state.selectedRepoPaths.clear();
    updateSelectionUI();
    renderGitReposTable();
  });

  // Phím tắt Escape để đóng modal hoặc hủy chọn tất cả
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const syncErrorsModal = document.getElementById("modal-sync-errors");
      if (syncErrorsModal && syncErrorsModal.classList.contains("active")) {
        closeSyncErrorsModal();
        return;
      }
      if (state.selectedRepoPaths.size > 0 && state.currentTab === "git-sync-view") {
        state.selectedRepoPaths.clear();
        updateSelectionUI();
        renderGitReposTable();
      }
    }
  });

  // Agent Toggles
  ["anti", "codex", "claude"].forEach(ag => {
    const toggle = document.getElementById(`toggle-agent-${ag}`);
    if (toggle) {
      toggle.addEventListener("change", async (e) => {
        const isChecked = e.target.checked;
        updateAgentCardStatus(ag, isChecked);
        if (state.config && state.config.skills_sync) {
          state.config.skills_sync.agents[ag] = isChecked ? 1 : 0;
        }
        try {
          await window.pywebview.api.toggle_agent(ag, isChecked);
          triggerSkillsScan();
        } catch (err) {
          console.error(err);
        }
      });
    }
  });

  // Skills Unified Sync Button
  document.getElementById("btn-sync-skills-unified").addEventListener("click", executeSkillsUnifiedSync);

  // Skills Search
  document.getElementById("skills-search-input").addEventListener("input", (e) => {
    state.skillsSearchQuery = e.target.value.toLowerCase().trim();
    renderSkillsTable();
  });

  // Cascade Delete Confirm Modal Buttons
  document.getElementById("btn-cancel-delete").addEventListener("click", closeCascadeDeleteModal);
  document.getElementById("btn-confirm-delete").addEventListener("click", confirmCascadeDelete);

  // Onboarding Wizard Buttons
  document.getElementById("btn-onboard-pick-scan").addEventListener("click", async () => {
    const res = await window.pywebview.api.pick_folder();
    if (!res.canceled && res.path) {
      document.getElementById("onboard-scan-path").value = res.path;
    }
  });
  document.getElementById("btn-onboard-pick-skills").addEventListener("click", async () => {
    const currentVal = document.getElementById("onboard-skills-lib").value;
    const res = await window.pywebview.api.pick_folder(currentVal);
    if (!res.canceled && res.path) {
      document.getElementById("onboard-skills-lib").value = res.path;
      const repoInput = document.getElementById("onboard-skills-repo");
      if (!repoInput.value.trim() && window.pywebview.api.get_git_remote_url) {
        try {
          const remoteRes = await window.pywebview.api.get_git_remote_url(res.path);
          if (remoteRes && remoteRes.success && remoteRes.url) {
            repoInput.value = remoteRes.url;
            showToast("Đã tự động nhận diện Git Remote URL từ thư mục", "info");
          }
        } catch (_) {}
      }
    }
  });
  document.getElementById("btn-onboard-finish").addEventListener("click", finishOnboarding);
}

// Chuyển Tab Mode Switcher
function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll(".mode-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".view-pane").forEach(pane => pane.classList.remove("active"));

  if (tabId === "git-sync-view") {
    document.getElementById("tab-btn-git").classList.add("active");
    document.getElementById("git-sync-view").classList.add("active");
  } else {
    document.getElementById("tab-btn-skills").classList.add("active");
    document.getElementById("skills-sync-view").classList.add("active");
    if (state.config && window.pywebview?.api && state.skills.length === 0) {
      triggerSkillsScan();
    }
  }
}

// ==========================================
// PHÂN HỆ 1: GIT MULTI-SYNC LOGIC
// ==========================================

async function triggerGitScan(customPath = null) {
  if (state.isScanningGit) return;
  state.isScanningGit = true;
  state.selectedRepoPaths.clear();
  updateSelectionUI();

  const summaryElem = document.getElementById("git-scan-summary");
  summaryElem.textContent = "Đang quét workspace và kiểm tra remote...";

  try {
    const res = await window.pywebview.api.scan_git_workspace(customPath);
    if (res.success) {
      state.gitRepos = res.repos || [];
      summaryElem.textContent = `Workspace: ${res.scan_path} • Thời gian quét: ${res.elapsed_sec}s • Tìm thấy: ${res.total_count} repos`;
      updateGitCounts();
      renderGitReposTable();
    } else {
      summaryElem.textContent = `Lỗi: ${res.error}`;
      showToast(res.error, "danger");
    }
  } catch (err) {
    console.error(err);
    summaryElem.textContent = "Lỗi thực thi quét Git";
  } finally {
    state.isScanningGit = false;
  }
}

function updateGitCounts() {
  const all = state.gitRepos.length;
  const activeRepos = state.gitRepos.filter(r => !r.is_ignored);
  const syncNeeded = activeRepos.filter(r => r.behind_count > 0 || r.ahead_count > 0).length;
  const clean = activeRepos.filter(r => r.is_clean && r.behind_count === 0 && r.ahead_count === 0).length;
  const dirty = activeRepos.filter(r => r.is_dirty || r.is_diverged).length;
  const changed = activeRepos.filter(r => r.is_dirty || r.behind_count > 0 || r.ahead_count > 0).length;
  const pullCount = activeRepos.filter(r => r.has_remote && r.behind_count > 0).length;
  const pushCount = activeRepos.filter(r => r.has_remote && r.ahead_count > 0).length;

  document.getElementById("count-all").textContent = all;
  document.getElementById("count-sync").textContent = syncNeeded;
  document.getElementById("count-clean").textContent = clean;
  document.getElementById("count-dirty").textContent = dirty;
  document.getElementById("count-changed").textContent = changed;
  const countSyncNow = document.getElementById("count-sync-now");
  if (countSyncNow) countSyncNow.textContent = changed;
  const countPullNow = document.getElementById("count-pull-now");
  if (countPullNow) countPullNow.textContent = pullCount;
  const countPushNow = document.getElementById("count-push-now");
  if (countPushNow) countPushNow.textContent = pushCount;
}

function getFilteredGitRepos() {
  const filtered = state.gitRepos.filter(repo => {
    // Lọc theo search input
    if (state.gitSearchQuery) {
      const match = repo.name.toLowerCase().includes(state.gitSearchQuery) ||
                    repo.rel_path.toLowerCase().includes(state.gitSearchQuery);
      if (!match) return false;
    }

    // Lọc theo filter tabs
    if (state.gitFilter === "needs_sync") {
      return !repo.is_ignored && (repo.behind_count > 0 || repo.ahead_count > 0);
    } else if (state.gitFilter === "clean") {
      return !repo.is_ignored && repo.is_clean && repo.behind_count === 0 && repo.ahead_count === 0;
    } else if (state.gitFilter === "dirty") {
      return !repo.is_ignored && (repo.is_dirty || repo.is_diverged);
    }
    return true;
  });

  // Đẩy các repo bị loại trừ (is_ignored) xuống cuối danh sách
  return filtered.sort((a, b) => {
    const aIgnored = !!a.is_ignored;
    const bIgnored = !!b.is_ignored;
    if (aIgnored === bIgnored) return 0;
    return aIgnored ? 1 : -1;
  });
}

function renderGitReposTable() {
  const tbody = document.getElementById("git-repos-tbody");
  tbody.innerHTML = "";

  const repos = getFilteredGitRepos();
  if (repos.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 24px;">Không tìm thấy repository phù hợp</td></tr>`;
    return;
  }

  repos.forEach(repo => {
    const isIgnored = !!repo.is_ignored;
    const isSelected = !isIgnored && state.selectedRepoPaths.has(repo.path);
    const tr = document.createElement("tr");
    tr.className = (isIgnored ? "row-ignored" : "") + (isSelected ? " selected" : "");
    tr.setAttribute("data-repo-path", repo.path);

    // Trạng thái File badge
    let fileBadge = `<span class="badge badge-success">${SVG_ICONS.check} Clean</span>`;
    if (repo.is_dirty) {
      fileBadge = `<span class="badge badge-danger">Dirty (${repo.dirty_files_count})</span>`;
    }

    // Git Sync status badge & Action buttons
    let syncBadge = `<span class="badge badge-success">${SVG_ICONS.check} Up-to-date</span>`;
    if (isIgnored) {
      syncBadge = `<span class="badge badge-muted">${SVG_ICONS.eyeOff} Loại trừ</span>`;
    } else if (repo.is_diverged) {
      syncBadge = `<span class="badge badge-danger">${SVG_ICONS.alertTriangle} Diverged</span>`;
    } else if (repo.behind_count > 0) {
      syncBadge = `<span class="badge badge-warning">${SVG_ICONS.arrowDown} Behind (${repo.behind_count})</span>`;
    } else if (repo.ahead_count > 0) {
      syncBadge = `<span class="badge badge-cyan">${SVG_ICONS.arrowUp} Ahead (${repo.ahead_count})</span>`;
    } else if (!repo.has_remote) {
      syncBadge = `<span class="badge badge-muted">No Remote</span>`;
    }

    // Offset
    const offsetStr = isIgnored ? "--" : `+${repo.ahead_count} / -${repo.behind_count}`;
    const suggestedActionStr = isIgnored ? "Đã loại trừ" : repo.suggested_action;

    // Kiểm tra nếu repo này vừa bị sync lỗi
    const lastResult = state.lastSyncResults?.[repo.path];
    let syncErrorIndicator = "";
    if (lastResult && !lastResult.success) {
      syncErrorIndicator = `
        <div style="margin-top: 3px;">
          <button type="button" class="badge badge-danger btn-view-repo-error" data-path="${escapeHtml(repo.path)}" style="cursor: pointer; padding: 2px 6px; border: none; font-family: inherit; font-size: 10px; display: inline-flex; align-items: center; gap: 4px;" aria-label="Xem chi tiết lỗi ${escapeHtml(lastResult.action.toUpperCase())} của repository ${escapeHtml(repo.name)}" title="Bấm để xem chi tiết lỗi: ${escapeHtml(lastResult.message)}">
            <span class="badge-dot badge-dot-danger"></span>Lỗi ${escapeHtml(lastResult.action.toUpperCase())}
          </button>
        </div>
      `;
    }

    tr.innerHTML = `
      <td style="text-align: center;">
        <input type="checkbox" class="repo-checkbox" ${isSelected ? "checked" : ""} ${isIgnored ? "disabled title='Repository đã bị loại trừ'" : ""}>
      </td>
      <td>
        <strong style="color: ${isIgnored ? 'var(--text-muted)' : 'var(--text-primary)'};">${escapeHtml(repo.name)}</strong>
        ${isIgnored ? '<span class="badge badge-muted" style="font-size: 9px; margin-left: 4px; padding: 1px 4px;">Ignored</span>' : ''}
        <div style="font-size: 10px; color: var(--text-muted); font-family: var(--font-mono);">${escapeHtml(repo.rel_path)}</div>
      </td>
      <td>
        <span class="badge badge-muted" style="font-family: var(--font-mono);">${escapeHtml(repo.current_branch)}</span>
      </td>
      <td>${fileBadge}</td>
      <td>${syncBadge}</td>
      <td><span class="offset-text" style="${isIgnored ? 'color: var(--text-muted);' : ''}">${offsetStr}</span></td>
      <td>
        <span style="font-size: 11px; color: var(--text-secondary);">${escapeHtml(suggestedActionStr)}</span>
        ${syncErrorIndicator}
      </td>
      <td style="text-align: right;">
        ${isIgnored
          ? `<button class="table-action-btn btn-unexclude" title="Khôi phục (Bỏ loại trừ)">${SVG_ICONS.eye}</button>
             <button class="table-action-btn" disabled style="opacity: 0.2; cursor: not-allowed;" title="Repo đã bị loại trừ">${SVG_ICONS.pull}</button>
             <button class="table-action-btn" disabled style="opacity: 0.2; cursor: not-allowed;" title="Repo đã bị loại trừ">${SVG_ICONS.push}</button>`
          : `<button class="table-action-btn btn-exclude" title="Loại trừ repo khỏi quét & đồng bộ">${SVG_ICONS.eyeOff}</button>
             <button class="table-action-btn btn-pull" title="Chỉ Pull repo này">${SVG_ICONS.pull}</button>
             <button class="table-action-btn btn-push" title="Chỉ Push repo này">${SVG_ICONS.push}</button>`
        }
      </td>
    `;

    // Row-click Selection (Click anywhere on the row to toggle selection)
    tr.addEventListener("click", (e) => {
      if (isIgnored) return; // Không cho click chọn dòng bị loại trừ
      // Bỏ qua nếu click trực tiếp vào nút action
      if (e.target.closest(".table-action-btn")) return;
      if (e.target.classList.contains("repo-checkbox")) {
        toggleRepoSelection(repo.path, e.target.checked);
        tr.classList.toggle("selected", e.target.checked);
        return;
      }

      const willSelect = !state.selectedRepoPaths.has(repo.path);
      toggleRepoSelection(repo.path, willSelect);
      const chk = tr.querySelector(".repo-checkbox");
      if (chk) chk.checked = willSelect;
      tr.classList.toggle("selected", willSelect);
    });

    // Row Actions
    const btnExclude = tr.querySelector(".btn-exclude");
    if (btnExclude) {
      btnExclude.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleExcludeRepo(repo.name, true);
      });
    }

    const btnUnexclude = tr.querySelector(".btn-unexclude");
    if (btnUnexclude) {
      btnUnexclude.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleExcludeRepo(repo.name, false);
      });
    }

    const btnPull = tr.querySelector(".btn-pull");
    if (btnPull) {
      btnPull.addEventListener("click", (e) => {
        e.stopPropagation();
        executeGitAction("pull", [repo.path]);
      });
    }

    const btnPush = tr.querySelector(".btn-push");
    if (btnPush) {
      btnPush.addEventListener("click", (e) => {
        e.stopPropagation();
        executeGitAction("push", [repo.path]);
      });
    }

    const errBtn = tr.querySelector(".btn-view-repo-error");
    if (errBtn) {
      errBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        const p = errBtn.getAttribute("data-path");
        const errItem = state.lastSyncResults[p];
        if (errItem) {
          openSyncErrorsModal({
            total: 1,
            success_count: 0,
            failed_count: 1,
            results: [errItem]
          });
        }
      });
    }

    tbody.appendChild(tr);
  });
}

function toggleRepoSelection(repoPath, select) {
  if (select) {
    state.selectedRepoPaths.add(repoPath);
  } else {
    state.selectedRepoPaths.delete(repoPath);
  }
  updateSelectionUI();
}

function updateSelectionUI() {
  const count = state.selectedRepoPaths.size;
  const activeCount = state.gitRepos.filter(r => !r.is_ignored).length;
  document.getElementById("selected-status-text").textContent = `Đã chọn: ${count} / ${activeCount} repos`;
  
  const floatingBar = document.getElementById("git-action-bar");
  if (count > 0) {
    floatingBar.style.display = "flex";
    document.getElementById("floating-selected-count").textContent = `${count} đã chọn`;
  } else {
    floatingBar.style.display = "none";
  }

  // Update header checkbox
  const chkSelectAll = document.getElementById("chk-select-all");
  const filtered = getFilteredGitRepos().filter(r => !r.is_ignored);
  const selectedInFiltered = filtered.filter(r => state.selectedRepoPaths.has(r.path)).length;
  if (filtered.length > 0 && selectedInFiltered === filtered.length) {
    chkSelectAll.checked = true;
    chkSelectAll.indeterminate = false;
  } else if (selectedInFiltered > 0) {
    chkSelectAll.checked = false;
    chkSelectAll.indeterminate = true;
  } else {
    chkSelectAll.checked = false;
    chkSelectAll.indeterminate = false;
  }
}

async function toggleExcludeRepo(repoName, shouldExclude) {
  try {
    const res = await window.pywebview.api.toggle_git_ignore(repoName, shouldExclude);
    if (res.success) {
      // 1. Cập nhật state config
      if (state.config && state.config.git_sync) {
        state.config.git_sync.ignore_list = res.ignore_list || [];
      }

      // 2. Cập nhật cờ is_ignored của repo trong danh sách hiện tại
      const repo = state.gitRepos.find(r => r.name === repoName);
      if (repo) {
        repo.is_ignored = shouldExclude;
        if (shouldExclude) {
          state.selectedRepoPaths.delete(repo.path);
          repo.sync_state = "IGNORED";
          repo.suggested_action = "Đã loại trừ";
        }
      }

      // 3. Nếu Modal Settings đang mở ở tab git-sync, render lại ngay lập tức
      const settingsModal = document.getElementById("modal-settings");
      if (settingsModal && settingsModal.classList.contains("active") && state.activeSettingsTab === "git-sync") {
        renderSettingsTabContent("git-sync");
      }

      updateSelectionUI();
      updateGitCounts();
      renderGitReposTable();
      showToast(shouldExclude ? `Đã loại trừ "${repoName}"` : `Đã khôi phục "${repoName}"`, "info");

      // Nếu khôi phục, tự động quét lại ngầm để cập nhật offset chính xác
      if (!shouldExclude) {
        triggerGitScan();
      }
    }
  } catch (err) {
    console.error(err);
    showToast("Lỗi thay đổi trạng thái loại trừ", "danger");
  }
}

async function excludeRepo(repoName) {
  toggleExcludeRepo(repoName, true);
}

async function executeGitAction(action, paths) {
  if (state.isSyncingGit || paths.length === 0) return;
  state.isSyncingGit = true;
  showToast(`Đang thực hiện ${action.toUpperCase()} cho ${paths.length} repos...`, "info");

  try {
    const res = await window.pywebview.api.sync_git_repos(paths, action);
    if (res.success) {
      // Lưu lại kết quả sync của từng repo vào state
      if (res.results) {
        res.results.forEach(item => {
          state.lastSyncResults[item.path] = item;
        });
      }

      const failedCount = res.failed_count !== undefined ? res.failed_count : (res.total - res.success_count);

      if (failedCount > 0) {
        showToast(`Đồng bộ: ${res.success_count}/${res.total} thành công, ${failedCount} repo gặp sự cố`, "warning", 5000);
        openSyncErrorsModal(res);
      } else {
        showToast(`Hoàn tất: Đã ${action.toUpperCase()} thành công cả ${res.total} repos`, "success");
      }
      triggerGitScan();
    } else {
      showToast(res.error || "Lỗi thực thi Git action", "danger");
    }
  } catch (err) {
    console.error(err);
    showToast("Lỗi thực thi Git action", "danger");
  } finally {
    state.isSyncingGit = false;
  }
}

// Modal Chi tiết Lỗi Đồng bộ Git
function openSyncErrorsModal(syncResponse) {
  const modal = document.getElementById("modal-sync-errors");
  if (!modal) return;

  // Lưu phần tử active trước khi mở modal để khôi phục focus khi đóng
  state.lastActiveElement = document.activeElement;

  const results = syncResponse?.results || [];
  const errors = results.filter(r => !r.success);
  state.currentErrorResults = errors;

  const titleEl = document.getElementById("sync-errors-title");
  const summaryEl = document.getElementById("sync-errors-summary");
  const listEl = document.getElementById("sync-errors-list");
  const iconEl = document.getElementById("sync-errors-icon");
  const retryBtn = document.getElementById("btn-retry-failed-sync");

  if (errors.length === 0) {
    if (titleEl) titleEl.textContent = "Kết quả Đồng bộ Git";
    if (iconEl) iconEl.style.color = "var(--color-success)";
    if (summaryEl) {
      summaryEl.innerHTML = `<span style="color: var(--color-success);">Hoàn tất: Đã đồng bộ thành công cả ${syncResponse.total || results.length} repositories.</span>`;
    }
    if (listEl) listEl.innerHTML = "";
    if (retryBtn) retryBtn.style.display = "none";
  } else {
    if (titleEl) titleEl.textContent = `Phát hiện Lỗi Đồng bộ Git (${errors.length} repo)`;
    if (iconEl) iconEl.style.color = "var(--color-danger)";
    if (summaryEl) {
      summaryEl.innerHTML = `Đồng bộ: <strong>${syncResponse.success_count || (syncResponse.total - errors.length)}/${syncResponse.total || results.length}</strong> repos thành công. Có <strong style="color: var(--color-danger);">${errors.length}</strong> repository gặp sự cố:`;
    }
    if (retryBtn) retryBtn.style.display = "inline-flex";

    if (listEl) {
      listEl.innerHTML = errors.map(item => `
        <div class="sync-error-card" style="background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: var(--radius-md); padding: 12px; display: flex; flex-direction: column; gap: 8px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="badge badge-danger"><span class="badge-dot badge-dot-danger"></span>${escapeHtml(item.action.toUpperCase())} THẤT BẠI</span>
              <strong style="color: var(--text-primary); font-family: var(--font-mono); font-size: 13px;">${escapeHtml(item.name || item.path.split('/').pop())}</strong>
            </div>
            <span style="font-size: 10px; color: var(--text-muted); font-family: var(--font-mono);">${escapeHtml(item.path)}</span>
          </div>

          <div style="font-size: 11px; color: #fbbf24; font-weight: 500; line-height: 1.4;">
            ${escapeHtml(item.message)}
          </div>

          ${item.cmd ? `
            <div style="font-size: 10.5px; color: var(--text-muted); font-family: var(--font-mono); background: rgba(255, 255, 255, 0.04); padding: 4px 8px; border-radius: 4px; display: flex; align-items: center; gap: 6px;">
              <span style="color: var(--accent-primary);">&gt;</span>
              <span>${escapeHtml(item.cmd)}</span>
            </div>
          ` : ''}

          ${item.raw_error ? `
            <div style="display: flex; flex-direction: column; gap: 4px;">
              <div style="font-size: 10px; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Git Output:</div>
              <pre style="margin: 0; padding: 10px; background: #08090d; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; font-family: var(--font-mono); font-size: 11px; line-height: 1.5; color: #f87171; white-space: pre-wrap; word-break: break-word; max-height: 140px; overflow-y: auto;">${escapeHtml(item.raw_error)}</pre>
            </div>
          ` : ''}
        </div>
      `).join("");
    }
  }

  modal.classList.add("active");
  const closeBtn = document.getElementById("btn-close-sync-errors");
  if (closeBtn) closeBtn.focus();
}

function closeSyncErrorsModal() {
  const modal = document.getElementById("modal-sync-errors");
  if (modal) modal.classList.remove("active");

  // Trả focus về phần tử kích hoạt trước đó
  if (state.lastActiveElement && typeof state.lastActiveElement.focus === "function") {
    state.lastActiveElement.focus();
    state.lastActiveElement = null;
  }
}

function copySyncErrorsLog() {
  if (!state.currentErrorResults || state.currentErrorResults.length === 0) {
    showToast("Không có log lỗi để sao chép", "info");
    return;
  }

  const lines = [
    "==================================================",
    "BÁO CÁO LỖI ĐỒNG BỘ GIT — VXDevSync",
    `Thời gian: ${new Date().toLocaleString()}`,
    "==================================================",
    ""
  ];

  state.currentErrorResults.forEach((item, idx) => {
    lines.push(`[${idx + 1}/${state.currentErrorResults.length}] Repo: ${item.name || item.path}`);
    lines.push(`    Đường dẫn: ${item.path}`);
    lines.push(`    Thao tác: ${item.action.toUpperCase()}`);
    if (item.cmd) lines.push(`    Lệnh chạy: ${item.cmd}`);
    lines.push(`    Tóm tắt: ${item.message}`);
    if (item.raw_error) {
      lines.push("    Chi tiết lỗi (Git Stderr):");
      lines.push(item.raw_error.split("\n").map(l => "      " + l).join("\n"));
    }
    lines.push("--------------------------------------------------");
  });

  const fullText = lines.join("\n");
  navigator.clipboard.writeText(fullText).then(() => {
    showToast("Đã sao chép toàn bộ log lỗi vào clipboard", "success");
  }).catch(() => {
    showToast("Không thể ghi vào clipboard", "danger");
  });
}

function retryFailedSyncRepos() {
  if (!state.currentErrorResults || state.currentErrorResults.length === 0) return;

  // Lọc bỏ các repo đã bị loại trừ khỏi danh sách retry
  const activeErrors = state.currentErrorResults.filter(item => {
    const repo = state.gitRepos.find(r => r.path === item.path);
    return repo ? !repo.is_ignored : true;
  });

  if (activeErrors.length === 0) {
    showToast("Tất cả các repository lỗi đều đã bị loại trừ", "info");
    closeSyncErrorsModal();
    return;
  }

  closeSyncErrorsModal();

  // Nhóm các repo theo action ban đầu để bảo toàn chính xác thao tác (pull / push / smart_sync)
  const pullPaths = activeErrors.filter(e => e.action === "pull").map(e => e.path);
  const pushPaths = activeErrors.filter(e => e.action === "push").map(e => e.path);
  const smartPaths = activeErrors.filter(e => e.action !== "pull" && e.action !== "push").map(e => e.path);

  if (pullPaths.length > 0) executeGitAction("pull", pullPaths);
  if (pushPaths.length > 0) executeGitAction("push", pushPaths);
  if (smartPaths.length > 0) executeGitAction("smart_sync", smartPaths);
}

function renderRecentWorkspacesDropdown() {
  const container = document.getElementById("recent-workspaces-list");
  container.innerHTML = "";
  const paths = (state.config.git_sync.recent_paths || []).slice(0, 5);

  if (paths.length === 0) {
    container.innerHTML = `<div style="font-size: 11px; color: var(--text-muted); padding: 4px 8px;">Chưa có thư mục gần đây</div>`;
    return;
  }

  paths.forEach(p => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "recent-item";
    item.textContent = p.split(/[\\/]/).filter(Boolean).pop() || p;
    item.title = p;
    item.addEventListener("click", () => {
      state.config.git_sync.scan_path = p;
      updateUIFromConfig();
      triggerGitScan(p);
    });
    container.appendChild(item);
  });
}

// ==========================================
// PHÂN HỆ 2: SKILLS AUTO-SYNC LOGIC
// ==========================================

async function triggerSkillsScan() {
  try {
    const res = await window.pywebview.api.get_skills_inventory();
    if (res.success) {
      state.skills = res.skills || [];
      document.getElementById("count-skills-total").textContent = res.total_count;
      renderSkillsTable();

      // Đếm số skills của từng agent
      let antiCount = 0, codexCount = 0, claudeCount = 0;
      state.skills.forEach(s => {
        if (s.agents.anti && s.agents.anti.exists) antiCount++;
        if (s.agents.codex && s.agents.codex.exists) codexCount++;
        if (s.agents.claude && s.agents.claude.exists) claudeCount++;
      });
      document.getElementById("count-agent-anti").textContent = `${antiCount} skills`;
      document.getElementById("count-agent-codex").textContent = `${codexCount} skills`;
      document.getElementById("count-agent-claude").textContent = `${claudeCount} skills`;
    }
  } catch (err) {
    console.error(err);
  }
}

function renderSkillsTable() {
  const tbody = document.getElementById("skills-tbody");
  tbody.innerHTML = "";

  const filtered = state.skills.filter(s => {
    if (state.skillsSearchQuery) {
      return s.name.toLowerCase().includes(state.skillsSearchQuery);
    }
    return true;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">Không tìm thấy kỹ năng nào</td></tr>`;
    return;
  }

  filtered.forEach(skill => {
    const tr = document.createElement("tr");

    // Central Library status
    const libBadge = skill.in_library 
      ? `<span class="badge badge-success"><span class="badge-dot badge-dot-success"></span>Có mặt</span>`
      : `<span class="badge badge-muted"><span class="badge-dot badge-dot-muted"></span>Thiếu</span>`;

    // Render helper for agents
    const getAgentBadge = (agentKey) => {
      const p = skill.agents[agentKey];
      if (!p || !p.exists) return `<span class="badge badge-muted"><span class="badge-dot badge-dot-muted"></span>Chưa có</span>`;
      if (p.is_synced) return `<span class="badge badge-success"><span class="badge-dot badge-dot-success"></span>Đồng bộ</span>`;
      return `<span class="badge badge-warning"><span class="badge-dot badge-dot-warning"></span>Lệch hash</span>`;
    };

    tr.innerHTML = `
      <td>
        <strong style="color: var(--text-primary); font-family: var(--font-mono);">${escapeHtml(skill.name)}</strong>
      </td>
      <td>${libBadge}</td>
      <td>${getAgentBadge("anti")}</td>
      <td>${getAgentBadge("codex")}</td>
      <td>${getAgentBadge("claude")}</td>
      <td style="text-align: right;">
        <button class="table-action-btn btn-danger-hover btn-delete-skill" title="Xóa triệt để" style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px;">
          ${SVG_ICONS.trash} <span>Xóa</span>
        </button>
      </td>
    `;

    tr.querySelector(".btn-delete-skill").addEventListener("click", () => {
      openCascadeDeleteModal(skill.name);
    });

    tbody.appendChild(tr);
  });
}

// Unified Smart Sync for Skills & Rules
async function executeSkillsUnifiedSync() {
  if (state.isSyncingSkills) return;
  state.isSyncingSkills = true;

  const hintElem = document.getElementById("skills-sync-hint");
  hintElem.textContent = "Đang đồng bộ Kỹ năng và Quy tắc AGENTS.md / CLAUDE.md...";
  showToast("Bắt đầu Đồng bộ Hợp nhất Kỹ năng & Rules...", "info");

  try {
    const res = await window.pywebview.api.sync_skills_unified();
    if (res.success) {
      hintElem.textContent = `Đã gom ${res.upstream_count} skills mới, phân bổ sang ${res.downstream_agents.length} agents. ${res.git_msg || ""}`;
      showToast("Đồng bộ Kỹ năng & Rules hoàn tất thành công!", "success");
      triggerSkillsScan();
    } else {
      hintElem.textContent = `Lỗi: ${res.error}`;
      showToast(res.error, "danger");
    }
  } catch (err) {
    console.error(err);
    hintElem.textContent = "Lỗi thực thi đồng bộ kỹ năng";
  } finally {
    state.isSyncingSkills = false;
  }
}

// Cascade Delete Modal
function openCascadeDeleteModal(skillName) {
  state.skillToDelete = skillName;
  document.getElementById("delete-skill-target-name").textContent = skillName;
  document.getElementById("modal-cascade-delete").classList.add("active");
}

function closeCascadeDeleteModal() {
  state.skillToDelete = "";
  document.getElementById("modal-cascade-delete").classList.remove("active");
}

async function confirmCascadeDelete() {
  const skillName = state.skillToDelete;
  if (!skillName) return;

  closeCascadeDeleteModal();
  showToast(`Đang xóa vĩnh viễn skill ${skillName}...`, "info");

  try {
    const res = await window.pywebview.api.delete_skills_cascade([skillName]);
    if (res.success) {
      showToast(`Đã xóa ${skillName} và cập nhật GitHub thành công!`, "success");
      triggerSkillsScan();
    } else {
      showToast(res.error || "Lỗi xóa kỹ năng", "danger");
    }
  } catch (err) {
    console.error(err);
    showToast("Lỗi kết nối khi xóa skill", "danger");
  }
}

// ==========================================
// SETTINGS MODAL
// ==========================================

function openSettingsModal() {
  document.getElementById("modal-settings").classList.add("active");
  renderSettingsTabContent(state.activeSettingsTab);
}

function closeSettingsModal() {
  document.getElementById("modal-settings").classList.remove("active");
}

function renderSettingsTabContent(tabKey) {
  const area = document.getElementById("settings-tab-content");
  const cfg = state.config;

  if (tabKey === "general") {
    area.innerHTML = `
      <section class="settings-description settings-form-section"><h4 class="settings-section-title">Giao diện & màu sắc</h4>
        <div class="settings-choice-grid">
          <label class="settings-choice"><input type="radio" name="setting-theme" value="dark" ${cfg.general.theme === "dark" ? "checked" : ""}>Dark Navy</label>
          <label class="settings-choice"><input type="radio" name="setting-theme" value="light" ${cfg.general.theme === "light" ? "checked" : ""}>Light Clean</label>
        </div>
      </section>
      <section class="settings-description settings-form-section"><h4 class="settings-section-title">Ngôn ngữ</h4>
        <div class="settings-radio-row">
          <label><input type="radio" name="setting-lang" value="vi" ${cfg.general.lang === "vi" ? "checked" : ""}>Tiếng Việt</label>
          <label><input type="radio" name="setting-lang" value="en" ${cfg.general.lang === "en" ? "checked" : ""}>English</label>
        </div>
      </section>
      <section class="settings-description settings-form-section"><h4 class="settings-section-title">Khi khởi động</h4>
        <label class="form-label" for="setting-default-tab">Tab mặc định</label>
        <select class="form-input settings-compact-select" id="setting-default-tab">
          <option value="git_sync" ${cfg.general.default_tab === "git_sync" ? "selected" : ""}>Git Multi-Sync</option>
          <option value="skills_sync" ${cfg.general.default_tab === "skills_sync" ? "selected" : ""}>Skills Auto-Sync</option>
        </select>
      </section>`;
  } else if (tabKey === "git-sync") {
    area.innerHTML = `
      <div class="form-group">
        <label class="form-label settings-section-title">Thư mục Workspace Quét Mặc định (scan_path):</label>
        <div class="form-input-row">
          <input type="text" class="form-input" id="setting-scan-path" value="${escapeHtml(cfg.git_sync.scan_path)}">
          <button class="btn-secondary" id="btn-browse-scan-path">Duyệt...</button>
        </div>
      </div>
      <div class="form-group">
        <label class="form-label settings-section-title">Độ sâu quét tối đa (max_depth):</label>
        <input type="number" class="form-input" id="setting-max-depth" value="${escapeHtml(cfg.git_sync.max_depth)}" min="1" max="10">
      </div>
      <div class="form-group">
        <label class="form-label settings-section-title">Danh sách Thư mục Loại trừ (Ignore List):</label>
        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 6px; max-height: 120px; overflow-y: auto;" id="setting-ignore-container">
          ${cfg.git_sync.ignore_list.map(item => `
            <div style="display: flex; justify-content: space-between; padding: 3px 6px; font-size: 11px;">
              <span>${escapeHtml(item)}</span>
              <button class="table-action-btn btn-danger-hover btn-remove-ignore" data-ignore="${escapeHtml(item)}" title="Xóa khỏi danh sách loại trừ">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          `).join("")}
        </div>
        <div class="form-input-row" style="margin-top: 6px;">
          <input type="text" class="form-input" id="setting-new-ignore" placeholder="Nhập tên thư mục bỏ qua...">
          <button class="btn-secondary" id="btn-add-ignore">+ Thêm</button>
        </div>
      </div>
    `;

    document.getElementById("btn-browse-scan-path").addEventListener("click", async () => {
      const res = await window.pywebview.api.pick_folder(cfg.git_sync.scan_path);
      if (!res.canceled && res.path) {
        document.getElementById("setting-scan-path").value = res.path;
      }
    });

    document.getElementById("btn-add-ignore").addEventListener("click", async () => {
      const val = document.getElementById("setting-new-ignore").value.trim();
      if (val && !cfg.git_sync.ignore_list.includes(val)) {
        try {
          const res = await window.pywebview.api.toggle_git_ignore(val, true);
          if (res.success) {
            cfg.git_sync.ignore_list = res.ignore_list || [];
            const r = state.gitRepos.find(x => x.name === val);
            if (r) {
              r.is_ignored = true;
              r.sync_state = "IGNORED";
              r.suggested_action = "Đã loại trừ";
              state.selectedRepoPaths.delete(r.path);
            }
            renderSettingsTabContent("git-sync");
            updateSelectionUI();
            updateGitCounts();
            renderGitReposTable();
            showToast(`Đã thêm "${val}" vào danh sách loại trừ`, "info");
          }
        } catch (err) {
          console.error(err);
        }
      }
    });

    document.querySelectorAll(".btn-remove-ignore").forEach(b => {
      b.addEventListener("click", async (e) => {
        const item = e.currentTarget.getAttribute("data-ignore");
        try {
          const res = await window.pywebview.api.toggle_git_ignore(item, false);
          if (res.success) {
            cfg.git_sync.ignore_list = res.ignore_list || [];
            const r = state.gitRepos.find(x => x.name === item);
            if (r) {
              r.is_ignored = false;
            }
            renderSettingsTabContent("git-sync");
            updateSelectionUI();
            updateGitCounts();
            renderGitReposTable();
            showToast(`Đã xóa "${item}" khỏi danh sách loại trừ`, "info");
            triggerGitScan();
          }
        } catch (err) {
          console.error(err);
        }
      });
    });
  } else if (tabKey === "skills-sync") {
    area.innerHTML = `
      <div class="form-group">
        <label class="form-label settings-section-title">Thư mục Central Skills Library (skills_lib):</label>
        <div class="form-input-row">
          <input type="text" class="form-input" id="setting-skills-lib" value="${escapeHtml(cfg.skills_sync.skills_lib)}">
          <button class="btn-secondary" id="btn-browse-skills-lib">Duyệt...</button>
        </div>
      </div>
      <div class="form-group">
        <label class="form-label settings-section-title">Git Remote URL (Tùy chọn, để trống nếu dùng Offline):</label>
        <input type="text" class="form-input" id="setting-git-repo" value="${escapeHtml(cfg.skills_sync.git_repo)}" placeholder="https://github.com/username/my_skills_library.git">
      </div>
      <div class="form-group">
        <label class="form-label settings-section-title">Quản lý Kỹ năng đã Xóa (Tombstone Manifest):</label>
        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 6px; max-height: 120px; overflow-y: auto;">
          ${(cfg.skills_sync.deleted_skills || []).length === 0 ? '<div style="font-size: 11px; color: var(--text-muted); padding: 4px;">Chưa có kỹ năng nào bị khai tử</div>' : ''}
          ${(cfg.skills_sync.deleted_skills || []).map(item => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 6px; font-size: 11px;">
              <span style="font-family: var(--font-mono); color: var(--color-danger);">${escapeHtml(item.name)}</span>
              <button class="btn-secondary btn-restore-tombstone" data-skill="${escapeHtml(item.name)}" style="font-size: 10px; padding: 2px 6px;">Khôi phục</button>
            </div>
          `).join("")}
        </div>
      </div>
    `;

    document.getElementById("btn-browse-skills-lib").addEventListener("click", async () => {
      const res = await window.pywebview.api.pick_folder(cfg.skills_sync.skills_lib);
      if (!res.canceled && res.path) {
        document.getElementById("setting-skills-lib").value = res.path;
        const repoInput = document.getElementById("setting-git-repo");
        if (repoInput && !repoInput.value.trim() && window.pywebview.api.get_git_remote_url) {
          try {
            const remoteRes = await window.pywebview.api.get_git_remote_url(res.path);
            if (remoteRes && remoteRes.success && remoteRes.url) {
              repoInput.value = remoteRes.url;
              showToast("Đã tự động nhận diện Git Remote URL từ thư mục", "info");
            }
          } catch (_) {}
        }
      }
    });

    document.querySelectorAll(".btn-restore-tombstone").forEach(b => {
      b.addEventListener("click", async (e) => {
        const skillName = e.currentTarget.getAttribute("data-skill");
        await window.pywebview.api.restore_skill(skillName);
        cfg.skills_sync.deleted_skills = cfg.skills_sync.deleted_skills.filter(x => x.name !== skillName);
        showToast(`Đã phục hồi ${skillName} khỏi danh sách Tombstone`, "success");
        renderSettingsTabContent("skills-sync");
        triggerSkillsScan();
      });
    });
  } else if (tabKey === "updates") {
    area.innerHTML = `
      <h4 class="settings-section-title">Cập nhật ứng dụng</h4>
      <div class="settings-info-card">
        <strong>Phiên bản hiện tại: v<span id="settings-current-version"></span></strong>
        <p id="update-status">Kiểm tra bản mới và cài cập nhật khi công việc đã hoàn tất.</p>
        <button id="check-app-update" class="btn-secondary">Kiểm tra cập nhật</button>
        <button id="install-app-update" class="btn-secondary" hidden>Cài và khởi động lại</button>
      </div>`;
    document.getElementById("settings-current-version").textContent = cfg.version;
    const checkButton = document.getElementById("check-app-update");
    const installButton = document.getElementById("install-app-update");
    const status = document.getElementById("update-status");
    checkButton.onclick = async () => {
      checkButton.disabled = true;
      installButton.hidden = true;
      status.textContent = "Đang kiểm tra...";
      try {
        const result = await window.pywebview.api.check_updates();
        status.textContent = result.success ? (result.available ? `Có phiên bản ${result.version}` : "Bạn đang dùng bản mới nhất") : result.error;
        installButton.hidden = !(result.success && result.available);
      } catch (error) { status.textContent = "Không kiểm tra được cập nhật; hãy thử lại."; }
      finally { checkButton.disabled = false; }
    };
    installButton.onclick = async () => {
      if (state.isSyncingGit || state.isSyncingSkills || state.isScanningGit) {
        status.textContent = "Hãy đợi tác vụ đồng bộ hoàn tất trước khi cập nhật.";
        return;
      }
      checkButton.disabled = true;
      installButton.disabled = true;
      status.textContent = "Đang tải gói cập nhật, xác thực chữ ký và giải nén (có thể mất 15-30 giây)...";
      try {
        const updatePromise = window.pywebview.api.install_update();
        const timeoutPromise = new Promise((_, reject) =>
          setTimeout(() => reject(new Error("Quá thời gian chờ phản hồi cập nhật (120s)")), 120000)
        );
        const result = await Promise.race([updatePromise, timeoutPromise]);
        if (result && result.success) {
          status.textContent = "Đã chuẩn bị cập nhật thành công. Ứng dụng đang khởi động lại...";
          showToast("Đã chuẩn bị cập nhật thành công. Đang khởi động lại...", "info");
        } else {
          status.textContent = result?.error || "Cập nhật thất bại; bạn có thể thử lại.";
          checkButton.disabled = false;
          installButton.disabled = false;
        }
      } catch (error) {
        status.textContent = "Cập nhật thất bại: " + (error?.message || "Lỗi kết nối; hãy thử lại.");
        checkButton.disabled = false;
        installButton.disabled = false;
      }
    };
  } else if (tabKey === "about") {
    area.innerHTML = `
      <div class="settings-app-card">
        <div class="settings-app-icon" aria-hidden="true"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m8 6-6 6 6 6m8-12 6 6-6 6"/></svg></div>
        <div><h2>VXDevSync <span class="settings-version" id="settings-about-version"></span></h2>
        <p class="settings-tagline">Đồng bộ Git và thư viện kỹ năng AI</p><p class="settings-author">Bùi Việt Linh</p>
        <a href="https://github.com/linhbv94" target="_blank" rel="noopener noreferrer">GitHub · Bùi Việt Linh ↗</a></div>
      </div>
      <section class="settings-description"><h4 class="settings-section-title">Về VXDevSync</h4>
        <p>Quản lý trạng thái và đồng bộ nhiều Git repository trong cùng workspace. Đồng bộ thư viện kỹ năng và quy tắc cho Antigravity, Codex và Claude Code từ một giao diện chung.</p>
      </section>
      <section class="settings-description"><strong>Công nghệ nền tảng:</strong><ul><li>Python + pywebview (WebView native)</li><li>HTML/CSS/JavaScript</li><li>Git CLI · thư viện kỹ năng dùng chung</li></ul></section>`;
    document.getElementById("settings-about-version").textContent = `v${cfg.version}`;
  } else if (tabKey === "support") {
    area.innerHTML = `
      <section class="settings-support-banner">
        <div class="settings-coffee-icon" aria-hidden="true"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 8h12v8a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V8Zm12 1h2a3 3 0 0 1 0 6h-2M7 2v3m5-3v3"/></svg></div>
        <div><h3>Mời tôi ly cà phê</h3>
        <p>Cảm ơn bạn đã sử dụng VXDevSync! Nếu ứng dụng hữu ích, bạn có thể mời tôi một ly cà phê để tiếp thêm động lực phát triển.</p></div>
      </section>
      <section class="settings-qr-card">
        <div class="settings-qr-paper"><img src="assets/support_qr.png" alt="Mã VietQR ủng hộ tác giả, dùng chung với VXMedia"><span>VietQR • Napas247</span></div>
        <p>Mở ứng dụng ngân hàng và quét mã QR để mời tác giả một ly cà phê. Cảm ơn sự ủng hộ của bạn!</p>
      </section>`;
  }
}

async function saveSettingsFromModal() {
  const cfg = state.config;
  
  // Read current fields if available
  const langEl = document.querySelector('[name="setting-lang"]:checked');
  if (langEl) cfg.general.lang = langEl.value;

  const themeEl = document.querySelector('[name="setting-theme"]:checked');
  if (themeEl) cfg.general.theme = themeEl.value;

  const tabEl = document.getElementById("setting-default-tab");
  if (tabEl) cfg.general.default_tab = tabEl.value;

  const scanEl = document.getElementById("setting-scan-path");
  if (scanEl) cfg.git_sync.scan_path = scanEl.value;

  const depthEl = document.getElementById("setting-max-depth");
  if (depthEl) cfg.git_sync.max_depth = parseInt(depthEl.value, 10) || 3;

  const libEl = document.getElementById("setting-skills-lib");
  if (libEl) cfg.skills_sync.skills_lib = libEl.value;

  const repoEl = document.getElementById("setting-git-repo");
  if (repoEl) cfg.skills_sync.git_repo = repoEl.value;

  try {
    const res = await window.pywebview.api.save_config({
      general: cfg.general,
      git_sync: cfg.git_sync,
      skills_sync: cfg.skills_sync
    });
    if (res.success) {
      showToast("Đã lưu cài đặt", "success");
      updateUIFromConfig();
      closeSettingsModal();
    }
  } catch (err) {
    console.error(err);
  }
}

function resetSettingsDefault() {
  if (confirm("Khôi phục cài đặt mặc định?")) {
    state.config.git_sync.max_depth = 3;
    state.config.git_sync.max_concurrency = 8;
    renderSettingsTabContent(state.activeSettingsTab);
  }
}

// Onboarding Modal
function openOnboardingModal() {
  document.getElementById("modal-onboarding").classList.add("active");
  document.getElementById("onboard-scan-path").value = state.config.git_sync.scan_path || "";
  document.getElementById("onboard-skills-lib").value = state.config.skills_sync.skills_lib || "";
  document.getElementById("onboard-skills-repo").value = state.config.skills_sync.git_repo || "";
}

async function finishOnboarding() {
  const scanPath = document.getElementById("onboard-scan-path").value.trim();
  const skillsLib = document.getElementById("onboard-skills-lib").value.trim();
  const skillsRepo = document.getElementById("onboard-skills-repo").value.trim();

  if (scanPath) state.config.git_sync.scan_path = scanPath;
  if (skillsLib) state.config.skills_sync.skills_lib = skillsLib;
  if (skillsRepo !== undefined) state.config.skills_sync.git_repo = skillsRepo;

  try {
    const res = await window.pywebview.api.save_config({
      git_sync: state.config.git_sync,
      skills_sync: state.config.skills_sync
    });
    if (res && res.success) {
      document.getElementById("modal-onboarding").classList.remove("active");
      updateUIFromConfig();
      triggerGitScan();
      showToast("Thiết lập ban đầu hoàn tất!", "success");
    } else {
      showToast(res?.error || "Không thể lưu cấu hình khởi tạo", "danger");
    }
  } catch (err) {
    console.error(err);
    showToast("Không thể lưu cấu hình khởi tạo", "danger");
  }
}

// Toast Helper
function showToast(message, type = "info", duration = 3000) {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = "toast";
  if (type === "success") toast.style.borderLeftColor = "var(--color-success)";
  if (type === "danger") toast.style.borderLeftColor = "var(--color-danger)";
  if (type === "warning") toast.style.borderLeftColor = "var(--color-warning)";
  toast.textContent = message;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.2s ease";
    setTimeout(() => toast.remove(), 200);
  }, duration);
}
