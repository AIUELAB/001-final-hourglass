/**
 * LogCollector - コンソールログ自動収集モジュール
 *
 * 機能:
 * - console.log/warn/error/info/debug をフックして自動収集
 * - IndexedDBへの永続化
 * - タイムスタンプ・コンテキスト自動付与
 * - リアルタイムビューア連携
 * - JSON/CSV/JSONLエクスポート
 *
 * @version 1.0.0
 * @author EPUP System
 */

class LogCollector {
    constructor(options = {}) {
        // 設定
        this.config = {
            dbName: options.dbName || 'DashboardLogs',
            dbVersion: options.dbVersion || 1,
            maxEntries: options.maxEntries || 10000,
            flushInterval: options.flushInterval || 5000,
            enableRemote: options.enableRemote || false,
            remoteEndpoint: options.remoteEndpoint || '/api/logs',
            contextExtractor: options.contextExtractor || this.defaultContextExtractor.bind(this),
            logLevels: options.logLevels || ['log', 'warn', 'error', 'info', 'debug'],
        };

        // 内部状態
        this.buffer = [];
        this.sessionId = this.generateSessionId();
        this.operationId = null;
        this.db = null;
        this.isInitialized = false;
        this.viewerCallbacks = [];
        this.flushTimer = null;

        // 元のconsoleメソッドを退避
        this.originalConsole = {};
        this.config.logLevels.forEach(level => {
            if (console[level]) {
                this.originalConsole[level] = console[level].bind(console);
            }
        });

        // 初期化
        this.init();
    }

    async init() {
        try {
            await this.initDatabase();
            this.hookConsoleMethods();
            this.startFlushTimer();

            // ページアンロード時の保存
            window.addEventListener('beforeunload', () => {
                this.flush();
            });

            // エラーイベントのキャッチ
            window.addEventListener('error', (event) => {
                this.captureError('uncaughtError', {
                    message: event.message,
                    filename: event.filename,
                    lineno: event.lineno,
                    colno: event.colno,
                    error: event.error,
                });
            });

            window.addEventListener('unhandledrejection', (event) => {
                this.captureError('unhandledRejection', {
                    reason: event.reason?.message || String(event.reason),
                    stack: event.reason?.stack,
                });
            });

            this.isInitialized = true;
            this.originalConsole.log?.('🔧 LogCollector初期化完了 (session:', this.sessionId, ')');

        } catch (error) {
            console.error('LogCollector初期化エラー:', error);
        }
    }

