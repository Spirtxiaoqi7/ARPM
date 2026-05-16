const STORAGE_KEYS = {
    api: "arpm.api.config",
    ui: "arpm.ui.config",
    currentSession: "arpm.ui.current_session"
};

const MAX_SESSION_NAME_LENGTH = 40;
const MAX_SESSION_LABEL_LENGTH = 30;
const THEME_KEYS = ["chat", "research"];

const I18N = {
    zh: {
        globalSearch: ["知识库", "全局检索与块管理"],
        sessionSearch: ["会话记忆", "当前历史块管理"],
        collapseOpen: ["收起侧栏", "保留主工作区"],
        collapseClosed: ["展开侧栏", "显示会话与设置"],
        commonSettings: ["常规设置", "身份、角色、API、检测"],
        paramSettings: ["参数设置", "检索、知识库、实验参数"],
        themeChat: "聊天风格",
        themeResearch: "研究风格",
        currentSession: "当前会话编号：",
        date: "日期：",
        apiStatus: "API状态",
        llm: "LLM：",
        arpmStatus: "ARPM系统状态：",
        notCreated: "未创建",
        apiConnected: "已连接",
        apiDisconnected: "未连接",
        arpmOk: "正常",
        arpmError: "异常",
        export: "导出当前会话",
        welcomeTitle: "ARPM v4",
        welcomeText: "召回内容与 prompt 写入会在右侧同步显示",
        configure: "配置 API 与角色",
        params: "查看检索参数",
        inputPlaceholder: "此空白为用户输入",
        ready: "就绪",
        stats: (knowledge, sessions, vectors) => `知识块 ${knowledge} · 会话 ${sessions} · 向量 ${vectors}`,
        clearContext: "清空上下文",
        clearContextIndex: "清空上下文和索引",
        ragPanel: "召回内容与 prompt 实际写入",
        cotPanel: "思维链 / 协议诊断",
        settingsTitle: "常规设置",
        paramsTitle: "参数设置",
        apiConfigTitle: "API 配置",
        apiKey: "API 密钥",
        baseUrl: "接口地址",
        modelName: "模型名称",
        userTitle: "用户设定",
        userName: "你的名字",
        userPersona: "你的人物设定（可选）",
        aiTitle: "AI角色设定",
        characterName: "角色名称",
        systemPrompt: "角色设定",
        basicTitle: "基础检测",
        basicDesc: "这里只放开源展示时最常用的连接与健康检测；检索、知识库和实验参数放在参数设置中。",
        protocolTitle: "分析式生成协议",
        protocolMode: "协议模式",
        reasoningMode: "模型思考链路",
        kbTitle: "知识库",
        childSize: "子块长度",
        parentSize: "父块长度",
        overlap: "重叠句数",
        ablationTitle: "消融实验开关",
        tuningTitle: "参数调优",
        presets: "预设",
        dangerTitle: "数据管理（危险操作）",
        testConnection: "测试连接",
        openDiagnostics: "打开系统自检",
        systemHealth: "系统健康检查",
        chooseFile: "选择文件",
        manage: "管理",
        save: "保存",
        saveParams: "保存参数",
        refresh: "刷新",
        apiTest: "测试API连接",
        arpmReport: "ARPM组件报告",
        loadKbChunks: "加载知识库块",
        loadChatChunks: "加载对话历史块",
        langToast: "已切换为中文展示",
        loadKb: "加载知识库...",
        loadMemory: "加载会话记忆...",
        kbLoaded: "知识库块已加载",
        memoryLoaded: "当前会话记忆块已加载",
        needSession: "请先创建或选择一个会话",
        collapsed: "侧栏已收起",
        expanded: "侧栏已展开",
        emptyExport: "当前会话为空，无需导出"
    },
    en: {
        globalSearch: ["Knowledge", "Global search and chunks"],
        sessionSearch: ["Memory", "Current session chunks"],
        collapseOpen: ["Collapse", "Keep the workspace focused"],
        collapseClosed: ["Expand", "Show sessions and settings"],
        commonSettings: ["General", "Identity, role, API, checks"],
        paramSettings: ["Parameters", "Retrieval, knowledge, experiments"],
        themeChat: "Chat",
        themeResearch: "Research",
        currentSession: "Session:",
        date: "Date:",
        apiStatus: "API",
        llm: "LLM:",
        arpmStatus: "ARPM",
        notCreated: "Not created",
        apiConnected: "Connected",
        apiDisconnected: "Disconnected",
        arpmOk: "OK",
        arpmError: "Issue",
        export: "Export session",
        welcomeTitle: "ARPM v4",
        welcomeText: "Retrieved context and prompt injection appear in the right panel.",
        configure: "Configure API and role",
        params: "Review retrieval parameters",
        inputPlaceholder: "Type your message here",
        ready: "Ready",
        stats: (knowledge, sessions, vectors) => `Knowledge ${knowledge} · Sessions ${sessions} · Vectors ${vectors}`,
        clearContext: "Clear context",
        clearContextIndex: "Clear context and index",
        ragPanel: "Retrieved context and prompt injection",
        cotPanel: "Reasoning / protocol diagnostics",
        settingsTitle: "General settings",
        paramsTitle: "Parameter settings",
        apiConfigTitle: "API configuration",
        apiKey: "API key",
        baseUrl: "Base URL",
        modelName: "Model",
        userTitle: "User profile",
        userName: "Your name",
        userPersona: "Your persona (optional)",
        aiTitle: "AI role",
        characterName: "Role name",
        systemPrompt: "Role prompt",
        basicTitle: "Basic checks",
        basicDesc: "Common connection and health checks live here; retrieval, knowledge, and experiment controls live under Parameters.",
        protocolTitle: "Generation protocol",
        protocolMode: "Protocol mode",
        reasoningMode: "Reasoning route",
        kbTitle: "Knowledge base",
        childSize: "Child chunk size",
        parentSize: "Parent chunk size",
        overlap: "Overlap sentences",
        ablationTitle: "Ablation switches",
        tuningTitle: "Parameter tuning",
        presets: "Presets",
        dangerTitle: "Data management (danger zone)",
        testConnection: "Test connection",
        openDiagnostics: "Open diagnostics",
        systemHealth: "Health check",
        chooseFile: "Choose file",
        manage: "Manage",
        save: "Save",
        saveParams: "Save parameters",
        refresh: "Refresh",
        apiTest: "Test API",
        arpmReport: "ARPM report",
        loadKbChunks: "Load knowledge chunks",
        loadChatChunks: "Load chat chunks",
        langToast: "Switched to English display",
        loadKb: "Loading knowledge...",
        loadMemory: "Loading memory...",
        kbLoaded: "Knowledge chunks loaded",
        memoryLoaded: "Session memory chunks loaded",
        needSession: "Create or select a session first",
        collapsed: "Sidebar collapsed",
        expanded: "Sidebar expanded",
        emptyExport: "This session is empty"
    }
};

const State = {
    sessionId: null,
    sessionName: "",
    sessionLabel: "",
    displayTitle: "",
    round: 1,
    messages: [],
    isGenerating: false,
    kbChunks: [],
    kbFilteredChunks: [],
    chatChunks: [],
    currentTab: "components",
    currentDeleteTab: "kb-delete",
    apiConfig: {
        api_key: "",
        base_url: "https://api.deepseek.com",
        model: "deepseek-chat"
    },
    sessionConfig: {
        user_name: "\u7528\u6237",
        user_persona: "",
        character_name: "AI\u52a9\u624b",
        system_prompt: ""
    },
    protocolConfig: {
        protocol_mode: "auto",
        reasoning_model_mode: "auto",
        auto_repair_response: true,
        diagnostic_mode: true
    },
    chunkConfig: {
        child_size: 200,
        parent_size: 600,
        overlap_sentences: 1
    },
    tuning: {
        knowledge_k: 5,
        chat_history_k: 10,
        similarity_threshold: 0.5,
        decay_rate_round: 20,
        decay_rate_hours: 168,
        rrf_k: 60,
        role_query_prefix_enabled: true,
        kb_user_name_boost: 0.08,
        kb_character_name_boost: 0.08,
        kb_source_name_boost: 0.05,
        chat_same_session_boost: 0.15,
        chat_exact_name_boost: 0.10,
        chat_text_name_boost: 0.04,
        temperature: 0.7,
        max_tokens: 2000
    },
    ablation: {
        rag_enabled: true,
        kb_enabled: true,
        chat_enabled: true,
        temporal_enabled: true,
        bm25_enabled: true,
        regeneration_enabled: true,
        regen_max_attempts: 1,
        regen_regex: true,
        regen_semantic: false,
        similarity_threshold: 0.5
    },
    uiState: null,
    language: "zh",
    theme: "chat",
    themeProfiles: {
        chat: { avatars: { user: null, assistant: null } },
        research: { avatars: { user: null, assistant: null } }
    }
};

const DOM = {
    welcome: document.getElementById("welcome"),
    chatContainer: document.getElementById("chat-container"),
    sessionList: document.getElementById("session-list"),
    modelDisplay: document.getElementById("model-display"),
    labelSessionId: document.getElementById("label-session-id"),
    labelSessionDate: document.getElementById("label-session-date"),
    labelApiStatus: document.getElementById("label-api-status"),
    labelLlm: document.getElementById("label-llm"),
    labelArpmStatus: document.getElementById("label-arpm-status"),
    labelRagPanel: document.getElementById("label-rag-panel"),
    labelCotPanel: document.getElementById("label-cot-panel"),
    titleSettings: document.getElementById("title-settings"),
    titleParams: document.getElementById("title-params"),
    sectionApiTitle: document.getElementById("section-api-title"),
    labelApiKey: document.getElementById("label-api-key"),
    labelBaseUrl: document.getElementById("label-base-url"),
    labelModelName: document.getElementById("label-model-name"),
    sectionUserTitle: document.getElementById("section-user-title"),
    labelUserName: document.getElementById("label-user-name"),
    labelUserPersona: document.getElementById("label-user-persona"),
    sectionAiTitle: document.getElementById("section-ai-title"),
    labelCharacterName: document.getElementById("label-character-name"),
    labelSystemPrompt: document.getElementById("label-system-prompt"),
    sectionBasicTitle: document.getElementById("section-basic-title"),
    basicDesc: document.getElementById("basic-desc"),
    sectionProtocolTitle: document.getElementById("section-protocol-title"),
    labelProtocolMode: document.getElementById("label-protocol-mode"),
    labelReasoningMode: document.getElementById("label-reasoning-mode"),
    sectionKbTitle: document.getElementById("section-kb-title"),
    labelChildSize: document.getElementById("label-child-size"),
    labelParentSize: document.getElementById("label-parent-size"),
    labelOverlap: document.getElementById("label-overlap"),
    sectionAblationTitle: document.getElementById("section-ablation-title"),
    sectionTuningTitle: document.getElementById("section-tuning-title"),
    labelPresets: document.getElementById("label-presets"),
    sectionDangerTitle: document.getElementById("section-danger-title"),
    uiPortText: document.getElementById("ui-port-text"),
    uiStatsText: document.getElementById("ui-stats-text"),
    sessionMetaId: document.getElementById("session-meta-id"),
    sessionMetaDate: document.getElementById("session-meta-date"),
    apiStatusText: document.getElementById("api-status-text"),
    arpmStatusText: document.getElementById("arpm-status-text"),
    btnExportCurrent: document.getElementById("btn-export-current"),
    btnGlobalSearch: document.getElementById("btn-global-search"),
    btnSessionSearch: document.getElementById("btn-session-search"),
    btnCollapseSidebar: document.getElementById("btn-collapse-sidebar"),
    btnThemeChat: document.getElementById("btn-theme-chat"),
    btnThemeResearch: document.getElementById("btn-theme-research"),
    btnLangZh: document.getElementById("btn-lang-zh"),
    btnLangEn: document.getElementById("btn-lang-en"),
    welcomeOpenSettings: document.getElementById("welcome-open-settings"),
    welcomeOpenParams: document.getElementById("welcome-open-params"),
    userInput: document.getElementById("user-input"),
    btnInputSettings: document.getElementById("btn-input-settings"),
    btnSend: document.getElementById("btn-send"),
    btnStop: document.getElementById("btn-stop"),
    statusText: document.getElementById("status-text"),
    roundText: document.getElementById("round-text"),
    btnNewChat: document.getElementById("new-chat"),
    btnClearChat: document.getElementById("btn-clear-chat"),
    btnClearChatIndex: document.getElementById("btn-clear-chat-index"),
    ragContent: document.getElementById("rag-content"),
    ragCount: document.getElementById("rag-count"),
    cotContent: document.getElementById("cot-content"),
    toastContainer: document.getElementById("toast-container"),
    ragHelpBtn: document.getElementById("rag-help-btn"),
    ragHelpModal: document.getElementById("rag-help-modal"),
    closeRagHelp: document.getElementById("close-rag-help"),
    ragHelpContent: document.getElementById("rag-help-content"),
    settingsModal: document.getElementById("settings-modal"),
    paramsModal: document.getElementById("params-modal"),
    paramsModalBody: document.getElementById("params-modal-body"),
    openSettings: document.getElementById("open-settings"),
    closeSettings: document.getElementById("close-settings"),
    closeParams: document.getElementById("close-params"),
    saveSettings: document.getElementById("save-settings"),
    saveParams: document.getElementById("save-params"),
    openDiagnoseBasic: document.getElementById("open-diagnose-basic"),
    btnCommonCheckApi: document.getElementById("btn-common-check-api"),
    btnCommonSystemDiag: document.getElementById("btn-common-system-diag"),
    commonDiagnoseStatus: document.getElementById("common-diagnose-status"),
    cfgApiKey: document.getElementById("cfg-api-key"),
    cfgBaseUrl: document.getElementById("cfg-base-url"),
    cfgModel: document.getElementById("cfg-model"),
    testApi: document.getElementById("test-api"),
    testResult: document.getElementById("test-result"),
    cfgUserName: document.getElementById("cfg-user-name"),
    cfgUserPersona: document.getElementById("cfg-user-persona"),
    labelUserAvatar: document.getElementById("label-user-avatar"),
    userAvatarPreview: document.getElementById("user-avatar-preview"),
    userAvatarInput: document.getElementById("user-avatar-input"),
    uploadUserAvatar: document.getElementById("upload-user-avatar"),
    resetUserAvatar: document.getElementById("reset-user-avatar"),
    cfgCharacterName: document.getElementById("cfg-character-name"),
    cfgSystemPrompt: document.getElementById("cfg-system-prompt"),
    labelAssistantAvatar: document.getElementById("label-assistant-avatar"),
    assistantAvatarPreview: document.getElementById("assistant-avatar-preview"),
    assistantAvatarInput: document.getElementById("assistant-avatar-input"),
    uploadAssistantAvatar: document.getElementById("upload-assistant-avatar"),
    resetAssistantAvatar: document.getElementById("reset-assistant-avatar"),
    cfgProtocolMode: document.getElementById("cfg-protocol-mode"),
    cfgReasoningModelMode: document.getElementById("cfg-reasoning-model-mode"),
    cfgAutoRepairResponse: document.getElementById("cfg-auto-repair-response"),
    cfgProtocolDiagnostic: document.getElementById("cfg-protocol-diagnostic"),
    cfgRagEnabled: document.getElementById("cfg-rag-enabled"),
    ragSubitems: document.getElementById("rag-subitems"),
    cfgKbEnabled: document.getElementById("cfg-kb-enabled"),
    cfgChatEnabled: document.getElementById("cfg-chat-enabled"),
    cfgTemporalEnabled: document.getElementById("cfg-temporal-enabled"),
    cfgBm25Enabled: document.getElementById("cfg-bm25-enabled"),
    cfgSimilarityThreshold: document.getElementById("cfg-similarity-threshold"),
    similarityThresholdValue: document.getElementById("similarity-threshold-value"),
    cfgRegenEnabled: document.getElementById("cfg-regen-enabled"),
    cfgRegenMax: document.getElementById("cfg-regen-max"),
    cfgRegenRegex: document.getElementById("cfg-regen-regex"),
    cfgRegenSemantic: document.getElementById("cfg-regen-semantic"),
    cfgKnowledgeK: document.getElementById("cfg-knowledge-k"),
    cfgChatHistoryK: document.getElementById("cfg-chat-history-k"),
    cfgDecayRound: document.getElementById("cfg-decay-round"),
    cfgDecayHours: document.getElementById("cfg-decay-hours"),
    cfgRrfK: document.getElementById("cfg-rrf-k"),
    cfgTemperature: document.getElementById("cfg-temperature"),
    cfgMaxTokens: document.getElementById("cfg-max-tokens"),
    cfgRoleQueryPrefix: document.getElementById("cfg-role-query-prefix"),
    cfgKbUserBoost: document.getElementById("cfg-kb-user-boost"),
    cfgKbCharacterBoost: document.getElementById("cfg-kb-character-boost"),
    cfgKbSourceBoost: document.getElementById("cfg-kb-source-boost"),
    cfgChatSessionBoost: document.getElementById("cfg-chat-session-boost"),
    cfgChatExactBoost: document.getElementById("cfg-chat-exact-boost"),
    cfgChatTextBoost: document.getElementById("cfg-chat-text-boost"),
    clearKb: document.getElementById("clear-kb"),
    clearChatHistory: document.getElementById("clear-chat-history"),
    clearAllData: document.getElementById("clear-all-data"),
    clearDataResult: document.getElementById("clear-data-result"),
    fileUpload: document.getElementById("file-upload"),
    uploadFile: document.getElementById("upload-file"),
    fileName: document.getElementById("file-name"),
    cfgChunkChildSize: document.getElementById("cfg-chunk-child-size"),
    cfgChunkParentSize: document.getElementById("cfg-chunk-parent-size"),
    cfgChunkOverlap: document.getElementById("cfg-chunk-overlap"),
    uploadProgressContainer: document.getElementById("upload-progress-container"),
    uploadProgressText: document.getElementById("upload-progress-text"),
    uploadProgressPercent: document.getElementById("upload-progress-percent"),
    uploadProgressBar: document.getElementById("upload-progress-bar"),
    kbCount: document.getElementById("kb-count"),
    manageKb: document.getElementById("manage-kb"),
    kbModal: document.getElementById("kb-modal"),
    closeKb: document.getElementById("close-kb"),
    kbSearch: document.getElementById("kb-search"),
    kbRefresh: document.getElementById("kb-refresh"),
    kbList: document.getElementById("kb-list"),
    diagnoseModal: document.getElementById("diagnose-modal"),
    openDiagnose: document.getElementById("open-diagnose"),
    closeDiagnose: document.getElementById("close-diagnose"),
    btnCheckApi: document.getElementById("btn-check-api"),
    btnArpmReport: document.getElementById("btn-arpm-report"),
    btnSystemDiag: document.getElementById("btn-system-diag"),
    diagnoseStatus: document.getElementById("diagnose-status"),
    apiCheckResult: document.getElementById("api-check-result"),
    arpmReportSection: document.getElementById("arpm-report-section"),
    tabComponents: document.getElementById("tab-components"),
    tabForgetting: document.getElementById("tab-forgetting"),
    tabStats: document.getElementById("tab-stats"),
    btnLoadKbChunks: document.getElementById("btn-load-kb-chunks"),
    kbChunksCount: document.getElementById("kb-chunks-count"),
    kbChunksList: document.getElementById("kb-chunks-list"),
    btnLoadChatChunks: document.getElementById("btn-load-chat-chunks"),
    chatChunksCount: document.getElementById("chat-chunks-count"),
    chatChunksList: document.getElementById("chat-chunks-list"),
    systemDiagResult: document.getElementById("system-diag-result")
};

