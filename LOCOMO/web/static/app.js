const state = {
  sessions: [],
  embeddingModels: [],
  selectedSessionIds: null,
  rows: [],
  filter: "all",
  page: 1,
  pageSize: 20,
  followLatest: true,
  jobId: null,
  pollTimer: null,
};

const $ = (id) => document.getElementById(id);
const SETTINGS_KEY = "locomo.qa.console.settings.v1";
const SETTINGS_FIELDS = [
  "mode",
  "method",
  "embedding-model",
  "limit",
  "top-k",
  "dual-route-enabled",
  "realtime-write-enabled",
  "run-id",
  "chat-history-k",
  "decay-round",
  "round-decay-enabled",
  "decay-hours",
  "time-decay-enabled",
  "api-delay",
  "save-prompts",
  "allow-large-qa",
  "resume-run",
  "api-key",
  "base-url",
  "model-name",
  "temperature",
  "max-tokens",
  "prompt-template",
  "system-prompt",
  "save-as-path",
];

const MODEL_NOTES = {
  "bge-m3": {
    tag: "中文/多语种推荐",
    note: "多语种语义模型，中文 LOCOMO、英文问题、跨语种证据都更稳。建议作为主实验模型。",
  },
  "bge-large-en-v1.5": {
    tag: "英文强基线",
    note: "英文检索能力强，维度较高。适合保留 LOCOMO 英文 QA 或做英文基线对照；中文任务通常不作为首选。",
  },
  "all-MiniLM-L6-v2": {
    tag: "轻量英文基线",
    note: "速度快、占用低、维度小。适合做轻量对照或快速冒烟测试；复杂长记忆召回能力弱于 BGE 系列。",
  },
  "text2vec-base-chinese": {
    tag: "原中文模型",
    note: "原工程中文向量模型。当前 LOCOMO 隔离索引未为它重建，所以默认不参与三模型对照。",
  },
};

const METHOD_NOTES = {
  ordinary_recent: "普通上下文：不检索向量/BM25，只取当前会话最近 K 条记忆，作为无检索基线。",
  pure_rag: "纯 RAG：主路使用所选向量模型召回 LOCOMO Top-K；启用双路时，额外按同方法召回对话历史 Top-N 写入 prompt。",
  bm25_only: "BM25：只用关键词 BM25+ 召回，适合精确词、实体、短语匹配消融。",
  hybrid_rrf: "混合 RRF：向量召回和 BM25 召回用 Reciprocal Rank Fusion 融合，不加 ARPM 时间权重。",
  arpm_full: "ARPM 完整：主路为向量召回 + analysis/response 协议；LOCOMO 默认不启用物理时间/轮次衰减，只保留时间字段用于推理和日志。",
  arpm_hybrid_rrf: "ARPM Hybrid：主路向量 + BM25 + RRF；启用实时二路时，每题回答后会写入本次 run 的隔离索引，下一题再作为对话历史 Top-N 召回。LOCOMO 默认不启用时间/轮次衰减。",
};

const PROMPT_TEMPLATES = {
  locomo_arpm_protocol: `You are answering a LOCOMO long-term conversation memory question using retrieved memory.

[Protocol Goal]
Use the retrieved memory as historical evidence and follow the ARPM analysis-response format.
The final answer used for evaluation must be placed inside <response>...</response>.
Distinguish LOCOMO evidence/knowledge-base content from conversation-history content, and never treat retrieved history as the current user message.

[Analysis Task]
Write exactly one short sentence inside <analysis>...</analysis>.
Summarize which retrieved evidence is relevant to the question.
If the memory does not contain enough evidence, state that the answer is unclear.
Do not reveal step-by-step reasoning.

[Answer Task]
Write the final answer inside <response>...</response>.
The answer must be short, factual, and based only on the retrieved memory.
If the evidence is insufficient, answer "I don't know".

[Required Output Format]
<analysis>one-sentence evidence summary</analysis>
<response>short factual answer</response>`,
  locomo_plain: `You are answering a LOCOMO long-term conversation memory question.

Use only information supported by the retrieved memory.
If the evidence is insufficient, answer "I don't know".
Keep the answer short and factual.
Do not explain.`,
  empty: "",
};

