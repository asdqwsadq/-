import { formatLogTime, syncNetworkTime } from "../services/time.js";

export function createLogsFeature({ logsBox, apiFetch }) {
  const actionMap = { create: "新增", update: "更新", delete: "删除" };
  const moduleMap = {
    students: "学生",
    teachers: "老师",
    courses: "课程",
    classes: "班级",
    employments: "就业",
    grades: "成绩",
    admin_users: "管理员账号",
  };

  async function loadLogs() {
    await syncNetworkTime();
    const result = await apiFetch("/api/logs");
    const logs = (result && result.items) || result;
    if (!Array.isArray(logs) || !logs.length) {
      logsBox.textContent = "暂无日志记录";
      return;
    }
    logsBox.innerHTML = logs
      .slice(0, 50)
      .map(
        (log) =>
          `${formatLogTime(log.created_at)} | ${log.username}(${log.role}) 对 ${
            moduleMap[log.module] || log.module
          }执行${actionMap[log.action] || log.action}，记录ID=${log.target_id ?? "-"}，说明：${log.detail || "-"}`
      )
      .join("<br>");
  }

  return { loadLogs };
}