const TUNING_PRESETS = {
    balanced: {
        knowledge_k: 5,
        chat_history_k: 12,
        similarity_threshold: 0.45,
        decay_rate_round: 25,
        decay_rate_hours: 240,
        rrf_k: 60,
        temperature: 0.7,
        max_tokens: 2000,
        role_query_prefix_enabled: true,
        kb_user_name_boost: 0.08,
        kb_character_name_boost: 0.08,
        kb_source_name_boost: 0.05,
        chat_same_session_boost: 0.15,
        chat_exact_name_boost: 0.10,
        chat_text_name_boost: 0.04
    },
    strict: {
        knowledge_k: 6,
        chat_history_k: 8,
        similarity_threshold: 0.58,
        decay_rate_round: 18,
        decay_rate_hours: 168,
        rrf_k: 60,
        temperature: 0.45,
        max_tokens: 1600,
        role_query_prefix_enabled: true,
        kb_user_name_boost: 0.06,
        kb_character_name_boost: 0.08,
        kb_source_name_boost: 0.06,
        chat_same_session_boost: 0.18,
        chat_exact_name_boost: 0.12,
        chat_text_name_boost: 0.03
    },
    companion: {
        knowledge_k: 4,
        chat_history_k: 14,
        similarity_threshold: 0.40,
        decay_rate_round: 35,
        decay_rate_hours: 336,
        rrf_k: 60,
        temperature: 0.75,
        max_tokens: 2200,
        role_query_prefix_enabled: true,
        kb_user_name_boost: 0.08,
        kb_character_name_boost: 0.08,
        kb_source_name_boost: 0.05,
        chat_same_session_boost: 0.20,
        chat_exact_name_boost: 0.12,
        chat_text_name_boost: 0.05
    }
};

const Utils = {
    escapeHtml(text) {
        return String(text ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    },

    formatText(text) {
        const escaped = this.escapeHtml(text);
        return escaped
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            .replace(/`([^`]+)`/g, "<code>$1</code>")
            .replace(/\n/g, "<br>");
    },

    generateSessionId() {
        if (window.crypto?.randomUUID) {
            return window.crypto.randomUUID();
        }
        return `session-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
    },

    showToast(message, type = "success", duration = 2600) {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;
        DOM.toastContainer.appendChild(toast);
        window.setTimeout(() => toast.remove(), duration);
    },

    setStatus(text, level = "") {
        DOM.statusText.textContent = text;
        DOM.statusText.className = "";
        if (level) {
            DOM.statusText.classList.add(level);
        }
        if (DOM.arpmStatusText) {
            DOM.arpmStatusText.textContent = level === "error" ? "异常" : "正常";
            DOM.arpmStatusText.className = level || "success";
        }
    },

    setDiagnoseStatus(text, level = "") {
        DOM.diagnoseStatus.textContent = text;
        DOM.diagnoseStatus.className = "";
        if (level) {
            DOM.diagnoseStatus.classList.add(level);
        }
    },

    openModal(element) {
        element?.classList.add("show");
    },

    closeModal(element) {
        element?.classList.remove("show");
    },

    async request(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
                ...(options.headers || {})
            }
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || data.message || `\u8bf7\u6c42\u5931\u8d25: ${response.status}`);
        }
        return data;
    }
};

function loadLocalApiConfig() {
    try {
        const raw = window.localStorage.getItem(STORAGE_KEYS.api);
        if (raw) {
            State.apiConfig = { ...State.apiConfig, ...JSON.parse(raw) };
        }
        const uiRaw = window.localStorage.getItem(STORAGE_KEYS.ui);
        if (uiRaw) {
            const uiConfig = JSON.parse(uiRaw);
            State.language = uiConfig.language === "en" ? "en" : "zh";
            State.theme = uiConfig.theme === "research" ? "research" : "chat";
        }
    } catch (error) {
        console.error("\u8bfb\u53d6\u672c\u5730 API \u914d\u7f6e\u5931\u8d25", error);
    }
}

function saveLocalApiConfig() {
    window.localStorage.setItem(STORAGE_KEYS.api, JSON.stringify(State.apiConfig));
}

function clampNumber(value, min, max, fallback) {
    const num = Number(value);
    if (Number.isNaN(num)) {
        return fallback;
    }
    return Math.min(max, Math.max(min, num));
}

function updateThresholdLabel() {
    DOM.similarityThresholdValue.textContent = (Number(DOM.cfgSimilarityThreshold.value || 50) / 100).toFixed(2);
}

function updateModelDisplay() {
    const text = I18N[State.language] || I18N.zh;
    const model = State.apiConfig.model || "deepseek-chat";
    DOM.modelDisplay.textContent = model;
    if (DOM.apiStatusText) {
        DOM.apiStatusText.textContent = State.apiConfig.api_key ? text.apiConnected : text.apiDisconnected;
        DOM.apiStatusText.className = State.apiConfig.api_key ? "success" : "";
    }
}

function renderUiState(uiState) {
    State.uiState = uiState;
    const app = uiState?.app || {};
    const stats = uiState?.stats || {};
    if (DOM.uiPortText) {
        DOM.uiPortText.textContent = State.language === "en" ? `Port ${app.port || 5000}` : `端口 ${app.port || 5000}`;
    }
    if (DOM.uiStatsText) {
        const text = I18N[State.language] || I18N.zh;
        DOM.uiStatsText.textContent = text.stats(stats.knowledge_chunks ?? 0, stats.session_count ?? 0, stats.knowledge_vectors ?? 0);
    }
    if (!State.apiConfig.model && app.default_model) {
        State.apiConfig.model = app.default_model;
    }
    updateModelDisplay();
}

async function refreshUiState() {
    try {
        const uiState = await Utils.request("/api/ui/state");
        renderUiState(uiState);
    } catch (error) {
        console.warn("UI state load failed", error);
    }
}

function updateRoundText() {
    DOM.roundText.textContent = State.language === "en" ? `Round ${State.round}` : `\u7b2c ${State.round} \u8f6e`;
}

function updateSessionMeta() {
    const text = I18N[State.language] || I18N.zh;
    if (DOM.sessionMetaId) {
        DOM.sessionMetaId.textContent = getDisplayTitle(State.sessionName, State.sessionLabel, State.sessionId) || text.notCreated;
    }
    if (DOM.sessionMetaDate) {
        DOM.sessionMetaDate.textContent = new Date().toLocaleDateString(State.language === "en" ? "en-US" : "zh-CN", {
            year: "numeric",
            month: "2-digit",
            day: "2-digit"
        });
    }
}

function getCurrentThemeKey() {
    return State.theme === "research" ? "research" : "chat";
}

function makeEmptyThemeProfiles() {
    return {
        chat: { avatars: { user: null, assistant: null } },
        research: { avatars: { user: null, assistant: null } }
    };
}

function getDisplayTitle(sessionName, sessionLabel, sessionId = "") {
    const name = normalizeSessionName(sessionName) || sessionId || "";
    const label = normalizeSessionName(sessionLabel);
    if (!label || label === name) {
        return name;
    }
    return `${name}（${label}）`;
}

function updateSendButtonState() {
    DOM.btnSend.disabled = State.isGenerating || !DOM.userInput.value.trim();
    DOM.btnStop.style.display = State.isGenerating ? "flex" : "none";
}

function getAvatarInfo(role) {
    return State.themeProfiles?.[getCurrentThemeKey()]?.avatars?.[role] || null;
}

function getAvatarUrlByRole(role) {
    return getAvatarInfo(role)?.url || null;
}

function getDefaultAvatarLabel(role) {
    return role === "assistant" ? "AI" : "\u6211";
}

function buildAvatarHtml(role) {
    const avatarUrl = getAvatarUrlByRole(role);
    if (avatarUrl) {
        return `<img src="${Utils.escapeHtml(avatarUrl)}" alt="${role === "assistant" ? "AI" : "\u7528\u6237"}">`;
    }
    return getDefaultAvatarLabel(role);
}

function updateSingleAvatarPreview(role) {
    const preview = role === "assistant" ? DOM.assistantAvatarPreview : DOM.userAvatarPreview;
    if (!preview) {
        return;
    }
    preview.innerHTML = buildAvatarHtml(role);
    preview.classList.toggle("has-image", Boolean(getAvatarUrlByRole(role)));
}

function updateAvatarPreview() {
    updateSingleAvatarPreview("user");
    updateSingleAvatarPreview("assistant");
}

function loadSessionAvatars(uiSettings = {}) {
    const themeProfiles = makeEmptyThemeProfiles();
    const rawProfiles = uiSettings?.theme_profiles || {};
    for (const theme of THEME_KEYS) {
        const avatars = rawProfiles?.[theme]?.avatars || {};
        themeProfiles[theme] = {
            avatars: {
                user: avatars.user || null,
                assistant: avatars.assistant || null
            }
        };
    }
    // Legacy ui_settings.avatars is kept as chat-theme data only. Research
    // stays independent and falls back to defaults until explicitly configured.
    if (!rawProfiles.chat && uiSettings?.avatars) {
        themeProfiles.chat.avatars.user = uiSettings.avatars.user || null;
        themeProfiles.chat.avatars.assistant = uiSettings.avatars.assistant || null;
    }
    State.themeProfiles = themeProfiles;
    updateAvatarPreview();
}

