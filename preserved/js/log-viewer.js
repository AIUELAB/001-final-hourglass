/**
 * LogViewer - ログ・アクション履歴ビューアUI
 *
 * 機能:
 * - フローティングパネルでリアルタイムログ表示
 * - ログレベルフィルタリング
 * - 検索機能
 * - エクスポート機能
 * - アクション履歴表示
 *
 * @version 1.0.0
 * @author EPUP System
 */

class LogViewer {
    constructor(logCollector, actionTracker, options = {}) {
        this.logCollector = logCollector;
        this.actionTracker = actionTracker;
        this.config = {
            maxDisplayLogs: options.maxDisplayLogs || 200,
            autoScroll: options.autoScroll !== false,
            defaultTab: options.defaultTab || 'logs',
            position: options.position || { right: '20px', bottom: '20px' },
            size: options.size || { width: '500px', height: '400px' },
            minimized: options.minimized || false,
            showToggleButton: options.showToggleButton !== false,
        };

        this.displayedLogs = [];
        this.displayedActions = [];
        this.filters = {
            level: 'all',
            search: '',
        };
        this.currentTab = this.config.defaultTab;
        this.isMinimized = this.config.minimized;

        this.init();
    }

    init() {
        this.createStyles();
        this.createPanel();
        this.bindEvents();

        // ログ・アクションのリアルタイム購読
        if (this.logCollector) {
            this.logCollector.onLogEntry((entry) => this.addLogEntry(entry));
        }
        if (this.actionTracker) {
            this.actionTracker.onAction((action) => this.addActionEntry(action));
        }

        // 既存ログの読み込み
        this.loadExistingLogs();

        console.log('👁️ LogViewer初期化完了');
    }

