/**
 * ARPM 对话系统 - 前端核心
 */

// 状态管理
const State = {
    sessionId: null,
    sessionName: null,
    round: 1,
    isGenerating: false,
    abortController: null,
    messages: [], // 当前会话的完整消息记录
    // 自动切分状态
    chunkState: {
        lastChunkedAt: 0,       // 上次切分时间戳
        lastChunkedRound: 0,    // 上次切分时的轮次
        chunkedMessageIds: new Set(), // 已切分的消息ID集合
        totalChunked: 0         // 累计切分次数
    },
    config: {
        apiKey: '',
        baseUrl: 'https://api.deepseek.com',
        model: 'deepseek-chat',
        systemPrompt: '',
        chunkSize: 600,
        topK: 5,
        decayRate: 20,
        // 消融测试配置
        arpmEnabled: true,
        bm25Enabled: true,
        cotRerank: true,
        temporalDecay: true,
        keywordBoost: true,
        // 自动切分配置
        autoChunk: true,
        autoChunkThreshold: 10000
    }
};

// DOM 元素
const DOM = {
    chatContainer: document.getElementById('chat-container'),
    sessionList: document.getElementById('session-list'),
    userInput: document.getElementById('user-input'),
    btnSend: document.getElementById('btn-send'),
    btnStop: document.getElementById('btn-stop'),
    btnClearChat: document.getElementById('btn-clear-chat'),
    statusText: document.getElementById('status-text'),
    roundText: document.getElementById('round-text'),
    ragContent: document.getElementById('rag-content'),
    ragCount: document.getElementById('rag-count'),
    cotContent: document.getElementById('cot-content'),
    
    // 弹窗
    settingsModal: document.getElementById('settings-modal'),
    btnNewChat: document.getElementById('new-chat'),
    btnOpenSettings: document.getElementById('open-settings'),
    btnCloseSettings: document.getElementById('close-settings'),
    btnSaveSettings: document.getElementById('save-settings'),
    
    // 配置表单
    cfgApiKey: document.getElementById('cfg-api-key'),
    cfgBaseUrl: document.getElementById('cfg-base-url'),
    cfgModel: document.getElementById('cfg-model'),
    cfgSystemPrompt: document.getElementById('cfg-system-prompt'),
    cfgChunkSize: document.getElementById('cfg-chunk-size'),
    cfgTopK: document.getElementById('cfg-top-k'),
    cfgDecay: document.getElementById('cfg-decay'),
    
    // 消融测试配置
    cfgArpmEnabled: document.getElementById('cfg-arpm-enabled'),
    cfgBm25Enabled: document.getElementById('cfg-bm25-enabled'),
    cfgCotRerank: document.getElementById('cfg-cot-rerank'),
    cfgTemporalDecay: document.getElementById('cfg-temporal-decay'),
    cfgKeywordBoost: document.getElementById('cfg-keyword-boost'),
    ablationSubitems: document.getElementById('ablation-subitems'),
    
    // 自动切分配置
    cfgAutoChunk: document.getElementById('cfg-auto-chunk'),
    cfgAutoChunkThreshold: document.getElementById('cfg-auto-chunk-threshold'),
    
    // 文件上传
    fileUpload: document.getElementById('file-upload'),
    btnUpload: document.getElementById('upload-file'),
    fileName: document.getElementById('file-name'),
    progressContainer: document.getElementById('progress-container'),
    progressFill: document.getElementById('progress-fill'),
    progressText: document.getElementById('progress-text'),
    kbCount: document.getElementById('kb-count'),
    
    // API测试
    btnTestApi: document.getElementById('test-api'),
    testResult: document.getElementById('test-result'),
    
    // Toast
    toastContainer: document.getElementById('toast-container'),
    
    // 知识库管理
    btnManageKb: document.getElementById('manage-kb'),
    kbModal: document.getElementById('kb-modal'),
    btnCloseKb: document.getElementById('close-kb'),
    kbList: document.getElementById('kb-list'),
    kbSearch: document.getElementById('kb-search'),
    kbFilter: document.getElementById('kb-filter'),
    
    // 条件编辑
    conditionModal: document.getElementById('condition-modal'),
    btnCloseCondition: document.getElementById('close-condition'),
    condEnabled: document.getElementById('cond-enabled'),
    condLogic: document.getElementById('cond-logic'),
    condRules: document.getElementById('cond-rules'),
    btnAddRule: document.getElementById('add-rule'),
    btnSaveCondition: document.getElementById('save-condition'),
    
    // 关键词编辑
    keywordModal: document.getElementById('keyword-modal'),
    btnCloseKeyword: document.getElementById('close-keyword'),
    keywordList: document.getElementById('keyword-list'),
    btnAddKeyword: document.getElementById('add-keyword'),
    btnSaveKeywords: document.getElementById('save-keywords'),
    
    // 怀旧模式编辑
    nostalgiaModal: document.getElementById('nostalgia-modal'),
    btnCloseNostalgia: document.getElementById('close-nostalgia'),
    nostalgiaEnabled: document.getElementById('nostalgia-enabled'),
    nostalgiaFactor: document.getElementById('nostalgia-factor'),
    btnSaveNostalgia: document.getElementById('save-nostalgia'),
    
    // 场景管理
    sceneModal: document.getElementById('scene-modal'),
    btnCloseScene: document.getElementById('close-scene'),
    btnNewScene: document.getElementById('new-scene'),
    sceneList: document.getElementById('scene-list'),
    btnSaveScene: document.getElementById('save-scene'),
    sceneStartRound: document.getElementById('scene-start-round'),
    sceneEndRound: document.getElementById('scene-end-round'),
    sceneTitle: document.getElementById('scene-title'),
    sceneSummary: document.getElementById('scene-summary'),
    
    // 诊断
    diagModal: document.getElementById('diag-modal'),
    btnCloseDiag: document.getElementById('close-diag'),
    btnRunDiag: document.getElementById('run-diag'),
    btnRunDiagFix: document.getElementById('run-diag-fix'),
    diagResults: document.getElementById('diag-results')
};