function setThemeAvatar(theme, role, avatarMeta) {
    const themeKey = theme === "research" ? "research" : "chat";
    State.themeProfiles = State.themeProfiles || makeEmptyThemeProfiles();
    State.themeProfiles[themeKey] = State.themeProfiles[themeKey] || { avatars: {} };
    State.themeProfiles[themeKey].avatars = State.themeProfiles[themeKey].avatars || {};
    State.themeProfiles[themeKey].avatars[role] = avatarMeta || null;
}

function applyAvatarToMessages() {
    DOM.chatContainer?.querySelectorAll(".message").forEach((node) => {
        const role = node.classList.contains("assistant") ? "assistant" : "user";
        const avatar = node.querySelector(".message-avatar");
        if (!avatar) {
            return;
        }
        avatar.innerHTML = buildAvatarHtml(role);
        avatar.classList.toggle("has-image", Boolean(getAvatarUrlByRole(role)));
    });
}

function validateAvatarFile(file) {
    if (!file) {
        throw new Error("\u8bf7\u9009\u62e9\u5934\u50cf\u56fe\u7247");
    }
    const allowedTypes = ["image/png", "image/jpeg", "image/webp"];
    const allowedExt = /\.(png|jpg|jpeg|webp)$/i;
    if (!allowedTypes.includes(file.type) && !allowedExt.test(file.name || "")) {
        throw new Error("\u4ec5\u652f\u6301 png\u3001jpg\u3001jpeg\u3001webp \u56fe\u7247");
    }
    if (file.size > 2 * 1024 * 1024) {
        throw new Error("\u5934\u50cf\u56fe\u7247\u4e0d\u80fd\u8d85\u8fc7 2MB");
    }
}

async function ensureAvatarSessionExists() {
    if (!State.sessionId) {
        State.sessionId = Utils.generateSessionId();
        saveCurrentSessionId();
    }
    await persistSessionConfig();
}

async function uploadSessionAvatar(role, file, theme = getCurrentThemeKey()) {
    validateAvatarFile(file);
    await ensureAvatarSessionExists();

    const formData = new FormData();
    formData.append("role", role);
    formData.append("theme", theme);
    formData.append("avatar", file);
    const result = await Utils.request(`/api/session/${encodeURIComponent(State.sessionId)}/avatar`, {
        method: "POST",
        body: formData
    });

    setThemeAvatar(theme, role, result.avatar || {
        url: result.avatar_url,
        role,
        theme
    });
    updateAvatarPreview();
    applyAvatarToMessages();
    Utils.showToast("\u5934\u50cf\u5df2\u66f4\u65b0");
}

async function deleteSessionAvatar(role, theme = getCurrentThemeKey()) {
    if (!State.sessionId) {
        setThemeAvatar(theme, role, null);
        updateAvatarPreview();
        applyAvatarToMessages();
        return;
    }
    await Utils.request(`/api/session/${encodeURIComponent(State.sessionId)}/avatar?role=${encodeURIComponent(role)}&theme=${encodeURIComponent(theme)}`, {
        method: "DELETE"
    });
    setThemeAvatar(theme, role, null);
    updateAvatarPreview();
    applyAvatarToMessages();
    Utils.showToast("\u5df2\u6062\u590d\u9ed8\u8ba4\u5934\u50cf");
}

function setupSettingsPanels() {
    if (!DOM.paramsModalBody) {
        return;
    }
    document.querySelectorAll("#settings-modal .param-section").forEach((section) => {
        DOM.paramsModalBody.appendChild(section);
    });
}

async function saveSettingsAndClose(modal) {
    await persistSessionConfig();
    Utils.closeModal(modal);
    Utils.showToast("\u8bbe\u7f6e\u5df2\u4fdd\u5b58");
    await loadSessions();
}

function setCommonDiagnoseStatus(text, level = "") {
    if (!DOM.commonDiagnoseStatus) {
        return;
    }
    DOM.commonDiagnoseStatus.textContent = text;
    DOM.commonDiagnoseStatus.className = level;
}

function setToolCopy(button, copy) {
    const copyNode = button?.querySelector(".tool-copy");
    if (!copyNode || !copy) {
        return;
    }
    copyNode.innerHTML = `<strong>${Utils.escapeHtml(copy[0])}</strong><small>${Utils.escapeHtml(copy[1])}</small>`;
}

function setSettingsCopy(button, copy) {
    const copyNode = button?.querySelector("span");
    if (!copyNode || !copy) {
        return;
    }
    copyNode.innerHTML = `<strong>${Utils.escapeHtml(copy[0])}</strong><small>${Utils.escapeHtml(copy[1])}</small>`;
}

function renderLanguage() {
    const text = I18N[State.language] || I18N.zh;
    const collapsed = document.body.classList.contains("sidebar-collapsed");
    setToolCopy(DOM.btnGlobalSearch, text.globalSearch);
    setToolCopy(DOM.btnSessionSearch, text.sessionSearch);
    setToolCopy(DOM.btnCollapseSidebar, collapsed ? text.collapseClosed : text.collapseOpen);
    setSettingsCopy(DOM.openDiagnose, text.commonSettings);
    setSettingsCopy(DOM.openSettings, text.paramSettings);

    DOM.labelSessionId && (DOM.labelSessionId.textContent = text.currentSession);
    DOM.labelSessionDate && (DOM.labelSessionDate.textContent = text.date);
    DOM.labelApiStatus && (DOM.labelApiStatus.textContent = text.apiStatus);
    DOM.labelLlm && (DOM.labelLlm.textContent = text.llm);
    DOM.labelArpmStatus && (DOM.labelArpmStatus.textContent = text.arpmStatus);
    DOM.btnExportCurrent && (DOM.btnExportCurrent.textContent = text.export);
    DOM.welcome?.querySelector("h1") && (DOM.welcome.querySelector("h1").textContent = text.welcomeTitle);
    DOM.welcome?.querySelector("p") && (DOM.welcome.querySelector("p").textContent = text.welcomeText);
    DOM.welcomeOpenSettings && (DOM.welcomeOpenSettings.textContent = text.configure);
    DOM.welcomeOpenParams && (DOM.welcomeOpenParams.textContent = text.params);
    DOM.userInput && (DOM.userInput.placeholder = text.inputPlaceholder);
    DOM.btnClearChat && (DOM.btnClearChat.textContent = text.clearContext);
    DOM.btnClearChatIndex && (DOM.btnClearChatIndex.textContent = text.clearContextIndex);
    DOM.labelRagPanel && (DOM.labelRagPanel.textContent = text.ragPanel);
    DOM.labelCotPanel && (DOM.labelCotPanel.textContent = text.cotPanel);
    DOM.titleSettings && (DOM.titleSettings.textContent = text.settingsTitle);
    DOM.titleParams && (DOM.titleParams.textContent = text.paramsTitle);
    DOM.btnThemeChat && (DOM.btnThemeChat.textContent = text.themeChat);
    DOM.btnThemeResearch && (DOM.btnThemeResearch.textContent = text.themeResearch);
    DOM.sectionApiTitle && (DOM.sectionApiTitle.textContent = text.apiConfigTitle);
    DOM.labelApiKey && (DOM.labelApiKey.textContent = text.apiKey);
    DOM.labelBaseUrl && (DOM.labelBaseUrl.textContent = text.baseUrl);
    DOM.labelModelName && (DOM.labelModelName.textContent = text.modelName);
    DOM.sectionUserTitle && (DOM.sectionUserTitle.textContent = text.userTitle);
    DOM.labelUserName && (DOM.labelUserName.textContent = text.userName);
    DOM.labelUserPersona && (DOM.labelUserPersona.textContent = text.userPersona);
    DOM.labelUserAvatar && (DOM.labelUserAvatar.textContent = State.language === "en" ? "User avatar" : "\u7528\u6237\u5934\u50cf");
    DOM.uploadUserAvatar && (DOM.uploadUserAvatar.textContent = State.language === "en" ? "Upload user avatar" : "\u4e0a\u4f20\u7528\u6237\u5934\u50cf");
    DOM.resetUserAvatar && (DOM.resetUserAvatar.textContent = State.language === "en" ? "Reset default" : "\u6062\u590d\u9ed8\u8ba4");
    DOM.sectionAiTitle && (DOM.sectionAiTitle.textContent = text.aiTitle);
    DOM.labelCharacterName && (DOM.labelCharacterName.textContent = text.characterName);
    DOM.labelSystemPrompt && (DOM.labelSystemPrompt.textContent = text.systemPrompt);
    DOM.labelAssistantAvatar && (DOM.labelAssistantAvatar.textContent = State.language === "en" ? "AI role avatar" : "AI \u89d2\u8272\u5934\u50cf");
    DOM.uploadAssistantAvatar && (DOM.uploadAssistantAvatar.textContent = State.language === "en" ? "Upload AI avatar" : "\u4e0a\u4f20 AI \u5934\u50cf");
    DOM.resetAssistantAvatar && (DOM.resetAssistantAvatar.textContent = State.language === "en" ? "Reset default" : "\u6062\u590d\u9ed8\u8ba4");
    DOM.sectionBasicTitle && (DOM.sectionBasicTitle.textContent = text.basicTitle);
    DOM.basicDesc && (DOM.basicDesc.textContent = text.basicDesc);
    DOM.sectionProtocolTitle && (DOM.sectionProtocolTitle.textContent = text.protocolTitle);
    DOM.labelProtocolMode && (DOM.labelProtocolMode.textContent = text.protocolMode);
    DOM.labelReasoningMode && (DOM.labelReasoningMode.textContent = text.reasoningMode);
    DOM.sectionKbTitle && (DOM.sectionKbTitle.textContent = text.kbTitle);
    DOM.labelChildSize && (DOM.labelChildSize.textContent = text.childSize);
    DOM.labelParentSize && (DOM.labelParentSize.textContent = text.parentSize);
    DOM.labelOverlap && (DOM.labelOverlap.textContent = text.overlap);
    DOM.sectionAblationTitle && (DOM.sectionAblationTitle.textContent = text.ablationTitle);
    DOM.sectionTuningTitle && (DOM.sectionTuningTitle.textContent = text.tuningTitle);
    DOM.labelPresets && (DOM.labelPresets.textContent = text.presets);
    DOM.sectionDangerTitle && (DOM.sectionDangerTitle.textContent = text.dangerTitle);
    DOM.testApi && (DOM.testApi.textContent = text.testConnection);
    DOM.openDiagnoseBasic && (DOM.openDiagnoseBasic.textContent = text.openDiagnostics);
    DOM.btnCommonCheckApi && (DOM.btnCommonCheckApi.textContent = text.testConnection);
    DOM.btnCommonSystemDiag && (DOM.btnCommonSystemDiag.textContent = text.systemHealth);
    DOM.uploadFile && (DOM.uploadFile.textContent = text.chooseFile);
    DOM.manageKb && (DOM.manageKb.textContent = text.manage);
    DOM.saveSettings && (DOM.saveSettings.textContent = text.save);
    DOM.saveParams && (DOM.saveParams.textContent = text.saveParams);
    DOM.kbRefresh && (DOM.kbRefresh.textContent = text.refresh);
    DOM.btnCheckApi && (DOM.btnCheckApi.textContent = text.apiTest);
    DOM.btnArpmReport && (DOM.btnArpmReport.textContent = text.arpmReport);
    DOM.btnSystemDiag && (DOM.btnSystemDiag.textContent = text.systemHealth);
    DOM.btnLoadKbChunks && (DOM.btnLoadKbChunks.textContent = text.loadKbChunks);
    DOM.btnLoadChatChunks && (DOM.btnLoadChatChunks.textContent = text.loadChatChunks);
    if (DOM.statusText && (DOM.statusText.textContent === I18N.zh.ready || DOM.statusText.textContent === I18N.en.ready)) {
        DOM.statusText.textContent = text.ready;
    }
    DOM.btnLangZh?.classList.toggle("active", State.language === "zh");
    DOM.btnLangEn?.classList.toggle("active", State.language === "en");
    DOM.btnLangZh && (DOM.btnLangZh.textContent = State.language === "en" ? "中文" : "中文模式");
    DOM.btnLangEn && (DOM.btnLangEn.textContent = "English");
}

function setButtonBusy(button, isBusy, text = "") {
    if (!button) {
        return;
    }
    if (isBusy) {
        button.dataset.originalHtml = button.innerHTML;
        button.disabled = true;
        button.classList.add("is-busy");
        if (text) {
            button.textContent = text;
        }
    } else {
        button.disabled = false;
        button.classList.remove("is-busy");
        if (button.dataset.originalHtml) {
            button.innerHTML = button.dataset.originalHtml;
            delete button.dataset.originalHtml;
            renderLanguage();
        }
    }
}

function setLanguage(language) {
    State.language = language;
    saveUiConfig();
    renderLanguage();
    renderUiState(State.uiState);
    updateSessionMeta();
    updateModelDisplay();
    updateRoundText();
    DOM.btnLangZh?.classList.toggle("active", language === "zh");
    DOM.btnLangEn?.classList.toggle("active", language === "en");
    Utils.showToast((I18N[language] || I18N.zh).langToast);
}

function saveUiConfig() {
    window.localStorage.setItem(STORAGE_KEYS.ui, JSON.stringify({
        language: State.language,
        theme: State.theme
    }));
}

function getSavedCurrentSessionId() {
    try {
        return window.localStorage.getItem(STORAGE_KEYS.currentSession) || "";
    } catch (error) {
        console.warn("Read current session failed", error);
        return "";
    }
}

function saveCurrentSessionId() {
    if (!State.sessionId) {
        return;
    }
    try {
        window.localStorage.setItem(STORAGE_KEYS.currentSession, State.sessionId);
    } catch (error) {
        console.warn("Save current session failed", error);
    }
}

function setTheme(theme) {
    State.theme = theme === "research" ? "research" : "chat";
    renderTheme();
    renderLanguage();
    updateAvatarPreview();
    applyAvatarToMessages();
    saveUiConfig();
}