function fmt(value) {
  if (value === undefined || value === null || value === "") return "-";
  const num = Number(value);
  if (Number.isFinite(num)) return num.toFixed(3);
  return String(value);
}

function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function setStatus(text) {
  $("status").textContent = text;
}

function readFieldValue(id) {
  const el = $(id);
  if (!el) return "";
  if (el.type === "checkbox") return Boolean(el.checked);
  return el.value;
}

function writeFieldValue(id, value) {
  const el = $(id);
  if (!el || value === undefined || value === null) return;
  if (el.type === "checkbox") {
    el.checked = Boolean(value);
  } else {
    el.value = String(value);
  }
}

function collectSettings({ includeApiKey = true } = {}) {
  const data = {};
  for (const id of SETTINGS_FIELDS) {
    if (!includeApiKey && id === "api-key") continue;
    data[id] = readFieldValue(id);
  }
  data.session_ids = selectedSessions();
  return data;
}

function applySettings(saved) {
  if (!saved || typeof saved !== "object") return;
  for (const id of SETTINGS_FIELDS) {
    if (Object.prototype.hasOwnProperty.call(saved, id)) {
      writeFieldValue(id, saved[id]);
    }
  }
  if (Array.isArray(saved.session_ids)) {
    state.selectedSessionIds = saved.session_ids.map(String);
  }
}

function loadLocalSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return;
    applySettings(JSON.parse(raw));
  } catch (err) {
    console.warn("Failed to load saved settings", err);
  }
}

async function loadProjectSettings() {
  try {
    const data = await request("/api/settings");
    const payload = data.settings?.settings || data.settings || {};
    if (Object.keys(payload).length) applySettings(payload);
  } catch (err) {
    console.warn("Failed to load project settings", err);
  }
}

function saveLocalSettings() {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(collectSettings({ includeApiKey: true })));
  } catch (err) {
    console.warn("Failed to save settings", err);
  }
}

async function saveProjectSettings() {
  saveLocalSettings();
  try {
    const res = await request("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ settings: collectSettings({ includeApiKey: true }) }),
    });
    setStatus(`当前配置已保存到项目：${res.path}`);
  } catch (err) {
    setStatus(`保存配置失败：${err.message}`);
  }
}

async function testApi() {
  const btn = $("btn-test-api");
  const label = $("api-test-status");
  const body = payload();
  btn.disabled = true;
  label.textContent = "测试中...";
  setStatus("正在测试 API 连通性...");
  try {
    const result = await request("/api/test-api", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_config: body.api_config }),
    });
    label.textContent = `可用 · ${result.latency_ms ?? "-"} ms · ${result.reply || "空回复"}`;
    setStatus(`API 可用：${result.reply || "空回复"}`);
  } catch (err) {
    label.textContent = `失败：${err.message}`;
    setStatus(`API 测试失败：${err.message}`);
  } finally {
    btn.disabled = false;
  }
}

function resetSavedSettings() {
  localStorage.removeItem(SETTINGS_KEY);
  setStatus("本地保存的设置已清除，刷新页面后会恢复默认值。");
}

function selectedPromptTemplate() {
  return PROMPT_TEMPLATES[$("prompt-template")?.value || "locomo_arpm_protocol"] ?? "";
}

function fillPromptTemplate() {
  $("system-prompt").value = selectedPromptTemplate();
  saveLocalSettings();
  setStatus("协议模板已填入。");
}

async function copyPromptTemplate() {
  const text = selectedPromptTemplate();
  try {
    await navigator.clipboard.writeText(text);
    setStatus("协议模板已复制。");
  } catch (err) {
    $("system-prompt").value = text;
    setStatus("浏览器不允许直接复制，已填入文本框。");
  }
}

