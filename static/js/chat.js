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
    config: {
        apiKey: '',
        baseUrl: 'https://api.deepseek.com',
        model: 'deepseek-chat',
        systemPrompt: '',
        chunkSize: 600,
        topK: 5,
        decayRate: 20
    }
};

// DOM 元素
const DOM = {
    chatContainer: document.getElementById('chat-container'),
    sessionList: document.getElementById('session-list'),
    userInput: document.getElementById('user-input'),
    btnSend: document.getElementById('btn-send'),
    btnStop: document.getElementById('btn-stop'),
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
    toastContainer: document.getElementById('toast-container')
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
        const analysisMatch = text.match(/<analysis>([\s\S]*?)<\/analysis>/i);
        const responseMatch = text.match(/<response>([\s\S]*?)<\/response>/i);
        
        return {
            analysis: analysisMatch ? analysisMatch[1].trim() : '',
            response: responseMatch ? responseMatch[1].trim() : text
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
    renderMessage(role, content, time) {
        const welcome = document.getElementById('welcome');
        if (welcome) welcome.remove();
        
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;
        
        const avatarText = role === 'user' ? '用' : 'AI';
        const parsedContent = role === 'assistant' 
            ? Utils.parseMarkdown(content) 
            : Utils.escapeHtml(content);
        
        const timeStr = time || Utils.formatTime();
        
        msgDiv.innerHTML = `
            <div class="message-content-wrapper">
                <div class="message-avatar">${avatarText}</div>
                <div class="message-body">
                    <div class="message-header">${role === 'user' ? '用户' : '助手'}</div>
                    <div class="message-text">${parsedContent}</div>
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
        
        // 保存到状态
        State.messages.push({
            role: role,
            content: content,
            time: time,
            timestamp: Date.now()
        });
        
        // 渲染到界面
        this.renderMessage(role, content, time);
        
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
            this.renderMessage(msg.role, msg.content, msg.time);
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
        
        DOM.settingsModal.classList.add('show');
    },

    closeSettings() {
        DOM.settingsModal.classList.remove('show');
    }
};

// 会话管理
const Session = {
    create() {
        State.sessionId = null;
        State.sessionName = null;
        State.messages = [];
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
            
            // 加载历史消息到界面
            UI.loadHistory(State.messages);
            
            // 设置轮次
            const lastRound = data.last_round || 1;
            UI.setRound(lastRound + 1);
            
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

        // 添加用户消息（会保存到State和后端）
        UI.addMessage('user', content);
        
        DOM.userInput.value = '';
        DOM.userInput.style.height = 'auto';
        UI.updateSendButton();

        UI.setGenerating(true);
        UI.setStatus('正在生成...', 'processing');

        State.abortController = new AbortController();
        const typingId = UI.addTypingIndicator();

        try {
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
                    decay_rate: State.config.decayRate
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
    },

    save() {
        State.config.apiKey = DOM.cfgApiKey.value.trim();
        State.config.baseUrl = DOM.cfgBaseUrl.value.trim();
        State.config.model = DOM.cfgModel.value.trim() || 'deepseek-chat';
        State.config.systemPrompt = DOM.cfgSystemPrompt.value.trim();
        State.config.chunkSize = parseInt(DOM.cfgChunkSize.value) || 600;
        State.config.topK = parseInt(DOM.cfgTopK.value) || 5;
        State.config.decayRate = parseFloat(DOM.cfgDecay.value) || 20;

        Storage.saveConfig(State.config);
        UI.closeSettings();
        UI.toast('配置已保存');
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

// 初始化
function init() {
    const saved = Storage.loadConfig();
    if (saved) {
        Object.assign(State.config, saved);
    }

    Chat.init();
    Upload.init();
    Settings.init();

    DOM.btnNewChat.addEventListener('click', () => Session.create());

    Session.refreshList();
    Upload.updateStats();

    DOM.userInput.focus();

    console.log('ARPM 系统已初始化');
}

document.addEventListener('DOMContentLoaded', init);