function renderTheme() {
    document.body.classList.toggle("theme-chat", State.theme === "chat");
    document.body.classList.toggle("theme-research", State.theme === "research");
    DOM.btnThemeChat?.classList.toggle("active", State.theme === "chat");
    DOM.btnThemeResearch?.classList.toggle("active", State.theme === "research");
}

function updateRagToggleState() {
    const disabled = !DOM.cfgRagEnabled.checked;
    DOM.ragSubitems.style.opacity = disabled ? "0.5" : "1";
    DOM.cfgKbEnabled.disabled = disabled;
    DOM.cfgChatEnabled.disabled = disabled;
}

function syncStateToForm() {
    DOM.cfgApiKey.value = State.apiConfig.api_key || "";
    DOM.cfgBaseUrl.value = State.apiConfig.base_url || "";
    DOM.cfgModel.value = State.apiConfig.model || "";
    DOM.cfgUserName.value = State.sessionConfig.user_name || "\u7528\u6237";
    DOM.cfgUserPersona.value = State.sessionConfig.user_persona || "";
    DOM.cfgCharacterName.value = State.sessionConfig.character_name || "AI\u52a9\u624b";
    DOM.cfgSystemPrompt.value = State.sessionConfig.system_prompt || "";
    DOM.cfgProtocolMode.value = State.protocolConfig.protocol_mode || "auto";
    DOM.cfgReasoningModelMode.value = State.protocolConfig.reasoning_model_mode || "auto";
    DOM.cfgAutoRepairResponse.checked = State.protocolConfig.auto_repair_response;
    DOM.cfgProtocolDiagnostic.checked = State.protocolConfig.diagnostic_mode;
    DOM.cfgChunkChildSize.value = State.chunkConfig.child_size;
    DOM.cfgChunkParentSize.value = State.chunkConfig.parent_size;
    DOM.cfgChunkOverlap.value = State.chunkConfig.overlap_sentences;
    DOM.cfgRagEnabled.checked = State.ablation.rag_enabled;
    DOM.cfgKbEnabled.checked = State.ablation.kb_enabled;
    DOM.cfgChatEnabled.checked = State.ablation.chat_enabled;
    DOM.cfgTemporalEnabled.checked = State.ablation.temporal_enabled;
    DOM.cfgBm25Enabled.checked = State.ablation.bm25_enabled;
    DOM.cfgRegenEnabled.checked = State.ablation.regeneration_enabled;
    DOM.cfgRegenMax.value = State.ablation.regen_max_attempts;
    DOM.cfgRegenRegex.checked = State.ablation.regen_regex;
    DOM.cfgRegenSemantic.checked = State.ablation.regen_semantic;
    DOM.cfgSimilarityThreshold.value = Math.round(State.ablation.similarity_threshold * 100);
    DOM.cfgKnowledgeK.value = State.tuning.knowledge_k;
    DOM.cfgChatHistoryK.value = State.tuning.chat_history_k;
    DOM.cfgDecayRound.value = State.tuning.decay_rate_round;
    DOM.cfgDecayHours.value = State.tuning.decay_rate_hours;
    DOM.cfgRrfK.value = State.tuning.rrf_k;
    DOM.cfgTemperature.value = State.tuning.temperature;
    DOM.cfgMaxTokens.value = State.tuning.max_tokens;
    DOM.cfgRoleQueryPrefix.checked = State.tuning.role_query_prefix_enabled;
    DOM.cfgKbUserBoost.value = State.tuning.kb_user_name_boost;
    DOM.cfgKbCharacterBoost.value = State.tuning.kb_character_name_boost;
    DOM.cfgKbSourceBoost.value = State.tuning.kb_source_name_boost;
    DOM.cfgChatSessionBoost.value = State.tuning.chat_same_session_boost;
    DOM.cfgChatExactBoost.value = State.tuning.chat_exact_name_boost;
    DOM.cfgChatTextBoost.value = State.tuning.chat_text_name_boost;
    updateThresholdLabel();
    updateModelDisplay();
    updateRagToggleState();
    updateAvatarPreview();
}

function syncFormToState() {
    State.apiConfig = {
        api_key: DOM.cfgApiKey.value.trim(),
        base_url: DOM.cfgBaseUrl.value.trim(),
        model: DOM.cfgModel.value.trim() || "deepseek-chat"
    };
    State.sessionConfig = {
        user_name: DOM.cfgUserName.value.trim() || "\u7528\u6237",
        user_persona: DOM.cfgUserPersona.value.trim(),
        character_name: DOM.cfgCharacterName.value.trim() || "AI\u52a9\u624b",
        system_prompt: DOM.cfgSystemPrompt.value
    };
    State.protocolConfig = {
        protocol_mode: DOM.cfgProtocolMode.value || "auto",
        reasoning_model_mode: DOM.cfgReasoningModelMode.value || "auto",
        auto_repair_response: DOM.cfgAutoRepairResponse.checked,
        diagnostic_mode: DOM.cfgProtocolDiagnostic.checked
    };
    State.chunkConfig = {
        child_size: clampNumber(DOM.cfgChunkChildSize.value, 50, 1000, 200),
        parent_size: clampNumber(DOM.cfgChunkParentSize.value, 100, 3000, 600),
        overlap_sentences: clampNumber(DOM.cfgChunkOverlap.value, 0, 10, 1)
    };
    State.ablation = {
        rag_enabled: DOM.cfgRagEnabled.checked,
        kb_enabled: DOM.cfgKbEnabled.checked,
        chat_enabled: DOM.cfgChatEnabled.checked,
        temporal_enabled: DOM.cfgTemporalEnabled.checked,
        bm25_enabled: DOM.cfgBm25Enabled.checked,
        regeneration_enabled: DOM.cfgRegenEnabled.checked,
        regen_max_attempts: Math.max(0, Number(DOM.cfgRegenMax.value || 1)),
        regen_regex: DOM.cfgRegenRegex.checked,
        regen_semantic: DOM.cfgRegenSemantic.checked,
        similarity_threshold: Number(DOM.cfgSimilarityThreshold.value || 50) / 100
    };
    State.tuning = {
        ...State.tuning,
        knowledge_k: clampNumber(DOM.cfgKnowledgeK.value, 1, 20, 5),
        chat_history_k: clampNumber(DOM.cfgChatHistoryK.value, 1, 30, 10),
        similarity_threshold: clampNumber(DOM.cfgSimilarityThreshold.value, 0, 100, 50) / 100,
        decay_rate_round: clampNumber(DOM.cfgDecayRound.value, 1, 500, 20),
        decay_rate_hours: clampNumber(DOM.cfgDecayHours.value, 1, 8760, 168),
        rrf_k: clampNumber(DOM.cfgRrfK.value, 1, 200, 60),
        temperature: clampNumber(DOM.cfgTemperature.value, 0, 2, 0.7),
        max_tokens: clampNumber(DOM.cfgMaxTokens.value, 64, 8192, 2000),
        role_query_prefix_enabled: DOM.cfgRoleQueryPrefix.checked,
        kb_user_name_boost: clampNumber(DOM.cfgKbUserBoost.value, 0, 1, 0.08),
        kb_character_name_boost: clampNumber(DOM.cfgKbCharacterBoost.value, 0, 1, 0.08),
        kb_source_name_boost: clampNumber(DOM.cfgKbSourceBoost.value, 0, 1, 0.05),
        chat_same_session_boost: clampNumber(DOM.cfgChatSessionBoost.value, 0, 1, 0.15),
        chat_exact_name_boost: clampNumber(DOM.cfgChatExactBoost.value, 0, 1, 0.10),
        chat_text_name_boost: clampNumber(DOM.cfgChatTextBoost.value, 0, 1, 0.04)
    };
    State.ablation.similarity_threshold = State.tuning.similarity_threshold;
}

function applyTuningPreset(name) {
    const preset = TUNING_PRESETS[name];
    if (!preset) {
        return;
    }
    State.tuning = { ...State.tuning, ...preset };
    State.ablation.similarity_threshold = State.tuning.similarity_threshold;
    syncStateToForm();
}

function createMessageElement(message) {
    const element = document.createElement("div");
    const roleName = message.role === "assistant"
        ? (State.sessionConfig.character_name || "AI\u52a9\u624b")
        : (State.sessionConfig.user_name || "\u7528\u6237");
    const avatarRole = message.role === "assistant" ? "assistant" : "user";
    const avatar = buildAvatarHtml(avatarRole);
    const avatarClass = getAvatarUrlByRole(avatarRole) ? " has-image" : "";
    const feedback = message.role === "assistant" && !message.pending
        ? `
            <div class="message-feedback">
                <button class="feedback-btn regenerate-msg" data-round="${message.round}">\u91cd\u65b0\u751f\u6210</button>
                <button class="feedback-btn delete-msg" data-round="${message.round}">\u5220\u9664\u8f6e\u6b21</button>
            </div>
        `
        : "";

    element.className = `message ${message.role}${message.pending ? " regenerating" : ""}`;
    element.dataset.round = message.round ?? "";
    element.innerHTML = `
        <div class="message-content-wrapper">
            <div class="message-avatar${avatarClass}">${avatar}</div>
            <div class="message-body">
                <div class="message-header">${Utils.escapeHtml(roleName)}</div>
                <div class="message-text">${Utils.formatText(message.content || "")}</div>
                ${feedback}
            </div>
        </div>
    `;
    return element;
}

function renderMessages() {
    DOM.chatContainer.querySelectorAll(".message").forEach((node) => node.remove());
    if (!State.messages.length) {
        DOM.welcome.style.display = "block";
        updateRoundText();
        updateSessionMeta();
        return;
    }
    DOM.welcome.style.display = "none";
    for (const message of State.messages) {
        DOM.chatContainer.appendChild(createMessageElement(message));
    }
    DOM.chatContainer.scrollTop = DOM.chatContainer.scrollHeight;
    updateRoundText();
    updateSessionMeta();
}

function renderSessions(items) {
    DOM.sessionList.innerHTML = "";
    if (!items.length) {
        DOM.sessionList.innerHTML = '<div class="empty" style="padding:16px;color:var(--text-tertiary);">\u6682\u65e0\u4f1a\u8bdd</div>';
        return;
    }

    for (const item of items) {
        const button = document.createElement("button");
        const sessionName = item.session_name || item.name || item.id;
        const sessionLabel = item.session_label || "";
        const displayTitle = item.display_title || getDisplayTitle(sessionName, sessionLabel, item.id);
        button.className = `session-item${item.id === State.sessionId ? " active" : ""}`;
        button.dataset.sessionId = item.id;
        button.innerHTML = `
            <span class="session-info">
                <span class="session-name">${Utils.escapeHtml(displayTitle || item.id)}</span>
                ${sessionLabel && sessionLabel !== sessionName ? `<span class="session-label">${Utils.escapeHtml(sessionLabel)}</span>` : ""}
                <span class="session-role">${Utils.escapeHtml(item.character_name || "AI\u52a9\u624b")}</span>
            </span>
            <span class="session-actions">
                <span class="session-rename" role="button" tabindex="0" title="\u91cd\u547d\u540d\u4f1a\u8bdd" aria-label="\u91cd\u547d\u540d\u4f1a\u8bdd">\u270e</span>
                <span class="session-label-edit" role="button" tabindex="0" title="\u7f16\u8f91\u4f1a\u8bdd\u5907\u6ce8" aria-label="\u7f16\u8f91\u4f1a\u8bdd\u5907\u6ce8">#</span>
                <span class="session-delete" role="button" tabindex="0" title="\u5220\u9664\u4f1a\u8bdd" aria-label="\u5220\u9664\u4f1a\u8bdd">\u00d7</span>
            </span>
        `;
        button.addEventListener("click", () => switchSession(item.id));
        const renameButton = button.querySelector(".session-rename");
        const labelButton = button.querySelector(".session-label-edit");
        const deleteButton = button.querySelector(".session-delete");
        renameButton?.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            promptRenameSession(item.id, sessionName || item.id).catch((error) => {
                console.error(error);
                Utils.showToast(error.message, "error");
            });
        });
        renameButton?.addEventListener("keydown", (event) => {
            if (event.key !== "Enter" && event.key !== " ") {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            promptRenameSession(item.id, sessionName || item.id).catch((error) => {
                console.error(error);
                Utils.showToast(error.message, "error");
            });
        });
        labelButton?.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            promptSessionLabel(item.id, sessionLabel).catch((error) => {
                console.error(error);
                Utils.showToast(error.message, "error");
            });
        });
        labelButton?.addEventListener("keydown", (event) => {
            if (event.key !== "Enter" && event.key !== " ") {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            promptSessionLabel(item.id, sessionLabel).catch((error) => {
                console.error(error);
                Utils.showToast(error.message, "error");
            });
        });
        deleteButton?.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            deleteSession(item.id, displayTitle || sessionName || item.id).catch((error) => {
                console.error(error);
                Utils.showToast(error.message, "error");
            });
        });
        deleteButton?.addEventListener("keydown", (event) => {
            if (event.key !== "Enter" && event.key !== " ") {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            deleteSession(item.id, item.name || item.id).catch((error) => {
                console.error(error);
                Utils.showToast(error.message, "error");
            });
        });
        DOM.sessionList.appendChild(button);
    }
}

function renderRagContext(context) {
    const knowledgeBlocks = context?.knowledge_blocks || [];
    const chatBlocks = context?.chat_blocks || [];
    const total = (context?.knowledge_count || 0) + (context?.chat_count || 0);
    DOM.ragCount.textContent = String(total);

    if (!total) {
        DOM.ragContent.innerHTML = '<div class="empty">\u5f53\u524d\u8f6e\u6ca1\u6709\u53ec\u56de\u5185\u5bb9</div>';
        return;
    }

    const items = [];
    for (const block of knowledgeBlocks) {
        items.push(`
            <div class="rag-item">
                <div class="rag-header">
                    <span class="rag-source">\u77e5\u8bc6\u5e93 \u00b7 ${Utils.escapeHtml(block.source || "unknown")}</span>
                    <span class="rag-score">\u8bed\u4e49 ${block.semantic_score ?? "-"}</span>
                </div>
                <div class="rag-text">${Utils.formatText(block.text || "")}</div>
                <div class="rag-meta">\u8f6e\u6b21 ${block.round_num ?? "-"} \u00b7 \u65f6\u95f4 ${Utils.escapeHtml(block.physical_time || "-")} \u00b7 \u6743\u91cd ${block.temporal_weight ?? "-"}</div>
            </div>
        `);
    }
    for (const block of chatBlocks) {
        items.push(`
            <div class="rag-item">
                <div class="rag-header">
                    <span class="rag-source">\u5bf9\u8bdd\u5386\u53f2 \u00b7 ${Utils.escapeHtml(block.user_name || "\u7528\u6237")} / ${Utils.escapeHtml(block.character_name || "AI\u52a9\u624b")}</span>
                    <span class="rag-score">\u8bed\u4e49 ${block.semantic_score ?? "-"}</span>
                </div>
                <div class="rag-text">${Utils.formatText(block.text || "")}</div>
                <div class="rag-meta">\u8f6e\u6b21 ${block.round_num ?? "-"} \u00b7 \u65f6\u95f4 ${Utils.escapeHtml(block.physical_time || "-")} \u00b7 \u6743\u91cd ${block.temporal_weight ?? "-"}</div>
            </div>
        `);
    }
    DOM.ragContent.innerHTML = items.join("");
}

