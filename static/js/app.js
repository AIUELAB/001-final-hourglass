// グローバル変数
let currentSection = 'containers';
let refreshInterval;

// DOM読み込み完了後の初期化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// アプリケーション初期化
function initializeApp() {
    setupEventListeners();
    loadInitialData();
    startAutoRefresh();
    initializeProgressUI();
}

// イベントリスナーの設定
function setupEventListeners() {
    // サイドバーナビゲーション
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.addEventListener('click', function() {
            const section = this.dataset.section;
            switchSection(section);
        });
    });

    // ヘッダーボタン
    document.getElementById('expandAll').addEventListener('click', toggleAllSections);
    document.getElementById('closeBtn').addEventListener('click', closeApplication);
}

// セクション切り替え
function switchSection(sectionName) {
    // 現在のセクションを非表示
    document.getElementById(`${currentSection}Section`).style.display = 'none';

    // サイドバーのアクティブ状態を更新
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-section="${sectionName}"]`).classList.add('active');

    // 新しいセクションを表示
    currentSection = sectionName;
    document.getElementById(`${sectionName}Section`).style.display = 'block';

    // セクションに応じたデータを読み込み
    switch(sectionName) {
        case 'containers':
            refreshContainers();
            break;
        case 'workflows':
            refreshWorkflows();
            break;
        case 'executions':
            refreshExecutions();
            break;
    }
}

// 全セクションの展開/折りたたみ
function toggleAllSections() {
    const button = document.getElementById('expandAll');
    const isExpanded = button.querySelector('i').classList.contains('fa-chevron-up');

    if (isExpanded) {
        button.querySelector('i').classList.replace('fa-chevron-up', 'fa-chevron-down');
        // 折りたたみ処理
    } else {
        button.querySelector('i').classList.replace('fa-chevron-down', 'fa-chevron-up');
        // 展開処理
    }
}

// アプリケーション終了
function closeApplication() {
    if (confirm('アプリケーションを終了しますか？')) {
        window.close();
    }
}

// 初期データ読み込み
function loadInitialData() {
    refreshContainers();
}

// 自動更新の開始
function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        switch(currentSection) {
            case 'containers':
                refreshContainers();
                break;
            case 'workflows':
                refreshWorkflows();
                break;
            case 'executions':
                refreshExecutions();
                break;
        }
    }, 10000); // 10秒ごとに更新
}

// Dockerコンテナ情報の更新
async function refreshContainers() {
    try {
        const response = await fetch('/api/containers');
        const data = await response.json();

        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        updateContainerList(data.containers);
    } catch (error) {
        showNotification('コンテナ情報の取得に失敗しました', 'error');
        console.error('Error fetching containers:', error);
    }
}

// コンテナリストの更新
function updateContainerList(containers) {
    const containerList = document.getElementById('containerList');
    containerList.innerHTML = '';

    if (containers.length === 0) {
        containerList.innerHTML = '<div class="no-data">コンテナが見つかりません</div>';
        return;
    }

    containers.forEach(container => {
        const containerItem = createContainerItem(container);
        containerList.appendChild(containerItem);
    });
}

// コンテナアイテムの作成
function createContainerItem(container) {
    const item = document.createElement('div');
    item.className = 'tree-item';

    const statusIcon = container.status === 'running' ? '▲' : '▼';
    const statusClass = container.status === 'running' ? 'status-running' : 'status-stopped';

    item.innerHTML = `
        <div class="container-item">
            <div class="container-status ${statusClass}">
                ${statusIcon}
            </div>
            <div class="container-info">
                <div class="container-name">${container.name}</div>
                <div class="container-details">
                    ${container.image} | ${container.status} | ID: ${container.id}
                </div>
            </div>
            <div class="container-actions">
                ${container.status === 'running'
                    ? `<button class="action-btn stop" onclick="stopContainer('${container.id}')">停止</button>`
                    : `<button class="action-btn start" onclick="startContainer('${container.id}')">起動</button>`
                }
                <button class="action-btn logs" onclick="showContainerLogs('${container.id}', '${container.name}')">ログ</button>
            </div>
        </div>
    `;

    return item;
}

// n8nワークフロー情報の更新
async function refreshWorkflows() {
    try {
        const response = await fetch('/api/n8n/workflows');
        const data = await response.json();

        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        updateWorkflowsGrid(data.workflows);
    } catch (error) {
        showNotification('ワークフロー情報の取得に失敗しました', 'error');
        console.error('Error fetching workflows:', error);
    }
}

// ワークフローグリッドの更新
function updateWorkflowsGrid(workflows) {
    const workflowsGrid = document.getElementById('workflowsGrid');
    workflowsGrid.innerHTML = '';

    if (workflows.length === 0) {
        workflowsGrid.innerHTML = '<div class="no-data">ワークフローが見つかりません</div>';
        return;
    }

    workflows.forEach(workflow => {
        const workflowCard = createWorkflowCard(workflow);
        workflowsGrid.appendChild(workflowCard);
    });
}

// ワークフローカードの作成
function createWorkflowCard(workflow) {
    const card = document.createElement('div');
    card.className = 'workflow-card';

    const statusText = workflow.active ? 'ACTIVE' : 'INACTIVE';
    const statusClass = workflow.active ? 'active' : 'inactive';

    const tagsHtml = workflow.tags.map(tag =>
        `<span class="workflow-tag">${tag}</span>`
    ).join('');

    card.innerHTML = `
        <div class="workflow-header">
            <div>
                <div class="workflow-name">${workflow.name}</div>
                <div class="workflow-status ${statusClass}">${statusText}</div>
            </div>
        </div>
        <div class="workflow-info">
            <div class="workflow-meta">
                <span>ノード: ${workflow.nodes}</span>
                <span>接続: ${workflow.connections}</span>
            </div>
            <div class="workflow-meta">
                <span>作成: ${formatDate(workflow.created_at)}</span>
                <span>更新: ${formatDate(workflow.updated_at)}</span>
            </div>
            ${tagsHtml ? `<div class="workflow-tags">${tagsHtml}</div>` : ''}
        </div>
        <div class="workflow-actions">
            ${workflow.active
                ? `<button class="workflow-btn deactivate" onclick="deactivateWorkflow('${workflow.id}')">無効化</button>`
                : `<button class="workflow-btn activate" onclick="activateWorkflow('${workflow.id}')">有効化</button>`
            }
            <button class="workflow-btn execute" onclick="executeWorkflow('${workflow.id}')">実行</button>
        </div>
    `;

    return card;
}

// n8n実行履歴の更新
async function refreshExecutions() {
    try {
        const response = await fetch('/api/n8n/executions');
        const data = await response.json();

        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        updateExecutionsList(data.executions);
    } catch (error) {
        showNotification('実行履歴の取得に失敗しました', 'error');
        console.error('Error fetching executions:', error);
    }
}

// 実行履歴リストの更新
function updateExecutionsList(executions) {
    const executionsList = document.getElementById('executionsList');
    executionsList.innerHTML = '';

    if (executions.length === 0) {
        executionsList.innerHTML = '<div class="no-data">実行履歴が見つかりません</div>';
        return;
    }

    executions.forEach(execution => {
        const executionItem = createExecutionItem(execution);
        executionsList.appendChild(executionItem);
    });
}

// 実行履歴アイテムの作成
function createExecutionItem(execution) {
    const item = document.createElement('div');
    item.className = 'execution-item';

    const statusClass = `execution-status ${execution.status}`;
    const duration = execution.duration ? `${execution.duration}ms` : 'N/A';

    item.innerHTML = `
        <div class="${statusClass}"></div>
        <div class="execution-info">
            <div class="execution-workflow">${execution.workflow_name}</div>
            <div class="execution-details">
                ステータス: ${execution.status} | 実行時間: ${duration}
                ${execution.error ? ` | エラー: ${execution.error}` : ''}
            </div>
        </div>
        <div class="execution-time">
            ${formatDate(execution.started_at)}
        </div>
    `;

    return item;
}

// コンテナ操作
async function startContainer(containerId) {
    try {
        const response = await fetch(`/api/containers/${containerId}/start`, { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            refreshContainers();
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        showNotification('コンテナの起動に失敗しました', 'error');
        console.error('Error starting container:', error);
    }
}

async function stopContainer(containerId) {
    try {
        const response = await fetch(`/api/containers/${containerId}/stop`, { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            refreshContainers();
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        showNotification('コンテナの停止に失敗しました', 'error');
        console.error('Error stopping container:', error);
    }
}

async function showContainerLogs(containerId, containerName) {
    try {
        const response = await fetch(`/api/containers/${containerId}/logs`);
        const data = await response.json();

        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        displayLogs(data.logs, `${containerName} のログ`);
    } catch (error) {
        showNotification('ログの取得に失敗しました', 'error');
        console.error('Error fetching logs:', error);
    }
}

// n8nワークフロー操作
async function activateWorkflow(workflowId) {
    try {
        const response = await fetch(`/api/n8n/workflows/${workflowId}/activate`, { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            refreshWorkflows();
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        showNotification('ワークフローの有効化に失敗しました', 'error');
        console.error('Error activating workflow:', error);
    }
}

async function deactivateWorkflow(workflowId) {
    try {
        const response = await fetch(`/api/n8n/workflows/${workflowId}/deactivate`, { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            refreshWorkflows();
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        showNotification('ワークフローの無効化に失敗しました', 'error');
        console.error('Error deactivating workflow:', error);
    }
}

async function executeWorkflow(workflowId) {
    try {
        const response = await fetch(`/api/n8n/workflows/${workflowId}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            refreshExecutions();
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        showNotification('ワークフローの実行に失敗しました', 'error');
        console.error('Error executing workflow:', error);
    }
}

