import { modules } from "./config/modules.js";
import { canWrite, clearToken, getRole, getToken, isAdmin, setToken, setUserAuth } from "./services/auth.js";
import { apiFetch as rawApiFetch } from "./services/http.js";
import { createChatFeature } from "./features/chat.js";
import { createLogsFeature } from "./features/logs.js";

const loginSection = document.getElementById("login-section");
const appSection = document.getElementById("app-section");
const roleBadge = document.getElementById("role-badge");
const loginForm = document.getElementById("login-form");
const logoutBtn = document.getElementById("logout-btn");
const tabs = document.getElementById("tabs");
const form = document.getElementById("module-form");
const toggleFormBtn = document.getElementById("toggle-form-btn");
const recordIdInput = document.getElementById("record-id");
const formGrid = document.getElementById("form-grid");
const queryGrid = document.getElementById("query-grid");
const queryPanel = document.getElementById("query-panel");
const toggleQueryBtn = document.getElementById("toggle-query-btn");
const tableHead = document.getElementById("table-head");
const tableBody = document.getElementById("table-body");
const moduleTitle = document.getElementById("module-title");
const submitBtn = document.getElementById("submit-btn");
const cancelBtn = document.getElementById("cancel-btn");
const refreshBtn = document.getElementById("refresh-btn");
const statsBtn = document.getElementById("stats-btn");
const statsBox = document.getElementById("stats-box");
const courseScoreBox = document.getElementById("course-score-box");
const logsBtn = document.getElementById("logs-btn");
const logsBox = document.getElementById("logs-box");
const logsSection = document.getElementById("logs-section");
const searchBtn = document.getElementById("search-btn");
const resetSearchBtn = document.getElementById("reset-search-btn");
const chatForm = document.getElementById("chat-form");
const chatOutput = document.getElementById("chat-output");
const chatChart = document.getElementById("chat-chart");

let currentModuleKey = "students";
const moduleState = {};
let moduleRenderVersion = 0;
let currentPage = 1;

function getCurrentPageSize() {
  return modules[currentModuleKey]?.pageSize || 19;
}

function apiFetch(url, options = {}) {
  return rawApiFetch(url, options, toggleView);
}

function getModuleState(moduleKey = currentModuleKey) {
  if (!moduleState[moduleKey]) moduleState[moduleKey] = { queryExpanded: false, formExpanded: false };
  return moduleState[moduleKey];
}

function formFieldId(fieldName) {
  return `form-${currentModuleKey}-${fieldName}`;
}

function queryFieldId(fieldName) {
  return `query-${currentModuleKey}-${fieldName}`;
}

function toggleView() {
  const logged = Boolean(getToken());
  loginSection.classList.toggle("hidden", logged);
  appSection.classList.toggle("hidden", !logged);
  if (logged) {
    const role = getRole();
    roleBadge.textContent = `当前角色：${role === "admin" ? "管理员（最高权限）" : role === "teacher" ? "老师（业务全权限）" : "学生（只读权限）"}`;
  }
}

function applyFormState() {
  const state = getModuleState();
  form.classList.toggle("hidden", !state.formExpanded);
  toggleFormBtn.textContent = state.formExpanded ? "收起新增" : "展开新增";
}

function renderTableMessage(message) {
  const visibleColumnCount = modules[currentModuleKey].fields.filter((f) => !f.hiddenInTable).length + 2;
  tableBody.innerHTML = `<tr><td colspan="${visibleColumnCount}">${message}</td></tr>`;
}

function renderQueryFields(config) {
  queryGrid.innerHTML = "";
  config.fields
    .filter((f) => f.name !== "password")
    .forEach((field) => {
      const input = document.createElement(field.type === "select" ? "select" : "input");
      input.id = queryFieldId(field.name);
      input.placeholder = `查询${field.label}`;
      if (field.type === "select") {
        const empty = document.createElement("option");
        empty.value = "";
        empty.textContent = `全部${field.label}`;
        input.appendChild(empty);
        (field.options || []).forEach((option) => {
          const item = document.createElement("option");
          item.value = option;
          item.textContent = option;
          input.appendChild(item);
        });
      } else {
        input.type = "text";
      }
      queryGrid.appendChild(input);
    });
}

function renderModule() {
  const config = modules[currentModuleKey];
  const state = getModuleState();
  moduleTitle.textContent = `新增${config.title.replace("管理", "")}`;
  queryPanel.classList.toggle("hidden", !state.queryExpanded);
  toggleQueryBtn.textContent = state.queryExpanded ? "收起查询/筛选" : "展开查询/筛选";
  formGrid.innerHTML = "";
  config.fields.forEach((field) => {
    const input = document.createElement(field.type === "select" ? "select" : "input");
    input.id = formFieldId(field.name);
    if (field.type === "select") {
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = `请选择${field.label}`;
      input.appendChild(placeholder);
      (field.options || []).forEach((option) => {
        const item = document.createElement("option");
        item.value = option;
        item.textContent = option;
        input.appendChild(item);
      });
    } else {
      input.placeholder = field.label;
      input.type = field.type || "text";
      if (field.step) input.step = field.step;
    }
    formGrid.appendChild(input);
  });
  renderQueryFields(config);
  tableHead.innerHTML = `<tr><th>ID</th>${config.fields.filter((f) => !f.hiddenInTable).map((f) => `<th>${f.label}</th>`).join("")}<th>操作</th></tr>`;
  toggleFormBtn.classList.toggle("hidden", !canWrite());
  logsSection.classList.toggle("hidden", !(isAdmin() && currentModuleKey === "adminUsers"));
  applyFormState();
}

