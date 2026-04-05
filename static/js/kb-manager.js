/**
 * ARPM 知识库管理模块 - 增强版
 * 支持分页、RAG检索、类型归类统计
 */

const KBManager = {
    // 数据状态
    allChunks: [],
    filteredChunks: [],
    displayedChunks: [],
    currentPage: 1,
    pageSize: 50,
    totalPages: 1,
    
    // 统计
    stats: {
        total: 0,
        blind: 0,
        nostalgia: 0,
        conditional: 0,
        keywords: 0,
        scene: 0,
        sources: {}
    },
    
    // 编辑状态
    currentEditingIdx: null,
    currentKeywords: [],
    expandedChunks: new Set(),
    
    // RAG模式
    isRagMode: false,
    lastRagQuery: '',

    // DOM 元素缓存
    DOM: {},

    /**
     * 初始化
     */
    init() {
        this.cacheDOM();
        this.bindEvents();
    },

    /**
     * 缓存DOM元素
     */
    cacheDOM() {
        // 主弹窗
        this.DOM.modal = document.getElementById('kb-modal');
        this.DOM.closeBtn = document.getElementById('close-kb');
        this.DOM.headerStats = document.getElementById('kb-header-stats');
        
        // 侧边栏统计
        this.DOM.statTotal = document.getElementById('stat-total');
        this.DOM.statBlind = document.getElementById('stat-blind');
        this.DOM.statNostalgia = document.getElementById('stat-nostalgia');
        this.DOM.statConditional = document.getElementById('stat-conditional');
        this.DOM.statKeywords = document.getElementById('stat-keywords');
        this.DOM.statScene = document.getElementById('stat-scene');
        this.DOM.sourcesList = document.getElementById('kb-sources-list');
        this.DOM.statItems = document.querySelectorAll('.stat-item');
        
        // 主内容区
        this.DOM.searchInput = document.getElementById('kb-search');
        this.DOM.ragSearchBtn = document.getElementById('kb-rag-search');
        this.DOM.filterSelect = document.getElementById('kb-filter');
        this.DOM.pageSizeSelect = document.getElementById('kb-page-size');
        this.DOM.refreshBtn = document.getElementById('kb-refresh');
        
        // RAG结果区域
        this.DOM.ragResults = document.getElementById('kb-rag-results');
        this.DOM.ragQueryText = document.getElementById('rag-query-text');
        this.DOM.clearRagBtn = document.getElementById('kb-clear-rag');
        
        // 列表和分页
        this.DOM.list = document.getElementById('kb-list');
        this.DOM.pagination = document.getElementById('kb-pagination');
        this.DOM.prevBtn = document.getElementById('kb-prev');
        this.DOM.nextBtn = document.getElementById('kb-next');
        this.DOM.pageInfo = document.getElementById('page-info');
        this.DOM.pageTotal = document.getElementById('page-total');
        
        // 子弹窗
        this.DOM.conditionModal = document.getElementById('condition-modal');
        this.DOM.keywordModal = document.getElementById('keyword-modal');
        this.DOM.nostalgiaModal = document.getElementById('nostalgia-modal');
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 主弹窗
        this.DOM.closeBtn?.addEventListener('click', () => this.close());
        this.DOM.modal?.addEventListener('click', (e) => {
            if (e.target === this.DOM.modal) this.close();
        });
        
        // 搜索和过滤
        this.DOM.searchInput?.addEventListener('input', () => {
            this.isRagMode = false;
            this.applyFilter();
        });
        this.DOM.ragSearchBtn?.addEventListener('click', () => this.performRagSearch());
        this.DOM.filterSelect?.addEventListener('change', () => {
            this.isRagMode = false;
            this.DOM.ragResults.style.display = 'none';
            this.applyFilter();
        });
        this.DOM.pageSizeSelect?.addEventListener('change', () => {
            this.pageSize = parseInt(this.DOM.pageSizeSelect.value);
            this.currentPage = 1;
            this.applyFilter();
        });
        this.DOM.refreshBtn?.addEventListener('click', () => this.load());
        this.DOM.clearRagBtn?.addEventListener('click', () => this.clearRagMode());
        
        // 分页
        this.DOM.prevBtn?.addEventListener('click', () => this.goToPage(this.currentPage - 1));
        this.DOM.nextBtn?.addEventListener('click', () => this.goToPage(this.currentPage + 1));
        
        // 统计项点击
        this.DOM.statItems?.forEach(item => {
            item.addEventListener('click', () => {
                const filter = item.dataset.filter;
                this.DOM.filterSelect.value = filter;
                this.isRagMode = false;
                this.DOM.ragResults.style.display = 'none';
                this.applyFilter();
            });
        });
        
        // 回车搜索
        this.DOM.searchInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                this.performRagSearch();
            }
        });
    },

    /**
     * 打开知识库管理
     */
    async open() {
        this.DOM.modal.classList.add('show');
        await this.load();
    },

    /**
     * 关闭知识库管理
     */
    close() {
        this.DOM.modal.classList.remove('show');
        this.clearRagMode();
    },

    /**
     * 加载数据
     */
    async load() {
        this.showLoading('加载知识库...');
        
        try {
            // 并行加载数据和统计
            const [knowledgeData, statsData] = await Promise.all([
                this.fetchKnowledge(),
                this.fetchStats()
            ]);
            
            this.allChunks = knowledgeData.chunks || [];
            this.updateStats(statsData);
            
            this.isRagMode = false;
            this.applyFilter();
            
            this.hideLoading();
        } catch (e) {
            console.error('加载知识库失败:', e);
            this.showError('加载失败: ' + e.message);
            this.DOM.list.innerHTML = '<div class="kb-empty">加载失败，请重试</div>';
        }
    },

    /**
     * 获取知识库数据
     */
    async fetchKnowledge() {
        const response = await fetch('/api/knowledge');
        if (!response.ok) throw new Error('获取数据失败');
        return response.json();
    },

    /**
     * 获取统计数据
     */
    async fetchStats() {
        const response = await fetch('/api/knowledge/stats');
        if (!response.ok) throw new Error('获取统计失败');
        return response.json();
    },

    /**
     * 更新统计显示
     */
    updateStats(stats) {
        this.stats = stats;
        
        // 更新头部统计
        this.DOM.headerStats.textContent = `共 ${stats.total} 个片段`;
        
        // 更新侧边栏统计
        this.DOM.statTotal.textContent = stats.total;
        this.DOM.statBlind.textContent = stats.blind;
        this.DOM.statNostalgia.textContent = stats.nostalgia;
        this.DOM.statConditional.textContent = stats.conditional;
        this.DOM.statKeywords.textContent = stats.keywords;
        this.DOM.statScene.textContent = stats.scene;
        
        // 更新来源列表
        this.renderSources(stats.sources);
    },

    /**
     * 渲染来源列表
     */
    renderSources(sources) {
        if (!sources || Object.keys(sources).length === 0) {
            this.DOM.sourcesList.innerHTML = '<div class="kb-empty">暂无来源数据</div>';
            return;
        }
        
        const sortedSources = Object.entries(sources)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10); // 只显示前10个
        
        this.DOM.sourcesList.innerHTML = sortedSources.map(([name, count]) => `
            <div class="source-item" title="${this.escapeHtml(name)}">
                <span class="source-name">${this.escapeHtml(name)}</span>
                <span class="source-count">${count}</span>
            </div>
        `).join('');
    },

    /**
     * 应用过滤
     */
    applyFilter() {
        const searchText = this.DOM.searchInput.value.toLowerCase().trim();
        const filterType = this.DOM.filterSelect.value;
        
        // 过滤数据
        this.filteredChunks = this.allChunks.filter(chunk => {
            // 类型过滤
            if (filterType !== 'all') {
                const meta = chunk.metadata || {};
                switch (filterType) {
                    case 'blind':
                        if (!meta.temporally_blind) return false;
                        break;
                    case 'nostalgia':
                        if (!meta.nostalgia_enabled) return false;
                        break;
                    case 'conditional':
                        if (!meta.conditions?.enabled) return false;
                        break;
                    case 'keywords':
                        if (!meta.keywords || meta.keywords.length === 0) return false;
                        break;
                    case 'scene':
                        if (!meta.scene_id) return false;
                        break;
                }
            }
            
            // 文本搜索
            if (searchText) {
                const text = (chunk.text || '').toLowerCase();
                const title = (chunk.metadata?.title || '').toLowerCase();
                const source = (chunk.metadata?.source || '').toLowerCase();
                if (!text.includes(searchText) && !title.includes(searchText) && !source.includes(searchText)) {
                    return false;
                }
            }
            
            return true;
        });
        
        this.currentPage = 1;
        this.renderPage();
    },

    /**
     * 执行RAG检索
     */
    async performRagSearch() {
        const query = this.DOM.searchInput.value.trim();
        if (!query) {
            this.showToast('请输入检索内容', 'error');
            return;
        }
        
        this.showLoading('RAG检索中...');
        this.DOM.ragSearchBtn.disabled = true;
        
        try {
            const response = await fetch('/api/knowledge/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, top_k: 20 })
            });
            
            if (!response.ok) throw new Error('检索失败');
            const data = await response.json();
            
            this.isRagMode = true;
            this.lastRagQuery = query;
            this.filteredChunks = data.results || [];
            
            // 显示RAG结果区域
            this.DOM.ragResults.style.display = 'block';
            this.DOM.ragQueryText.textContent = query;
            
            this.currentPage = 1;
            this.renderPage();
            
            this.showToast(`检索完成，找到 ${this.filteredChunks.length} 个相关片段`);
        } catch (e) {
            console.error('RAG检索失败:', e);
            this.showError('检索失败: ' + e.message);
        } finally {
            this.hideLoading();
            this.DOM.ragSearchBtn.disabled = false;
        }
    },

    /**
     * 清除RAG模式
     */
    clearRagMode() {
        this.isRagMode = false;
        this.lastRagQuery = '';
        this.DOM.ragResults.style.display = 'none';
        this.applyFilter();
    },

    /**
     * 渲染当前页
     */
    renderPage() {
        // 计算分页
        this.totalPages = Math.ceil(this.filteredChunks.length / this.pageSize) || 1;
        if (this.currentPage > this.totalPages) this.currentPage = this.totalPages;
        if (this.currentPage < 1) this.currentPage = 1;
        
        // 截取当前页数据
        const start = (this.currentPage - 1) * this.pageSize;
        const end = start + this.pageSize;
        this.displayedChunks = this.filteredChunks.slice(start, end);
        
        // 渲染列表
        this.renderList();
        
        // 更新分页控件
        this.updatePagination();
    },

    /**
     * 渲染列表
     */
    renderList() {
        if (this.displayedChunks.length === 0) {
            this.DOM.list.innerHTML = `
                <div class="kb-empty">
                    <div class="kb-empty-icon">📭</div>
                    <div>没有找到匹配的片段</div>
                </div>
            `;
            return;
        }
        
        this.DOM.list.innerHTML = this.displayedChunks.map(chunk => {
            const meta = chunk.metadata || {};
            const isBlind = meta.temporally_blind;
            const hasConditions = meta.conditions?.enabled;
            const hasKeywords = meta.keywords && meta.keywords.length > 0;
            const isNostalgia = meta.nostalgia_enabled;
            const inScene = meta.scene_id;
            const isExpanded = this.expandedChunks.has(chunk.index);
            
            const badges = [];
            if (isBlind) badges.push('<span class="badge-mini" style="background:#fef3c7" title="时间锁定">🔒</span>');
            if (isNostalgia) badges.push('<span class="badge-mini" style="background:#fde68a" title="怀旧模式">📜</span>');
            if (hasConditions) badges.push('<span class="badge-mini" style="background:#dbeafe" title="条件激活">📋</span>');
            if (hasKeywords) badges.push(`<span class="badge-mini" style="background:#ddd6fe" title="${meta.keywords.length} 个关键词">🔑${meta.keywords.length}</span>`);
            if (inScene) badges.push('<span class="badge-mini" style="background:#c7d2fe" title="场景中">🎬</span>');
            
            const source = meta.source || '未知来源';
            const sourceShort = source.length > 15 ? source.substring(0, 12) + '...' : source;
            
            return `
                <div class="kb-row ${isExpanded ? 'expanded' : ''}" data-idx="${chunk.index}">
                    <div class="kb-col-index">#${chunk.index}</div>
                    <div class="kb-col-badges">${badges.join('')}</div>
                    <div class="kb-col-content">
                        <div class="kb-text-preview" onclick="KBManager.toggleExpand(${chunk.index})">
                            ${this.escapeHtml(chunk.text?.substring(0, 150) || '(无内容)')}...
                        </div>
                        ${isExpanded ? `
                            <div class="kb-text-full">${this.escapeHtml(chunk.text || '')}</div>
                            <div style="margin-top:8px;font-size:12px;color:var(--text-tertiary)">
                                来源: ${this.escapeHtml(source)} | 
                                时间: ${new Date(meta.timestamp * 1000).toLocaleString()}
                            </div>
                        ` : ''}
                    </div>
                    <div class="kb-col-source" title="${this.escapeHtml(source)}">${this.escapeHtml(sourceShort)}</div>
                    <div class="kb-col-actions">
                        <button class="btn-icon ${isBlind ? 'active' : ''}" 
                                onclick="KBManager.toggleBlind(${chunk.index})" 
                                title="${isBlind ? '取消时间锁定' : '时间锁定'}">
                            🔒
                        </button>
                        <button class="btn-icon ${isNostalgia ? 'active' : ''}" 
                                onclick="KBManager.editNostalgia(${chunk.index})" 
                                title="怀旧模式">
                            📜
                        </button>
                        <button class="btn-icon ${hasKeywords ? 'active' : ''}" 
                                onclick="KBManager.editKeywords(${chunk.index})" 
                                title="关键词">
                            🔑
                        </button>
                        <button class="btn-icon ${hasConditions ? 'active' : ''}" 
                                onclick="KBManager.editCondition(${chunk.index})" 
                                title="条件">
                            📋
                        </button>
                        <button class="btn-icon btn-danger" 
                                onclick="KBManager.delete(${chunk.index})" 
                                title="删除">
                            🗑️
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    },

    /**
     * 更新分页控件
     */
    updatePagination() {
        this.DOM.pageInfo.textContent = `第 ${this.currentPage} 页 / 共 ${this.totalPages} 页`;
        this.DOM.pageTotal.textContent = `共 ${this.filteredChunks.length} 条`;
        this.DOM.prevBtn.disabled = this.currentPage <= 1;
        this.DOM.nextBtn.disabled = this.currentPage >= this.totalPages;
    },

    /**
     * 跳转到指定页
     */
    goToPage(page) {
        if (page < 1 || page > this.totalPages) return;
        this.currentPage = page;
        this.renderPage();
        // 滚动到顶部
        this.DOM.list.scrollTop = 0;
    },

    /**
     * 切换文本展开
     */
    toggleExpand(idx) {
        if (this.expandedChunks.has(idx)) {
            this.expandedChunks.delete(idx);
        } else {
            this.expandedChunks.add(idx);
        }
        this.renderList();
    },

    // ==================== 操作功能 ====================

    /**
     * 切换时间锁定
     */
    async toggleBlind(idx) {
        const chunk = this.allChunks.find(c => c.index === idx);
        const newState = !chunk?.metadata?.temporally_blind;
        
        this.showLoading(newState ? '锁定中...' : '解锁中...');
        
        try {
            await fetch(`/api/knowledge/${idx}/blind`, {
                method: newState ? 'POST' : 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ blind: newState })
            });
            
            // 更新本地数据
            if (chunk) {
                chunk.metadata = chunk.metadata || {};
                chunk.metadata.temporally_blind = newState;
            }
            
            this.updateStats(await this.fetchStats());
            this.renderList();
            this.showToast(newState ? '已锁定该片段' : '已取消锁定');
        } catch (e) {
            this.showError('操作失败: ' + e.message);
        } finally {
            this.hideLoading();
        }
    },

    /**
     * 删除片段
     */
    async delete(idx) {
        if (!confirm(`确定要删除片段 #${idx} 吗？\n\n此操作不可恢复！`)) return;
        
        this.showLoading('删除中...');
        
        try {
            await fetch(`/api/knowledge?index=${idx}`, { method: 'DELETE' });
            
            // 从本地数据中移除
            this.allChunks = this.allChunks.filter(c => c.index !== idx);
            
            // 重新应用过滤
            this.applyFilter();
            
            // 更新统计
            this.updateStats(await this.fetchStats());
            
            this.showToast('已删除');
        } catch (e) {
            this.showError('删除失败: ' + e.message);
        } finally {
            this.hideLoading();
        }
    },

    /**
     * 编辑关键词
     */
    async editKeywords(idx) {
        this.currentEditingIdx = idx;
        
        try {
            const response = await fetch(`/api/knowledge/${idx}/keywords`);
            const data = await response.json();
            this.currentKeywords = data.keywords || [];
            this.renderKeywordModal();
            this.DOM.keywordModal.classList.add('show');
        } catch (e) {
            this.showError('加载关键词失败: ' + e.message);
        }
    },

    renderKeywordModal() {
        const list = document.getElementById('keyword-list');
        list.innerHTML = this.currentKeywords.map((kw, i) => `
            <div class="keyword-item">
                <input type="text" value="${this.escapeHtml(kw.text)}" 
                       placeholder="关键词" 
                       onchange="KBManager.updateKeyword(${i}, 'text', this.value)">
                <input type="number" value="${kw.weight}" step="0.1" min="1" max="3" 
                       onchange="KBManager.updateKeyword(${i}, 'weight', this.value)">
                <button class="btn-icon btn-danger" onclick="KBManager.removeKeyword(${i})">✕</button>
            </div>
        `).join('');
    },

    addKeyword() {
        this.currentKeywords.push({ text: '', weight: 1.5 });
        this.renderKeywordModal();
    },

    updateKeyword(idx, field, value) {
        if (field === 'weight') value = parseFloat(value);
        this.currentKeywords[idx][field] = value;
    },

    removeKeyword(idx) {
        this.currentKeywords.splice(idx, 1);
        this.renderKeywordModal();
    },

    async saveKeywords() {
        const validKeywords = this.currentKeywords.filter(k => k.text.trim());
        
        this.showLoading('保存中...');
        
        try {
            await fetch(`/api/knowledge/${this.currentEditingIdx}/keywords`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keywords: validKeywords })
            });
            
            // 更新本地数据
            const chunk = this.allChunks.find(c => c.index === this.currentEditingIdx);
            if (chunk) {
                chunk.metadata = chunk.metadata || {};
                chunk.metadata.keywords = validKeywords;
            }
            
            this.DOM.keywordModal.classList.remove('show');
            this.updateStats(await this.fetchStats());
            this.renderList();
            this.showToast(`已保存 ${validKeywords.length} 个关键词`);
        } catch (e) {
            this.showError('保存失败: ' + e.message);
        } finally {
            this.hideLoading();
        }
    },

    /**
     * 编辑怀旧模式
     */
    async editNostalgia(idx) {
        this.currentEditingIdx = idx;
        
        try {
            const response = await fetch(`/api/knowledge/${idx}/nostalgia`);
            const data = await response.json();
            
            document.getElementById('nostalgia-enabled').checked = data.nostalgia?.enabled || false;
            document.getElementById('nostalgia-factor').value = data.nostalgia?.factor || 0.01;
            this.DOM.nostalgiaModal.classList.add('show');
        } catch (e) {
            this.showError('加载失败: ' + e.message);
        }
    },

    async saveNostalgia() {
        const enabled = document.getElementById('nostalgia-enabled').checked;
        const factor = parseFloat(document.getElementById('nostalgia-factor').value);
        
        this.showLoading('保存中...');
        
        try {
            await fetch(`/api/knowledge/${this.currentEditingIdx}/nostalgia`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled, factor })
            });
            
            // 更新本地数据
            const chunk = this.allChunks.find(c => c.index === this.currentEditingIdx);
            if (chunk) {
                chunk.metadata = chunk.metadata || {};
                chunk.metadata.nostalgia_enabled = enabled;
            }
            
            this.DOM.nostalgiaModal.classList.remove('show');
            this.updateStats(await this.fetchStats());
            this.renderList();
            this.showToast(enabled ? '已启用怀旧模式' : '已禁用怀旧模式');
        } catch (e) {
            this.showError('保存失败: ' + e.message);
        } finally {
            this.hideLoading();
        }
    },

    /**
     * 编辑条件
     */
    async editCondition(idx) {
        this.currentEditingIdx = idx;
        const chunk = this.allChunks.find(c => c.index === idx);
        const conditions = chunk?.metadata?.conditions || { enabled: false, logic: 'AND', rules: [] };
        
        document.getElementById('cond-enabled').checked = conditions.enabled;
        document.getElementById('cond-logic').value = conditions.logic;
        
        // 渲染规则
        const rulesContainer = document.getElementById('cond-rules');
        rulesContainer.innerHTML = '';
        
        if (conditions.rules?.length) {
            conditions.rules.forEach((rule, i) => this.addRuleToDOM(rule, i));
        } else {
            this.addRuleToDOM({ type: 'keyword', settings: {}, negate: false });
        }
        
        this.DOM.conditionModal.classList.add('show');
    },

    addRuleToDOM(rule = {}, idx) {
        const div = document.createElement('div');
        div.className = 'cond-rule';
        div.innerHTML = `
            <div class="rule-header">
                <select class="rule-type" onchange="KBManager.onRuleTypeChange(this)">
                    <option value="keyword" ${rule.type === 'keyword' ? 'selected' : ''}>关键词</option>
                    <option value="regex" ${rule.type === 'regex' ? 'selected' : ''}>正则表达式</option>
                    <option value="round_range" ${rule.type === 'round_range' ? 'selected' : ''}>轮次范围</option>
                </select>
                <label><input type="checkbox" class="rule-negate" ${rule.negate ? 'checked' : ''}> 取反</label>
                <button class="btn-icon btn-danger" onclick="this.closest('.cond-rule').remove()">✕</button>
            </div>
            <div class="rule-settings">
                ${this.getRuleSettingsHTML(rule.type || 'keyword', rule.settings)}
            </div>
        `;
        
        document.getElementById('cond-rules').appendChild(div);
    },

    onRuleTypeChange(select) {
        const settingsDiv = select.closest('.cond-rule').querySelector('.rule-settings');
        settingsDiv.innerHTML = this.getRuleSettingsHTML(select.value);
    },

    getRuleSettingsHTML(type, settings = {}) {
        switch (type) {
            case 'keyword':
                return `
                    <input type="text" class="rule-keywords" placeholder="关键词，逗号分隔" 
                           value="${(settings.keywords || []).join(', ')}">
                    <select class="rule-match">
                        <option value="any" ${settings.match_mode !== 'all' ? 'selected' : ''}>任一匹配</option>
                        <option value="all" ${settings.match_mode === 'all' ? 'selected' : ''}>全部匹配</option>
                    </select>
                `;
            case 'regex':
                return `<input type="text" class="rule-patterns" placeholder="正则表达式" 
                               value="${(settings.patterns || []).join(', ')}">`;
            case 'round_range':
                return `
                    <input type="number" class="rule-min" placeholder="最小轮次" value="${settings.min_round || ''}">
                    <input type="number" class="rule-max" placeholder="最大轮次" value="${settings.max_round || ''}">
                `;
            default:
                return '';
        }
    },

    async saveCondition() {
        const conditions = {
            enabled: document.getElementById('cond-enabled').checked,
            logic: document.getElementById('cond-logic').value,
            rules: []
        };
        
        // 收集规则
        document.querySelectorAll('#cond-rules .cond-rule').forEach(ruleEl => {
            const type = ruleEl.querySelector('.rule-type').value;
            const negate = ruleEl.querySelector('.rule-negate').checked;
            const settings = {};
            
            switch (type) {
                case 'keyword':
                    settings.keywords = ruleEl.querySelector('.rule-keywords').value
                        .split(',').map(s => s.trim()).filter(Boolean);
                    settings.match_mode = ruleEl.querySelector('.rule-match').value;
                    break;
                case 'regex':
                    settings.patterns = ruleEl.querySelector('.rule-patterns').value
                        .split(',').map(s => s.trim()).filter(Boolean);
                    break;
                case 'round_range':
                    settings.min_round = parseInt(ruleEl.querySelector('.rule-min').value) || 1;
                    settings.max_round = parseInt(ruleEl.querySelector('.rule-max').value) || 999;
                    break;
            }
            
            conditions.rules.push({ type, settings, negate });
        });
        
        this.showLoading('保存中...');
        
        try {
            await fetch(`/api/knowledge/${this.currentEditingIdx}/conditions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ conditions })
            });
            
            // 更新本地数据
            const chunk = this.allChunks.find(c => c.index === this.currentEditingIdx);
            if (chunk) {
                chunk.metadata = chunk.metadata || {};
                chunk.metadata.conditions = conditions;
            }
            
            this.DOM.conditionModal.classList.remove('show');
            this.updateStats(await this.fetchStats());
            this.renderList();
            this.showToast('条件已保存');
        } catch (e) {
            this.showError('保存失败: ' + e.message);
        } finally {
            this.hideLoading();
        }
    },

    // ==================== 工具方法 ====================

    /**
     * 显示加载状态
     */
    showLoading(message = '加载中...') {
        this.hideLoading();
        const div = document.createElement('div');
        div.className = 'kb-action-status processing';
        div.id = 'kb-action-status';
        div.innerHTML = `
            <div class="status-spinner"></div>
            <span>${message}</span>
        `;
        document.body.appendChild(div);
    },

    /**
     * 隐藏加载状态
     */
    hideLoading() {
        const el = document.getElementById('kb-action-status');
        if (el) el.remove();
    },

    /**
     * 显示成功消息
     */
    showToast(message, type = 'success') {
        this.hideLoading();
        const div = document.createElement('div');
        div.className = `kb-action-status ${type}`;
        div.id = 'kb-action-status';
        div.innerHTML = type === 'success' ? `✓ ${message}` : message;
        document.body.appendChild(div);
        
        setTimeout(() => {
            div.style.opacity = '0';
            div.style.transform = 'translateX(-50%) translateY(-20px)';
            setTimeout(() => div.remove(), 300);
        }, 2000);
    },

    /**
     * 显示错误消息
     */
    showError(message) {
        this.showToast(message, 'error');
    },

    /**
     * HTML转义
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// 绑定子弹窗关闭事件
document.addEventListener('DOMContentLoaded', () => {
    // 关键词弹窗
    document.getElementById('close-keyword')?.addEventListener('click', () => {
        document.getElementById('keyword-modal').classList.remove('show');
    });
    document.getElementById('add-keyword')?.addEventListener('click', () => KBManager.addKeyword());
    document.getElementById('save-keywords')?.addEventListener('click', () => KBManager.saveKeywords());
    
    // 怀旧弹窗
    document.getElementById('close-nostalgia')?.addEventListener('click', () => {
        document.getElementById('nostalgia-modal').classList.remove('show');
    });
    document.getElementById('save-nostalgia')?.addEventListener('click', () => KBManager.saveNostalgia());
    
    // 条件弹窗
    document.getElementById('close-condition')?.addEventListener('click', () => {
        document.getElementById('condition-modal').classList.remove('show');
    });
    document.getElementById('add-rule')?.addEventListener('click', () => KBManager.addRuleToDOM());
    document.getElementById('save-condition')?.addEventListener('click', () => KBManager.saveCondition());
    
    // 点击外部关闭
    ['keyword-modal', 'nostalgia-modal', 'condition-modal'].forEach(id => {
        document.getElementById(id)?.addEventListener('click', (e) => {
            if (e.target.id === id) e.target.classList.remove('show');
        });
    });
});