    async initDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.config.dbName, this.config.dbVersion);

            request.onerror = () => reject(request.error);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // ログエントリストア
                if (!db.objectStoreNames.contains('logs')) {
                    const logStore = db.createObjectStore('logs', {
                        keyPath: 'id',
                        autoIncrement: true
                    });
                    logStore.createIndex('timestamp', 'timestamp');
                    logStore.createIndex('level', 'level');
                    logStore.createIndex('sessionId', 'sessionId');
                    logStore.createIndex('operationId', 'operationId');
                }

                // 操作履歴ストア
                if (!db.objectStoreNames.contains('operations')) {
                    const opStore = db.createObjectStore('operations', {
                        keyPath: 'id'
                    });
                    opStore.createIndex('timestamp', 'timestamp');
                    opStore.createIndex('type', 'type');
                    opStore.createIndex('sessionId', 'sessionId');
                }

                // セッション情報ストア
                if (!db.objectStoreNames.contains('sessions')) {
                    const sessionStore = db.createObjectStore('sessions', {
                        keyPath: 'sessionId'
                    });
                    sessionStore.createIndex('startTime', 'startTime');
                }
            };

            request.onsuccess = () => {
                this.db = request.result;

                // セッション情報を記録
                this.saveSession({
                    sessionId: this.sessionId,
                    startTime: new Date().toISOString(),
                    userAgent: navigator.userAgent,
                    url: window.location.href,
                });

                resolve();
            };
        });
    }

    hookConsoleMethods() {
        const self = this;

        this.config.logLevels.forEach(level => {
            if (!self.originalConsole[level]) return;

            console[level] = function(...args) {
                // 元のconsoleを呼び出し
                self.originalConsole[level](...args);

                // 自己参照によるループ防止
                if (self._isLogging) return;
                self._isLogging = true;

                try {
                    // ログエントリ作成
                    const entry = self.createLogEntry(level, args);

                    // バッファに追加
                    self.buffer.push(entry);

                    // リアルタイムビューア通知
                    self.notifyViewers(entry);
                } finally {
                    self._isLogging = false;
                }
            };
        });
    }

    createLogEntry(level, args) {
        const now = new Date();
        return {
            timestamp: now.toISOString(),
            timestampMs: now.getTime(),
            level: level,
            message: this.formatMessage(args),
            rawArgs: args.map(arg => this.serializeArg(arg)),
            sessionId: this.sessionId,
            operationId: this.operationId,
            context: this.config.contextExtractor(),
            url: window.location.href,
            pathname: window.location.pathname,
        };
    }

    formatMessage(args) {
        return args.map(arg => {
            if (arg === null) return 'null';
            if (arg === undefined) return 'undefined';
            if (typeof arg === 'object') {
                try {
                    if (arg instanceof Error) {
                        return `${arg.name}: ${arg.message}`;
                    }
                    return JSON.stringify(arg);
                } catch {
                    return String(arg);
                }
            }
            return String(arg);
        }).join(' ');
    }

    serializeArg(arg) {
        if (arg === null) return null;
        if (arg === undefined) return undefined;

        if (arg instanceof Error) {
            return {
                _type: 'Error',
                name: arg.name,
                message: arg.message,
                stack: arg.stack,
            };
        }

        if (arg instanceof HTMLElement) {
            return {
                _type: 'HTMLElement',
                tagName: arg.tagName,
                id: arg.id,
                className: arg.className,
            };
        }

        if (typeof arg === 'function') {
            return {
                _type: 'Function',
                name: arg.name || 'anonymous',
            };
        }

        if (typeof arg === 'object') {
            try {
                // 循環参照対策
                const seen = new WeakSet();
                return JSON.parse(JSON.stringify(arg, (key, value) => {
                    if (typeof value === 'object' && value !== null) {
                        if (seen.has(value)) {
                            return '[Circular]';
                        }
                        seen.add(value);
                    }
                    return value;
                }));
            } catch {
                return { _type: 'unserializable', toString: String(arg) };
            }
        }

        return arg;
    }

    defaultContextExtractor() {
        const context = {
            activeTab: null,
            resultCount: null,
            currentPage: null,
            searchQuery: null,
        };

        try {
            const activeTab = document.querySelector('.tab-button.active');
            if (activeTab) {
                context.activeTab = activeTab.dataset?.tab || activeTab.textContent?.trim();
            }

            const resultCount = document.getElementById('result-count');
            if (resultCount) {
                context.resultCount = resultCount.textContent?.trim();
            }

            if (typeof window.currentPage !== 'undefined') {
                context.currentPage = window.currentPage;
            }

            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                context.searchQuery = searchInput.value;
            }
        } catch (e) {
            // コンテキスト取得エラーは無視
        }

        return context;
    }

    captureError(type, errorInfo) {
        const entry = {
            timestamp: new Date().toISOString(),
            timestampMs: Date.now(),
            level: 'error',
            message: `[${type}] ${errorInfo.message || errorInfo.reason || 'Unknown error'}`,
            rawArgs: [errorInfo],
            sessionId: this.sessionId,
            operationId: this.operationId,
            context: this.config.contextExtractor(),
            url: window.location.href,
            pathname: window.location.pathname,
            errorType: type,
        };

        this.buffer.push(entry);
        this.notifyViewers(entry);
    }

    // 操作ID管理
    startOperation(type, metadata = {}) {
        this.operationId = `op_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

        const operation = {
            id: this.operationId,
            type: type,
            startTime: new Date().toISOString(),
            metadata: metadata,
            sessionId: this.sessionId,
            status: 'in_progress',
        };

        this.saveOperation(operation);

        return this.operationId;
    }

    endOperation(result = 'success', error = null) {
        if (this.operationId) {
            this.updateOperation(this.operationId, {
                endTime: new Date().toISOString(),
                status: result,
                error: error ? { message: error.message, stack: error.stack } : null,
            });
        }
        const completedOpId = this.operationId;
        this.operationId = null;
        return completedOpId;
    }

    async saveOperation(operation) {
        if (!this.db) return;

        try {
            const tx = this.db.transaction('operations', 'readwrite');
            const store = tx.objectStore('operations');
            store.put(operation);
        } catch (e) {
            this.originalConsole.warn?.('Operation保存エラー:', e);
        }
    }

    async updateOperation(operationId, updates) {
        if (!this.db) return;

        try {
            const tx = this.db.transaction('operations', 'readwrite');
            const store = tx.objectStore('operations');

            const request = store.get(operationId);
            request.onsuccess = () => {
                const operation = request.result;
                if (operation) {
                    Object.assign(operation, updates);
                    store.put(operation);
                }
            };
        } catch (e) {
            this.originalConsole.warn?.('Operation更新エラー:', e);
        }
    }

    async saveSession(session) {
        if (!this.db) return;

        try {
            const tx = this.db.transaction('sessions', 'readwrite');
            const store = tx.objectStore('sessions');
            store.put(session);
        } catch (e) {
            this.originalConsole.warn?.('Session保存エラー:', e);
        }
    }

    // IndexedDBへのフラッシュ
    async flush() {
        if (this.buffer.length === 0 || !this.db) return;

        const entries = this.buffer.splice(0, this.buffer.length);

        try {
            const tx = this.db.transaction('logs', 'readwrite');
            const store = tx.objectStore('logs');

            for (const entry of entries) {
                store.add(entry);
            }

            await new Promise((resolve, reject) => {
                tx.oncomplete = resolve;
                tx.onerror = () => reject(tx.error);
            });

            // 古いエントリの削除
            await this.pruneOldEntries();

            // リモート送信
            if (this.config.enableRemote && entries.length > 0) {
                this.sendToRemote(entries);
            }

        } catch (e) {
            this.originalConsole.warn?.('LogCollector flush エラー:', e);
            // エントリをバッファに戻す
            this.buffer.unshift(...entries);
        }
    }

    async pruneOldEntries() {
        if (!this.db) return;

        try {
            const tx = this.db.transaction('logs', 'readwrite');
            const store = tx.objectStore('logs');

            const countRequest = store.count();

            await new Promise((resolve) => {
                countRequest.onsuccess = async () => {
                    const count = countRequest.result;
                    if (count > this.config.maxEntries) {
                        const deleteCount = count - this.config.maxEntries;
                        const cursorRequest = store.openCursor();
                        let deleted = 0;

                        cursorRequest.onsuccess = (event) => {
                            const cursor = event.target.result;
                            if (cursor && deleted < deleteCount) {
                                cursor.delete();
                                deleted++;
                                cursor.continue();
                            } else {
                                resolve();
                            }
                        };
                    } else {
                        resolve();
                    }
                };
            });
        } catch (e) {
            this.originalConsole.warn?.('古いログ削除エラー:', e);
        }
    }

    startFlushTimer() {
        if (this.flushTimer) {
            clearInterval(this.flushTimer);
        }
        this.flushTimer = setInterval(() => this.flush(), this.config.flushInterval);
    }

    stopFlushTimer() {
        if (this.flushTimer) {
            clearInterval(this.flushTimer);
            this.flushTimer = null;
        }
    }

    generateSessionId() {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substr(2, 9);
        return `sess_${timestamp}_${random}`;
    }

    // ビューア通知
    onLogEntry(callback) {
        this.viewerCallbacks.push(callback);
        return () => {
            const index = this.viewerCallbacks.indexOf(callback);
            if (index > -1) {
                this.viewerCallbacks.splice(index, 1);
            }
        };
    }

    notifyViewers(entry) {
        this.viewerCallbacks.forEach(cb => {
            try {
                cb(entry);
            } catch (e) {
                this.originalConsole.warn?.('ビューアコールバックエラー:', e);
            }
        });

        // カスタムイベントも発火
        window.dispatchEvent(new CustomEvent('logCollector:newEntry', {
            detail: entry
        }));
    }

    // リモート送信
    async sendToRemote(entries) {
        try {
            const response = await fetch(this.config.remoteEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sessionId: this.sessionId,
                    entries: entries,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            this.originalConsole.warn?.('LogCollector: リモート送信失敗', error.message);
        }
    }

    // ログ取得API
    async getLogs(options = {}) {
        if (!this.db) return [];

        const {
            level,
            startTime,
            endTime,
            operationId,
            sessionId,
            limit = 1000,
            offset = 0,
        } = options;

        return new Promise((resolve, reject) => {
            try {
                const tx = this.db.transaction('logs', 'readonly');
                const store = tx.objectStore('logs');
                const logs = [];
                let skipped = 0;

                const cursorRequest = store.index('timestamp').openCursor(null, 'prev');

                cursorRequest.onsuccess = (event) => {
                    const cursor = event.target.result;
                    if (cursor && logs.length < limit) {
                        const entry = cursor.value;

                        // フィルタリング
                        let include = true;
                        if (level && entry.level !== level) include = false;
                        if (operationId && entry.operationId !== operationId) include = false;
                        if (sessionId && entry.sessionId !== sessionId) include = false;
                        if (startTime && new Date(entry.timestamp) < new Date(startTime)) include = false;
                        if (endTime && new Date(entry.timestamp) > new Date(endTime)) include = false;

                        if (include) {
                            if (skipped < offset) {
                                skipped++;
                            } else {
                                logs.push(entry);
                            }
                        }
                        cursor.continue();
                    } else {
                        resolve(logs);
                    }
                };

                cursorRequest.onerror = () => reject(cursorRequest.error);
            } catch (e) {
                reject(e);
            }
        });
    }

    // 統計取得
    async getStats() {
        if (!this.db) return null;

        const logs = await this.getLogs({ limit: this.config.maxEntries });

        const stats = {
            totalLogs: logs.length,
            byLevel: {},
            bySession: {},
            timeRange: {
                start: logs.length > 0 ? logs[logs.length - 1].timestamp : null,
                end: logs.length > 0 ? logs[0].timestamp : null,
            },
        };

        logs.forEach(log => {
            stats.byLevel[log.level] = (stats.byLevel[log.level] || 0) + 1;
            stats.bySession[log.sessionId] = (stats.bySession[log.sessionId] || 0) + 1;
        });

        return stats;
    }

    // 操作履歴取得
    async getOperations(options = {}) {
        if (!this.db) return [];

        const { type, sessionId, limit = 100 } = options;

        return new Promise((resolve, reject) => {
            try {
                const tx = this.db.transaction('operations', 'readonly');
                const store = tx.objectStore('operations');
                const operations = [];

                const cursorRequest = store.index('timestamp').openCursor(null, 'prev');

                cursorRequest.onsuccess = (event) => {
                    const cursor = event.target.result;
                    if (cursor && operations.length < limit) {
                        const op = cursor.value;

                        let include = true;
                        if (type && op.type !== type) include = false;
                        if (sessionId && op.sessionId !== sessionId) include = false;

                        if (include) {
                            operations.push(op);
                        }
                        cursor.continue();
                    } else {
                        resolve(operations);
                    }
                };

                cursorRequest.onerror = () => reject(cursorRequest.error);
            } catch (e) {
                reject(e);
            }
        });
    }

    // エクスポート
    async exportLogs(format = 'json', options = {}) {
        const logs = await this.getLogs({
            limit: options.limit || this.config.maxEntries,
            ...options,
        });

        switch (format) {
            case 'json':
                return JSON.stringify(logs, null, 2);

            case 'jsonl':
                return logs.map(l => JSON.stringify(l)).join('\n');

            case 'csv': {
                const headers = ['timestamp', 'level', 'message', 'operationId', 'sessionId'];
                const rows = logs.map(l => [
                    l.timestamp,
                    l.level,
                    `"${(l.message || '').replace(/"/g, '""')}"`,
                    l.operationId || '',
                    l.sessionId || '',
                ]);
                return [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
            }

            default:
                throw new Error(`Unknown format: ${format}`);
        }
    }

    // データベースクリア
    async clearLogs() {
        if (!this.db) return;

        const tx = this.db.transaction(['logs', 'operations'], 'readwrite');
        tx.objectStore('logs').clear();
        tx.objectStore('operations').clear();

        await new Promise((resolve) => {
            tx.oncomplete = resolve;
        });

        this.originalConsole.log?.('🗑️ ログをクリアしました');
    }

    // デストラクタ
    destroy() {
        this.stopFlushTimer();
        this.flush();

        // 元のconsoleを復元
        this.config.logLevels.forEach(level => {
            if (this.originalConsole[level]) {
                console[level] = this.originalConsole[level];
            }
        });

        if (this.db) {
            this.db.close();
            this.db = null;
        }

        this.isInitialized = false;
    }
}

// グローバルエクスポート
window.LogCollector = LogCollector;