function renderTabs() {
  tabs.innerHTML = "";
  Object.entries(modules).forEach(([key, config]) => {
    if (config.adminOnly && !isAdmin()) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = `tab-btn ${key === currentModuleKey ? "active" : ""}`;
    button.textContent = config.title;
    button.addEventListener("click", () => {
      if (key === currentModuleKey) return;
      moduleRenderVersion += 1;
      currentModuleKey = key;
      currentPage = 1;
      renderTabs();
      renderModule();
      loadList().catch((e) => alert(e.message));
      loadStats().catch((e) => alert(e.message));
      if (isAdmin() && currentModuleKey === "adminUsers") logsFeature.loadLogs().catch((e) => alert(e.message));
    });
    tabs.appendChild(button);
  });
}

function buildQueryString() {
  const params = new URLSearchParams();
  const config = modules[currentModuleKey];
  config.fields
    .filter((f) => f.name !== "password")
    .forEach((f) => {
      const value = (document.getElementById(queryFieldId(f.name))?.value || "").trim();
      if (value) params.append(f.name, value);
    });
  params.append("page", String(currentPage));
  params.append("page_size", String(getCurrentPageSize()));
  const query = params.toString();
  return query ? `?${query}` : "";
}

function resetForm() {
  form.reset();
  recordIdInput.value = "";
  submitBtn.textContent = "保存";
  cancelBtn.classList.add("hidden");
}

function getFormData() {
  const config = modules[currentModuleKey];
  const payload = {};
  config.fields.forEach((f) => {
    const value = document.getElementById(formFieldId(f.name)).value.trim();
    if (currentModuleKey === "adminUsers") {
      if (recordIdInput.value && !value) return;
      if (!recordIdInput.value && !value && f.name !== "is_active") return;
      payload[f.name] = f.name === "is_active" ? value.toLowerCase() !== "false" : value;
      return;
    }
    payload[f.name] = f.type === "number" ? Number(value) : value;
  });
  return payload;
}

function setFormData(data) {
  modules[currentModuleKey].fields.forEach((f) => {
    const value = f.name === "password" ? "" : f.name === "is_active" ? String(data[f.name] ?? true) : data[f.name] ?? "";
    document.getElementById(formFieldId(f.name)).value = value;
  });
}

function validateAdminRows(rows) {
  return rows.every((item) => typeof item.username === "string" && typeof item.role === "string");
}

