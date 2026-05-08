export function createChatFeature({ chatOutput, chatChart, apiFetch }) {
  let chartInstance = null;
  let requestId = 0;

  function clearChatChart() {
    if (chartInstance) {
      chartInstance.dispose();
      chartInstance = null;
    }
    chatChart.classList.add("hidden");
    chatChart.innerHTML = "";
  }

  function isValidChartPayload(chart) {
    return Boolean(chart && typeof chart === "object" && chart.option && typeof chart.option === "object");
  }

  function renderChatChart(chart) {
    if (!isValidChartPayload(chart)) {
      clearChatChart();
      return;
    }
    if (typeof echarts === "undefined") {
      chatOutput.textContent = "图表库未加载，请刷新页面后重试。";
      clearChatChart();
      return;
    }
    clearChatChart();
    chatChart.classList.remove("hidden");
    chartInstance = echarts.init(chatChart);
    chartInstance.setOption(chart.option, true);
  }

  async function sendMessage(message) {
    requestId += 1;
    const currentRequestId = requestId;
    chatOutput.textContent = "AI 思考中...";
    clearChatChart();
    const result = await apiFetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (currentRequestId !== requestId) return;
    chatOutput.textContent = result.answer || "无响应";
    renderChatChart(result.chart);
  }

  return { sendMessage, clearChatChart };
}