function exportCurrentSession() {
    if (!State.messages.length) {
        Utils.showToast((I18N[State.language] || I18N.zh).emptyExport, "error");
        return;
    }

    const lines = [
        `ARPM-v4 \u5f53\u524d\u4f1a\u8bdd\u5bfc\u51fa`,
        `\u4f1a\u8bdd\u7f16\u53f7: ${State.sessionName || State.sessionId || "-"}`,
        `\u5bfc\u51fa\u65f6\u95f4: ${new Date().toISOString()}`,
        ""
    ];

    for (const message of State.messages) {
        const roleName = message.role === "assistant"
            ? (State.sessionConfig.character_name || "AI\u52a9\u624b")
            : (State.sessionConfig.user_name || "\u7528\u6237");
        lines.push(`[${message.round ?? "-"}] ${roleName}:`);
        lines.push(message.content || "");
        lines.push("");
    }

    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${State.sessionName || State.sessionId || "arpm-session"}.txt`;
    document.body.appendChild(link);
    link.click();
    URL.revokeObjectURL(link.href);
    link.remove();
}

function isProtocolRepairPlaceholder(text) {
    const normalized = String(text || "")
        .replace(/<\/?analysis>/gi, "")
        .replace(/[\s\u3000]+/g, "")
        .replace(/[。．.]+$/g, "");
    return normalized === "\u534f\u8bae\u4fee\u590d\uff1a\u539f\u8f93\u51fa\u7f3a\u5c11\u663e\u5f0f\u5206\u6790";
}

function renderAnalysis(analysis, protocolInfo = null) {
    const rawDisplayAnalysis = protocolInfo?.original_analysis || analysis;
    const displayAnalysis = isProtocolRepairPlaceholder(rawDisplayAnalysis) ? "" : rawDisplayAnalysis;
    const showProtocolBlock = protocolInfo && !isProtocolRepairPlaceholder(rawDisplayAnalysis);
    const protocolBlock = showProtocolBlock ? `
        <div class="rag-item" style="margin-bottom:10px;">
            <div class="rag-header">
                <span class="rag-source">\u534f\u8bae\u8bca\u65ad</span>
                <span class="rag-score">${protocolInfo.resolved_model_mode || "-"}</span>
            </div>
            <div class="rag-meta">
                analysis_tag=${protocolInfo.has_analysis_tag} \u00b7 response_tag=${protocolInfo.has_response_tag}
                \u00b7 visible_reply=${protocolInfo.visible_reply} \u00b7 thinking_only=${protocolInfo.looks_thinking_only}
                \u00b7 repaired=${protocolInfo.was_repaired ?? false} \u00b7 needs_repair=${protocolInfo.needs_repair}
            </div>
        </div>
    ` : "";
    if (!displayAnalysis && !protocolBlock) {
        DOM.cotContent.innerHTML = '<div class="empty">\u5f53\u524d\u8f6e\u6ca1\u6709\u989d\u5916\u5206\u6790</div>';
        return;
    }
    DOM.cotContent.innerHTML = `${protocolBlock}<div class="rag-item"><div class="rag-text">${Utils.formatText(displayAnalysis || "\u65e0\u663e\u5f0f\u5206\u6790\u5185\u5bb9")}</div></div>`;
}

async function refreshKnowledgeStats() {
    try {
        const stats = await Utils.request("/api/knowledge/stats");
        DOM.kbCount.textContent = String(stats.knowledge?.total_chunks || stats.knowledge?.total_parents || 0);
    } catch (error) {
        console.error("\u8bfb\u53d6\u77e5\u8bc6\u5e93\u7edf\u8ba1\u5931\u8d25", error);
    }
}

async function loadSessions() {
    const sessions = await Utils.request("/api/sessions");
    renderSessions(sessions);
    return sessions;
}

function normalizeSessionName(name) {
    return String(name || "").trim();
}

function validateSessionName(name) {
    const normalized = normalizeSessionName(name);
    if (!normalized) {
        throw new Error("\u4f1a\u8bdd\u540d\u79f0\u4e0d\u80fd\u4e3a\u7a7a");
    }
    if (normalized.length > MAX_SESSION_NAME_LENGTH) {
        throw new Error(`\u4f1a\u8bdd\u540d\u79f0\u4e0d\u80fd\u8d85\u8fc7 ${MAX_SESSION_NAME_LENGTH} \u4e2a\u5b57\u7b26`);
    }
    return normalized;
}

function validateSessionLabel(label) {
    const normalized = normalizeSessionName(label);
    if (normalized.length > MAX_SESSION_LABEL_LENGTH) {
        throw new Error(`\u4f1a\u8bdd\u5907\u6ce8\u4e0d\u80fd\u8d85\u8fc7 ${MAX_SESSION_LABEL_LENGTH} \u4e2a\u5b57\u7b26`);
    }
    return normalized;
}

async function renameSession(sessionId, newName) {
    const sessionName = validateSessionName(newName);
    return Utils.request(`/api/session/${encodeURIComponent(sessionId)}/name`, {
        method: "PATCH",
        body: JSON.stringify({ session_name: sessionName })
    });
}

async function updateSessionLabel(sessionId, label) {
    const sessionLabel = validateSessionLabel(label);
    return Utils.request(`/api/session/${encodeURIComponent(sessionId)}/label`, {
        method: "PATCH",
        body: JSON.stringify({ session_label: sessionLabel })
    });
}

function askSessionName({ title, initialValue = "", confirmText = "\u4fdd\u5b58", allowEmpty = false, maxLength = MAX_SESSION_NAME_LENGTH, inputLabel = "\u4f1a\u8bdd\u663e\u793a\u540d\u79f0", hint = "" }) {
    return new Promise((resolve) => {
        const modal = document.createElement("div");
        modal.className = "modal session-name-modal show";
        modal.innerHTML = `
            <div class="modal-content session-name-dialog" role="dialog" aria-modal="true" aria-labelledby="session-name-title">
                <div class="modal-header">
                    <h2 id="session-name-title">${Utils.escapeHtml(title)}</h2>
                    <button type="button" class="btn-close session-name-close" aria-label="\u5173\u95ed">&times;</button>
                </div>
                <div class="modal-body session-name-body">
                    <label for="session-name-input">${Utils.escapeHtml(inputLabel)}</label>
                    <input id="session-name-input" class="session-name-input" type="text" maxlength="${maxLength}" value="${Utils.escapeHtml(initialValue || "")}" placeholder="\u4f8b\u5982\uff1a\u4ea7\u54c1\u65b9\u6848\u8ba8\u8bba">
                    <div class="session-name-hint">${Utils.escapeHtml(hint || `\u6700\u591a ${maxLength} \u4e2a\u5b57\u7b26\uff0c\u4ec5\u7528\u4e8e\u5de6\u4fa7\u4f1a\u8bdd\u5217\u8868\u663e\u793a`)}</div>
                    <div class="session-name-error" aria-live="polite"></div>
                </div>
                <div class="modal-footer session-name-footer">
                    <button type="button" class="btn-secondary session-name-cancel">\u53d6\u6d88</button>
                    <button type="button" class="btn-primary session-name-confirm">${Utils.escapeHtml(confirmText)}</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        const input = modal.querySelector("#session-name-input");
        const error = modal.querySelector(".session-name-error");
        const confirm = modal.querySelector(".session-name-confirm");
        const cancel = modal.querySelector(".session-name-cancel");
        const close = modal.querySelector(".session-name-close");
        let settled = false;

        const cleanup = (value) => {
            if (settled) {
                return;
            }
            settled = true;
            document.removeEventListener("keydown", handleKeydown);
            modal.remove();
            resolve(value);
        };

        const submit = () => {
            try {
                const value = allowEmpty ? normalizeSessionName(input.value) : validateSessionName(input.value);
                if (allowEmpty && value.length > maxLength) {
                    throw new Error(`\u4f1a\u8bdd\u5907\u6ce8\u4e0d\u80fd\u8d85\u8fc7 ${maxLength} \u4e2a\u5b57\u7b26`);
                }
                cleanup(value);
            } catch (err) {
                error.textContent = err.message;
                input.focus();
            }
        };

        function handleKeydown(event) {
            if (event.key === "Escape") {
                cleanup(null);
            }
            if (event.key === "Enter") {
                event.preventDefault();
                submit();
            }
        }

        confirm.addEventListener("click", submit);
        cancel.addEventListener("click", () => cleanup(null));
        close.addEventListener("click", () => cleanup(null));
        modal.addEventListener("click", (event) => {
            if (event.target === modal) {
                cleanup(null);
            }
        });
        input.addEventListener("input", () => {
            error.textContent = "";
        });
        document.addEventListener("keydown", handleKeydown);

        window.requestAnimationFrame(() => {
            input.focus();
            input.select();
        });
    });
}

async function promptRenameSession(sessionId, currentName = "") {
    const sessionName = await askSessionName({
        title: "\u91cd\u547d\u540d\u4f1a\u8bdd",
        initialValue: currentName || "",
        confirmText: "\u4fdd\u5b58"
    });
    if (sessionName === null) {
        return;
    }
    const result = await renameSession(sessionId, sessionName);
    if (sessionId === State.sessionId) {
        State.sessionName = result.session_name || sessionName;
        State.sessionLabel = result.session_label || State.sessionLabel || "";
        State.displayTitle = result.display_title || getDisplayTitle(State.sessionName, State.sessionLabel, State.sessionId);
        updateSessionMeta();
    }
    await loadSessions();
    Utils.showToast("\u4f1a\u8bdd\u540d\u79f0\u5df2\u66f4\u65b0");
}

async function promptSessionLabel(sessionId, currentLabel = "") {
    const sessionLabel = await askSessionName({
        title: "\u7f16\u8f91\u4f1a\u8bdd\u5907\u6ce8",
        initialValue: currentLabel || "",
        confirmText: "\u4fdd\u5b58",
        allowEmpty: true,
        maxLength: MAX_SESSION_LABEL_LENGTH,
        inputLabel: "\u4f1a\u8bdd\u5907\u6ce8\u540d",
        hint: `\u6700\u591a ${MAX_SESSION_LABEL_LENGTH} \u4e2a\u5b57\u7b26\uff0c\u53ef\u7559\u7a7a\uff0c\u4e0d\u53c2\u4e0e prompt\u3001RAG \u6216\u6587\u4ef6\u540d`
    });
    if (sessionLabel === null) {
        return;
    }
    const result = await updateSessionLabel(sessionId, sessionLabel);
    if (sessionId === State.sessionId) {
        State.sessionName = result.session_name || State.sessionName;
        State.sessionLabel = result.session_label || "";
        State.displayTitle = result.display_title || getDisplayTitle(State.sessionName, State.sessionLabel, State.sessionId);
        updateSessionMeta();
    }
    await loadSessions();
    Utils.showToast(sessionLabel ? "\u4f1a\u8bdd\u5907\u6ce8\u5df2\u66f4\u65b0" : "\u4f1a\u8bdd\u5907\u6ce8\u5df2\u6e05\u7a7a");
}