// ログ表示
function displayLogs(logs, title) {
    const logArea = document.getElementById('logArea');
    const logContent = document.getElementById('logContent');

    logContent.innerHTML = logs.split('\n').map(line =>
        `<div>${line}</div>`
    ).join('');

    logArea.style.display = 'flex';
}

// ログエリアを閉じる
function closeLogArea() {
    document.getElementById('logArea').style.display = 'none';
}

// 通知表示
function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');

    notification.textContent = message;
    notification.className = `notification ${type} show`;

    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// 日付フォーマット
function formatDate(dateString) {
    if (!dateString) return 'N/A';

    try {
        const date = new Date(dateString);
        // 無効な日付の場合は元の文字列を返す
        if (isNaN(date.getTime())) {
            return dateString;
        }
        return date.toLocaleString('ja-JP');
    } catch (error) {
        // 日付パースに失敗した場合は元の文字列を返す
        console.warn('Date parsing failed:', error);
        return dateString;
    }
}

// エラーハンドリング
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    showNotification('予期しないエラーが発生しました', 'error');
});

// ページ離脱時の処理
window.addEventListener('beforeunload', function() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

// ------------------------------
// 進捗UIとジョブポーリング
// ------------------------------
function initializeProgressUI() {
    try {
        const containersSection = document.getElementById('containersSection');
        if (!containersSection) return;

        // すでに設置済みなら二重追加を防ぐ
        if (document.getElementById('startJobBtn')) return;

        const progressContainer = document.createElement('div');
        progressContainer.className = 'card';
        progressContainer.style.marginTop = '12px';
        progressContainer.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
              <button id="startJobBtn" class="refresh-btn" title="再計算を開始">
                <i class="fas fa-play"></i>
              </button>
              <div id="progressText" style="flex:1; font-size: 12px; color: #444;">未実行</div>
            </div>
            <progress id="progressBar" max="100" value="0" style="width:100%; margin-top:8px;"></progress>
        `;

        containersSection.prepend(progressContainer);

        document.getElementById('startJobBtn').addEventListener('click', startJobProgress);
    } catch (e) {
        console.error('initializeProgressUI error:', e);
    }
}

let __progressPollingTimer = null;
let __currentJobId = null;

async function startJobProgress() {
    try {
        setProgressUI({ text: '開始中…', value: 0 });
        const res = await fetch('/api/jobs/start', { method: 'POST' });
        if (!res.ok) throw new Error('開始APIが失敗しました');
        const data = await res.json();
        __currentJobId = data.jobId;
        startProgressPolling(__currentJobId);
    } catch (e) {
        console.error('開始エラー:', e);
        setProgressUI({ text: '開始に失敗しました', value: 0 });
    }
}

function startProgressPolling(jobId) {
    if (__progressPollingTimer) clearInterval(__progressPollingTimer);
    __progressPollingTimer = setInterval(async () => {
        try {
            const res = await fetch('/api/jobs/progress', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jobId })
            });
            if (!res.ok) throw new Error('進捗APIが失敗しました');
            const data = await res.json();
            const text = `ステータス: ${data.status} / ${data.message || ''}`;
            setProgressUI({ text, value: data.progress || 0 });

            if (data.status !== 'running') {
                clearInterval(__progressPollingTimer);
                __progressPollingTimer = null;
            }
        } catch (e) {
            console.error('進捗取得エラー:', e);
            setProgressUI({ text: '進捗の取得に失敗しました', value: 0 });
            clearInterval(__progressPollingTimer);
            __progressPollingTimer = null;
        }
    }, 1000);
}

function setProgressUI({ text, value }) {
    const textEl = document.getElementById('progressText');
    const barEl = document.getElementById('progressBar');
    if (textEl) textEl.textContent = text;
    if (barEl && typeof value === 'number') barEl.value = value;
}
