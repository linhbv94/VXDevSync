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
    startUpdateUI();

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
    console.error(devText("Lỗi khởi tạo ứng dụng:"), err);
    showToast(devText("Lỗi kết nối với Python backend"), "danger");
  }
}

// Cập nhật các thành phần UI từ Config
function updateUIFromConfig() {
  document.documentElement.dataset.theme = state.config.general.theme;
  document.documentElement.lang = state.config.general.lang;
  window.applyUiLanguage();
  window.pywebview?.api.set_ui_language?.(state.config.general.lang)?.catch(console.error);
  const gitCfg = state.config.git_sync;
  const skillsCfg = state.config.skills_sync;

  // Titlebar Workspace Path
  const currentPath = gitCfg.scan_path || devText("Chưa chọn workspace");
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
    libPathElem.textContent = skillsCfg.skills_lib || devText("Chưa cấu hình");
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
      <span class="status-text">${isActive ? devText("Đang kích hoạt") : devText("Chưa kích hoạt")}</span>
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
          showToast(devText("Đã cập nhật Thư viện Kỹ năng"), "success");
          triggerSkillsScan();
        } else {
          showToast(updateRes.error || devText("Lỗi cập nhật đường dẫn"), "danger");
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
    showToast((devText("Đã chọn ") + (state.selectedRepoPaths.size) + devText(" repos có thay đổi")), "info");
  });

  // Git Smart Sync Changed Directly (One-Click Sync)
  document.getElementById("btn-smart-sync-changed").addEventListener("click", () => {
    const activeRepos = state.gitRepos.filter(r => !r.is_ignored);
    const changed = activeRepos.filter(r => r.is_dirty || r.behind_count > 0 || r.ahead_count > 0);
    if (changed.length === 0) {
      showToast(devText("Tất cả repository đã đồng bộ!"), "info");
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
        showToast(devText("Không tìm thấy repository có remote để Pull"), "info");
        return;
      }
      const behindRepos = activeRepos.filter(r => r.behind_count > 0);
      if (behindRepos.length === 0) {
        showToast(devText("Không có repository nào cần Pull (Tất cả đã ở phiên bản mới nhất)"), "info");
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
        showToast(devText("Không có repository nào có commit mới cần Push"), "info");
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
    if (e.isComposing) return;
    if (e.key === "Escape") {
      const syncErrorsModal = document.getElementById("modal-sync-errors");
      if (syncErrorsModal && syncErrorsModal.classList.contains("active")) {
        closeSyncErrorsModal();
        return;
      }
      if (document.getElementById("modal-settings").classList.contains("active")) {
        e.preventDefault();
        closeSettingsModal();
        return;
      }
      if (state.selectedRepoPaths.size > 0 && state.currentTab === "git-sync-view") {
        state.selectedRepoPaths.clear();
        updateSelectionUI();
        renderGitReposTable();
      }
    }
    if (e.key === "Tab" && document.getElementById("modal-settings").classList.contains("active")) {
      const modal = document.getElementById("modal-settings");
      const controls = Array.from(modal.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href],[tabindex="0"]'))
        .filter(el => el.getClientRects().length > 0);
      const first = controls[0], last = controls[controls.length - 1];
      if (!first) { e.preventDefault(); return; }
      const outside = !modal.contains(document.activeElement);
      if (e.shiftKey && (outside || document.activeElement === first)) {
        e.preventDefault(); last.focus();
      } else if (!e.shiftKey && (outside || document.activeElement === last)) {
        e.preventDefault(); first.focus();
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
            showToast(devText("Đã tự động nhận diện Git Remote URL từ thư mục"), "info");
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
  summaryElem.textContent = devText("Đang quét workspace và kiểm tra remote...");

  try {
    const res = await window.pywebview.api.scan_git_workspace(customPath);
    if (res.success) {
      state.gitRepos = res.repos || [];
      summaryElem.textContent = (devText("Workspace: ") + (res.scan_path) + devText(" • Thời gian quét: ") + (res.elapsed_sec) + devText("s • Tìm thấy: ") + (res.total_count) + devText(" repos"));
      updateGitCounts();
      renderGitReposTable();
    } else {
      summaryElem.textContent = (devText("Lỗi: ") + (res.error) + devText(""));
      showToast(res.error, "danger");
    }
  } catch (err) {
    console.error(err);
    summaryElem.textContent = devText("Lỗi thực thi quét Git");
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
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 24px;"><span data-ui-copy="m_76e3b5b28cc7">Không tìm thấy repository phù hợp</span></td></tr>`;
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
      syncBadge = `<span class="badge badge-muted">${SVG_ICONS.eyeOff}<span data-ui-copy="m_fe50ff850e60"> Loại trừ</span></span>`;
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
    const suggestedActionStr = isIgnored ? devText("Đã loại trừ") : repo.suggested_action;

    // Kiểm tra nếu repo này vừa bị sync lỗi
    const lastResult = state.lastSyncResults?.[repo.path];
    let syncErrorIndicator = "";
    if (lastResult && !lastResult.success) {
      syncErrorIndicator = `
        <div style="margin-top: 3px;">
          <button type="button" class="badge badge-danger btn-view-repo-error" data-path="${escapeHtml(repo.path)}" style="cursor: pointer; padding: 2px 6px; border: none; font-family: inherit; font-size: 10px; display: inline-flex; align-items: center; gap: 4px;" aria-label="Xem chi tiết lỗi ${escapeHtml(lastResult.action.toUpperCase())} của repository ${escapeHtml(repo.name)}" title="Bấm để xem chi tiết lỗi: ${escapeHtml(lastResult.message)}">
            <span class="badge-dot badge-dot-danger"></span><span data-ui-copy="m_e68991b78542">Lỗi </span>${escapeHtml(lastResult.action.toUpperCase())}
          </button>
        </div>
      `;
    }

    tr.innerHTML = `
      <td style="text-align: center;">
        <input type="checkbox" class="repo-checkbox" ${isSelected ? "checked" : ""} ${isIgnored ? devText("disabled title='Repository đã bị loại trừ'") : ""}>
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
          ? `<button class="table-action-btn btn-unexclude" title="Khôi phục (Bỏ loại trừ)" data-ui-title="m_f931daa9602a">${SVG_ICONS.eye}</button>
             <button class="table-action-btn" disabled style="opacity: 0.2; cursor: not-allowed;" title="Repo đã bị loại trừ" data-ui-title="m_f213c2ef89d8">${SVG_ICONS.pull}</button>
             <button class="table-action-btn" disabled style="opacity: 0.2; cursor: not-allowed;" title="Repo đã bị loại trừ" data-ui-title="m_f213c2ef89d8">${SVG_ICONS.push}</button>`
          : `<button class="table-action-btn btn-exclude" title="Loại trừ repo khỏi quét & đồng bộ" data-ui-title="m_b50b631be52e">${SVG_ICONS.eyeOff}</button>
             <button class="table-action-btn btn-pull" title="Chỉ Pull repo này" data-ui-title="m_e654f0f3c9a9">${SVG_ICONS.pull}</button>
             <button class="table-action-btn btn-push" title="Chỉ Push repo này" data-ui-title="m_00a036125a41">${SVG_ICONS.push}</button>`
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
  document.getElementById("selected-status-text").textContent = (devText("Đã chọn: ") + (count) + devText(" / ") + (activeCount) + devText(" repos"));
  
  const floatingBar = document.getElementById("git-action-bar");
  if (count > 0) {
    floatingBar.style.display = "flex";
    document.getElementById("floating-selected-count").textContent = (devText("") + (count) + devText(" đã chọn"));
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
          repo.suggested_action = devText("Đã loại trừ");
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
      showToast(shouldExclude ? (devText("Đã loại trừ \"") + (repoName) + devText("\"")) : (devText("Đã khôi phục \"") + (repoName) + devText("\"")), "info");

      // Nếu khôi phục, tự động quét lại ngầm để cập nhật offset chính xác
      if (!shouldExclude) {
        triggerGitScan();
      }
    }
  } catch (err) {
    console.error(err);
    showToast(devText("Lỗi thay đổi trạng thái loại trừ"), "danger");
  }
}

async function excludeRepo(repoName) {
  toggleExcludeRepo(repoName, true);
}

async function executeGitAction(action, paths) {
  if (state.isSyncingGit || paths.length === 0) return;
  state.isSyncingGit = true;
  showToast((devText("Đang thực hiện ") + (action.toUpperCase()) + devText(" cho ") + (paths.length) + devText(" repos...")), "info");

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
        showToast((devText("Đồng bộ: ") + (res.success_count) + devText("/") + (res.total) + devText(" thành công, ") + (failedCount) + devText(" repo gặp sự cố")), "warning", 5000);
        openSyncErrorsModal(res);
      } else {
        showToast((devText("Hoàn tất: Đã ") + (action.toUpperCase()) + devText(" thành công cả ") + (res.total) + devText(" repos")), "success");
      }
      triggerGitScan();
    } else {
      showToast(res.error || devText("Lỗi thực thi Git action"), "danger");
    }
  } catch (err) {
    console.error(err);
    showToast(devText("Lỗi thực thi Git action"), "danger");
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
    if (titleEl) titleEl.textContent = devText("Kết quả Đồng bộ Git");
    if (iconEl) iconEl.style.color = "var(--color-success)";
    if (summaryEl) {
      summaryEl.innerHTML = `<span style="color: var(--color-success);"><span data-ui-copy="m_43655afcabba">Hoàn tất: Đã đồng bộ thành công cả </span>${syncResponse.total || results.length} repositories.</span>`;
    }
    if (listEl) listEl.innerHTML = "";
    if (retryBtn) retryBtn.style.display = "none";
  } else {
    if (titleEl) titleEl.textContent = (devText("Phát hiện Lỗi Đồng bộ Git (") + (errors.length) + devText(" repo)"));
    if (iconEl) iconEl.style.color = "var(--color-danger)";
    if (summaryEl) {
      summaryEl.innerHTML = `<span data-ui-copy="m_9bd7e05309e8">Đồng bộ: </span><strong>${syncResponse.success_count || (syncResponse.total - errors.length)}/${syncResponse.total || results.length}</strong><span data-ui-copy="m_6e43c10c61f6"> repos thành công. Có </span><strong style="color: var(--color-danger);">${errors.length}</strong><span data-ui-copy="m_30775e37b24a"> repository gặp sự cố:</span>`;
    }
    if (retryBtn) retryBtn.style.display = "inline-flex";

    if (listEl) {
      listEl.innerHTML = errors.map(item => `
        <div class="sync-error-card" style="background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: var(--radius-md); padding: 12px; display: flex; flex-direction: column; gap: 8px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="badge badge-danger"><span class="badge-dot badge-dot-danger"></span>${escapeHtml(item.action.toUpperCase())}<span data-ui-copy="m_61854dbfeb0b"> THẤT BẠI</span></span>
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
    showToast(devText("Không có log lỗi để sao chép"), "info");
    return;
  }

  const lines = [
    "==================================================",
    devText("BÁO CÁO LỖI ĐỒNG BỘ GIT — VXDevSync"),
    (devText("Thời gian: ") + (new Date().toLocaleString()) + devText("")),
    "==================================================",
    ""
  ];

  state.currentErrorResults.forEach((item, idx) => {
    lines.push(`[${idx + 1}/${state.currentErrorResults.length}] Repo: ${item.name || item.path}`);
    lines.push((devText("    Đường dẫn: ") + (item.path) + devText("")));
    lines.push((devText("    Thao tác: ") + (item.action.toUpperCase()) + devText("")));
    if (item.cmd) lines.push((devText("    Lệnh chạy: ") + (item.cmd) + devText("")));
    lines.push((devText("    Tóm tắt: ") + (item.message) + devText("")));
    if (item.raw_error) {
      lines.push(devText("    Chi tiết lỗi (Git Stderr):"));
      lines.push(item.raw_error.split("\n").map(l => "      " + l).join("\n"));
    }
    lines.push("--------------------------------------------------");
  });

  const fullText = lines.join("\n");
  navigator.clipboard.writeText(fullText).then(() => {
    showToast(devText("Đã sao chép toàn bộ log lỗi vào clipboard"), "success");
  }).catch(() => {
    showToast(devText("Không thể ghi vào clipboard"), "danger");
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
    showToast(devText("Tất cả các repository lỗi đều đã bị loại trừ"), "info");
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
    container.innerHTML = `<div style="font-size: 11px; color: var(--text-muted); padding: 4px 8px;"><span data-ui-copy="m_2fd134d92bdd">Chưa có thư mục gần đây</span></div>`;
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
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;"><span data-ui-copy="m_5410e6a4f0ea">Không tìm thấy kỹ năng nào</span></td></tr>`;
    return;
  }

  filtered.forEach(skill => {
    const tr = document.createElement("tr");

    // Central Library status
    const libBadge = skill.in_library 
      ? `<span class="badge badge-success"><span class="badge-dot badge-dot-success"></span><span data-ui-copy="m_29f843752d6e">Có mặt</span></span>`
      : `<span class="badge badge-muted"><span class="badge-dot badge-dot-muted"></span><span data-ui-copy="m_ca7704d32d0b">Thiếu</span></span>`;

    // Render helper for agents
    const getAgentBadge = (agentKey) => {
      const p = skill.agents[agentKey];
      if (!p || !p.exists) return `<span class="badge badge-muted"><span class="badge-dot badge-dot-muted"></span><span data-ui-copy="m_bc2b97d69a94">Chưa có</span></span>`;
      if (p.is_synced) return `<span class="badge badge-success"><span class="badge-dot badge-dot-success"></span><span data-ui-copy="m_9950cc180da2">Đồng bộ</span></span>`;
      return `<span class="badge badge-warning"><span class="badge-dot badge-dot-warning"></span><span data-ui-copy="m_aedec7e35235">Lệch hash</span></span>`;
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
        <button class="table-action-btn btn-danger-hover btn-delete-skill" title="Xóa triệt để" style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px;" data-ui-title="m_ddcbe18380c3">
          ${SVG_ICONS.trash} <span><span data-ui-copy="m_57435a5c8444">Xóa</span></span>
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
  hintElem.textContent = devText("Đang đồng bộ Kỹ năng và Quy tắc AGENTS.md / CLAUDE.md...");
  showToast(devText("Bắt đầu Đồng bộ Hợp nhất Kỹ năng & Rules..."), "info");

  try {
    const res = await window.pywebview.api.sync_skills_unified();
    if (res.success) {
      hintElem.textContent = (devText("Đã gom ") + (res.upstream_count) + devText(" skills mới, phân bổ sang ") + (res.downstream_agents.length) + devText(" agents. ") + (res.git_msg || "") + devText(""));
      showToast(devText("Đồng bộ Kỹ năng & Rules hoàn tất thành công!"), "success");
      triggerSkillsScan();
    } else {
      hintElem.textContent = (devText("Lỗi: ") + (res.error) + devText(""));
      showToast(res.error, "danger");
    }
  } catch (err) {
    console.error(err);
    hintElem.textContent = devText("Lỗi thực thi đồng bộ kỹ năng");
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
  showToast((devText("Đang xóa vĩnh viễn skill ") + (skillName) + devText("...")), "info");

  try {
    const res = await window.pywebview.api.delete_skills_cascade([skillName]);
    if (res.success) {
      showToast((devText("Đã xóa ") + (skillName) + devText(" và cập nhật GitHub thành công!")), "success");
      triggerSkillsScan();
    } else {
      showToast(res.error || devText("Lỗi xóa kỹ năng"), "danger");
    }
  } catch (err) {
    console.error(err);
    showToast(devText("Lỗi kết nối khi xóa skill"), "danger");
  }
}

// ==========================================
// SETTINGS MODAL
// ==========================================

const settingsDraftFields = new Map();
const settingsDraftIds = ['setting-default-tab', 'setting-scan-path', 'setting-max-depth', 'setting-skills-lib', 'setting-git-repo'];
function captureSettingsDraft() {
  for (const id of settingsDraftIds) {
    const input = document.getElementById(id);
    if (input) settingsDraftFields.set(id, input.value);
  }
}
function restoreSettingsDraft() {
  for (const [id, value] of settingsDraftFields) {
    const input = document.getElementById(id);
    if (input) input.value = value; // Property assignment preserves paths, quotes and HTML characters.
  }
}

function openSettingsModal() {
  if (!document.getElementById('modal-settings').classList.contains('active')) {
    state.settingsReturnFocus = document.activeElement;
    settingsDraftFields.clear();
    document.getElementById('settings-tab-content').replaceChildren();
  }
  document.getElementById("modal-settings").classList.add("active");
  renderSettingsTabContent(state.activeSettingsTab);
  document.querySelector(`[data-settings-tab="${state.activeSettingsTab}"]`)?.focus();
}

function closeSettingsModal() {
  document.getElementById("modal-settings").classList.remove("active");
  const previous = state.settingsReturnFocus;
  state.settingsReturnFocus = null;
  if (previous?.isConnected) previous.focus();
}

function renderSettingsTabContent(tabKey) {
  captureSettingsDraft();
  const area = document.getElementById("settings-tab-content");
  const cfg = state.config;
  const vi = cfg.general.lang !== 'en';
  const labels = {general:vi?'Chung':'General','git-sync':'Git Multi-Sync','skills-sync':'Skills Auto-Sync',updates:vi?devText("Cập nhật"):'Updates',about:vi?devText("Giới thiệu"):'About',support:vi?devText("Ủng hộ tác giả"):'Support Author'};
  document.querySelectorAll('[data-settings-tab]').forEach(button => {button.querySelector('span').textContent = labels[button.dataset.settingsTab];button.classList.toggle('is_active',button.dataset.settingsTab===tabKey);});
  document.getElementById('settings-title').textContent = 'VXDevSync Settings';
  document.getElementById('btn-settings-reset').innerHTML = window.VXSettingsUI.reset({language:vi?'vi':'en'});
  document.getElementById('btn-settings-save').textContent = ['general','updates','about','support'].includes(tabKey) ? (vi?devText("Đóng"):'Close') : (vi?devText("Lưu & Đóng"):'Save & Close');

  if (tabKey === "general") {
    area.innerHTML = window.VXSettingsUI.general({language: vi?'vi':'en',theme:cfg.general.theme,themes:['dark','light']});
  } else if (tabKey === "git-sync") {
    area.innerHTML = `      <section class="settings-description settings-form-section"><h4 class="settings-section-title">${updateText('Khi khởi động','Startup')}</h4>
        <label class="form-label" for="setting-default-tab">${updateText('Tab mặc định','Default tab')}</label>
        <select class="form-input settings-compact-select" id="setting-default-tab">
          <option value="git_sync" ${cfg.general.default_tab === "git_sync" ? "selected" : ""}>Git Multi-Sync</option>
          <option value="skills_sync" ${cfg.general.default_tab === "skills_sync" ? "selected" : ""}>Skills Auto-Sync</option>
        </select>
      </section>
      <div class="form-group">
        <label class="form-label settings-section-title"><span data-ui-copy="m_1b31b0f469fb">Thư mục Workspace Quét Mặc định (scan_path):</span></label>
        <div class="form-input-row">
          <input type="text" class="form-input" id="setting-scan-path" value="${escapeHtml(cfg.git_sync.scan_path)}">
          <button class="btn-secondary" id="btn-browse-scan-path"><span data-ui-copy="m_7e8f43a90dc3">Duyệt...</span></button>
        </div>
      </div>
      <div class="form-group">
        <label class="form-label settings-section-title"><span data-ui-copy="m_0a20de39cb24">Độ sâu quét tối đa (max_depth):</span></label>
        <input type="number" class="form-input" id="setting-max-depth" value="${escapeHtml(cfg.git_sync.max_depth)}" min="1" max="10">
      </div>
      <div class="form-group">
        <label class="form-label settings-section-title"><span data-ui-copy="m_ff8c56f9c8d3">Danh sách Thư mục Loại trừ (Ignore List):</span></label>
        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 6px; max-height: 120px; overflow-y: auto;" id="setting-ignore-container">
          ${cfg.git_sync.ignore_list.map(item => `
            <div style="display: flex; justify-content: space-between; padding: 3px 6px; font-size: 11px;">
              <span>${escapeHtml(item)}</span>
              <button class="table-action-btn btn-danger-hover btn-remove-ignore" data-ignore="${escapeHtml(item)}" title="Xóa khỏi danh sách loại trừ" data-ui-title="m_36eddcc61b97">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          `).join("")}
        </div>
        <div class="form-input-row" style="margin-top: 6px;">
          <input type="text" class="form-input" id="setting-new-ignore" placeholder="Nhập tên thư mục bỏ qua..." data-ui-placeholder="m_f17171a95099">
          <button class="btn-secondary" id="btn-add-ignore"><span data-ui-copy="m_48ae74d5d69c">+ Thêm</span></button>
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
              r.suggested_action = devText("Đã loại trừ");
              state.selectedRepoPaths.delete(r.path);
            }
            renderSettingsTabContent("git-sync");
            updateSelectionUI();
            updateGitCounts();
            renderGitReposTable();
            showToast((devText("Đã thêm \"") + (val) + devText("\" vào danh sách loại trừ")), "info");
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
            showToast((devText("Đã xóa \"") + (item) + devText("\" khỏi danh sách loại trừ")), "info");
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
        <label class="form-label settings-section-title"><span data-ui-copy="m_e175cd3e49b3">Thư mục Central Skills Library (skills_lib):</span></label>
        <div class="form-input-row">
          <input type="text" class="form-input" id="setting-skills-lib" value="${escapeHtml(cfg.skills_sync.skills_lib)}">
          <button class="btn-secondary" id="btn-browse-skills-lib"><span data-ui-copy="m_7e8f43a90dc3">Duyệt...</span></button>
        </div>
      </div>
      <div class="form-group">
        <label class="form-label settings-section-title"><span data-ui-copy="m_cc07b027db15">Git Remote URL (Tùy chọn, để trống nếu dùng Offline):</span></label>
        <input type="text" class="form-input" id="setting-git-repo" value="${escapeHtml(cfg.skills_sync.git_repo)}" placeholder="https://github.com/username/my_skills_library.git">
      </div>
      <div class="form-group">
        <label class="form-label settings-section-title"><span data-ui-copy="m_97f61b5709bd">Quản lý Kỹ năng đã Xóa (Tombstone Manifest):</span></label>
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
              showToast(devText("Đã tự động nhận diện Git Remote URL từ thư mục"), "info");
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
        showToast((devText("Đã phục hồi ") + (skillName) + devText(" khỏi danh sách Tombstone")), "success");
        renderSettingsTabContent("skills-sync");
        triggerSkillsScan();
      });
    });
  } else if (tabKey === "updates") {
    const content = `<div class="vx_settings_update_status"><p id="update-status" role="status"></p><button id="check-app-update" class="vx_settings_primary">${updateText('Kiểm tra cập nhật','Check for updates')}</button><button id="install-app-update" class="vx_settings_primary" hidden>${updateText('Cập nhật & khởi động lại','Update & restart')}</button></div>`;
    area.innerHTML = window.VXSettingsUI.updates({language:vi?'vi':'en',appVersion:cfg.version,content});
    document.getElementById("check-app-update").onclick = () => runUpdateAction(false);
    document.getElementById("install-app-update").onclick = () => runUpdateAction(true);
    paintUpdateUI();
  } else if (tabKey === "about") {
    area.innerHTML = window.VXSettingsUI.about({language:vi?'vi':'en',appName:'VXDevSync',appVersion:cfg.version,
      tagline:updateText('Đồng bộ Git và thư viện kỹ năng AI','Sync Git repositories and AI skills'),
      description:updateText('Quản lý trạng thái và đồng bộ nhiều Git repository trong cùng workspace. Đồng bộ thư viện kỹ năng và quy tắc cho Antigravity, Codex và Claude Code từ một giao diện chung.','Inspect and sync Git repositories in a workspace. Share skills and rules across Antigravity, Codex and Claude Code from one interface.'),
      repository:'https://github.com/linhbv94/VXDevSync'});
  } else if (tabKey === "support") {
    area.innerHTML = window.VXSettingsUI.support({language:vi?'vi':'en',qrSource:'assets/support_qr.png'});
    const image=area.querySelector('img');
    image.addEventListener('error',()=>{const placeholder=document.createElement('div');placeholder.className='vx_settings_qr_placeholder';placeholder.textContent=window.VXSettingsUI.copy(vi?'vi':'en').qrMissing;image.replaceWith(placeholder);},{once:true});
  }

  restoreSettingsDraft();
}

document.addEventListener('change', async event => {
  if(!event.target.matches('[name="setting-theme"], [name="setting-lang"]')) return;
  const previous = {...state.config.general};
  state.config.general[event.target.name === 'setting-lang' ? 'lang' : 'theme'] = event.target.value;
  try {
    const result = await window.pywebview.api.save_config({general: state.config.general});
    if(!result.success) throw Error(result.error || 'save_config failed');
    updateUIFromConfig(); renderSettingsTabContent('general');
  } catch(error) {state.config.general = previous; renderSettingsTabContent('general'); showToast(String(error), 'danger');}
});

async function saveSettingsFromModal(closeAfter = true) {
  if(['general','updates','about','support'].includes(state.activeSettingsTab)) {closeSettingsModal();return;}

  const cfg = structuredClone(state.config);
  
  // Read current fields if available
  const langEl = document.querySelector('[name="setting-lang"]:checked');
  if (langEl) cfg.general.lang = langEl.value;

  const themeEl = document.querySelector('[name="setting-theme"]:checked');
  if (themeEl) cfg.general.theme = themeEl.value;

  captureSettingsDraft();
  const fields = settingsDraftFields;
  if (fields.has('setting-default-tab')) cfg.general.default_tab = fields.get('setting-default-tab');
  if (fields.has('setting-scan-path')) cfg.git_sync.scan_path = fields.get('setting-scan-path');
  if (fields.has('setting-max-depth')) cfg.git_sync.max_depth = parseInt(fields.get('setting-max-depth'), 10) || 3;
  if (fields.has('setting-skills-lib')) cfg.skills_sync.skills_lib = fields.get('setting-skills-lib');
  if (fields.has('setting-git-repo')) cfg.skills_sync.git_repo = fields.get('setting-git-repo');

  try {
    const res = await window.pywebview.api.save_config({
      general: cfg.general,
      git_sync: cfg.git_sync,
      skills_sync: cfg.skills_sync
    });
    if (res.success) {
      state.config = cfg;
      showToast(devText("Đã lưu cài đặt"), "success");
      updateUIFromConfig();
      if(closeAfter !== false) closeSettingsModal();
    } else {throw Error(res.error || "save_config failed");}
  } catch (err) {
    showToast(updateText("Chưa lưu được cài đặt: ","Settings were not saved: ")+String(err),"danger");
  }
}

async function resetSettingsDefault() {
  if(!confirm(updateText('Khôi phục các tùy chọn mặc định? Thư mục và ngôn ngữ được giữ nguyên.', 'Reset preferences? Folders and language will be preserved.'))) return;
  const cfg = structuredClone(state.config);
  cfg.general.theme='dark';cfg.general.default_tab='git_sync';cfg.git_sync.max_depth=3;cfg.git_sync.max_concurrency=8;
  try {
    const result=await window.pywebview.api.save_config({general:cfg.general,git_sync:cfg.git_sync});
    if(!result.success) throw Error(result.error || 'save_config failed');
    state.config=cfg;updateUIFromConfig();renderSettingsTabContent(state.activeSettingsTab);
  }catch(error){showToast(String(error),'danger');}
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
      showToast(devText("Thiết lập ban đầu hoàn tất!"), "success");
    } else {
      showToast(res?.error || devText("Không thể lưu cấu hình khởi tạo"), "danger");
    }
  } catch (err) {
    console.error(err);
    showToast(devText("Không thể lưu cấu hình khởi tạo"), "danger");
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

// One UI owner for startup notice and Settings. Progress is read from the engine.
let updateSnapshot = {status:'idle',noticeVisible:false};
let updateBusy = false;
let updateActionError = null;
let updatePollBusy = false;
let noticePaintSignature = null;
const dismissedUpdateVersions = new Set();
function updateText(vi, en) {return state.config?.general.lang === 'en' ? en : vi;}
function updateMessage() {
  const v = updateSnapshot.version || '';
  const phase = updateSnapshot.status;
  const messages = {
    idle:updateText('Kiểm tra phiên bản mới.', 'Check for a new version.'),
    checking:updateText('Đang kiểm tra…', 'Checking for updates…'),
    available:updateText('Có phiên bản mới', 'Update available')+' v'+v,
    current:updateText('Bạn đang dùng phiên bản mới nhất.', 'You are up to date.'),
    downloading:updateText('Đang tải cập nhật', 'Downloading update')+(Number.isFinite(updateSnapshot.progress)?' '+Math.round(updateSnapshot.progress)+'%':'…'),
    verifying:updateText('Đang xác minh…', 'Verifying…'),
    installing:updateText('Đang cài cập nhật…', 'Installing update…'),
    handed_off:updateText('Đang khởi động lại…', 'Restarting…'),
    error:updateText('Cập nhật chưa hoàn tất. Hãy thử lại.', 'Update failed. Please try again.')
  };return messages[phase] || phase;
}
function paintUpdateUI() {
  const working = updateBusy || ['checking','downloading','verifying','installing','handed_off'].includes(updateSnapshot.status);
  const status = document.getElementById('update-status'); if(status) status.textContent = updateMessage();
  const check = document.getElementById('check-app-update'); if(check) {check.disabled=working;check.textContent=updateText('Kiểm tra cập nhật','Check for updates');}
  const install = document.getElementById('install-app-update'); if(install) {install.hidden=updateSnapshot.status!=='available';install.disabled=working;install.textContent=updateText('Cập nhật & khởi động lại','Update & restart');}
  const signature=JSON.stringify([updateSnapshot,updateBusy,state.config?.general.lang,[...dismissedUpdateVersions]]);
  if(signature === noticePaintSignature) return;
  noticePaintSignature = signature;
  let notice = document.getElementById('app-update-notice');
  if(!notice) {notice=document.createElement('section');notice.id='app-update-notice';notice.setAttribute('aria-label','Application updates');document.body.append(notice);}
  notice.hidden=!(updateSnapshot.noticeVisible && !dismissedUpdateVersions.has(updateSnapshot.version)) && !['downloading','verifying','installing','handed_off'].includes(updateSnapshot.status);
  notice.replaceChildren();
  const message=document.createElement('p');message.setAttribute('role','status');message.textContent=updateMessage();notice.append(message);
  if(updateSnapshot.error) {const details=document.createElement('details'), summary=document.createElement('summary');summary.textContent=updateText('Chi tiết lỗi','Error details');details.append(summary,document.createTextNode(String(updateSnapshot.error)));notice.append(details);}
  const button=document.createElement('button');button.className='btn-primary';button.disabled=working;button.textContent=updateSnapshot.status==='available'?updateText('Cập nhật & khởi động lại','Update & restart'):updateText('Thử lại','Retry');button.onclick=()=>runUpdateAction(updateSnapshot.status==='available');notice.append(button);
  if(!working){const close=document.createElement('button');close.className='btn-secondary';close.textContent=updateText('Để sau','Later');close.onclick=()=>{dismissedUpdateVersions.add(updateSnapshot.version);paintUpdateUI();};notice.append(close);}
}
async function pollUpdateUI() {
  if(updatePollBusy) return;
  updatePollBusy=true;
  try {
    const snapshot=await window.pywebview.api.get_update_status();
    if(snapshot.success) updateSnapshot=updateActionError ? {...snapshot,status:'error',error:updateActionError,noticeVisible:true} : snapshot;
    paintUpdateUI();
  }catch(error){console.warn(error);}finally{updatePollBusy=false;}
}
async function runUpdateAction(install) {
  if(updateBusy) return;
  if(install && (state.isSyncingGit || state.isSyncingSkills || state.isScanningGit)) {showToast(updateText('Hãy đợi tác vụ hoàn tất trước khi cập nhật.','Wait for the active task to finish before updating.'),'info');return;}
  updateActionError=null;updateBusy=true;paintUpdateUI();
  try {const result=await window.pywebview.api[install?'install_update':'check_updates']();if(!result.success) throw Error(result.error || 'Update failed');await pollUpdateUI();}
  catch(error){updateActionError=String(error);updateSnapshot={...updateSnapshot,status:'error',error:updateActionError,noticeVisible:true};}
  finally{updateBusy=false;paintUpdateUI();}
}
function startUpdateUI(){void runUpdateAction(false);setInterval(pollUpdateUI,1000);}