// 工具函数
const Utils = {
    generateId() {
        const now = new Date();
        const dateStr = now.getFullYear().toString().slice(-2) +
            String(now.getMonth() + 1).padStart(2, '0') +
            String(now.getDate()).padStart(2, '0');
        const timeStr = String(now.getHours()).padStart(2, '0') +
            String(now.getMinutes()).padStart(2, '0');
        const random = Math.random().toString(36).substring(2, 5).toUpperCase();
        return `${dateStr}-${timeStr}-${random}`;
    },

    formatTime(date = new Date()) {
        const h = date.getHours().toString().padStart(2, '0');
        const m = date.getMinutes().toString().padStart(2, '0');
        return `${h}:${m}`;
    },

    formatDateTime(date = new Date()) {
        const m = date.getMonth() + 1;
        const d = date.getDate();
        const h = date.getHours().toString().padStart(2, '0');
        const min = date.getMinutes().toString().padStart(2, '0');
        return `${m}月${d}日 ${h}:${min}`;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    parseMarkdown(text) {
        if (!text) return '';
        
        // 代码块
        text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        
        // 行内代码
        text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // 粗体
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        
        // 斜体
        text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        
        // 换行
        text = text.replace(/\n/g, '<br>');
        
        return text;
    },

    parseResponse(text) {
        if (!text) return { analysis: '', response: '' };
        
        const originalText = text.trim();
        
        // 策略1: 匹配 XML 标签格式 <analysis>...</analysis> <response>...</response>
        const analysisMatch = originalText.match(/<analysis>([\s\S]*?)<\/analysis>/i);
        const responseMatch = originalText.match(/<response>([\s\S]*?)<\/response>/i);
        
        if (analysisMatch || responseMatch) {
            return {
                analysis: analysisMatch ? analysisMatch[1].trim() : '',
                response: responseMatch ? responseMatch[1].trim() : originalText.replace(/<analysis>[\s\S]*?<\/analysis>/gi, '').trim()
            };
        }
        
        // 策略2: 检测显式思维链格式并提取实际回复
        // 思维链通常以数字编号或特定关键词开头，实际回复以动作描写（括号）或对话开始
        
        // 先尝试找以动作/对话开头的部分（通常是回复）
        // 匹配：（动作描写）或"对话内容"或直接对话
        const actionPatterns = [
            /([（(（][^）)）]*[）)）][^\n]*)/,  // （动作描写）
            /([""""][^""""]+[""""][^\n]*)/,      // "对话内容"
            /((?:\n|^)[\u4e00-\u9fa5]+[，。！？][^\n]{10,})/,  // 纯中文句子（较长）
        ];
        
        // 策略3: 识别思维链分隔符
        // 思维链通常包含：记忆评估、知识排序、推理过程、分析、思考等关键词
        const thoughtKeywords = /(?:^|\n)(?:\d+[\.．]\s*|\*\s*|\-\s*)?(?:记忆评估|知识排序|推理过程|思考过程|分析过程|详细分析|思考|分析|评估|排序|推理)[：:\s]/i;
        const dividerPattern = /(?:\n\s*\n|\n\s*[\-—]{3,}\s*\n)/; // 空行或分隔线
        
        // 如果检测到思维链关键词
        if (thoughtKeywords.test(originalText)) {
            // 尝试找分隔符后的内容
            const parts = originalText.split(dividerPattern);
            if (parts.length >= 2) {
                // 最后一部分通常是实际回复
                const lastPart = parts[parts.length - 1].trim();
                const otherParts = parts.slice(0, -1).join('\n\n').trim();
                
                // 验证最后一部分是否像回复（不以思维关键词开头）
                if (!thoughtKeywords.test(lastPart.substring(0, 50))) {
                    return {
                        analysis: otherParts,
                        response: lastPart
                    };
                }
            }
            
            // 尝试从动作描写处分割
            for (const pattern of actionPatterns) {
                const match = originalText.match(pattern);
                if (match) {
                    const actionIndex = originalText.indexOf(match[1]);
                    if (actionIndex > 0) {
                        const thoughtPart = originalText.substring(0, actionIndex).trim();
                        const replyPart = originalText.substring(actionIndex).trim();
                        
                        // 确保思维部分确实包含关键词
                        if (thoughtKeywords.test(thoughtPart)) {
                            return {
                                analysis: thoughtPart,
                                response: replyPart
                            };
                        }
                    }
                }
            }
        }
        
        // 策略4: 处理 DeepSeek-R1 等模型的 <think>...</think> 标签
        const thinkMatch = originalText.match(/<think>([\s\S]*?)<\/think>/i);
        if (thinkMatch) {
            const thought = thinkMatch[1].trim();
            const reply = originalText.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
            return {
                analysis: thought,
                response: reply || originalText
            };
        }
        
        // 策略5: 通用 fallback - 如果文本很长且包含换行，尝试提取最后一段
        if (originalText.length > 200 && originalText.includes('\n')) {
            const lines = originalText.split('\n');
            // 找最后一个非空行
            for (let i = lines.length - 1; i >= 0; i--) {
                const line = lines[i].trim();
                if (line.length > 10 && !thoughtKeywords.test(line)) {
                    // 检查这一行及之后的内容
                    const potentialReply = lines.slice(i).join('\n').trim();
                    const thoughtPart = lines.slice(0, i).join('\n').trim();
                    
                    if (potentialReply.length > 20) {
                        return {
                            analysis: thoughtPart,
                            response: potentialReply
                        };
                    }
                }
            }
        }
        
        // 默认返回原始文本作为回复，无分析
        return {
            analysis: '',
            response: originalText
        };
    },

    // 导出对话为txt格式
    exportToTxt(messages, sessionName) {
        let content = `ARPM 对话记录\n`;
        content += `会话: ${sessionName}\n`;
        content += `导出时间: ${new Date().toLocaleString()}\n`;
        content += `=${'='.repeat(50)}\n\n`;
        
        messages.forEach((msg, i) => {
            const role = msg.role === 'user' ? '用户' : '助手';
            const time = msg.time || '';
            content += `[${role}] ${time}\n`;
            content += `${msg.content}\n\n`;
        });
        
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `对话记录_${sessionName}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
};

// 存储
const Storage = {
    saveConfig(config) {
        try {
            localStorage.setItem('arpm_config', JSON.stringify(config));
        } catch (e) {
            console.error('保存配置失败:', e);
        }
    },

    loadConfig() {
        try {
            const data = localStorage.getItem('arpm_config');
            return data ? JSON.parse(data) : null;
        } catch (e) {
            console.error('加载配置失败:', e);
            return null;
        }
    }
};

// API
const API = {
    async request(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.message || `请求失败 (${response.status})`);
        }
        
        return response.json();
    },

    async sendMessage(data, signal) {
        return this.request('/api/chat', {
            method: 'POST',
            body: JSON.stringify(data),
            signal
        });
    },

    async saveHistory(sessionId, messages) {
        return this.request('/api/history', {
            method: 'POST',
            body: JSON.stringify({ session_id: sessionId, messages })
        });
    },

    async getHistory(sessionId) {
        return this.request(`/api/history/${sessionId}`);
    },

    async testConnection(data) {
        return this.request('/api/test', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async uploadBatch(chunks) {
        return this.request('/api/upload_batch', {
            method: 'POST',
            body: JSON.stringify({ chunks })
        });
    },

    async getKnowledge() {
        return this.request('/api/knowledge');
    },

    async getSessions() {
        return this.request('/api/sessions');
    },

    // 知识库管理
    async getKnowledge() {
        return this.request('/api/knowledge');
    },

    async deleteKnowledge(idx) {
        return this.request(`/api/knowledge?index=${idx}`, {
            method: 'DELETE'
        });
    },

    async setTemporallyBlind(idx, blind) {
        return this.request(`/api/knowledge/${idx}/blind`, {
            method: blind ? 'POST' : 'DELETE',
            body: JSON.stringify({ blind })
        });
    },

    async getConditions(idx) {
        return this.request(`/api/knowledge/${idx}/conditions`);
    },

    async setConditions(idx, conditions) {
        return this.request(`/api/knowledge/${idx}/conditions`, {
            method: 'POST',
            body: JSON.stringify({ conditions })
        });
    },

    async deleteConditions(idx) {
        return this.request(`/api/knowledge/${idx}/conditions`, {
            method: 'DELETE'
        });
    },

    // 关键词管理
    async getKeywords(idx) {
        return this.request(`/api/knowledge/${idx}/keywords`);
    },

    async setKeywords(idx, keywords) {
        return this.request(`/api/knowledge/${idx}/keywords`, {
            method: 'POST',
            body: JSON.stringify({ keywords })
        });
    },

    // 怀旧模式
    async getNostalgia(idx) {
        return this.request(`/api/knowledge/${idx}/nostalgia`);
    },

    async setNostalgia(idx, enabled, factor) {
        return this.request(`/api/knowledge/${idx}/nostalgia`, {
            method: 'POST',
            body: JSON.stringify({ enabled, factor })
        });
    },

    // 场景管理
    async getScenes() {
        return this.request('/api/scenes');
    },

    async createScene(data) {
        return this.request('/api/scenes', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async deleteScene(sceneId) {
        return this.request(`/api/scenes/${sceneId}`, {
            method: 'DELETE'
        });
    },

    // 诊断
    async runDiagnostics(autoFix = false) {
        return this.request('/api/diagnostics', {
            method: 'POST',
            body: JSON.stringify({ auto_fix: autoFix })
        });
    },

    // 获取 chunk 详情
    async getChunkDetail(idx) {
        return this.request(`/api/knowledge/${idx}`);
    }
};

// UI
const UI = {
    toast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        DOM.toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(20px)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    setStatus(text, type = '') {
        DOM.statusText.textContent = text;
        DOM.statusText.className = type;
    },

    setRound(round) {
        State.round = round;
        DOM.roundText.textContent = `第 ${round} 轮`;
    },

    setGenerating(generating) {
        State.isGenerating = generating;
        
        if (generating) {
            DOM.btnSend.style.display = 'none';
            DOM.btnStop.style.display = 'flex';
            DOM.userInput.disabled = true;
        } else {
            DOM.btnSend.style.display = 'flex';
            DOM.btnStop.style.display = 'none';
            DOM.userInput.disabled = false;
            DOM.userInput.focus();
            this.updateSendButton();
        }
    },

    updateSendButton() {
        const hasContent = DOM.userInput.value.trim().length > 0;
        DOM.btnSend.disabled = !hasContent || State.isGenerating;
    },

    // 渲染消息到界面（不保存到State）
    renderMessage(role, content, time, options = {}) {
        const welcome = document.getElementById('welcome');
        if (welcome) welcome.remove();
        
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;
        
        // 生成消息唯一ID
        const messageId = options.timestamp || Date.now();
        msgDiv.dataset.messageId = messageId;
        msgDiv.dataset.role = role;
        
        const avatarText = role === 'user' ? '用' : 'AI';
        const parsedContent = role === 'assistant' 
            ? Utils.parseMarkdown(content) 
            : Utils.escapeHtml(content);
        
        const timeStr = time || Utils.formatTime();
        
        // AI消息添加反馈按钮，用户消息添加删除按钮
        const actionHtml = role === 'assistant' ? `
            <div class="message-feedback">
                <button class="feedback-btn like" onclick="FeedbackManager.handleLike(${messageId}, this)" title="喜欢这类回复">
                    👍 有用
                </button>
                <button class="feedback-btn dislike" onclick="FeedbackManager.handleDislike(${messageId}, this)" title="不喜欢这类回复">
                    👎 无用
                </button>
                <button class="feedback-btn report" onclick="FeedbackManager.openReport(${messageId}, '${Utils.escapeHtml(content).replace(/'/g, "\\'")}')" title="内容不合规">
                    🚫 举报
                </button>
                <button class="feedback-btn delete-msg" onclick="Chat.deleteMessage(${messageId})" title="删除此消息">
                    🗑️ 删除
                </button>
                <span class="feedback-status"></span>
            </div>
        ` : `
            <div class="message-feedback">
                <button class="feedback-btn delete-msg" onclick="Chat.deleteMessage(${messageId})" title="删除此消息">
                    🗑️ 删除
                </button>
                <span class="feedback-status"></span>
            </div>
        `;
        
        msgDiv.innerHTML = `
            <div class="message-content-wrapper">
                <div class="message-avatar">${avatarText}</div>
                <div class="message-body">
                    <div class="message-header">${role === 'user' ? '用户' : '助手'}</div>
                    <div class="message-text">${parsedContent}</div>
                    ${actionHtml}
                </div>
            </div>
        `;
        
        DOM.chatContainer.appendChild(msgDiv);
        this.scrollToBottom();
        
        return msgDiv;
    },

    // 添加新消息（同时保存到State）
    addMessage(role, content) {
        const time = Utils.formatTime();
        const timestamp = Date.now();
        
        // 保存到状态
        State.messages.push({
            role: role,
            content: content,
            time: time,
            timestamp: timestamp
        });
        
        // 渲染到界面
        this.renderMessage(role, content, time, { timestamp });
        
        // 异步保存到后端
        if (State.sessionId) {
            API.saveHistory(State.sessionId, State.messages).catch(e => {
                console.error('保存历史失败:', e);
            });
        }
    },

    // 加载历史消息
    loadHistory(messages) {
        // 清空当前显示
        DOM.chatContainer.innerHTML = '';
        
        if (!messages || messages.length === 0) {
            DOM.chatContainer.innerHTML = `
                <div class="welcome" id="welcome">
                    <h1>ARPM 智能对话系统</h1>
                    <p>基于异步轮次管理与检索增强生成技术</p>
                </div>
            `;
            return;
        }
        
        // 渲染所有历史消息
        messages.forEach(msg => {
            this.renderMessage(msg.role, msg.content, msg.time, { 
                timestamp: msg.timestamp || Date.now() 
            });
        });
    },

    addTypingIndicator() {
        const id = 'typing-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message assistant';
        msgDiv.id = id;
        
        msgDiv.innerHTML = `
            <div class="message-content-wrapper">
                <div class="message-avatar">AI</div>
                <div class="message-body">
                    <div class="message-header">助手</div>
                    <div class="typing">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        
        const welcome = document.getElementById('welcome');
        if (welcome) welcome.remove();
        
        DOM.chatContainer.appendChild(msgDiv);
        this.scrollToBottom();
        
        return id;
    },

    removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    },

    scrollToBottom() {
        DOM.chatContainer.scrollTop = DOM.chatContainer.scrollHeight;
    },

    updateRag(contexts) {
        DOM.ragCount.textContent = contexts ? contexts.length : 0;
        
        if (!contexts || contexts.length === 0) {
            DOM.ragContent.innerHTML = '<div class="empty">无检索结果</div>';
            return;
        }
        
        DOM.ragContent.innerHTML = contexts.map((ctx, i) => `
            <div class="rag-item">
                <span class="rag-index">#${i + 1}</span>
                <div class="rag-text">${Utils.escapeHtml(ctx.substring(0, 120))}${ctx.length > 120 ? '...' : ''}</div>
            </div>
        `).join('');
    },

    updateCot(analysis) {
        if (!analysis || analysis.trim().length === 0) {
            DOM.cotContent.innerHTML = '<div class="empty">等待分析...</div>';
            return;
        }
        
        const steps = analysis.split(/\n/).filter(line => line.trim());
        
        DOM.cotContent.innerHTML = steps.map((step, i) => {
            const cleanStep = step.trim().replace(/^\d+[.\s]+/, '');
            if (!cleanStep) return '';
            return `
                <div class="cot-step">
                    <span class="cot-step-num">${i + 1}</span>
                    <span class="cot-step-text">${Utils.escapeHtml(cleanStep)}</span>
                </div>
            `;
        }).join('');
    },

    renderSessions(sessions) {
        if (!sessions || sessions.length === 0) {
            DOM.sessionList.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-tertiary); font-size: 13px;">暂无历史会话</div>';
            return;
        }
        
        DOM.sessionList.innerHTML = sessions.map(s => `
            <div class="session-item ${s.id === State.sessionId ? 'active' : ''}" data-id="${s.id}" title="${s.name}">
                <span class="session-name">${s.display_name || s.name}</span>
                <button class="btn-export" data-id="${s.id}" title="导出">⬇</button>
            </div>
        `).join('');
        
        // 绑定会话切换事件
        DOM.sessionList.querySelectorAll('.session-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.classList.contains('btn-export')) {
                    e.stopPropagation();
                    Session.export(item.dataset.id);
                } else {
                    Session.switch(item.dataset.id);
                }
            });
        });
    },

    updateProgress(percent, text) {
        DOM.progressFill.style.width = percent + '%';
        DOM.progressText.textContent = text || percent + '%';
    },

    showProgress() {
        DOM.progressContainer.style.display = 'flex';
    },

    hideProgress() {
        DOM.progressContainer.style.display = 'none';
        DOM.progressFill.style.width = '0%';
        DOM.progressText.textContent = '0%';
    },

    openSettings() {
        const cfg = State.config;
        DOM.cfgApiKey.value = cfg.apiKey || '';
        DOM.cfgBaseUrl.value = cfg.baseUrl || '';
        DOM.cfgModel.value = cfg.model || '';
        DOM.cfgSystemPrompt.value = cfg.systemPrompt || '';
        DOM.cfgChunkSize.value = cfg.chunkSize || 600;
        DOM.cfgTopK.value = cfg.topK || 5;
        DOM.cfgDecay.value = cfg.decayRate || 20;
        
        // 消融测试配置
        DOM.cfgArpmEnabled.checked = cfg.arpmEnabled !== false;
        DOM.cfgBm25Enabled.checked = cfg.bm25Enabled !== false;
        DOM.cfgCotRerank.checked = cfg.cotRerank !== false;
        DOM.cfgTemporalDecay.checked = cfg.temporalDecay !== false;
        DOM.cfgKeywordBoost.checked = cfg.keywordBoost !== false;
        
        // 自动切分配置
        DOM.cfgAutoChunk.checked = cfg.autoChunk !== false;
        DOM.cfgAutoChunkThreshold.value = cfg.autoChunkThreshold || 10000;
        
        // 更新子组件状态
        this.updateAblationSubitems();
        
        DOM.settingsModal.classList.add('show');
    },

    closeSettings() {
        DOM.settingsModal.classList.remove('show');
    },
    
    updateAblationSubitems() {
        const arpmEnabled = DOM.cfgArpmEnabled?.checked;
        const subitems = DOM.ablationSubitems;
        if (subitems) {
            if (arpmEnabled) {
                subitems.classList.remove('disabled');
            } else {
                subitems.classList.add('disabled');
            }
        }
    }
};

// 会话管理
const Session = {
    create() {
        State.sessionId = null;
        State.sessionName = null;
        State.messages = [];
        // 重置切分状态
        State.chunkState = {
            lastChunkedAt: 0,
            lastChunkedRound: 0,
            chunkedMessageIds: new Set(),
            totalChunked: 0
        };
        UI.setRound(1);
        
        DOM.chatContainer.innerHTML = `
            <div class="welcome" id="welcome">
                <h1>ARPM 智能对话系统</h1>
                <p>基于异步轮次管理与检索增强生成技术</p>
            </div>
        `;
        
        DOM.ragContent.innerHTML = '<div class="empty">等待检索...</div>';
        DOM.ragCount.textContent = '0';
        DOM.cotContent.innerHTML = '<div class="empty">等待分析...</div>';
        
        UI.setStatus('就绪');
        this.refreshList();
        UI.toast('新对话已创建');
    },

    async switch(sessionId) {
        if (!sessionId || sessionId === State.sessionId) return;
        
        try {
            // 获取会话历史
            const data = await API.getHistory(sessionId);
            
            State.sessionId = sessionId;
            State.sessionName = data.session_name || sessionId;
            State.messages = data.messages || [];
            
            // 重置切分状态（新会话）
            State.chunkState = {
                lastChunkedAt: 0,
                lastChunkedRound: 0,
                chunkedMessageIds: new Set(),
                totalChunked: 0
            };
            
            // 加载历史消息到界面
            UI.loadHistory(State.messages);
            
            // 设置轮次
            const lastRound = data.last_round || 1;
            UI.setRound(lastRound + 1);
            
            // 检查加载的历史消息长度
            const loadedContextLength = State.messages.map(m => m.content).join('\n').length;
            console.log(`[切换会话] 已加载 ${State.messages.length} 条消息，共 ${loadedContextLength} 字符`);
            
            UI.toast(`已加载会话: ${State.sessionName}`);
            this.refreshList();
            
        } catch (e) {
            console.error('加载会话失败:', e);
            UI.toast('加载会话失败: ' + e.message, 'error');
        }
    },

    async export(sessionId) {
        try {
            const data = await API.getHistory(sessionId);
            const messages = data.messages || [];
            const sessionName = data.session_name || sessionId;
            
            if (messages.length === 0) {
                UI.toast('该会话无内容可导出', 'error');
                return;
            }
            
            Utils.exportToTxt(messages, sessionName);
            UI.toast('已导出对话记录');
        } catch (e) {
            console.error('导出失败:', e);
            UI.toast('导出失败: ' + e.message, 'error');
        }
    },

    async refreshList() {
        try {
            const sessions = await API.getSessions();
            UI.renderSessions(sessions);
        } catch (e) {
            console.error('获取会话列表失败:', e);
        }
    }
};

// 聊天逻辑
const Chat = {
    init() {
        DOM.userInput.addEventListener('input', () => {
            DOM.userInput.style.height = 'auto';
            DOM.userInput.style.height = Math.min(DOM.userInput.scrollHeight, 200) + 'px';
            UI.updateSendButton();
        });

        DOM.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!DOM.btnSend.disabled) this.send();
            }
        });

        DOM.btnSend.addEventListener('click', () => this.send());
        DOM.btnStop.addEventListener('click', () => this.stop());
        DOM.btnClearChat?.addEventListener('click', () => this.showClearConfirm());
        
        // 绑定清空确认弹窗事件
        document.getElementById('cancel-clear-chat')?.addEventListener('click', () => this.hideClearConfirm());
        document.getElementById('confirm-clear-chat')?.addEventListener('click', () => this.confirmClearChat());
        document.getElementById('clear-chat-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'clear-chat-modal') this.hideClearConfirm();
        });
    },
    
    // 显示清空确认弹窗
    showClearConfirm() {
        if (!State.sessionId || State.messages.length === 0) {
            UI.toast('当前没有聊天记录', 'info');
            return;
        }
        
        // 更新弹窗信息
        document.getElementById('clear-chat-session-name').textContent = State.sessionName || '当前会话';
        document.getElementById('clear-chat-msg-count').textContent = State.messages.length;
        
        // 显示弹窗
        document.getElementById('clear-chat-modal').classList.add('show');
    },
    
    // 隐藏清空确认弹窗
    hideClearConfirm() {
        document.getElementById('clear-chat-modal').classList.remove('show');
    },
    
    // 确认清空聊天记录
    async confirmClearChat() {
        this.hideClearConfirm();
        
        if (!State.sessionId) return;
        
        try {
            // 清空前端状态
            State.messages = [];
            State.round = 1;
            UI.setRound(1);
            
            // 清空界面
            DOM.chatContainer.innerHTML = `
                <div class="welcome" id="welcome">
                    <h1>ARPM 智能对话系统</h1>
                    <p>基于异步轮次管理与检索增强生成技术</p>
                    <p style="color: var(--text-tertiary); margin-top: 12px; font-size: 13px;">聊天记录已清空</p>
                </div>
            `;
            
            // 清空后端存储
            await API.saveHistory(State.sessionId, []);
            
            // 重置切分状态
            State.chunkState = {
                lastChunkedAt: 0,
                lastChunkedRound: 0,
                chunkedMessageIds: new Set(),
                totalChunked: 0
            };
            
            UI.toast('✅ 聊天记录已清空', 'success');
            console.log(`[清空记录] 会话 ${State.sessionId} 的聊天记录已清空`);
            
        } catch (e) {
            console.error('[清空记录] 失败:', e);
            UI.toast('清空失败: ' + e.message, 'error');
        }
    },
    
    // 删除单条消息
    async deleteMessage(messageId) {
        const msgIndex = State.messages.findIndex(m => m.timestamp === messageId);
        if (msgIndex < 0) return;
        
        const msg = State.messages[msgIndex];
        
        // 二次确认（简单确认）
        if (!confirm(`确定要删除这条${msg.role === 'user' ? '用户' : '助手'}消息吗？`)) {
            return;
        }
        
        try {
            // 从状态中删除
            State.messages.splice(msgIndex, 1);
            
            // 从界面删除
            const msgDiv = document.querySelector(`[data-message-id="${messageId}"]`);
            if (msgDiv) {
                msgDiv.style.opacity = '0';
                msgDiv.style.transform = 'translateX(20px)';
                setTimeout(() => msgDiv.remove(), 300);
            }
            
            // 更新后端存储
            if (State.sessionId) {
                await API.saveHistory(State.sessionId, State.messages);
            }
            
            console.log(`[删除消息] 消息ID ${messageId} 已删除`);
            
        } catch (e) {
            console.error('[删除消息] 失败:', e);
            UI.toast('删除失败: ' + e.message, 'error');
        }
    },

    async send() {
        const content = DOM.userInput.value.trim();
        if (!content || State.isGenerating) return;

        if (!State.config.apiKey) {
            UI.toast('请先配置 API 密钥', 'error');
            UI.openSettings();
            return;
        }

        // 如果是新会话，生成会话ID
        if (!State.sessionId) {
            State.sessionId = Utils.generateId();
            State.sessionName = Utils.formatDateTime();
            // 保存初始会话信息
            await API.saveHistory(State.sessionId, []).catch(() => {});
        }
        
        // [会话隔离验证] 确保使用的是当前会话的消息
        const currentSessionId = State.sessionId;
        const currentMessageCount = State.messages.length;
        console.log(`[会话隔离] 会话ID: ${currentSessionId}, 消息数: ${currentMessageCount}`);
        
        // 检查是否需要自动切分上下文
        // 新策略：保留所有上下文，只切分新增到知识库，用ID标记防止重复
        const threshold = State.config.autoChunkThreshold || 10000;
        
        // 获取未切分的消息（排除已切分的）
        const unchunkedMessages = State.messages.filter(m => 
            m.role === 'assistant' && !State.chunkState.chunkedMessageIds.has(m.timestamp)
        );
        
        // 计算未切分内容的总长度
        const unchunkedLength = unchunkedMessages.map(m => m.content).join('\n').length;
        const currentContextLength = State.messages.map(m => m.content).join('\n').length + content.length;
        
        const now = Date.now();
        const timeSinceLastChunk = now - State.chunkState.lastChunkedAt;
        
        // 切分条件：未切分内容超过阈值，且满足防抖
        const shouldChunk = State.config.autoChunk !== false && 
                           unchunkedLength >= threshold &&  // 未切分内容超过阈值
                           timeSinceLastChunk > 60000;      // 60秒内不重复切分
        
        console.log(`[自动切分检查] 未切分: ${unchunkedLength}字符, 总计: ${currentContextLength}字符, 阈值: ${threshold}`);
        
        if (shouldChunk) {
            console.log(`[自动切分] 触发条件满足，开始切分 ${unchunkedMessages.length} 条未切分消息`);
            UI.toast(`📝 检测到 ${unchunkedMessages.length} 条新回复可归档，正在处理...`, 'info');
            
            const chunkedCount = await this.autoChunkContext(unchunkedMessages);
            
            if (chunkedCount > 0) {
                // 更新切分记录
                State.chunkState.lastChunkedAt = Date.now();
                State.chunkState.lastChunkedRound = State.round;
                State.chunkState.totalChunked += chunkedCount;
                
                // 标记已切分的消息
                unchunkedMessages.forEach(m => {
                    State.chunkState.chunkedMessageIds.add(m.timestamp);
                });
                
                console.log(`[自动切分] 完成，已归档 ${chunkedCount} 条，累计 ${State.chunkState.totalChunked} 条`);
                UI.toast(`✅ 已自动归档 ${chunkedCount} 条回复到知识库（上下文保留）`, 'success');
            }
        }

        // 添加用户消息（会保存到State和后端）
        UI.addMessage('user', content);
        
        DOM.userInput.value = '';
        DOM.userInput.style.height = 'auto';
        UI.updateSendButton();

        UI.setGenerating(true);
        UI.setStatus('正在生成...', 'processing');

        State.abortController = new AbortController();
        const typingId = UI.addTypingIndicator();
        
        // [会话隔离验证] 发送前再次验证会话未变更
        if (currentSessionId !== State.sessionId) {
            console.error(`[会话隔离警告] 会话已变更! 原: ${currentSessionId}, 新: ${State.sessionId}`);
            UI.toast('会话已变更，请重新发送', 'error');
            UI.removeTypingIndicator(typingId);
            UI.setGenerating(false);
            return;
        }

        try {
            console.log(`[API请求] 会话: ${State.sessionId}, 当前消息数: ${State.messages.length}`);
            
            const response = await API.sendMessage({
                message: content,
                session_id: State.sessionId,
                round: State.round,
                api_config: {
                    api_key: State.config.apiKey,
                    base_url: State.config.baseUrl,
                    model: State.config.model
                },
                system_prompt: State.config.systemPrompt,
                params: {
                    top_k: State.config.topK,
                    decay_rate: State.config.decayRate,
                    // 消融测试配置
                    arpm_enabled: State.config.arpmEnabled,
                    bm25_enabled: State.config.bm25Enabled,
                    cot_rerank: State.config.cotRerank,
                    temporal_decay: State.config.temporalDecay,
                    keyword_boost: State.config.keywordBoost
                }
            }, State.abortController.signal);

            UI.removeTypingIndicator(typingId);

            if (response.session_id) {
                State.sessionId = response.session_id;
            }

            UI.updateRag(response.rag_context);

            const { analysis, response: replyText } = Utils.parseResponse(response.reply);

            UI.updateCot(analysis);

            if (State.round === 1 && response.status === 'stored') {
                UI.addMessage('assistant', '首轮分析完成，背景知识已存入记忆。请继续第二轮对话获取完整回复。');
            } else {
                UI.addMessage('assistant', replyText);
            }

            UI.setRound(State.round + 1);
            Session.refreshList();
            UI.setStatus('完成', 'success');

        } catch (error) {
            UI.removeTypingIndicator(typingId);
            
            if (error.name === 'AbortError') {
                UI.addMessage('assistant', '生成已取消');
                UI.setStatus('已取消');
            } else {
                console.error('发送失败:', error);
                UI.addMessage('assistant', `错误：${error.message}`);
                UI.setStatus('发送失败', 'error');
                UI.toast(error.message, 'error');
            }
        } finally {
            UI.setGenerating(false);
            State.abortController = null;
        }
    },

    stop() {
        if (State.abortController) {
            State.abortController.abort();
        }
    },
    
    /**
     * 自动切分上下文到知识库
     * 新策略：保留所有上下文，只将内容归档到知识库，不删除messages
     * @param {Array} messagesToChunk - 需要切分的消息列表
     * @returns {number} - 成功切分的消息数
     */
    async autoChunkContext(messagesToChunk) {
        try {
            if (!messagesToChunk || messagesToChunk.length === 0) {
                console.log('[自动切分] 没有需要切分的消息');
                return 0;
            }
            
            console.log(`[自动切分] 待切分消息数: ${messagesToChunk.length}`);
            
            // 只切分AI回复（assistant角色）
            const assistantMessages = messagesToChunk.filter(m => m.role === 'assistant');
            
            // 构建要切分的文本（每条AI回复作为一个文档）
            const chunks = assistantMessages.map((m, idx) => ({
                text: m.content,
                metadata: {
                    timestamp: Date.now() / 1000,
                    source: `对话归档_${State.sessionId}_轮次${State.round}`,
                    length: m.content.length,
                    session_id: State.sessionId,
                    round: State.round,
                    message_timestamp: m.timestamp,
                    auto_chunked: true,  // 标记为自动切分
                    chunk_index: idx
                }
            })).filter(c => c.text.length > 50); // 过滤太短的回复
            
            if (chunks.length === 0) {
                console.log('[自动切分] 没有符合要求的内容');
                return 0;
            }
            
            console.log(`[自动切分] 生成 ${chunks.length} 个片段`);
            
            // 批量上传
            await Upload.uploadBatches(chunks);
            
            // 更新知识库统计
            await Upload.updateStats();
            
            return chunks.length;
        } catch (e) {
            console.error('[自动切分] 失败:', e);
            UI.toast('自动归档失败: ' + e.message, 'error');
            return 0;
        }
    }
};

// 文件上传
const Upload = {
    init() {
        DOM.btnUpload.addEventListener('click', () => DOM.fileUpload.click());
        DOM.fileUpload.addEventListener('change', (e) => this.handleFile(e));
    },

    async handleFile(e) {
        const file = e.target.files[0];
        if (!file) return;

        const ext = '.' + file.name.split('.').pop().toLowerCase();
        const allowed = ['.txt', '.md', '.json'];
        
        if (!allowed.includes(ext)) {
            UI.toast('仅支持 .txt .md .json 文件', 'error');
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            UI.toast('文件大小不能超过 5MB', 'error');
            return;
        }

        DOM.fileName.textContent = file.name;
        UI.showProgress();
        UI.updateProgress(10, '读取中...');

        try {
            const text = await this.readFile(file);
            UI.updateProgress(30, '分块中...');

            const chunks = this.chunkText(text, file.name);
            UI.updateProgress(50, `分块完成 (${chunks.length}个)`);

            await this.uploadBatches(chunks);

            UI.updateProgress(100, '完成');
            UI.toast(`成功导入 ${chunks.length} 个片段`);
            
            this.updateStats();

            setTimeout(() => {
                UI.hideProgress();
                DOM.fileName.textContent = '';
            }, 1500);

        } catch (error) {
            console.error('上传失败:', error);
            UI.toast('上传失败: ' + error.message, 'error');
            UI.hideProgress();
        }

        DOM.fileUpload.value = '';
    },

    readFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = () => reject(new Error('文件读取失败'));
            reader.readAsText(file);
        });
    },

    chunkText(text, source) {
        const chunkSize = parseInt(DOM.cfgChunkSize.value) || 600;
        const sentences = text.split(/(?<=[。！？；.!?;\n])\s*/).filter(s => s.trim());
        const chunks = [];
        const timestamp = Date.now() / 1000;

        let i = 0;
        while (i < sentences.length) {
            let chunk = '';
            let j = i;

            while (j < sentences.length && chunk.length + sentences[j].length <= chunkSize) {
                chunk += sentences[j];
                j++;
            }

            if (!chunk && sentences[i]) {
                chunk = sentences[i].slice(0, chunkSize);
                j = i + 1;
            }

            if (chunk) {
                chunks.push({
                    text: chunk.trim(),
                    metadata: {
                        timestamp,
                        source,
                        length: chunk.length
                    }
                });
            }

            i = j < sentences.length ? Math.max(i + 1, j - 1) : j;
        }

        return chunks;
    },

    async uploadBatches(chunks) {
        const batchSize = 50;
        const total = chunks.length;
        let uploaded = 0;

        for (let i = 0; i < chunks.length; i += batchSize) {
            const batch = chunks.slice(i, i + batchSize);
            await API.uploadBatch(batch);
            uploaded += batch.length;
            
            const progress = 50 + Math.floor((uploaded / total) * 50);
            UI.updateProgress(progress, `上传中 ${uploaded}/${total}`);
        }
    },

    async updateStats() {
        try {
            const data = await API.getKnowledge();
            DOM.kbCount.textContent = data.total_chunks || 0;
        } catch (e) {
            console.error('获取统计失败:', e);
        }
    }
};

// 设置
const Settings = {
    init() {
        DOM.btnOpenSettings.addEventListener('click', () => UI.openSettings());
        DOM.btnCloseSettings.addEventListener('click', () => UI.closeSettings());
        DOM.btnSaveSettings.addEventListener('click', () => this.save());
        DOM.btnTestApi.addEventListener('click', () => this.testApi());

        DOM.settingsModal.addEventListener('click', (e) => {
            if (e.target === DOM.settingsModal) {
                UI.closeSettings();
            }
        });
        
        // 消融测试事件监听
        DOM.cfgArpmEnabled?.addEventListener('change', () => UI.updateAblationSubitems());
    },

    save() {
        State.config.apiKey = DOM.cfgApiKey.value.trim();
        State.config.baseUrl = DOM.cfgBaseUrl.value.trim();
        State.config.model = DOM.cfgModel.value.trim() || 'deepseek-chat';
        State.config.systemPrompt = DOM.cfgSystemPrompt.value.trim();
        State.config.chunkSize = parseInt(DOM.cfgChunkSize.value) || 600;
        State.config.topK = parseInt(DOM.cfgTopK.value) || 5;
        State.config.decayRate = parseFloat(DOM.cfgDecay.value) || 20;
        
        // 消融测试配置
        State.config.arpmEnabled = DOM.cfgArpmEnabled?.checked !== false;
        State.config.bm25Enabled = DOM.cfgBm25Enabled?.checked !== false;
        State.config.cotRerank = DOM.cfgCotRerank?.checked !== false;
        State.config.temporalDecay = DOM.cfgTemporalDecay?.checked !== false;
        State.config.keywordBoost = DOM.cfgKeywordBoost?.checked !== false;
        
        // 自动切分配置
        State.config.autoChunk = DOM.cfgAutoChunk?.checked !== false;
        State.config.autoChunkThreshold = parseInt(DOM.cfgAutoChunkThreshold?.value) || 10000;

        Storage.saveConfig(State.config);
        UI.closeSettings();
        
        // 显示消融测试提示
        if (!State.config.arpmEnabled) {
            UI.toast('⚠️ ARPM系统已关闭，将使用纯LLM对话', 'warning');
        } else if (!State.config.bm25Enabled || !State.config.cotRerank || !State.config.temporalDecay || !State.config.keywordBoost) {
            const disabled = [];
            if (!State.config.bm25Enabled) disabled.push('BM25+');
            if (!State.config.cotRerank) disabled.push('CoT重排序');
            if (!State.config.temporalDecay) disabled.push('时间衰减');
            if (!State.config.keywordBoost) disabled.push('关键词提升');
            UI.toast(`🔬 消融模式: 已关闭 ${disabled.join(', ')}`, 'info');
        } else {
            UI.toast('配置已保存');
        }
    },

    async testApi() {
        const apiKey = DOM.cfgApiKey.value.trim();
        const baseUrl = DOM.cfgBaseUrl.value.trim();
        const model = DOM.cfgModel.value.trim() || 'deepseek-chat';

        if (!apiKey) {
            DOM.testResult.textContent = '请输入 API 密钥';
            DOM.testResult.className = 'error';
            return;
        }

        DOM.testResult.textContent = '测试中...';
        DOM.testResult.className = '';

        try {
            await API.testConnection({ api_key: apiKey, base_url: baseUrl, model });
            DOM.testResult.textContent = '连接成功';
            DOM.testResult.className = 'success';
        } catch (error) {
            DOM.testResult.textContent = error.message;
            DOM.testResult.className = 'error';
        }
    }
};

// 知识库管理 - 使用新的KBManager模块
const KnowledgeManager = {
    init() {
        // 初始化新的KBManager
        if (typeof KBManager !== 'undefined') {
            KBManager.init();
        }
        
        // 绑定管理按钮
        if (DOM.btnManageKb) {
            DOM.btnManageKb.addEventListener('click', () => {
                if (typeof KBManager !== 'undefined') {
                    KBManager.open();
                }
            });
        }
        
        // 场景管理事件
        DOM.btnCloseScene?.addEventListener('click', () => this.closeSceneModal());
        DOM.btnNewScene?.addEventListener('click', () => this.openSceneCreate());
        DOM.btnSaveScene?.addEventListener('click', () => this.saveScene());
        
        // 诊断事件
        DOM.btnCloseDiag?.addEventListener('click', () => this.closeDiagModal());
        DOM.btnRunDiag?.addEventListener('click', () => this.runDiagnostics(false));
        DOM.btnRunDiagFix?.addEventListener('click', () => this.runDiagnostics(true));
        
        // 点击外部关闭
        DOM.sceneModal?.addEventListener('click', (e) => {
            if (e.target === DOM.sceneModal) this.closeSceneModal();
        });
        DOM.diagModal?.addEventListener('click', (e) => {
            if (e.target === DOM.diagModal) this.closeDiagModal();
        });
        
        // 添加诊断按钮到设置面板
        this.addDiagButton();
    },

    addDiagButton() {
        const kbSection = document.querySelector('.config-section:has(#manage-kb)');
        if (kbSection && !kbSection.querySelector('.btn-diag')) {
            const diagBtn = document.createElement('button');
            diagBtn.className = 'btn-secondary btn-diag';
            diagBtn.style.marginTop = '10px';
            diagBtn.innerHTML = '🔍 系统诊断';
            diagBtn.onclick = () => this.openDiagModal();
            kbSection.appendChild(diagBtn);
        }
    },

    // ==================== 场景管理 ====================
    openSceneCreate() {
        DOM.sceneStartRound.value = '1';
        DOM.sceneEndRound.value = '10';
        DOM.sceneTitle.value = '';
        DOM.sceneSummary.value = '';
        document.getElementById('scene-form').style.display = 'block';
        document.getElementById('scene-list-view').style.display = 'none';
    },

    closeSceneModal() {
        DOM.sceneModal.classList.remove('show');
    },

    async loadScenes() {
        try {
            const data = await API.getScenes();
            const scenes = data.scenes || [];
            DOM.sceneList.innerHTML = scenes.map(s => `
                <div class="scene-item">
                    <div class="scene-title">${s.title}</div>
                    <div class="scene-range">轮次 ${s.start_round} - ${s.end_round}</div>
                    <button class="btn-icon btn-danger" onclick="KnowledgeManager.deleteScene('${s.id}')">🗑️</button>
                </div>
            `).join('') || '<div class="empty">暂无场景</div>';
        } catch (e) {
            DOM.sceneList.innerHTML = '<div class="empty">加载失败</div>';
        }
    },

    async saveScene() {
        try {
            await API.createScene({
                start_round: parseInt(DOM.sceneStartRound.value),
                end_round: parseInt(DOM.sceneEndRound.value),
                title: DOM.sceneTitle.value,
                summary: DOM.sceneSummary.value
            });
            UI.toast('场景已创建');
            document.getElementById('scene-form').style.display = 'none';
            document.getElementById('scene-list-view').style.display = 'block';
            await this.loadScenes();
        } catch (e) {
            UI.toast('创建失败: ' + e.message, 'error');
        }
    },

    async deleteScene(sceneId) {
        if (!confirm('确定删除此场景？')) return;
        try {
            await API.deleteScene(sceneId);
            UI.toast('场景已删除');
            await this.loadScenes();
        } catch (e) {
            UI.toast('删除失败: ' + e.message, 'error');
        }
    },

    // ==================== 诊断系统 ====================
    openDiagModal() {
        DOM.diagModal.classList.add('show');
        DOM.diagResults.innerHTML = '<div class="empty">点击运行诊断</div>';
    },

    closeDiagModal() {
        DOM.diagModal.classList.remove('show');
    },

    async runDiagnostics(autoFix) {
        DOM.diagResults.innerHTML = '<div class="empty">诊断中...</div>';
        try {
            const report = await API.runDiagnostics(autoFix);
            const summary = report.summary;
            
            let html = `
                <div class="diag-summary ${summary.healthy ? 'healthy' : 'unhealthy'}">
                    <div>状态: ${summary.healthy ? '✅ 健康' : '⚠️ 有问题'}</div>
                    <div>检查项: ${summary.ok} 正常 / ${summary.warnings} 警告 / ${summary.errors} 错误</div>
                    ${summary.fixed > 0 ? `<div>已修复: ${summary.fixed} 项</div>` : ''}
                </div>
            `;
            
            html += '<div class="diag-checks">';
            for (const check of report.checks) {
                const icon = check.status === 'ok' ? '✅' : check.status === 'warning' ? '⚠️' : '❌';
                html += `
                    <div class="diag-check ${check.status}">
                        <span class="diag-icon">${icon}</span>
                        <span class="diag-name">${check.name}</span>
                        <span class="diag-message">${check.message}</span>
                    </div>
                `;
            }
            html += '</div>';
            
            DOM.diagResults.innerHTML = html;
        } catch (e) {
            DOM.diagResults.innerHTML = '<div class="empty error">诊断失败: ' + e.message + '</div>';
        }
    }
};

// 初始化
function init() {
    const saved = Storage.loadConfig();
    if (saved) {
        Object.assign(State.config, saved);
    }
}

// 消息反馈管理器
const FeedbackManager = {
    currentReportId: null,
    currentReportContent: null,
    feedbackCache: new Map(), // 缓存已反馈的消息

    init() {
        // 绑定举报弹窗事件
        document.getElementById('close-report')?.addEventListener('click', () => this.closeReportModal());
        document.getElementById('cancel-report')?.addEventListener('click', () => this.closeReportModal());
        document.getElementById('submit-report')?.addEventListener('click', () => this.submitReport());
        
        // 点击外部关闭
        document.getElementById('report-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'report-modal') this.closeReportModal();
        });
    },

    // 处理点赞
    async handleLike(messageId, btn) {
        if (this.feedbackCache.has(messageId)) return;
        
        btn.classList.add('liked');
        btn.disabled = true;
        
        const statusEl = btn.closest('.message-feedback').querySelector('.feedback-status');
        statusEl.textContent = '✓ 已记录您的偏好';
        
        this.feedbackCache.set(messageId, { type: 'like', time: Date.now() });
        
        // 发送反馈到后端（用于偏好学习，不直接修改AI行为）
        try {
            await this.sendFeedback({
                message_id: messageId,
                type: 'like',
                session_id: State.sessionId,
                timestamp: Date.now()
            });
            console.log(`[反馈] 消息 ${messageId} 已点赞，用于偏好学习`);
        } catch (e) {
            console.error('[反馈] 发送失败:', e);
        }
    },

    // 处理差评
    async handleDislike(messageId, btn) {
        if (this.feedbackCache.has(messageId)) return;
        
        btn.classList.add('disliked');
        btn.disabled = true;
        
        const statusEl = btn.closest('.message-feedback').querySelector('.feedback-status');
        statusEl.textContent = '✓ 已记录您的偏好';
        
        this.feedbackCache.set(messageId, { type: 'dislike', time: Date.now() });
        
        // 发送反馈到后端（用于偏好学习，不直接修改AI行为）
        try {
            await this.sendFeedback({
                message_id: messageId,
                type: 'dislike',
                session_id: State.sessionId,
                timestamp: Date.now()
            });
            console.log(`[反馈] 消息 ${messageId} 已差评，用于偏好学习`);
        } catch (e) {
            console.error('[反馈] 发送失败:', e);
        }
    },

    // 打开举报弹窗
    openReport(messageId, content) {
        if (this.feedbackCache.has(messageId) && this.feedbackCache.get(messageId).type === 'report') {
            UI.toast('此消息已被举报', 'info');
            return;
        }
        
        this.currentReportId = messageId;
        this.currentReportContent = content;
        
        // 重置表单
        document.querySelectorAll('input[name="report-reason"]').forEach(r => r.checked = false);
        document.querySelector('input[name="report-reason"][value="other"]').checked = true;
        document.getElementById('report-detail-text').value = '';
        
        document.getElementById('report-modal').classList.add('show');
    },

    // 关闭举报弹窗
    closeReportModal() {
        document.getElementById('report-modal').classList.remove('show');
        this.currentReportId = null;
        this.currentReportContent = null;
    },

    // 提交举报
    async submitReport() {
        if (!this.currentReportId) return;
        
        const reason = document.querySelector('input[name="report-reason"]:checked')?.value || 'other';
        const detail = document.getElementById('report-detail-text').value.trim();
        
        // 标记已举报
        this.feedbackCache.set(this.currentReportId, { 
            type: 'report', 
            reason,
            time: Date.now() 
        });
        
        // 关闭弹窗
        this.closeReportModal();
        
        // 找到对应的消息元素并标记
        const msgDiv = document.querySelector(`[data-message-id="${this.currentReportId}"]`);
        if (msgDiv) {
            msgDiv.classList.add('regenerating');
            
            // 显示重新生成提示
            const textDiv = msgDiv.querySelector('.message-text');
            const originalContent = textDiv.innerHTML;
            textDiv.innerHTML = `
                <div class="regenerate-indicator">
                    <div class="spinner"></div>
                    <span>内容不合规，正在重新生成...</span>
                </div>
            `;
            
            try {
                // 1. 归档不合规内容
                await this.archiveContent({
                    message_id: this.currentReportId,
                    content: this.currentReportContent,
                    reason: reason,
                    detail: detail,
                    session_id: State.sessionId,
                    timestamp: Date.now()
                });
                
                // 2. 重新生成回复
                const newContent = await this.regenerateResponse(this.currentReportId);
                
                // 3. 更新显示
                textDiv.innerHTML = Utils.parseMarkdown(newContent);
                
                // 4. 添加已归档标签
                const header = msgDiv.querySelector('.message-header');
                header.innerHTML += '<span class="archived-tag">已重新生成</span>';
                
                // 5. 更新messages数组
                const msgIndex = State.messages.findIndex(m => m.timestamp === this.currentReportId);
                if (msgIndex >= 0) {
                    State.messages[msgIndex].content = newContent;
                    State.messages[msgIndex].regenerated = true;
                    State.messages[msgIndex].original_content = this.currentReportContent;
                    await API.saveHistory(State.sessionId, State.messages);
                }
                
                UI.toast('内容已重新生成并归档', 'success');
                
            } catch (e) {
                console.error('[举报] 重新生成失败:', e);
                textDiv.innerHTML = originalContent;
                UI.toast('重新生成失败: ' + e.message, 'error');
            } finally {
                msgDiv.classList.remove('regenerating');
            }
        }
    },

    // 发送反馈到后端
    async sendFeedback(data) {
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('反馈提交失败');
        return response.json();
    },

    // 归档不合规内容
    async archiveContent(data) {
        const response = await fetch('/api/archive', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('归档失败');
        return response.json();
    },

    // 重新生成回复
    async regenerateResponse(messageId) {
        // 找到对应用户的问题（该消息的前一条）
        const msgIndex = State.messages.findIndex(m => m.timestamp === messageId);
        let userQuestion = '';
        if (msgIndex > 0 && State.messages[msgIndex - 1].role === 'user') {
            userQuestion = State.messages[msgIndex - 1].content;
        }
        
        // 调用API重新生成（带安全提示）
        const response = await fetch('/api/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message_id: messageId,
                user_question: userQuestion,
                session_id: State.sessionId,
                api_config: {
                    api_key: State.config.apiKey,
                    base_url: State.config.baseUrl,
                    model: State.config.model
                },
                system_prompt: State.config.systemPrompt,
                params: {
                    top_k: State.config.topK,
                    decay_rate: State.config.decayRate,
                    arpm_enabled: State.config.arpmEnabled,
                    bm25_enabled: State.config.bm25Enabled,
                    cot_rerank: State.config.cotRerank,
                    temporal_decay: State.config.temporalDecay,
                    keyword_boost: State.config.keywordBoost
                }
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || '重新生成失败');
        }
        
        const data = await response.json();
        return data.reply;
    }
};

// 初始化函数
function init() {
    const saved = Storage.loadConfig();
    if (saved) {
        Object.assign(State.config, saved);
    }

    Chat.init();
    Upload.init();
    Settings.init();
    KnowledgeManager.init();
    FeedbackManager.init();  // 初始化反馈管理器

    DOM.btnNewChat.addEventListener('click', () => Session.create());

    Session.refreshList();
    Upload.updateStats();

    DOM.userInput.focus();

    console.log('ARPM 系统已初始化');
}

document.addEventListener('DOMContentLoaded', init);