async function loadList() {
  const moduleKeyAtRequest = currentModuleKey;
  const requestVersion = moduleRenderVersion;
  const { endpoint, fields } = modules[currentModuleKey];
  renderTableMessage("加载中...");
  const result = await apiFetch(`${endpoint}${buildQueryString()}`);
  if (requestVersion !== moduleRenderVersion || moduleKeyAtRequest !== currentModuleKey) return;
  const list = Array.isArray(result) ? result : (result.items || []);
  const total = result.total ?? list.length;
  if (currentModuleKey === "adminUsers" && !validateAdminRows(list)) {
    renderTableMessage("管理员接口返回数据异常，已阻止渲染");
    return;
  }
  tableBody.innerHTML = "";
  list.forEach((item) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${item.id}</td>${fields.filter((f) => !f.hiddenInTable).map((f) => `<td>${item[f.name] ?? ""}</td>`).join("")}<td>${canWrite() ? `<div class="row-actions"><button data-action="edit" data-id="${item.id}">编辑</button><button data-action="delete" data-id="${item.id}" class="danger">删除</button></div>` : "<span>仅查看</span>"}</td>`;
    tableBody.appendChild(tr);
  });
  renderPagination(total);
}

function renderPagination(total) {
  const pageSize = getCurrentPageSize();
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  let container = document.getElementById("pagination-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "pagination-container";
    container.className = "pagination";
    const tableSection = document.querySelector("#table-body").closest("section.card");
    if (tableSection) tableSection.appendChild(container);
  }
  if (totalPages <= 1 && total <= pageSize) {
    container.innerHTML = `<span class="pagination-info">共 ${total} 条记录</span>`;
    return;
  }
  let html = `<span class="pagination-info">共 ${total} 条记录，第 ${currentPage}/${totalPages} 页</span>`;
  html += `<button data-page="${currentPage - 1}" ${currentPage <= 1 ? "disabled" : ""}>上一页</button>`;
  const startPage = Math.max(1, currentPage - 2);
  const endPage = Math.min(totalPages, currentPage + 2);
  for (let p = startPage; p <= endPage; p++) {
    html += `<button data-page="${p}" class="${p === currentPage ? "active" : ""}">${p}</button>`;
  }
  html += `<button data-page="${currentPage + 1}" ${currentPage >= totalPages ? "disabled" : ""}>下一页</button>`;
  container.innerHTML = html;
  container.querySelectorAll("button[data-page]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = parseInt(btn.dataset.page);
      if (!isNaN(target) && target >= 1 && target <= totalPages) {
        currentPage = target;
        loadList().catch((e) => alert(e.message));
      }
    });
  });
}

async function loadStats() {
  const moduleKeyAtRequest = currentModuleKey;
  const requestVersion = moduleRenderVersion;
  const dashboard = await apiFetch("/api/dashboard-stats");
  if (requestVersion !== moduleRenderVersion || moduleKeyAtRequest !== currentModuleKey) return;
  const s = dashboard.overview;
  const statMap = {
    students: [["学生总数", s.students], ["成绩平均分", s.avg_score], ["就业率", `${s.employment_rate}%`]],
    teachers: [["教师总数", s.teachers], ["课程总数", s.courses], ["班级总数", s.classes]],
    courses: [["课程总数", s.courses], ["成绩记录数", s.grades], ["平均分", s.avg_score]],
    classes: [["班级总数", s.classes], ["学生总数", s.students], ["教师总数", s.teachers]],
    employments: [["就业记录数", s.employments], ["就业率", `${s.employment_rate}%`], ["学生总数", s.students]],
    grades: [["成绩记录数", s.grades], ["平均分", s.avg_score], ["就业率", `${s.employment_rate}%`]],
  };
  statsBox.innerHTML = (statMap[currentModuleKey] || []).map((item) => `<div class="stat-item">${item[0]}<strong>${item[1]}</strong></div>`).join("");
  courseScoreBox.textContent = currentModuleKey === "students" || currentModuleKey === "grades" ? "" : "当前板块暂无课程维度统计";
}

const chatFeature = createChatFeature({ chatOutput, chatChart, apiFetch });
const logsFeature = createLogsFeature({ logsBox, apiFetch });

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = { username: document.getElementById("username").value, password: document.getElementById("password").value };
  const result = await apiFetch("/api/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload), handleAuthError: false });
  setToken(result.token);
  setUserAuth({ role: result.role, username: result.username });
  toggleView();
  renderTabs();
  renderModule();
  await loadList();
  await loadStats();
  if (isAdmin() && currentModuleKey === "adminUsers") await logsFeature.loadLogs();
});

logoutBtn.addEventListener("click", () => {
  clearToken();
  toggleView();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!canWrite()) return;
  const payload = getFormData();
  const { endpoint } = modules[currentModuleKey];
  const id = recordIdInput.value;
  if (id) {
    await apiFetch(`${endpoint}/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  } else {
    await apiFetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  }
  resetForm();
  await loadList();
  if (isAdmin() && currentModuleKey === "adminUsers") await logsFeature.loadLogs();
});

tableBody.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button || !canWrite()) return;
  const { endpoint } = modules[currentModuleKey];
  const id = button.dataset.id;
  if (button.dataset.action === "delete") {
    if (!confirm("确认删除该记录吗？")) return;
    await apiFetch(`${endpoint}/${id}`, { method: "DELETE" });
    await loadList();
    if (isAdmin() && currentModuleKey === "adminUsers") await logsFeature.loadLogs();
    return;
  }
  const item = await apiFetch(`${endpoint}/${id}`);
  recordIdInput.value = item.id;
  setFormData(item);
  submitBtn.textContent = "更新";
  cancelBtn.classList.remove("hidden");
});

cancelBtn.addEventListener("click", resetForm);

refreshBtn.addEventListener("click", () => loadList().catch((e) => alert(e.message)));
statsBtn.addEventListener("click", () => loadStats().catch((e) => alert(e.message)));
logsBtn.addEventListener("click", () => logsFeature.loadLogs().catch((e) => alert(e.message)));
searchBtn.addEventListener("click", () => { currentPage = 1; loadList().catch((e) => alert(e.message)); });
resetSearchBtn.addEventListener("click", () => {
  currentPage = 1;
  queryGrid.querySelectorAll("input, select").forEach((el) => {
    el.value = "";
  });
  loadList().catch((e) => alert(e.message));
});
toggleQueryBtn.addEventListener("click", () => {
  const state = getModuleState();
  state.queryExpanded = !state.queryExpanded;
  queryPanel.classList.toggle("hidden", !state.queryExpanded);
  toggleQueryBtn.textContent = state.queryExpanded ? "收起查询/筛选" : "展开查询/筛选";
});
toggleFormBtn.addEventListener("click", () => {
  const state = getModuleState();
  state.formExpanded = !state.formExpanded;
  applyFormState();
});
chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = document.getElementById("chat-input").value.trim();
  if (!message) return;
  try {
    await chatFeature.sendMessage(message);
  } catch (error) {
    chatOutput.textContent = error.message;
  }
});

function bootstrap() {
  renderTabs();
  renderModule();
  toggleView();
  if (!getToken()) return;
  loadList().catch(() => {});
  loadStats().catch(() => {});
  if (isAdmin() && currentModuleKey === "adminUsers") logsFeature.loadLogs().catch(() => {});
}

bootstrap();
