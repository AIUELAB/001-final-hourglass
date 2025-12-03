/**
 * ActionTracker - ユーザー操作追跡モジュール
 *
 * 追跡対象:
 * - 検索・フィルタ操作
 * - ソート変更
 * - ページネーション
 * - タブ切り替え
 * - データ更新イベント
 * - エラー発生
 *
 * @version 1.0.0
 * @author EPUP System
 */

class ActionTracker {
    constructor(logCollector, options = {}) {
        this.logCollector = logCollector;
        this.config = {
            maxActions: options.maxActions || 1000,
            debounceMs: options.debounceMs || 500,
            trackMouseEvents: options.trackMouseEvents || false,
            autoBindEvents: options.autoBindEvents !== false,
        };

        this.actions = [];
        this.callbacks = [];
        this.debounceTimers = {};
        this.isInitialized = false;

        if (this.config.autoBindEvents) {
            // DOMContentLoadedを待って初期化
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.init());
            } else {
                this.init();
            }
        }
    }

    init() {
        this.initEventListeners();
        this.isInitialized = true;
        console.log('📋 ActionTracker初期化完了');
    }

    initEventListeners() {
        // 検索入力
        this.bindSearchInput();

        // フィルター変更
        this.bindFilterSelects();

        // ソート変更
        this.bindSortables();

        // タブ切り替え
        this.bindTabButtons();

        // ページネーション
        this.bindPagination();

        // 表示件数変更
        this.bindItemsPerPage();

        // グローバルエラー
        this.bindErrorHandlers();

        // MutationObserverで動的要素を監視
        this.initMutationObserver();
    }

    bindSearchInput() {
        const searchInputs = document.querySelectorAll('#search-input, .search-input, [data-action-track="search"]');
        searchInputs.forEach(input => {
            if (input._actionTrackerBound) return;
            input._actionTrackerBound = true;

            input.addEventListener('input', this.debounce((e) => {
                this.trackAction('search', {
                    query: e.target.value,
                    inputId: e.target.id || null,
                });
            }, this.config.debounceMs));

            // Enterキーでの検索
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    this.trackAction('searchSubmit', {
                        query: e.target.value,
                        inputId: e.target.id || null,
                    });
                }
            });
        });
    }

    bindFilterSelects() {
        const filterSelects = document.querySelectorAll('.filter-select, [data-action-track="filter"]');
        filterSelects.forEach(select => {
            if (select._actionTrackerBound) return;
            select._actionTrackerBound = true;

            select.addEventListener('change', (e) => {
                this.trackAction('filter', {
                    filterType: e.target.id || e.target.name || e.target.dataset.filterType,
                    value: e.target.value,
                    selectedText: e.target.options?.[e.target.selectedIndex]?.text,
                });
            });
        });
    }

    bindSortables() {
        const sortables = document.querySelectorAll('.sortable, .sortable-label, [data-action-track="sort"]');
        sortables.forEach(el => {
            if (el._actionTrackerBound) return;
            el._actionTrackerBound = true;

            el.addEventListener('click', (e) => {
                const sortEl = e.target.closest('[data-sort]');
                if (sortEl) {
                    this.trackAction('sort', {
                        field: sortEl.dataset.sort,
                        elementId: sortEl.id || null,
                    });
                }
            });
        });
    }

    bindTabButtons() {
        const tabButtons = document.querySelectorAll('.tab-button, [data-action-track="tab"]');
        tabButtons.forEach(btn => {
            if (btn._actionTrackerBound) return;
            btn._actionTrackerBound = true;

            btn.addEventListener('click', (e) => {
                const tab = e.target.closest('.tab-button, [data-tab]');
                if (tab) {
                    this.trackAction('tabSwitch', {
                        tab: tab.dataset.tab || tab.textContent?.trim(),
                        previousTab: document.querySelector('.tab-button.active')?.dataset?.tab,
                    });
                }
            });
        });
    }

    bindPagination() {
        const paginationIds = ['btn-first-page', 'btn-prev-page', 'btn-next-page', 'btn-last-page'];
        paginationIds.forEach(id => {
            const btn = document.getElementById(id);
            if (btn && !btn._actionTrackerBound) {
                btn._actionTrackerBound = true;

                btn.addEventListener('click', () => {
                    this.trackAction('pagination', {
                        action: id.replace('btn-', '').replace('-page', ''),
                        currentPage: typeof window.currentPage !== 'undefined' ? window.currentPage : null,
                        totalPages: typeof window.getTotalPages === 'function' ? window.getTotalPages() : null,
                    });
                });
            }
        });

        // ページ番号直接入力
        const pageInput = document.getElementById('page-input');
        if (pageInput && !pageInput._actionTrackerBound) {
            pageInput._actionTrackerBound = true;

            pageInput.addEventListener('change', (e) => {
                this.trackAction('pageJump', {
                    targetPage: parseInt(e.target.value, 10),
                    currentPage: typeof window.currentPage !== 'undefined' ? window.currentPage : null,
                });
            });
        }
    }

    bindItemsPerPage() {
        const itemsPerPageSelect = document.getElementById('items-per-page');
        if (itemsPerPageSelect && !itemsPerPageSelect._actionTrackerBound) {
            itemsPerPageSelect._actionTrackerBound = true;

            itemsPerPageSelect.addEventListener('change', (e) => {
                this.trackAction('itemsPerPageChange', {
                    value: e.target.value,
                    previousValue: typeof window.itemsPerPage !== 'undefined' ? window.itemsPerPage : null,
                });
            });
        }
    }

    bindErrorHandlers() {
        // グローバルエラーは LogCollector が既にキャッチしているので、
        // ここではアクションとして記録するのみ
        window.addEventListener('error', (e) => {
            this.trackAction('jsError', {
                message: e.message,
                filename: e.filename,
                lineno: e.lineno,
                colno: e.colno,
            });
        });

        window.addEventListener('unhandledrejection', (e) => {
            this.trackAction('promiseRejection', {
                reason: e.reason?.message || String(e.reason),
            });
        });
    }

    initMutationObserver() {
        // 動的に追加される要素を監視
        const observer = new MutationObserver((mutations) => {
            let needsRebind = false;

            mutations.forEach(mutation => {
                if (mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            // 新しい要素にイベントをバインド
                            if (node.matches?.('.sortable, .sortable-label, .filter-select, .tab-button, [data-action-track]')) {
                                needsRebind = true;
                            }
                            if (node.querySelector?.('.sortable, .sortable-label, .filter-select, .tab-button, [data-action-track]')) {
                                needsRebind = true;
                            }
                        }
                    });
                }
            });

            if (needsRebind) {
                this.bindSortables();
                this.bindFilterSelects();
                this.bindTabButtons();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
        });
    }

    trackAction(type, metadata = {}) {
        const action = {
            id: this.generateActionId(),
            timestamp: new Date().toISOString(),
            timestampMs: Date.now(),
            type: type,
            metadata: metadata,
            context: this.getContext(),
            sessionId: this.logCollector?.sessionId || null,
        };

        // LogCollectorと連携（操作IDを設定）
        if (this.logCollector) {
            this.logCollector.startOperation(type, metadata);
        }

        // 内部配列に追加
        this.actions.unshift(action);
        if (this.actions.length > this.config.maxActions) {
            this.actions.pop();
        }

        // コールバック通知
        this.notifyCallbacks(action);

        // カスタムイベント発火
        window.dispatchEvent(new CustomEvent('actionTracker:newAction', {
            detail: action
        }));

        return action.id;
    }

    generateActionId() {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substr(2, 6);
        return `act_${timestamp}_${random}`;
    }

    getContext() {
        const context = {
            url: window.location.href,
            pathname: window.location.pathname,
            activeTab: null,
            resultCount: null,
            currentPage: null,
            viewportWidth: window.innerWidth,
            viewportHeight: window.innerHeight,
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
        } catch (e) {
            // コンテキスト取得エラーは無視
        }

        return context;
    }

    // 外部から操作を終了
    endCurrentOperation(result = 'success', error = null) {
        if (this.logCollector) {
            return this.logCollector.endOperation(result, error);
        }
        return null;
    }

    // コールバック登録
    onAction(callback) {
        this.callbacks.push(callback);
        return () => {
            const index = this.callbacks.indexOf(callback);
            if (index > -1) {
                this.callbacks.splice(index, 1);
            }
        };
    }

    notifyCallbacks(action) {
        this.callbacks.forEach(cb => {
            try {
                cb(action);
            } catch (e) {
                console.warn('ActionTrackerコールバックエラー:', e);
            }
        });
    }

    // アクション取得
    getActions(options = {}) {
        const { type, limit = 100, startTime, endTime } = options;
        let filtered = this.actions;

        if (type) {
            filtered = filtered.filter(a => a.type === type);
        }

        if (startTime) {
            filtered = filtered.filter(a => new Date(a.timestamp) >= new Date(startTime));
        }

        if (endTime) {
            filtered = filtered.filter(a => new Date(a.timestamp) <= new Date(endTime));
        }

        return filtered.slice(0, limit);
    }

    // アクションの統計
    getStats() {
        const stats = {
            totalActions: this.actions.length,
            byType: {},
            recentErrors: [],
            timeRange: {
                start: this.actions.length > 0 ? this.actions[this.actions.length - 1].timestamp : null,
                end: this.actions.length > 0 ? this.actions[0].timestamp : null,
            },
        };

        this.actions.forEach(action => {
            stats.byType[action.type] = (stats.byType[action.type] || 0) + 1;

            if (action.type === 'jsError' || action.type === 'promiseRejection') {
                if (stats.recentErrors.length < 10) {
                    stats.recentErrors.push(action);
                }
            }
        });

        return stats;
    }

    // 操作とログの紐付け検索
    async getLogsForAction(actionId) {
        if (!this.logCollector) return [];

        const action = this.actions.find(a => a.id === actionId);
        if (!action) return [];

        // 操作の前後5秒のログを取得
        const startTime = new Date(action.timestampMs - 1000).toISOString();
        const endTime = new Date(action.timestampMs + 5000).toISOString();

        return this.logCollector.getLogs({ startTime, endTime });
    }

    // エクスポート
    exportActions(format = 'json') {
        switch (format) {
            case 'json':
                return JSON.stringify(this.actions, null, 2);

            case 'jsonl':
                return this.actions.map(a => JSON.stringify(a)).join('\n');

            case 'csv': {
                const headers = ['timestamp', 'type', 'metadata', 'context'];
                const rows = this.actions.map(a => [
                    a.timestamp,
                    a.type,
                    `"${JSON.stringify(a.metadata).replace(/"/g, '""')}"`,
                    `"${JSON.stringify(a.context).replace(/"/g, '""')}"`,
                ]);
                return [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
            }

            default:
                throw new Error(`Unknown format: ${format}`);
        }
    }

    // クリア
    clearActions() {
        this.actions = [];
        console.log('🗑️ アクション履歴をクリアしました');
    }

    // デバウンス用ユーティリティ
    debounce(func, wait) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // 特定タイプのアクション数をカウント
    countByType(type, withinMs = null) {
        let filtered = this.actions.filter(a => a.type === type);

        if (withinMs) {
            const threshold = Date.now() - withinMs;
            filtered = filtered.filter(a => a.timestampMs >= threshold);
        }

        return filtered.length;
    }
}

// グローバルエクスポート
window.ActionTracker = ActionTracker;