async function deleteSession(sessionId, sessionName = "") {
    const label = sessionName || sessionId;
    if (!window.confirm(`\u786e\u5b9a\u5220\u9664\u4f1a\u8bdd\u300c${label}\u300d\u5417\uff1f`)) {
        return;
    }

    await Utils.request(`/api/session/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    if (sessionId === State.sessionId) {
        window.localStorage.removeItem(STORAGE_KEYS.currentSession);
        const sessions = await loadSessions();
        if (sessions.length > 0) {
            await loadHistory(sessions[0].id);
            await loadSessions();
        } else {
            createNewSession();
        }
    } else {
        await loadSessions();
    }
    await refreshUiState();
    Utils.showToast("\u4f1a\u8bdd\u5df2\u5220\u9664");
}

async function loadHistory(sessionId) {
    const data = await Utils.request(`/api/history/${sessionId}`);
    State.sessionId = data.session_id;
    State.sessionName = data.session_name || data.session_id;
    State.sessionLabel = data.session_label || "";
    State.displayTitle = data.display_title || getDisplayTitle(State.sessionName, State.sessionLabel, data.session_id);
    State.messages = data.messages || [];
    State.round = (data.last_round || 0) + 1;
    State.sessionConfig = { ...State.sessionConfig, ...(data.config || {}) };
    State.protocolConfig = { ...State.protocolConfig, ...(data.config?.protocol_config || {}) };
    State.chunkConfig = { ...State.chunkConfig, ...(data.config?.chunk_config || {}) };
    State.tuning = { ...State.tuning, ...(data.config?.tuning_config || {}) };
    State.ablation.similarity_threshold = State.tuning.similarity_threshold;
    loadSessionAvatars(data.ui_settings || {});
    syncStateToForm();
    renderMessages();
    renderRagContext(null);
    renderAnalysis("");
    saveCurrentSessionId();
}

async function switchSession(sessionId) {
    if (!sessionId || sessionId === State.sessionId) {
        return;
    }
    await loadHistory(sessionId);
    await loadSessions();
    Utils.setStatus("\u5df2\u5207\u6362\u4f1a\u8bdd");
}

function createNewSession() {
    State.sessionId = Utils.generateSessionId();
    State.sessionName = "";
    State.sessionLabel = "";
    State.displayTitle = "";
    State.messages = [];
    State.round = 1;
    loadSessionAvatars({});
    renderMessages();
    renderRagContext(null);
    renderAnalysis("");
    saveCurrentSessionId();
    loadSessions().catch(console.error);
    Utils.setStatus("\u65b0\u4f1a\u8bdd\u5df2\u521b\u5efa");
}

async function createNamedSession() {
    const sessionName = await askSessionName({
        title: "\u65b0\u5efa\u4f1a\u8bdd",
        initialValue: "",
        confirmText: "\u521b\u5efa"
    });
    if (sessionName === null) {
        return;
    }

    createNewSession();
    try {
        const result = await renameSession(State.sessionId, sessionName);
        State.sessionName = result.session_name || sessionName;
        State.sessionLabel = result.session_label || "";
        State.displayTitle = result.display_title || getDisplayTitle(State.sessionName, State.sessionLabel, State.sessionId);
        updateSessionMeta();
        await loadSessions();
    } catch (error) {
        Utils.showToast(error.message, "error");
    }
}

async function persistSessionConfig() {
    if (!State.sessionId) {
        State.sessionId = Utils.generateSessionId();
        saveCurrentSessionId();
    }
    syncFormToState();
    saveLocalApiConfig();
    updateModelDisplay();
    updateRagToggleState();
    await Utils.request("/api/chat/config", {
        method: "POST",
        body: JSON.stringify({
            session_id: State.sessionId,
            user_name: State.sessionConfig.user_name,
            user_persona: State.sessionConfig.user_persona,
            character_name: State.sessionConfig.character_name,
            system_prompt: State.sessionConfig.system_prompt,
            protocol_config: State.protocolConfig,
            tuning_config: State.tuning,
            chunk_config: State.chunkConfig
        })
    });
}

function buildChatPayload(message) {
    return {
        session_id: State.sessionId,
        round: State.round,
        message,
        api_config: State.apiConfig,
        user_name: State.sessionConfig.user_name,
        user_persona: State.sessionConfig.user_persona,
        character_name: State.sessionConfig.character_name,
        system_prompt: State.sessionConfig.system_prompt,
        protocol_config: State.protocolConfig,
        tuning_config: State.tuning,
        ablation_config: {
            rag_enabled: State.ablation.rag_enabled,
            kb_enabled: State.ablation.kb_enabled,
            chat_enabled: State.ablation.chat_enabled,
            temporal_enabled: State.ablation.temporal_enabled,
            bm25_enabled: State.ablation.bm25_enabled,
            regeneration_enabled: State.ablation.regeneration_enabled,
            regen_max_attempts: State.ablation.regen_max_attempts,
            regen_regex: State.ablation.regen_regex,
            regen_semantic: State.ablation.regen_semantic
        },
        similarity_threshold: State.ablation.similarity_threshold
    };
}

async function sendMessage() {
    if (State.isGenerating) {
        return;
    }

    const content = DOM.userInput.value.trim();
    if (!content) {
        return;
    }

    if (!State.sessionId) {
        State.sessionId = Utils.generateSessionId();
    }

    syncFormToState();
    saveLocalApiConfig();
    await persistSessionConfig();

    const currentRound = State.round;
    State.isGenerating = true;
    updateSendButtonState();
    Utils.setStatus("\u751f\u6210\u4e2d...");

    State.messages.push(
        {
            role: "user",
            content,
            round: currentRound,
            timestamp: new Date().toISOString()
        },
        {
            role: "assistant",
            content: "\u6b63\u5728\u751f\u6210\uff0c\u8bf7\u7a0d\u5019...",
            round: currentRound,
            pending: true,
            timestamp: new Date().toISOString()
        }
    );
    renderMessages();
    DOM.userInput.value = "";
    autoResizeInput();
    updateSendButtonState();

    try {
        const result = await Utils.request("/api/chat", {
            method: "POST",
            headers: { "X-ARPM-Theme": getCurrentThemeKey() },
            body: JSON.stringify(buildChatPayload(content))
        });

        State.messages = State.messages.filter((item) => !item.pending);
        State.messages.push({
            role: "assistant",
            content: result.reply || "",
            round: currentRound,
            timestamp: new Date().toISOString()
        });
        State.round = (result.round || currentRound) + 1;
        State.sessionConfig = { ...State.sessionConfig, ...(result.config || {}) };
        State.protocolConfig = { ...State.protocolConfig, ...(result.config?.protocol_config || {}) };
        State.chunkConfig = { ...State.chunkConfig, ...(result.config?.chunk_config || {}) };
        State.tuning = { ...State.tuning, ...(result.config?.tuning_config || {}) };
        State.ablation.similarity_threshold = State.tuning.similarity_threshold;
        renderMessages();
        renderRagContext(result.rag_context);
        renderAnalysis(result.analysis || "", result.protocol_info || null);
        saveCurrentSessionId();
        await loadSessions();
        Utils.setStatus("\u5df2\u5b8c\u6210", "success");
    } catch (error) {
        State.messages = State.messages.filter((item) => !item.pending);
        renderMessages();
        renderRagContext(null);
        renderAnalysis("");
        Utils.setStatus("\u53d1\u9001\u5931\u8d25", "error");
        Utils.showToast(error.message, "error", 3600);
    } finally {
        State.isGenerating = false;
        updateSendButtonState();
    }
}

async function cancelGeneration() {
    if (!State.sessionId || !State.isGenerating) {
        return;
    }
    try {
        await Utils.request("/api/chat/cancel", {
            method: "POST",
            body: JSON.stringify({ session_id: State.sessionId })
        });
        Utils.setStatus("\u5df2\u53d1\u9001\u4e2d\u6b62\u8bf7\u6c42", "warning");
    } catch (error) {
        Utils.showToast(error.message, "error");
    }
}

async function regenerateRound(round) {
    const userMessage = State.messages.find((item) => item.role === "user" && Number(item.round) === Number(round));
    if (!userMessage) {
        Utils.showToast("\u672a\u627e\u5230\u8be5\u8f6e\u7528\u6237\u6d88\u606f", "error");
        return;
    }

    syncFormToState();
    try {
        Utils.setStatus(`\u6b63\u5728\u91cd\u65b0\u751f\u6210\u7b2c ${round} \u8f6e...`);
        const result = await Utils.request("/api/chat/regenerate", {
            method: "POST",
            headers: { "X-ARPM-Theme": getCurrentThemeKey() },
            body: JSON.stringify({
                ...buildChatPayload(userMessage.content),
                round: Number(round)
            })
        });
        await loadHistory(State.sessionId);
        renderAnalysis(result.analysis || "", result.protocol_info || null);
        Utils.setStatus(`\u7b2c ${round} \u8f6e\u5df2\u91cd\u65b0\u751f\u6210`, "success");
    } catch (error) {
        Utils.showToast(error.message, "error");
        Utils.setStatus("\u91cd\u65b0\u751f\u6210\u5931\u8d25", "error");
    }
}

async function deleteRound(round) {
    if (!window.confirm(`\u786e\u5b9a\u5220\u9664\u7b2c ${round} \u8f6e\u6d88\u606f\u548c\u7d22\u5f15\u5417\uff1f`)) {
        return;
    }
    try {
        await Utils.request("/api/chat/delete-message", {
            method: "POST",
            body: JSON.stringify({
                session_id: State.sessionId,
                round: Number(round)
            })
        });
        await loadHistory(State.sessionId);
        await loadSessions();
        Utils.setStatus(`\u7b2c ${round} \u8f6e\u5df2\u5220\u9664`, "success");
    } catch (error) {
        Utils.showToast(error.message, "error");
    }
}

async function clearCurrentChat() {
    if (!State.sessionId) {
        return;
    }
    if (!window.confirm("\u786e\u5b9a\u6e05\u7a7a\u5f53\u524d\u4f1a\u8bdd\u4e0a\u4e0b\u6587\u5417\uff1f")) {
        return;
    }
    try {
        await Utils.request("/api/history", {
            method: "POST",
            body: JSON.stringify({
                session_id: State.sessionId,
                messages: []
            })
        });
        State.messages = [];
        State.round = 1;
        renderMessages();
        renderRagContext(null);
        renderAnalysis("");
        Utils.setStatus("\u5f53\u524d\u4f1a\u8bdd\u5df2\u6e05\u7a7a", "success");
    } catch (error) {
        Utils.showToast(error.message, "error");
    }
}

async function clearCurrentChatAndIndex() {
    if (!State.sessionId) {
        return;
    }
    if (!window.confirm("\u786e\u5b9a\u6e05\u7a7a\u5f53\u524d\u4f1a\u8bdd\u4e0a\u4e0b\u6587\u548c\u5411\u91cf\u7d22\u5f15\u5417\uff1f")) {
        return;
    }
    try {
        await Utils.request("/api/history", {
            method: "POST",
            body: JSON.stringify({
                session_id: State.sessionId,
                messages: []
            })
        });
        await Utils.request(`/api/session/${State.sessionId}/chat_index`, {
            method: "DELETE"
        });
        State.messages = [];
        State.round = 1;
        renderMessages();
        renderRagContext(null);
        renderAnalysis("");
        Utils.setStatus("\u5f53\u524d\u4f1a\u8bdd\u4e0a\u4e0b\u6587\u548c\u7d22\u5f15\u5df2\u6e05\u7a7a", "success");
    } catch (error) {
        Utils.showToast(error.message, "error");
    }
}

function setUploadProgress(percent, text) {
    DOM.uploadProgressContainer.style.display = "block";
    DOM.uploadProgressBar.style.width = `${percent}%`;
    DOM.uploadProgressPercent.textContent = `${percent}%`;
    DOM.uploadProgressText.textContent = text;
}

function hideUploadProgress() {
    DOM.uploadProgressContainer.style.display = "none";
    DOM.uploadProgressBar.style.width = "0%";
    DOM.uploadProgressPercent.textContent = "0%";
    DOM.uploadProgressText.textContent = "\u51c6\u5907\u4e0a\u4f20...";
}

async function uploadKnowledgeFile(file) {
    if (!file) {
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("chunk_config", JSON.stringify(State.chunkConfig));
    DOM.fileName.textContent = file.name;
    setUploadProgress(10, "\u5f00\u59cb\u4e0a\u4f20...");

    try {
        const response = await fetch("/api/knowledge", {
            method: "POST",
            body: formData
        });
        setUploadProgress(70, "\u670d\u52a1\u5668\u5904\u7406\u4e2d...");
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || data.message || "\u4e0a\u4f20\u5931\u8d25");
        }
        setUploadProgress(100, `\u4e0a\u4f20\u5b8c\u6210\uff0c\u5171\u65b0\u589e ${data.count || 0} \u4e2a\u7247\u6bb5`);
        await refreshKnowledgeStats();
        await loadKnowledgeChunks();
        Utils.showToast("\u77e5\u8bc6\u5e93\u4e0a\u4f20\u5b8c\u6210");
        window.setTimeout(hideUploadProgress, 1200);
    } catch (error) {
        hideUploadProgress();
        Utils.showToast(error.message, "error");
    }
}

function renderKnowledgeList() {
    const keyword = DOM.kbSearch.value.trim().toLowerCase();
    State.kbFilteredChunks = State.kbChunks.filter((chunk) => {
        if (!keyword) {
            return true;
        }
        return [chunk.text, chunk.source, chunk.chunk_id].some((value) =>
            String(value || "").toLowerCase().includes(keyword)
        );
    });

    if (!State.kbFilteredChunks.length) {
        DOM.kbList.innerHTML = '<div class="empty">\u6ca1\u6709\u5339\u914d\u7684\u77e5\u8bc6\u5757</div>';
        return;
    }

    DOM.kbList.innerHTML = State.kbFilteredChunks.map((chunk) => `
        <div class="chunk-item">
            <div class="chunk-header">
                <code>${Utils.escapeHtml(chunk.chunk_id || "")}</code>
                <span class="chunk-source">${Utils.escapeHtml(chunk.source || "unknown")}</span>
                <button class="feedback-btn delete-kb-chunk" data-chunk-id="${Utils.escapeHtml(chunk.chunk_id || "")}">\u5220\u9664</button>
            </div>
            <div class="chunk-text">${Utils.formatText(chunk.text || "")}</div>
            <div class="chunk-meta">\u5b50\u5757\u6570 ${chunk.child_count ?? 0}</div>
        </div>
    `).join("");
}

async function loadKnowledgeChunks() {
    const data = await Utils.request("/api/knowledge/chunks");
    State.kbChunks = data.chunks || [];
    renderKnowledgeList();
}

async function deleteKnowledgeChunk(chunkId) {
    if (!window.confirm(`\u786e\u5b9a\u5220\u9664\u77e5\u8bc6\u5757 ${chunkId} \u5417\uff1f`)) {
        return;
    }
    try {
        await Utils.request(`/api/knowledge/chunk/${chunkId}`, {
            method: "DELETE"
        });
        await refreshKnowledgeStats();
        await loadKnowledgeChunks();
        Utils.showToast(`\u77e5\u8bc6\u5757 ${chunkId} \u5df2\u5220\u9664`);
    } catch (error) {
        Utils.showToast(error.message, "error");
    }
}

function renderDiagnosticHtml(report) {
    const checks = (report.checks || []).map((item) => `
        <div class="chunk-item">
            <div class="chunk-header">
                <strong>${Utils.escapeHtml(item.name)}</strong>
                <span class="chunk-source">${Utils.escapeHtml(item.status)}</span>
            </div>
            <div class="chunk-text">${Utils.escapeHtml(item.message || "")}</div>
        </div>
    `).join("");

    return `
        <div class="diagnose-summary ${report.healthy ? "healthy" : "unhealthy"}">
            <span class="ok">\u6b63\u5e38 ${report.summary?.ok ?? 0}</span>
            <span class="warning">\u8b66\u544a ${report.summary?.warnings ?? 0}</span>
            <span class="error">\u9519\u8bef ${report.summary?.errors ?? 0}</span>
        </div>
        ${checks || '<div class="empty">\u65e0\u68c0\u67e5\u7ed3\u679c</div>'}
    `;
}

function renderArpmReport(report) {
    DOM.arpmReportSection.style.display = "block";
    const currentRuntime = `
        <div class="chunk-item">
            <div class="chunk-header">
                <strong>\u5f53\u524d\u4f1a\u8bdd\u53c2\u6570</strong>
                <span class="chunk-source">runtime</span>
            </div>
            <div class="chunk-text">\u8fd9\u91cc\u5c55\u793a\u5f53\u524d\u524d\u7aef\u5b9e\u9645\u63d0\u4ea4\u7ed9\u540e\u7aef\u7684\u8c03\u53c2\u4e0e\u5206\u5757\u914d\u7f6e\uff0c\u4fbf\u4e8e\u8c03\u4f18\u548c\u590d\u73b0\u5b9e\u9a8c\u3002</div>
            <div class="chunk-meta">
                knowledge_k: ${State.tuning.knowledge_k} · chat_history_k: ${State.tuning.chat_history_k} · similarity_threshold: ${State.tuning.similarity_threshold}
                · decay_round: ${State.tuning.decay_rate_round} · decay_hours: ${State.tuning.decay_rate_hours} · rrf_k: ${State.tuning.rrf_k}
                · role_prefix: ${State.tuning.role_query_prefix_enabled} · kb_user_boost: ${State.tuning.kb_user_name_boost}
                · kb_char_boost: ${State.tuning.kb_character_name_boost} · kb_source_boost: ${State.tuning.kb_source_name_boost}
                · chat_session_boost: ${State.tuning.chat_same_session_boost} · chat_exact_boost: ${State.tuning.chat_exact_name_boost}
                · chat_text_boost: ${State.tuning.chat_text_name_boost} · temperature: ${State.tuning.temperature}
                · max_tokens: ${State.tuning.max_tokens} · chunk_child: ${State.chunkConfig.child_size}
                · chunk_parent: ${State.chunkConfig.parent_size} · chunk_overlap: ${State.chunkConfig.overlap_sentences}
            </div>
        </div>
        <div class="chunk-item">
            <div class="chunk-header">
                <strong>\u534f\u8bae\u63a7\u5236</strong>
                <span class="chunk-source">protocol</span>
            </div>
            <div class="chunk-text">\u5206\u6790\u5f0f\u751f\u6210\u534f\u8bae\u4e0e\u601d\u8003\u578b\u6a21\u578b\u517c\u5bb9\u7b56\u7565\u3002</div>
            <div class="chunk-meta">
                protocol_mode: ${State.protocolConfig.protocol_mode}
                · reasoning_model_mode: ${State.protocolConfig.reasoning_model_mode}
                · auto_repair_response: ${State.protocolConfig.auto_repair_response}
                · diagnostic_mode: ${State.protocolConfig.diagnostic_mode}
            </div>
        </div>
    `;
    DOM.tabComponents.innerHTML = currentRuntime + (report.components || []).map((component) => `
        <div class="chunk-item">
            <div class="chunk-header">
                <strong>${Utils.escapeHtml(component.name)}</strong>
                <span class="chunk-source">${Utils.escapeHtml(component.status)}</span>
            </div>
            <div class="chunk-text">${Utils.escapeHtml(component.description || "")}</div>
            <div class="chunk-meta">${(component.config || []).map((item) => `${item.name}: ${item.value}`).join(" · ")}</div>
        </div>
    `).join("");

    DOM.tabForgetting.innerHTML = (report.forgetting_logics || []).map((item) => `
        <div class="chunk-item">
            <div class="chunk-header">
                <strong>${Utils.escapeHtml(item.name)}</strong>
                <span class="chunk-source">\u903b\u8f91</span>
            </div>
            <div class="chunk-text">${Utils.escapeHtml(item.description || "")}</div>
            <div class="chunk-meta">\u516c\u5f0f: ${Utils.escapeHtml(item.formula || "")}</div>
        </div>
    `).join("");

    DOM.tabStats.innerHTML = `
        <div class="chunk-item">
            <div class="chunk-header"><strong>\u77e5\u8bc6\u5e93</strong><span class="chunk-source">${Utils.escapeHtml(report.knowledge_stats?.status || "")}</span></div>
            <div class="chunk-meta">\u7236\u5757 ${report.knowledge_stats?.total_parents ?? 0} \u00b7 \u5b50\u5757 ${report.knowledge_stats?.total_children ?? 0}</div>
        </div>
        <div class="chunk-item">
            <div class="chunk-header"><strong>\u5bf9\u8bdd\u5386\u53f2</strong><span class="chunk-source">${Utils.escapeHtml(report.chat_stats?.status || "")}</span></div>
            <div class="chunk-meta">\u4f1a\u8bdd ${report.chat_stats?.total_sessions ?? 0} \u00b7 \u539f\u5b50\u5757 ${report.chat_stats?.total_atoms ?? 0}</div>
        </div>
    `;
}

async function runApiTest(target) {
    syncFormToState();
    const result = await Utils.request("/api/test", {
        method: "POST",
        body: JSON.stringify({
            api_key: State.apiConfig.api_key,
            base_url: State.apiConfig.base_url,
            model: State.apiConfig.model
        })
    });

    if (target === "settings") {
        DOM.testResult.textContent = result.message || "\u8fde\u63a5\u6210\u529f";
        DOM.testResult.style.color = result.success ? "#16a34a" : "#dc2626";
    } else {
        DOM.apiCheckResult.style.display = "block";
        DOM.apiCheckResult.querySelector(".diagnose-content").innerHTML = `
            <div class="chunk-item">
                <div class="chunk-header">
                    <strong>API \u8fde\u63a5</strong>
                    <span class="chunk-source">${result.success ? "success" : "error"}</span>
                </div>
                <div class="chunk-text">${Utils.escapeHtml(result.message || "")}</div>
            </div>
        `;
    }
}

async function runSystemDiagnosis() {
    Utils.setDiagnoseStatus("\u68c0\u67e5\u4e2d...", "processing");
    const report = await Utils.request("/api/diagnostics");
    DOM.systemDiagResult.style.display = "block";
    DOM.systemDiagResult.querySelector(".diagnose-content").innerHTML = renderDiagnosticHtml(report);
    Utils.setDiagnoseStatus(report.healthy ? "\u7cfb\u7edf\u5065\u5eb7" : "\u53d1\u73b0\u5f02\u5e38", report.healthy ? "success" : "warning");
}

async function loadArpmReport() {
    Utils.setDiagnoseStatus("\u8bfb\u53d6\u62a5\u544a\u4e2d...", "processing");
    const report = await Utils.request("/api/diagnostics/arpm");
    renderArpmReport(report);
    Utils.setDiagnoseStatus("\u7ec4\u4ef6\u62a5\u544a\u5df2\u52a0\u8f7d", "success");
}

function switchArpmTab(tab) {
    State.currentTab = tab;
    document.querySelectorAll(".arpm-tab").forEach((button) => {
        button.classList.toggle("active", button.dataset.tab === tab);
    });
    DOM.tabComponents.style.display = tab === "components" ? "block" : "none";
    DOM.tabForgetting.style.display = tab === "forgetting" ? "block" : "none";
    DOM.tabStats.style.display = tab === "stats" ? "block" : "none";
}

function switchDeleteTab(tab) {
    State.currentDeleteTab = tab;
    document.querySelectorAll(".delete-tab").forEach((button) => {
        button.classList.toggle("active", button.dataset.tab === tab);
    });
    document.getElementById("tab-kb-delete").style.display = tab === "kb-delete" ? "block" : "none";
    document.getElementById("tab-chat-delete").style.display = tab === "chat-delete" ? "block" : "none";
}

async function loadDiagnosticKnowledgeChunks() {
    const data = await Utils.request("/api/knowledge/chunks");
    DOM.kbChunksCount.textContent = `\u5171 ${data.total || 0} \u4e2a\u5757`;
    DOM.kbChunksList.innerHTML = (data.chunks || []).map((chunk) => `
        <div class="chunk-item">
            <div class="chunk-header">
                <code>${Utils.escapeHtml(chunk.chunk_id || "")}</code>
                <span class="chunk-source">${Utils.escapeHtml(chunk.source || "unknown")}</span>
                <button class="feedback-btn delete-kb-diag" data-chunk-id="${Utils.escapeHtml(chunk.chunk_id || "")}">\u5220\u9664</button>
            </div>
            <div class="chunk-text">${Utils.formatText(chunk.text || "")}</div>
        </div>
    `).join("") || '<div class="empty">\u6682\u65e0\u77e5\u8bc6\u5e93\u5757</div>';
}

async function loadDiagnosticChatChunks(sessionId = null) {
    const data = await Utils.request(sessionId ? `/api/chat/chunks/${encodeURIComponent(sessionId)}` : "/api/chat/chunks");
    DOM.chatChunksCount.textContent = `\u5171 ${data.total_chunks ?? data.total ?? 0} \u4e2a\u5757`;
    DOM.chatChunksList.innerHTML = (data.chunks || []).map((chunk) => `
        <div class="chunk-item">
            <div class="chunk-header">
                <code>${Utils.escapeHtml(chunk.chunk_id || "")}</code>
                <span class="chunk-role">${Utils.escapeHtml(chunk.session_id || "")}</span>
                <button class="feedback-btn delete-chat-diag" data-chunk-id="${Utils.escapeHtml(chunk.chunk_id || "")}">\u5220\u9664</button>
            </div>
            <div class="chunk-text">${Utils.formatText(chunk.text || "")}</div>
        </div>
    `).join("") || '<div class="empty">\u6682\u65e0\u5bf9\u8bdd\u5757</div>';
}

async function deleteDiagnosticChunk(type, chunkId) {
    const url = type === "kb" ? `/api/knowledge/chunk/${chunkId}` : `/api/chat/chunk/${chunkId}`;
    const label = type === "kb" ? "\u77e5\u8bc6\u5757" : "\u5bf9\u8bdd\u5757";

    if (!window.confirm(`\u786e\u5b9a\u5220\u9664${label} ${chunkId} \u5417\uff1f`)) {
        return;
    }

    await Utils.request(url, { method: "DELETE" });
    if (type === "kb") {
        await loadDiagnosticKnowledgeChunks();
        await refreshKnowledgeStats();
        await loadKnowledgeChunks();
    } else {
        await loadDiagnosticChatChunks();
        if (State.sessionId) {
            await loadHistory(State.sessionId);
        }
    }
}

async function clearData(payload) {
    const result = await Utils.request("/api/data/clear_all", {
        method: "POST",
        body: JSON.stringify({
            confirm: true,
            ...payload
        })
    });
    DOM.clearDataResult.style.display = "block";
    DOM.clearDataResult.textContent = result.message || "\u64cd\u4f5c\u5b8c\u6210";
    await refreshKnowledgeStats();
    await loadSessions();
    createNewSession();
}

function buildRagHelp() {
    DOM.ragHelpContent.innerHTML = `
        <div class="chunk-item">
            <div class="chunk-header"><strong>\u603b\u6d41\u7a0b</strong><span class="chunk-source">ARPM</span></div>
            <div class="chunk-text">\u5f53\u524d\u524d\u7aef\u53ea\u5c55\u793a\u540e\u7aef\u771f\u5b9e\u5b58\u5728\u7684\u94fe\u8def\uff1a\u77e5\u8bc6\u5e93\u53ec\u56de\u3001\u5bf9\u8bdd\u5386\u53f2\u53ec\u56de\u3001\u5206\u522b\u52a0\u6743\u3001\u6700\u7ec8\u751f\u6210\uff0c\u4ee5\u53ca\u751f\u6210\u540e\u72ec\u7acb\u6267\u884c\u7684\u5bf9\u8bdd\u539f\u5b50\u5199\u5165\u3002</div>
        </div>
        <div class="chunk-item">
            <div class="chunk-header"><strong>\u77e5\u8bc6\u5e93\u53ec\u56de</strong><span class="chunk-source">Top-K</span></div>
            <div class="chunk-text">\u4ece\u5168\u5c40\u77e5\u8bc6\u5e93\u7d22\u5f15\u4e2d\u53ec\u56de\u76f8\u5173\u7236\u5757\u3002\u77e5\u8bc6\u5e93\u7ed3\u679c\u4f1a\u5355\u72ec\u8ba1\u7b97\u81ea\u5df1\u7684\u89d2\u8272\u6743\u91cd\u548c\u53cc\u65f6\u6001\u6743\u91cd\uff0c\u4e0d\u548c\u5bf9\u8bdd\u5386\u53f2\u5171\u7528\u4e00\u5957\u7ed3\u679c\u96c6\u3002</div>
        </div>
        <div class="chunk-item">
            <div class="chunk-header"><strong>\u5bf9\u8bdd\u5386\u53f2\u53ec\u56de</strong><span class="chunk-source">Session</span></div>
            <div class="chunk-text">\u4ec5\u68c0\u7d22\u5f53\u524d\u4f1a\u8bdd\u7684\u5386\u53f2\u539f\u5b50\u5757\uff0c\u4e0d\u4f1a\u6df7\u5165\u5176\u4ed6\u4f1a\u8bdd\u3002\u5bf9\u8bdd\u5386\u53f2\u7ed3\u679c\u4e5f\u4f1a\u72ec\u7acb\u8ba1\u7b97\u81ea\u5df1\u7684\u6743\u91cd\u3002</div>
        </div>
        <div class="chunk-item">
            <div class="chunk-header"><strong>\u53cc\u65f6\u6001\u6743\u91cd</strong><span class="chunk-source">Temporal</span></div>
            <div class="chunk-text">\u540e\u7aef\u4f1a\u5206\u522b\u5bf9\u77e5\u8bc6\u5e93\u7ed3\u679c\u548c\u5bf9\u8bdd\u5386\u53f2\u7ed3\u679c\u65bd\u52a0\u8f6e\u6b21\u8870\u51cf\u4e0e\u7269\u7406\u65f6\u95f4\u8870\u51cf\uff0c\u524d\u7aef\u5c55\u793a\u7684\u662f\u5404\u81ea\u52a0\u6743\u540e\u7684\u7ed3\u679c\u3002</div>
        </div>
        <div class="chunk-item">
            <div class="chunk-header"><strong>\u539f\u5b50\u5199\u5165</strong><span class="chunk-source">Write Path</span></div>
            <div class="chunk-text">\u539f\u5b50\u5199\u5165\u53d1\u751f\u5728\u751f\u6210\u5b8c\u6210\u4e4b\u540e\uff0c\u53ea\u8d1f\u8d23\u628a\u5f53\u524d\u8f6e\u5bf9\u8bdd\u5199\u5165\u5f53\u524d\u4f1a\u8bdd\u7684 chat \u5411\u91cf\u7d22\u5f15\u3002\u5b83\u4e0d\u53c2\u4e0e\u77e5\u8bc6\u5e93\u6743\u91cd\u8ba1\u7b97\u3002</div>
        </div>
    `;
}

function autoResizeInput() {
    DOM.userInput.style.height = "auto";
    DOM.userInput.style.height = `${Math.min(DOM.userInput.scrollHeight, 200)}px`;
}

function bindEvents() {
    DOM.userInput.addEventListener("input", () => {
        autoResizeInput();
        updateSendButtonState();
    });

    DOM.userInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage().catch((error) => {
                console.error(error);
                Utils.showToast(error.message, "error");
            });
        }
    });

    DOM.btnSend.addEventListener("click", () => sendMessage().catch((error) => {
        console.error(error);
        Utils.showToast(error.message, "error");
    }));
    DOM.btnStop.addEventListener("click", () => cancelGeneration().catch(console.error));
    DOM.btnNewChat.addEventListener("click", () => createNamedSession().catch((error) => {
        console.error(error);
        Utils.showToast(error.message, "error");
    }));
    DOM.btnExportCurrent?.addEventListener("click", exportCurrentSession);
    DOM.btnGlobalSearch?.addEventListener("click", async () => {
        const text = I18N[State.language] || I18N.zh;
        setButtonBusy(DOM.btnGlobalSearch, true, text.loadKb);
        Utils.openModal(DOM.kbModal);
        try {
            await loadKnowledgeChunks();
            Utils.showToast(text.kbLoaded);
        } catch (error) {
            Utils.showToast(error.message, "error");
        } finally {
            setButtonBusy(DOM.btnGlobalSearch, false);
        }
    });
    DOM.btnSessionSearch?.addEventListener("click", async () => {
        const text = I18N[State.language] || I18N.zh;
        if (!State.sessionId) {
            Utils.showToast(text.needSession, "error");
            return;
        }
        setButtonBusy(DOM.btnSessionSearch, true, text.loadMemory);
        Utils.openModal(DOM.diagnoseModal);
        switchDeleteTab("chat-delete");
        try {
            await loadDiagnosticChatChunks(State.sessionId);
            Utils.showToast(text.memoryLoaded);
        } catch (error) {
            Utils.showToast(error.message, "error");
        } finally {
            setButtonBusy(DOM.btnSessionSearch, false);
        }
    });
    DOM.btnCollapseSidebar?.addEventListener("click", () => {
        document.body.classList.toggle("sidebar-collapsed");
        renderLanguage();
        const text = I18N[State.language] || I18N.zh;
        Utils.showToast(document.body.classList.contains("sidebar-collapsed") ? text.collapsed : text.expanded);
    });
    DOM.btnThemeChat?.addEventListener("click", () => setTheme("chat"));
    DOM.btnThemeResearch?.addEventListener("click", () => setTheme("research"));
    DOM.btnLangZh?.addEventListener("click", () => setLanguage("zh"));
    DOM.btnLangEn?.addEventListener("click", () => setLanguage("en"));
    DOM.welcomeOpenSettings?.addEventListener("click", () => Utils.openModal(DOM.settingsModal));
    DOM.welcomeOpenParams?.addEventListener("click", () => Utils.openModal(DOM.paramsModal));
    DOM.btnInputSettings?.addEventListener("click", () => Utils.openModal(DOM.settingsModal));
    DOM.btnClearChat.addEventListener("click", () => clearCurrentChat().catch(console.error));
    DOM.btnClearChatIndex.addEventListener("click", () => clearCurrentChatAndIndex().catch(console.error));

    DOM.openDiagnose.addEventListener("click", () => Utils.openModal(DOM.settingsModal));
    DOM.openSettings.addEventListener("click", () => Utils.openModal(DOM.paramsModal));
    DOM.closeSettings.addEventListener("click", () => Utils.closeModal(DOM.settingsModal));
    DOM.closeParams?.addEventListener("click", () => Utils.closeModal(DOM.paramsModal));
    DOM.saveSettings.addEventListener("click", async () => {
        try {
            await saveSettingsAndClose(DOM.settingsModal);
        } catch (error) {
            Utils.showToast(error.message, "error");
        }
    });
    DOM.saveParams?.addEventListener("click", async () => {
        try {
            await saveSettingsAndClose(DOM.paramsModal);
        } catch (error) {
            Utils.showToast(error.message, "error");
        }
    });
    DOM.openDiagnoseBasic?.addEventListener("click", () => Utils.openModal(DOM.diagnoseModal));
    DOM.btnCommonCheckApi?.addEventListener("click", async () => {
        try {
            setCommonDiagnoseStatus("\u6b63\u5728\u6d4b\u8bd5 API...", "processing");
            await runApiTest("settings");
            setCommonDiagnoseStatus("API \u8fde\u63a5\u6b63\u5e38", "success");
        } catch (error) {
            setCommonDiagnoseStatus("API \u8fde\u63a5\u5931\u8d25", "error");
            DOM.testResult.textContent = error.message;
            DOM.testResult.style.color = "#dc2626";
        }
    });
    DOM.btnCommonSystemDiag?.addEventListener("click", async () => {
        try {
            setCommonDiagnoseStatus("\u6b63\u5728\u68c0\u67e5\u7cfb\u7edf...", "processing");
            Utils.openModal(DOM.diagnoseModal);
            await runSystemDiagnosis();
            setCommonDiagnoseStatus("\u7cfb\u7edf\u68c0\u67e5\u5b8c\u6210", "success");
        } catch (error) {
            setCommonDiagnoseStatus("\u7cfb\u7edf\u68c0\u67e5\u5931\u8d25", "error");
            Utils.showToast(error.message, "error");
        }
    });

    DOM.testApi.addEventListener("click", async () => {
        try {
            await runApiTest("settings");
        } catch (error) {
            DOM.testResult.textContent = error.message;
            DOM.testResult.style.color = "#dc2626";
        }
    });

    DOM.cfgSimilarityThreshold.addEventListener("input", updateThresholdLabel);
    DOM.cfgRagEnabled.addEventListener("change", updateRagToggleState);
    DOM.uploadUserAvatar?.addEventListener("click", () => DOM.userAvatarInput?.click());
    DOM.uploadAssistantAvatar?.addEventListener("click", () => DOM.assistantAvatarInput?.click());
    DOM.userAvatarInput?.addEventListener("change", async () => {
        const [file] = DOM.userAvatarInput.files || [];
        try {
            await uploadSessionAvatar("user", file);
        } catch (error) {
            Utils.showToast(error.message, "error");
        } finally {
            DOM.userAvatarInput.value = "";
        }
    });
    DOM.assistantAvatarInput?.addEventListener("change", async () => {
        const [file] = DOM.assistantAvatarInput.files || [];
        try {
            await uploadSessionAvatar("assistant", file);
        } catch (error) {
            Utils.showToast(error.message, "error");
        } finally {
            DOM.assistantAvatarInput.value = "";
        }
    });
    DOM.resetUserAvatar?.addEventListener("click", () => deleteSessionAvatar("user").catch((error) => {
        Utils.showToast(error.message, "error");
    }));
    DOM.resetAssistantAvatar?.addEventListener("click", () => deleteSessionAvatar("assistant").catch((error) => {
        Utils.showToast(error.message, "error");
    }));
    document.querySelectorAll(".tuning-preset").forEach((button) => {
        button.addEventListener("click", () => {
            applyTuningPreset(button.dataset.preset);
            Utils.showToast(`\u5df2\u5e94\u7528\u53c2\u6570\u9884\u8bbe\uff1a${button.textContent}`);
        });
    });

    DOM.uploadFile.addEventListener("click", () => DOM.fileUpload.click());
    DOM.fileUpload.addEventListener("change", () => {
        const [file] = DOM.fileUpload.files || [];
        uploadKnowledgeFile(file).catch(console.error);
    });
    DOM.manageKb.addEventListener("click", async () => {
        Utils.openModal(DOM.kbModal);
        try {
            await loadKnowledgeChunks();
        } catch (error) {
            Utils.showToast(error.message, "error");
        }
    });
    DOM.closeKb.addEventListener("click", () => Utils.closeModal(DOM.kbModal));
    DOM.kbRefresh.addEventListener("click", () => loadKnowledgeChunks().catch(console.error));
    DOM.kbSearch.addEventListener("input", renderKnowledgeList);

    DOM.closeDiagnose.addEventListener("click", () => Utils.closeModal(DOM.diagnoseModal));
    DOM.btnCheckApi.addEventListener("click", () => runApiTest("diagnose").then(() => {
        Utils.setDiagnoseStatus("API \u6d4b\u8bd5\u5b8c\u6210", "success");
    }).catch((error) => {
        Utils.setDiagnoseStatus("API \u6d4b\u8bd5\u5931\u8d25", "error");
        Utils.showToast(error.message, "error");
    }));
    DOM.btnArpmReport.addEventListener("click", () => loadArpmReport().catch((error) => {
        Utils.setDiagnoseStatus("\u7ec4\u4ef6\u62a5\u544a\u52a0\u8f7d\u5931\u8d25", "error");
        Utils.showToast(error.message, "error");
    }));
    DOM.btnSystemDiag.addEventListener("click", () => runSystemDiagnosis().catch((error) => {
        Utils.setDiagnoseStatus("\u7cfb\u7edf\u68c0\u67e5\u5931\u8d25", "error");
        Utils.showToast(error.message, "error");
    }));
    DOM.btnLoadKbChunks.addEventListener("click", () => loadDiagnosticKnowledgeChunks().catch((error) => {
        Utils.showToast(error.message, "error");
    }));
    DOM.btnLoadChatChunks.addEventListener("click", () => loadDiagnosticChatChunks().catch((error) => {
        Utils.showToast(error.message, "error");
    }));

    DOM.clearKb.addEventListener("click", async () => {
        if (!window.confirm("\u786e\u5b9a\u6e05\u7a7a\u77e5\u8bc6\u5e93\u5417\uff1f")) {
            return;
        }
        try {
            await Utils.request("/api/knowledge/clear", {
                method: "POST",
                body: JSON.stringify({ confirm: true })
            });
            DOM.clearDataResult.style.display = "block";
            DOM.clearDataResult.textContent = "\u77e5\u8bc6\u5e93\u5df2\u6e05\u7a7a";
            await refreshKnowledgeStats();
            await loadKnowledgeChunks().catch(() => {});
        } catch (error) {
            Utils.showToast(error.message, "error");
        }
    });

    DOM.clearChatHistory.addEventListener("click", async () => {
        if (!window.confirm("\u786e\u5b9a\u6e05\u7a7a\u6240\u6709\u5bf9\u8bdd\u5386\u53f2\u548c\u4f1a\u8bdd\u6587\u4ef6\u5417\uff1f")) {
            return;
        }
        try {
            await clearData({ clear_kb: false, clear_chat: true, clear_sessions: true });
        } catch (error) {
            Utils.showToast(error.message, "error");
        }
    });

    DOM.clearAllData.addEventListener("click", async () => {
        if (!window.confirm("\u786e\u5b9a\u6e05\u7a7a\u77e5\u8bc6\u5e93\u3001\u5bf9\u8bdd\u5386\u53f2\u548c\u6240\u6709\u4f1a\u8bdd\u5417\uff1f")) {
            return;
        }
        try {
            await clearData({ clear_kb: true, clear_chat: true, clear_sessions: true });
        } catch (error) {
            Utils.showToast(error.message, "error");
        }
    });

    DOM.ragHelpBtn.addEventListener("click", () => Utils.openModal(DOM.ragHelpModal));
    DOM.closeRagHelp.addEventListener("click", () => Utils.closeModal(DOM.ragHelpModal));

    document.querySelectorAll(".arpm-tab").forEach((button) => {
        button.addEventListener("click", () => switchArpmTab(button.dataset.tab));
    });
    document.querySelectorAll(".delete-tab").forEach((button) => {
        button.addEventListener("click", () => switchDeleteTab(button.dataset.tab));
    });

    document.addEventListener("click", (event) => {
        const regenerate = event.target.closest(".regenerate-msg");
        if (regenerate) {
            regenerateRound(Number(regenerate.dataset.round)).catch(console.error);
            return;
        }

        const deleteMsg = event.target.closest(".delete-msg");
        if (deleteMsg) {
            deleteRound(Number(deleteMsg.dataset.round)).catch(console.error);
            return;
        }

        const deleteKb = event.target.closest(".delete-kb-chunk");
        if (deleteKb) {
            deleteKnowledgeChunk(deleteKb.dataset.chunkId).catch(console.error);
            return;
        }

        const deleteKbDiag = event.target.closest(".delete-kb-diag");
        if (deleteKbDiag) {
            deleteDiagnosticChunk("kb", deleteKbDiag.dataset.chunkId).catch(console.error);
            return;
        }

        const deleteChatDiag = event.target.closest(".delete-chat-diag");
        if (deleteChatDiag) {
            deleteDiagnosticChunk("chat", deleteChatDiag.dataset.chunkId).catch(console.error);
            return;
        }

        // Settings and diagnostic modals intentionally ignore backdrop clicks.
        // This protects long configuration edits from accidental outside clicks.
    });
}

async function init() {
    loadLocalApiConfig();
    syncStateToForm();
    renderTheme();
    renderLanguage();
    updateModelDisplay();
    updateSessionMeta();
    setupSettingsPanels();
    bindEvents();
    buildRagHelp();
    renderAnalysis("");
    renderRagContext(null);
    renderMessages();
    updateSendButtonState();
    await refreshKnowledgeStats();
    await refreshUiState();

    try {
        const sessions = await loadSessions();
        if (sessions.length > 0) {
            const savedSessionId = getSavedCurrentSessionId();
            const restoredSession = sessions.find((item) => item.id === savedSessionId);
            await loadHistory((restoredSession || sessions[0]).id);
            await loadSessions();
        } else {
            createNewSession();
        }
    } catch (error) {
        console.error(error);
        Utils.showToast(`\u521d\u59cb\u5316\u5931\u8d25: ${error.message}`, "error", 4000);
        createNewSession();
    }
}

init().catch((error) => {
    console.error(error);
    Utils.showToast(error.message, "error", 4000);
});