    createStyles() {
        if (document.getElementById('log-viewer-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'log-viewer-styles';
        styles.textContent = `
            .log-viewer-panel {
                position: fixed;
                z-index: 99999;
                background: #1e1e1e;
                border-radius: 8px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
                color: #d4d4d4;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                transition: all 0.3s ease;
            }

            .log-viewer-panel.minimized {
                width: 200px !important;
                height: 40px !important;
            }

            .log-viewer-panel.minimized .log-viewer-content,
            .log-viewer-panel.minimized .log-viewer-tabs,
            .log-viewer-panel.minimized .log-viewer-toolbar {
                display: none;
            }

            .log-viewer-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 12px;
                background: #333;
                cursor: move;
                user-select: none;
            }

            .log-viewer-title {
                font-weight: 600;
                color: #fff;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .log-viewer-title .badge {
                background: #4fc3f7;
                color: #000;
                padding: 2px 6px;
                border-radius: 10px;
                font-size: 10px;
                font-weight: 700;
            }

            .log-viewer-controls {
                display: flex;
                gap: 8px;
            }

            .log-viewer-btn {
                background: transparent;
                border: none;
                color: #aaa;
                cursor: pointer;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 14px;
                transition: all 0.2s;
            }

            .log-viewer-btn:hover {
                background: #444;
                color: #fff;
            }

            .log-viewer-tabs {
                display: flex;
                background: #2d2d2d;
                border-bottom: 1px solid #444;
            }

            .log-viewer-tab {
                padding: 8px 16px;
                background: transparent;
                border: none;
                color: #888;
                cursor: pointer;
                font-size: 12px;
                border-bottom: 2px solid transparent;
                transition: all 0.2s;
            }

            .log-viewer-tab:hover {
                color: #fff;
                background: #383838;
            }

            .log-viewer-tab.active {
                color: #4fc3f7;
                border-bottom-color: #4fc3f7;
            }

            .log-viewer-toolbar {
                display: flex;
                gap: 8px;
                padding: 8px;
                background: #2d2d2d;
                border-bottom: 1px solid #444;
                flex-wrap: wrap;
            }

            .log-viewer-toolbar select,
            .log-viewer-toolbar input {
                background: #1e1e1e;
                border: 1px solid #444;
                color: #d4d4d4;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
            }

            .log-viewer-toolbar select:focus,
            .log-viewer-toolbar input:focus {
                outline: none;
                border-color: #4fc3f7;
            }

            .log-viewer-toolbar input {
                flex: 1;
                min-width: 100px;
            }

            .log-viewer-content {
                flex: 1;
                overflow-y: auto;
                padding: 8px;
            }

            .log-entry {
                padding: 4px 8px;
                margin-bottom: 2px;
                border-radius: 4px;
                display: flex;
                gap: 8px;
                align-items: flex-start;
                transition: background 0.2s;
            }

            .log-entry:hover {
                background: #2d2d2d;
            }

            .log-entry.level-log { border-left: 3px solid #888; }
            .log-entry.level-info { border-left: 3px solid #4fc3f7; }
            .log-entry.level-warn { border-left: 3px solid #ffb74d; color: #ffb74d; }
            .log-entry.level-error { border-left: 3px solid #f44336; color: #f44336; }
            .log-entry.level-debug { border-left: 3px solid #9e9e9e; color: #9e9e9e; }

            .log-time {
                color: #666;
                font-size: 10px;
                white-space: nowrap;
                min-width: 70px;
            }

            .log-level {
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                min-width: 40px;
            }

            .log-message {
                flex: 1;
                word-break: break-word;
                white-space: pre-wrap;
            }

            .action-entry {
                padding: 6px 10px;
                margin-bottom: 4px;
                background: #2d2d2d;
                border-radius: 4px;
                border-left: 3px solid #4fc3f7;
            }

            .action-entry.type-error,
            .action-entry.type-jsError,
            .action-entry.type-promiseRejection {
                border-left-color: #f44336;
            }

            .action-entry.type-search { border-left-color: #64b5f6; }
            .action-entry.type-filter { border-left-color: #81c784; }
            .action-entry.type-sort { border-left-color: #ffb74d; }
            .action-entry.type-tabSwitch { border-left-color: #ba68c8; }
            .action-entry.type-pagination { border-left-color: #4db6ac; }

            .action-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 4px;
            }

            .action-type {
                font-weight: 600;
                color: #fff;
            }

            .action-time {
                color: #666;
                font-size: 10px;
            }

            .action-meta {
                font-size: 11px;
                color: #888;
            }

            .log-viewer-footer {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 6px 12px;
                background: #2d2d2d;
                border-top: 1px solid #444;
                font-size: 10px;
                color: #666;
            }

            .log-viewer-toggle-btn {
                position: fixed;
                z-index: 99998;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 50%;
                width: 48px;
                height: 48px;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                font-size: 20px;
                transition: all 0.3s;
            }

            .log-viewer-toggle-btn:hover {
                transform: scale(1.1);
            }

            .log-viewer-toggle-btn.has-errors {
                background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
                animation: pulse-error 2s infinite;
            }

            @keyframes pulse-error {
                0%, 100% { box-shadow: 0 4px 12px rgba(244, 67, 54, 0.3); }
                50% { box-shadow: 0 4px 20px rgba(244, 67, 54, 0.6); }
            }

            .resize-handle {
                position: absolute;
                width: 10px;
                height: 10px;
                bottom: 0;
                left: 0;
                cursor: sw-resize;
            }
        `;
        document.head.appendChild(styles);
    }

    createPanel() {
        // トグルボタン
        if (this.config.showToggleButton) {
            this.toggleBtn = document.createElement('button');
            this.toggleBtn.className = 'log-viewer-toggle-btn';
            this.toggleBtn.innerHTML = '📋';
            this.toggleBtn.title = 'ログビューア';
            this.toggleBtn.style.right = '20px';
            this.toggleBtn.style.bottom = '20px';
            document.body.appendChild(this.toggleBtn);
        }

        // メインパネル
        this.panel = document.createElement('div');
        this.panel.className = 'log-viewer-panel';
        this.panel.style.right = this.config.position.right;
        this.panel.style.bottom = this.config.position.bottom;
        this.panel.style.width = this.config.size.width;
        this.panel.style.height = this.config.size.height;

        if (this.isMinimized) {
            this.panel.classList.add('minimized');
        }

        this.panel.innerHTML = `
            <div class="log-viewer-header">
                <div class="log-viewer-title">
                    <span>📋 Log Viewer</span>
                    <span class="badge" id="log-count">0</span>
                </div>
                <div class="log-viewer-controls">
                    <button class="log-viewer-btn" id="btn-minimize" title="最小化">−</button>
                    <button class="log-viewer-btn" id="btn-export" title="エクスポート">💾</button>
                    <button class="log-viewer-btn" id="btn-clear" title="クリア">🗑️</button>
                    <button class="log-viewer-btn" id="btn-close" title="閉じる">✕</button>
                </div>
            </div>
            <div class="log-viewer-tabs">
                <button class="log-viewer-tab ${this.currentTab === 'logs' ? 'active' : ''}" data-tab="logs">ログ</button>
                <button class="log-viewer-tab ${this.currentTab === 'actions' ? 'active' : ''}" data-tab="actions">操作履歴</button>
                <button class="log-viewer-tab ${this.currentTab === 'stats' ? 'active' : ''}" data-tab="stats">統計</button>
            </div>
            <div class="log-viewer-toolbar">
                <select id="level-filter">
                    <option value="all">全レベル</option>
                    <option value="error">Error</option>
                    <option value="warn">Warn</option>
                    <option value="info">Info</option>
                    <option value="log">Log</option>
                    <option value="debug">Debug</option>
                </select>
                <input type="text" id="search-filter" placeholder="検索...">
                <label style="color: #888; font-size: 11px; display: flex; align-items: center; gap: 4px;">
                    <input type="checkbox" id="auto-scroll" ${this.config.autoScroll ? 'checked' : ''}>
                    自動スクロール
                </label>
            </div>
            <div class="log-viewer-content" id="log-content">
                <!-- ログエントリがここに追加される -->
            </div>
            <div class="log-viewer-footer">
                <span id="status-text">Ready</span>
                <span id="session-info">Session: ${this.logCollector?.sessionId?.slice(-8) || 'N/A'}</span>
            </div>
            <div class="resize-handle"></div>
        `;

        document.body.appendChild(this.panel);

        // 要素参照
        this.contentEl = this.panel.querySelector('#log-content');
        this.logCountEl = this.panel.querySelector('#log-count');
        this.statusEl = this.panel.querySelector('#status-text');
    }

    bindEvents() {
        // トグルボタン
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', () => this.togglePanel());
        }

        // ヘッダードラッグ
        const header = this.panel.querySelector('.log-viewer-header');
        this.initDrag(header);

        // コントロールボタン
        this.panel.querySelector('#btn-minimize').addEventListener('click', () => this.toggleMinimize());
        this.panel.querySelector('#btn-export').addEventListener('click', () => this.showExportDialog());
        this.panel.querySelector('#btn-clear').addEventListener('click', () => this.clearAll());
        this.panel.querySelector('#btn-close').addEventListener('click', () => this.hidePanel());

        // タブ切り替え
        this.panel.querySelectorAll('.log-viewer-tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // フィルター
        this.panel.querySelector('#level-filter').addEventListener('change', (e) => {
            this.filters.level = e.target.value;
            this.renderContent();
        });

        this.panel.querySelector('#search-filter').addEventListener('input', (e) => {
            this.filters.search = e.target.value.toLowerCase();
            this.renderContent();
        });

        this.panel.querySelector('#auto-scroll').addEventListener('change', (e) => {
            this.config.autoScroll = e.target.checked;
        });

        // リサイズハンドル
        this.initResize();
    }

    initDrag(handle) {
        let isDragging = false;
        let startX, startY, startRight, startBottom;

        handle.addEventListener('mousedown', (e) => {
            if (e.target.closest('.log-viewer-btn')) return;

            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            startRight = parseInt(this.panel.style.right) || 20;
            startBottom = parseInt(this.panel.style.bottom) || 20;

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });

        const onMouseMove = (e) => {
            if (!isDragging) return;

            const deltaX = startX - e.clientX;
            const deltaY = startY - e.clientY;

            this.panel.style.right = Math.max(0, startRight + deltaX) + 'px';
            this.panel.style.bottom = Math.max(0, startBottom + deltaY) + 'px';
        };

        const onMouseUp = () => {
            isDragging = false;
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
    }

    initResize() {
        const handle = this.panel.querySelector('.resize-handle');
        let isResizing = false;
        let startX, startY, startWidth, startHeight;

        handle.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;
            startWidth = this.panel.offsetWidth;
            startHeight = this.panel.offsetHeight;

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });

        const onMouseMove = (e) => {
            if (!isResizing) return;

            const deltaX = startX - e.clientX;
            const deltaY = startY - e.clientY;

            this.panel.style.width = Math.max(300, startWidth + deltaX) + 'px';
            this.panel.style.height = Math.max(200, startHeight + deltaY) + 'px';
        };

        const onMouseUp = () => {
            isResizing = false;
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
    }

    async loadExistingLogs() {
        if (this.logCollector) {
            const logs = await this.logCollector.getLogs({ limit: this.config.maxDisplayLogs });
            this.displayedLogs = logs.reverse();
        }

        if (this.actionTracker) {
            this.displayedActions = this.actionTracker.getActions({ limit: this.config.maxDisplayLogs });
        }

        this.renderContent();
        this.updateLogCount();
    }

    addLogEntry(entry) {
        this.displayedLogs.push(entry);
        if (this.displayedLogs.length > this.config.maxDisplayLogs) {
            this.displayedLogs.shift();
        }

        if (this.currentTab === 'logs') {
            this.appendLogEntryToDOM(entry);
        }

        this.updateLogCount();

        // エラー時にトグルボタンをハイライト
        if (entry.level === 'error' && this.toggleBtn) {
            this.toggleBtn.classList.add('has-errors');
        }
    }

    addActionEntry(action) {
        this.displayedActions.unshift(action);
        if (this.displayedActions.length > this.config.maxDisplayLogs) {
            this.displayedActions.pop();
        }

        if (this.currentTab === 'actions') {
            this.prependActionEntryToDOM(action);
        }
    }

    appendLogEntryToDOM(entry) {
        if (!this.matchesFilters(entry)) return;

        const entryEl = this.createLogEntryElement(entry);
        this.contentEl.appendChild(entryEl);

        if (this.config.autoScroll) {
            this.contentEl.scrollTop = this.contentEl.scrollHeight;
        }
    }

    prependActionEntryToDOM(action) {
        const entryEl = this.createActionEntryElement(action);
        this.contentEl.insertBefore(entryEl, this.contentEl.firstChild);
    }

    createLogEntryElement(entry) {
        const div = document.createElement('div');
        div.className = `log-entry level-${entry.level}`;

        const time = new Date(entry.timestamp).toLocaleTimeString('ja-JP');
        const message = this.escapeHtml(entry.message);

        div.innerHTML = `
            <span class="log-time">${time}</span>
            <span class="log-level">${entry.level}</span>
            <span class="log-message">${message}</span>
        `;

        return div;
    }

    createActionEntryElement(action) {
        const div = document.createElement('div');
        div.className = `action-entry type-${action.type}`;

        const time = new Date(action.timestamp).toLocaleTimeString('ja-JP');
        const typeLabel = this.getActionTypeLabel(action.type);
        const metaStr = this.formatActionMetadata(action.metadata);

        div.innerHTML = `
            <div class="action-header">
                <span class="action-type">${typeLabel}</span>
                <span class="action-time">${time}</span>
            </div>
            <div class="action-meta">${metaStr}</div>
        `;

        return div;
    }

    getActionTypeLabel(type) {
        const labels = {
            search: '🔍 検索',
            searchSubmit: '🔍 検索実行',
            filter: '🏷️ フィルタ',
            sort: '↕️ ソート',
            tabSwitch: '📑 タブ切替',
            pagination: '📄 ページ移動',
            pageJump: '📄 ページジャンプ',
            itemsPerPageChange: '📊 表示件数',
            jsError: '❌ JSエラー',
            promiseRejection: '⚠️ Promise拒否',
        };
        return labels[type] || type;
    }

    formatActionMetadata(metadata) {
        if (!metadata || Object.keys(metadata).length === 0) return '-';

        return Object.entries(metadata)
            .map(([k, v]) => `${k}: ${this.escapeHtml(String(v))}`)
            .join(' | ');
    }

    matchesFilters(entry) {
        if (this.filters.level !== 'all' && entry.level !== this.filters.level) {
            return false;
        }

        if (this.filters.search && !entry.message.toLowerCase().includes(this.filters.search)) {
            return false;
        }

        return true;
    }

    renderContent() {
        this.contentEl.innerHTML = '';

        if (this.currentTab === 'logs') {
            const filtered = this.displayedLogs.filter(e => this.matchesFilters(e));
            filtered.forEach(entry => {
                this.contentEl.appendChild(this.createLogEntryElement(entry));
            });

            if (this.config.autoScroll) {
                this.contentEl.scrollTop = this.contentEl.scrollHeight;
            }
        } else if (this.currentTab === 'actions') {
            this.displayedActions.forEach(action => {
                this.contentEl.appendChild(this.createActionEntryElement(action));
            });
        } else if (this.currentTab === 'stats') {
            this.renderStats();
        }
    }

    async renderStats() {
        const logStats = this.logCollector ? await this.logCollector.getStats() : null;
        const actionStats = this.actionTracker ? this.actionTracker.getStats() : null;

        let html = '<div style="padding: 10px;">';

        if (logStats) {
            html += `
                <h3 style="color: #fff; margin: 0 0 10px;">ログ統計</h3>
                <div style="margin-bottom: 15px;">
                    <div>総ログ数: <strong>${logStats.totalLogs}</strong></div>
                    <div style="margin-top: 8px;">
                        ${Object.entries(logStats.byLevel).map(([level, count]) => `
                            <span style="display: inline-block; margin-right: 10px;">
                                ${level}: <strong>${count}</strong>
                            </span>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        if (actionStats) {
            html += `
                <h3 style="color: #fff; margin: 0 0 10px;">操作統計</h3>
                <div>
                    <div>総操作数: <strong>${actionStats.totalActions}</strong></div>
                    <div style="margin-top: 8px;">
                        ${Object.entries(actionStats.byType).map(([type, count]) => `
                            <span style="display: inline-block; margin-right: 10px;">
                                ${type}: <strong>${count}</strong>
                            </span>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        html += '</div>';
        this.contentEl.innerHTML = html;
    }

    updateLogCount() {
        const errorCount = this.displayedLogs.filter(l => l.level === 'error').length;
        const total = this.displayedLogs.length;

        this.logCountEl.textContent = errorCount > 0 ? `${errorCount}❌ / ${total}` : total;
    }

    switchTab(tab) {
        this.currentTab = tab;

        this.panel.querySelectorAll('.log-viewer-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });

        this.renderContent();
    }

    togglePanel() {
        if (this.panel.style.display === 'none') {
            this.showPanel();
        } else {
            this.hidePanel();
        }
    }

    showPanel() {
        this.panel.style.display = 'flex';
        if (this.toggleBtn) {
            this.toggleBtn.classList.remove('has-errors');
        }
    }

    hidePanel() {
        this.panel.style.display = 'none';
    }

    toggleMinimize() {
        this.isMinimized = !this.isMinimized;
        this.panel.classList.toggle('minimized', this.isMinimized);
    }

    async showExportDialog() {
        const format = prompt('エクスポート形式を選択 (json / jsonl / csv):', 'json');
        if (!format) return;

        try {
            let data, filename, mimeType;

            if (this.currentTab === 'logs') {
                data = await this.logCollector.exportLogs(format);
                filename = `logs_${new Date().toISOString().slice(0, 10)}.${format === 'jsonl' ? 'jsonl' : format}`;
            } else if (this.currentTab === 'actions') {
                data = this.actionTracker.exportActions(format);
                filename = `actions_${new Date().toISOString().slice(0, 10)}.${format === 'jsonl' ? 'jsonl' : format}`;
            }

            mimeType = format === 'csv' ? 'text/csv' : 'application/json';
            this.downloadFile(data, filename, mimeType);

            this.statusEl.textContent = `エクスポート完了: ${filename}`;
        } catch (e) {
            alert('エクスポートエラー: ' + e.message);
        }
    }

    downloadFile(data, filename, mimeType) {
        const blob = new Blob([data], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    async clearAll() {
        if (!confirm('ログと操作履歴をクリアしますか？')) return;

        if (this.logCollector) {
            await this.logCollector.clearLogs();
        }
        if (this.actionTracker) {
            this.actionTracker.clearActions();
        }

        this.displayedLogs = [];
        this.displayedActions = [];
        this.renderContent();
        this.updateLogCount();
        this.statusEl.textContent = 'クリア完了';
    }

    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    destroy() {
        if (this.panel) {
            this.panel.remove();
        }
        if (this.toggleBtn) {
            this.toggleBtn.remove();
        }
    }
}

// グローバルエクスポート
window.LogViewer = LogViewer;

// 自動初期化用のヘルパー
window.initLogMonitoring = function(options = {}) {
    // LogCollector初期化
    const logCollector = new LogCollector({
        maxEntries: options.maxEntries || 10000,
        flushInterval: options.flushInterval || 5000,
        enableRemote: options.enableRemote || false,
        remoteEndpoint: options.remoteEndpoint || '/api/logs',
    });

    // ActionTracker初期化
    const actionTracker = new ActionTracker(logCollector, {
        maxActions: options.maxActions || 1000,
    });

    // LogViewer初期化
    const logViewer = new LogViewer(logCollector, actionTracker, {
        maxDisplayLogs: options.maxDisplayLogs || 200,
        autoScroll: options.autoScroll !== false,
        minimized: options.minimized || false,
    });

    // グローバル参照
    window.logCollector = logCollector;
    window.actionTracker = actionTracker;
    window.logViewer = logViewer;

    return { logCollector, actionTracker, logViewer };
};