function clearPromptTemplate() {
  $("system-prompt").value = "";
  $("prompt-template").value = "empty";
  saveLocalSettings();
  setStatus("协议 Prompt 已清空，可自行填写。");
}

async function request(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

async function loadSessions() {
  const data = await request("/api/sessions");
  state.sessions = data.sessions || [];
  state.embeddingModels = data.embedding_models || [];
  renderEmbeddingModels();
  renderSessions();
}

function renderEmbeddingModels() {
  const select = $("embedding-model");
  if (!select) return;
  const preferred = select.value || "bge-m3";
  const usable = state.embeddingModels.filter((model) => model.index_exists);
  const models = usable.length ? usable : state.embeddingModels;
  if (!models.length) return;
  select.innerHTML = models.map((model) => {
    const label = `${model.name} · ${model.language || "-"} · dim ${model.dim || "-"}`;
    const selected = model.name === preferred || (!preferred && model.name === "bge-m3") ? "selected" : "";
    const disabled = model.index_exists ? "" : "disabled";
    return `<option value="${esc(model.name)}" ${selected} ${disabled}>${esc(label)}${model.index_exists ? "" : "（未建索引）"}</option>`;
  }).join("");
  if ([...select.options].every((option) => !option.selected) && select.options.length) {
    const bgeM3 = [...select.options].find((option) => option.value === "bge-m3" && !option.disabled);
    (bgeM3 || select.options[0]).selected = true;
  }
  updateEmbeddingModelInfo();
}

function currentEmbeddingModel() {
  const name = $("embedding-model")?.value || "bge-m3";
  return state.embeddingModels.find((model) => model.name === name) || {
    name,
    language: "Multilingual",
    dim: 1024,
    index_exists: true,
  };
}

function updateEmbeddingModelInfo() {
  const box = $("embedding-model-info");
  if (!box) return;
  const method = $("method")?.value || "pure_rag";
  const model = currentEmbeddingModel();
  const note = MODEL_NOTES[model.name] || {
    tag: "自定义模型",
    note: "使用本地注册表中的向量模型，检索结果会进入对应模型的隔离向量库。",
  };
  const enabled = !["ordinary_recent", "bm25_only"].includes(method);
  const statusText = model.index_exists ? "索引已建立" : "未建立索引";
  const useText = enabled
    ? `后端将使用隔离索引：locomo_vector_db/${model.name}/chat。`
    : "当前方法不走向量召回；该模型选择不会影响本次检索。";
  box.innerHTML = `
    <div class="model-info-title">${esc(model.name)} <span>${esc(note.tag)}</span></div>
    <div class="model-info-body">${esc(note.note)}</div>
    <div class="model-info-grid">
      <b>语言</b><span>${esc(model.language || "-")}</span>
      <b>维度</b><span>${esc(model.dim || "-")}</span>
      <b>状态</b><span class="${model.index_exists ? "ok-text" : "bad-text"}">${esc(statusText)}</span>
    </div>
    <div class="model-info-foot">${esc(useText)}</div>
  `;
  const methodInfo = $("method-info");
  if (methodInfo) methodInfo.textContent = METHOD_NOTES[method] || "";
}

function renderSessions() {
  const selected = state.selectedSessionIds ? new Set(state.selectedSessionIds) : null;
  const html = state.sessions.map((s, index) => `
    <div class="session-item">
      <label>
        <input type="checkbox" class="session-check" value="${esc(s.session_id)}" ${(selected ? selected.has(String(s.session_id)) : index === 0) ? "checked" : ""}>
        <span>${esc(s.session_id)}</span>
      </label>
      <div class="session-meta">${esc(s.speaker_a || "?")} / ${esc(s.speaker_b || "?")} · turn ${s.chunks ?? 0} · QA ${s.qa ?? 0}</div>
    </div>
  `).join("");
  $("session-list").innerHTML = html || "<p class='hint'>没有发现 LOCOMO 会话，请先导入数据。</p>";
}

function selectedSessions() {
  return [...document.querySelectorAll(".session-check:checked")].map((el) => el.value);
}

function payload() {
  return {
    mode: $("mode").value,
    method: $("method").value,
    embedding_model: $("embedding-model").value || "bge-m3",
    session_ids: selectedSessions(),
    limit_per_session: Number($("limit").value || 10),
    top_k: Number($("top-k").value || 20),
    dual_route_enabled: $("dual-route-enabled").checked,
    realtime_write_enabled: $("realtime-write-enabled").checked,
    run_id: $("run-id").value.trim(),
    chat_history_k: Number($("chat-history-k").value || 10),
    decay_rate_round: Number($("decay-round").value || 20),
    round_decay_enabled: $("round-decay-enabled").checked,
    decay_rate_hours: Number($("decay-hours").value || 168),
    time_decay_enabled: $("time-decay-enabled").checked,
    api_delay_seconds: Number($("api-delay").value || 1),
    save_prompts: $("save-prompts").checked,
    allow_large_qa: $("allow-large-qa").checked,
    resume_run: $("resume-run").checked,
    system_prompt: $("system-prompt").value,
    api_config: {
      api_key: $("api-key").value,
      base_url: $("base-url").value,
      model: $("model-name").value,
      temperature: Number($("temperature").value || 0),
      max_tokens: Number($("max-tokens").value || 512),
    },
  };
}

function ensureRunId(body) {
  if (!body.dual_route_enabled || !body.realtime_write_enabled) return body;
  if (!body.resume_run || !body.run_id) {
    const stamp = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
    body.run_id = `locomo_run_${stamp}_${Math.random().toString(16).slice(2, 8)}`;
    $("run-id").value = body.run_id;
    saveLocalSettings();
  }
  return body;
}

function updateProgress(job) {
  const total = Number(job.total || 0);
  const done = Number(job.done || 0);
  const pct = total ? Math.min(100, Math.round((done / total) * 100)) : 0;
  $("progress-text").textContent = `${done} / ${total}`;
  $("job-state").textContent = job.status || "idle";
  $("progress-fill").style.width = `${pct}%`;
  $("current-item").textContent = job.current || "当前没有任务";
}

function stopPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

async function pollJob(jobId) {
  try {
    const job = await request(`/api/jobs/${jobId}`);
    state.rows = job.rows || [];
    if (state.followLatest) state.page = Math.max(1, Math.ceil(filteredRows().length / state.pageSize));
    renderMetrics(job.summary || {});
    renderChart(state.rows);
    renderResults();
    updateProgress(job);
    const err = job.errors?.length ? `，错误 ${job.errors.length} 条` : "";
    const resume = job.resume_source ? "，已启用断点续跑" : "";
    setStatus(`${job.status}：${job.done || 0}/${job.total || 0}${err}${resume}`);
    if (["completed", "failed", "cancelled"].includes(job.status)) {
      stopPolling();
      $("btn-run").disabled = false;
      state.jobId = null;
      if (state.rows.length) {
        setStatus(`${job.status}：${job.done || 0}/${job.total || 0}${err}${resume}，CSV 已自动生成，可下载或另存为。`);
      }
    }
  } catch (err) {
    stopPolling();
    $("btn-run").disabled = false;
    setStatus(`轮询失败：${err.message}`);
  }
}

async function run() {
  const body = ensureRunId(payload());
  if (!body.session_ids.length) {
    setStatus("请至少选择一个会话。");
    return;
  }
  if (body.mode === "qa" && !body.allow_large_qa && body.session_ids.length * body.limit_per_session > 100) {
    setStatus("QA 生成超过 100 条，请减少数量或勾选允许大批量 QA。");
    return;
  }
  stopPolling();
  state.rows = [];
  state.page = 1;
  state.followLatest = true;
  renderMetrics({});
  renderChart([]);
  renderResults();
  updateProgress({ status: "starting", done: 0, total: 0, current: "正在创建任务" });
  setStatus("正在创建后台任务...");
  $("btn-run").disabled = true;
  try {
    const job = await request("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    state.jobId = job.job_id;
    updateProgress(job);
    setStatus(`任务已启动：${job.job_id}`);
    state.pollTimer = setInterval(() => pollJob(job.job_id), 900);
    await pollJob(job.job_id);
  } catch (err) {
    $("btn-run").disabled = false;
    state.jobId = null;
    setStatus(`运行失败：${err.message}`);
  }
}

async function stopJob() {
  if (!state.jobId) {
    setStatus("当前没有正在运行的任务。");
    return;
  }
  try {
    const job = await request(`/api/jobs/${state.jobId}/cancel`, { method: "POST" });
    updateProgress(job);
    setStatus("已请求停止，若正在等待 API，会在当前请求结束后停止。");
  } catch (err) {
    setStatus(`停止失败：${err.message}`);
  }
}

function clearView() {
  state.rows = [];
  state.page = 1;
  state.followLatest = true;
  renderMetrics({});
  renderChart([]);
  renderResults();
  updateProgress({ status: "idle", done: 0, total: 0, current: "当前没有任务" });
}

async function clearRecords() {
  if (state.jobId) {
    setStatus("请先停止或等待当前任务结束，再清空记录。");
    return;
  }
  if (!confirm("确认清空最新结果和后台任务记录？这不会删除 LOCOMO 原始数据、会话索引和 LOCOMO/log 归档日志。")) return;
  try {
    const res = await request("/api/results/clear", { method: "POST" });
    clearView();
    setStatus(res.message || "记录已清空。");
  } catch (err) {
    setStatus(`清空失败：${err.message}`);
  }
}

async function saveAsCsv() {
  const path = $("save-as-path").value.trim();
  if (!path) {
    setStatus("请先填写另存路径，例如 D:\\LOCOMO\\result.csv");
    return;
  }
  try {
    const res = await request("/api/export/save-as", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    setStatus(`CSV 已另存为：${res.path}`);
  } catch (err) {
    setStatus(`另存失败：${err.message}`);
  }
}

function renderMetrics(summary) {
  $("m-count").textContent = summary.count ?? 0;
  $("m-r5").textContent = fmt(summary.recall_at_5 ?? 0);
  $("m-r10").textContent = fmt(summary.recall_at_10 ?? 0);
  $("m-mrr").textContent = fmt(summary.mrr ?? 0);
  $("m-em").textContent = summary.em === undefined ? "-" : fmt(summary.em);
  $("m-f1").textContent = summary.f1 === undefined ? "-" : fmt(summary.f1);
}

function renderChart(rows) {
  const grouped = new Map();
  for (const row of rows) {
    const key = row.session_id;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(row);
  }
  const parts = [];
  for (const [sid, group] of grouped) {
    const value = group.reduce((sum, row) => sum + Number(row.recall_at_10 || 0), 0) / Math.max(group.length, 1);
    parts.push(`
      <div class="bar-row">
        <div class="bar-label" title="${esc(sid)}">${esc(sid)}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${Math.round(value * 100)}%"></div></div>
        <div class="bar-value">${fmt(value)}</div>
      </div>
    `);
  }
  $("chart").innerHTML = parts.join("") || "<p class='hint'>暂无图表。</p>";
}

function filteredRows() {
  let rows = state.rows;
  if (state.filter === "miss") rows = rows.filter((row) => !Number(row.recall_at_10 || 0));
  return rows;
}

function updatePager(totalRows) {
  const totalPages = Math.max(1, Math.ceil(totalRows / state.pageSize));
  state.page = Math.min(Math.max(1, state.page), totalPages);
  $("page-info").textContent = `第 ${state.page} / ${totalPages} 页 · 每页 ${state.pageSize} 题 · 共 ${totalRows} 题`;
  $("page-prev").disabled = state.page <= 1;
  $("page-next").disabled = state.page >= totalPages;
}

function renderChunkList(chunks, goldEvidence = []) {
  const goldSet = new Set(goldEvidence || []);
  return (chunks || []).map((c, idx) => {
    const w = c.weight_trace || {};
    const isGold = Boolean(w.is_gold_evidence) || goldSet.has(c.dia_id);
    return `
      <div class="chunk">
        <div class="chunk-meta">
          #${idx + 1} · ${esc(c.dia_id)} ${isGold ? "<span class='gold-tag'>官方证据</span>" : ""}
          · ${esc(c.route || "locomo_evidence")} · round=${esc(c.round_num)} · ${esc(c.physical_time)} · ${esc(c.speaker)}
        </div>
        <div class="weight-grid">
          <span>原始向量分</span><b>${fmt(w.base_score ?? c.score)}</b>
          <span>向量模型</span><b>${esc(w.embedding_model || c.embedding_model || "-")}</b>
          <span>召回来源</span><b>${esc(c.retrieval_source || (Array.isArray(c.retrieval_sources) ? c.retrieval_sources.join("+") : "") || "vector")}</b>
          <span>BM25分</span><b>${fmt(c.bm25_score)}</b>
          <span>RRF分</span><b>${fmt(c.rrf_score)}</b>
          <span>向量/BM25名次</span><b>${esc(`${c.vector_rank || "-"} / ${c.bm25_rank || "-"}`)}</b>
          <span>语义分</span><b>${fmt(w.semantic_score)}</b>
          <span>轮次差</span><b>${esc(w.delta_round ?? "-")}</b>
          <span>轮次权重</span><b>${fmt(w.round_weight)}</b>
          <span>时间差/小时</span><b>${fmt(w.hours_delta)}</b>
          <span>时间权重</span><b>${fmt(w.time_weight)}</b>
          <span>时间总权重</span><b>${fmt(w.temporal_weight)}</b>
          <span>最终加权分</span><b>${fmt(w.weighted_score ?? c.weighted_score ?? c.score)}</b>
        </div>
        <div class="formula">${esc(w.formula || "weighted_score = base_score")}</div>
        <div class="chunk-text">${esc(c.text_raw)}</div>
      </div>
    `;
  }).join("");
}

function renderResults() {
  const rows = filteredRows();
  updatePager(rows.length);
  if (!rows.length) {
    $("results").className = "results empty";
    $("results").textContent = "没有符合条件的结果。";
    return;
  }
  $("results").className = "results";
  const start = (state.page - 1) * state.pageSize;
  const pageRows = rows.slice(start, start + state.pageSize);
  $("results").innerHTML = pageRows.map((row, pageIndex) => {
    const serial = start + pageIndex + 1;
    const hit = Number(row.recall_at_10 || 0) > 0;
    const chunks = renderChunkList(row.retrieved_chunks || [], row.gold_evidence || []);
    const chatChunks = renderChunkList(row.chat_history_chunks || [], row.gold_evidence || []);
    return `
      <article class="qa-card">
        <div class="qa-head">
          <div>
            <div class="qa-title">#${serial} ${esc(row.question)}</div>
            <div class="qa-sub">${esc(row.qa_id)} · ${esc(row.session_id)} · category ${esc(row.category)}</div>
          </div>
          <span class="badge ${hit ? "hit" : "miss"}">${hit ? "Hit@10" : "Miss@10"}</span>
        </div>
        <div class="qa-body">
          <div class="kv"><b>官方答案</b><span>${esc(row.gold_answer)}</span></div>
          <div class="kv"><b>模型答案</b><span>${esc(row.pred_answer || "-")}</span></div>
          <div class="kv"><b>analysis</b><span>${esc(row.analysis_answer || "-")}</span></div>
          <details>
            <summary>模型原始输出</summary>
            <pre class="raw-output">${esc(row.raw_pred_answer || "-")}</pre>
          </details>
          <div class="kv"><b>官方证据</b><span>${esc((row.gold_evidence || []).join(", "))}</span></div>
          <div class="kv"><b>召回证据</b><span>${esc((row.retrieved_dia_ids || []).join(", "))}</span></div>
          <div class="kv"><b>对话历史二路</b><span>${esc((row.chat_history_dia_ids || []).join(", ") || "-")}</span></div>
          <div class="kv"><b>实时写入</b><span>${esc(row.realtime_run_id ? `${row.realtime_run_id} · ${(row.written_realtime_chunk || {}).dia_id || "未写入"}` : "-")}</span></div>
          <div class="kv"><b>指标</b><span>R@5=${fmt(row.recall_at_5)} · R@10=${fmt(row.recall_at_10)} · MRR=${fmt(row.mrr)} · EM=${fmt(row.em)} · F1=${fmt(row.f1)}</span></div>
          <details open>
            <summary>主路 LOCOMO 召回片段与加权细节</summary>
            <div class="chunks">${chunks}</div>
          </details>
          <details ${chatChunks ? "open" : ""}>
            <summary>二路对话历史召回片段与加权细节</summary>
            <div class="chunks">${chatChunks || "<p class='hint'>未启用双路注入。</p>"}</div>
          </details>
        </div>
      </article>
    `;
  }).join("");
}

function bind() {
  $("btn-refresh").addEventListener("click", () => loadSessions().catch((e) => setStatus(e.message)));
  $("btn-clear").addEventListener("click", clearRecords);
  $("btn-reset-settings").addEventListener("click", resetSavedSettings);
  $("btn-save-as").addEventListener("click", saveAsCsv);
  $("btn-fill-template").addEventListener("click", fillPromptTemplate);
  $("btn-copy-template").addEventListener("click", copyPromptTemplate);
  $("btn-clear-prompt").addEventListener("click", clearPromptTemplate);
  $("btn-test-api").addEventListener("click", testApi);
  $("btn-all").addEventListener("click", () => {
    const checks = [...document.querySelectorAll(".session-check")];
    const allChecked = checks.every((el) => el.checked);
    checks.forEach((el) => { el.checked = !allChecked; });
    saveLocalSettings();
  });
  $("btn-run").addEventListener("click", run);
  $("btn-stop").addEventListener("click", stopJob);
  $("filter-all").addEventListener("click", () => {
    state.filter = "all";
    state.page = 1;
    state.followLatest = false;
    $("filter-all").classList.add("active");
    $("filter-miss").classList.remove("active");
    renderResults();
  });
  $("filter-miss").addEventListener("click", () => {
    state.filter = "miss";
    state.page = 1;
    state.followLatest = false;
    $("filter-miss").classList.add("active");
    $("filter-all").classList.remove("active");
    renderResults();
  });
  $("btn-save-settings").addEventListener("click", saveProjectSettings);
  $("page-prev").addEventListener("click", () => {
    state.page = Math.max(1, state.page - 1);
    state.followLatest = false;
    renderResults();
  });
  $("page-next").addEventListener("click", () => {
    state.page += 1;
    state.followLatest = false;
    renderResults();
  });
  $("mode").addEventListener("change", () => {
    $("api-panel").style.opacity = $("mode").value === "qa" ? "1" : "0.45";
  });
  $("method").addEventListener("change", () => {
    updateEmbeddingModelInfo();
    saveLocalSettings();
  });
  $("embedding-model").addEventListener("change", () => {
    updateEmbeddingModelInfo();
    saveLocalSettings();
  });
  document.querySelector(".settings")?.addEventListener("input", saveLocalSettings);
  document.querySelector(".settings")?.addEventListener("change", saveLocalSettings);
}

async function init() {
  loadLocalSettings();
  await loadProjectSettings();
  bind();
  await loadSessions();
  const data = await request("/api/results/latest");
  state.rows = data.rows || [];
  renderMetrics(data.summary || {});
  renderChart(state.rows);
  renderResults();
  setStatus("数据已加载。");
}

init()
  .catch((err) => setStatus(`加载失败：${err.message}`));
