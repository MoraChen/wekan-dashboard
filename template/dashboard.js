
let filteredCards1 = [];
let filteredCards2 = [];

let chartListInstance = null;
let chartSwimInstance = null;
let chartMemberInstance = null;
let chartTrendInstance = null;

// 需求 #1 & #3: 子分頁控制
let riskSubTab = 'overview';
let t1SubTab = 'risk';
let t2SubTab = 'newdone';
let riskSwimFilter = '';

// Tab 2 Lazy Init
let tab2Initialized = false;
// Tab 3: AI 分析 Lazy Init
let tab3Initialized = false;
// Tab 4: 成果亮點 Lazy Init
let tab4Initialized = false;

// 成果亮點資料（Python 注入）

// AI 分析資料（Python 注入）

// 改動 2: 子分頁 Lazy Render
let t1DirtyPanels = new Set(['newdone','doing','risk','all','parent']);
let t2DirtyPanels = new Set(['newdone','all','parent']);
let t1FilterDates = { startDt: null, endDt: null };
let t2FilterDates = { startDt: null, endDt: null };

// 改動 3: 全部明細分頁
let t1AllPage = 1;
let t2AllPage = 1;
const PAGE_SIZE = 100;

// 改動 4: 父子結構 Lazy Expand
const parentGroupData = {};
let currentChildrenMap = {}; // 遞迴父子展開用（由 renderParentGroups 更新）

// ==================== 初始化 ====================

function initFilters() {
    // Tab 1 pickers
    const t1ListPicker = makePicker('t1-list-picker-dropdown','t1-list-picker-btn','t1-list-picker-items','全部欄位');
    const t1SwimPicker = makePicker('t1-swim-picker-dropdown','t1-swim-picker-btn','t1-swim-picker-items','全部主題');
    const t1LabelPicker = makePicker('t1-label-picker-dropdown','t1-label-picker-btn','t1-label-picker-items','全部標籤');
    const t1StatusPicker = makePicker('t1-status-picker-dropdown','t1-status-picker-btn','t1-status-picker-items','全部狀態');
    const t1ArchivedPicker = makePicker('t1-archived-picker-dropdown','t1-archived-picker-btn','t1-archived-picker-items','封存狀態');

    // Tab 2 pickers
    const t2SwimPicker = makePicker('t2-swim-picker-dropdown','t2-swim-picker-btn','t2-swim-picker-items','全部主題');
    const t2LabelPicker = makePicker('t2-label-picker-dropdown','t2-label-picker-btn','t2-label-picker-items','全部標籤');
    const t2MemberPicker = makePicker('t2-member-picker-dropdown','t2-member-picker-btn','t2-member-picker-items','全部成員');
    const t2StatusPicker = makePicker('t2-status-picker-dropdown','t2-status-picker-btn','t2-status-picker-items','全部狀態');
    const t2ArchivedPicker = makePicker('t2-archived-picker-dropdown','t2-archived-picker-btn','t2-archived-picker-items','封存狀態');
    const t2TaskTypePicker = makePicker('t2-tasktype-picker-dropdown','t2-tasktype-picker-btn','t2-tasktype-picker-items','全部類型');

    // Populate list picker (Tab 1 only)
    const DEFAULT_LIST_SELECTIONS = ['Goal＆專案資訊','Backlog','Ready to GO','Doing','Waiting','Review / 使用者Test','DONE','Closed'];
    const listsHtml = Object.entries(RAW.listsMap)
        .map(([id,name]) => {
            const checked = DEFAULT_LIST_SELECTIONS.includes(name) ? 'checked' : '';
            return `<div class="picker-item"><input type="checkbox" value="${id}" ${checked} onchange="applyFilters1()"> ${name}</div>`;
        })
        .join('');
    document.getElementById('t1-list-picker-items').innerHTML = listsHtml;

    // Populate swim pickers
    // DEFAULT_SWIM_SELECTIONS 從 team_config.json board.default_swim_selections 讀取
    // 空陣列 = 全選；有值 = 只預先勾選指定主題
    const swimsHtml = Object.entries(RAW.swimlanesMap)
        .map(([id,name]) => {
            const checked = (DEFAULT_SWIM_SELECTIONS.length === 0 || DEFAULT_SWIM_SELECTIONS.includes(name)) ? 'checked' : '';
            return `<div class="picker-item"><input type="checkbox" value="${id}" ${checked} onchange="applyFilters1();applyFilters2()"> ${name}</div>`;
        })
        .join('');
    document.getElementById('t1-swim-picker-items').innerHTML = swimsHtml;
    document.getElementById('t2-swim-picker-items').innerHTML = swimsHtml;

    // Populate label pickers（預設全選）
    const labelsHtml = Object.entries(RAW.labelsMap)
        .map(([id,name]) => `<div class="picker-item"><input type="checkbox" value="${id}" checked onchange="applyFilters1();applyFilters2()"> ${name}</div>`)
        .join('');
    document.getElementById('t1-label-picker-items').innerHTML = labelsHtml;
    document.getElementById('t2-label-picker-items').innerHTML = labelsHtml;

    // Populate member picker (Tab 2 only)
    const membersHtml = Object.entries(RAW.users)
        .map(([id,name]) => `<div class="picker-item"><input type="checkbox" value="${id}" onchange="applyFilters2()"> ${name}</div>`)
        .join('');
    document.getElementById('t2-member-picker-items').innerHTML = membersHtml;

    // Populate status pickers
    const statusOptions = [
        { key: 'doing',    label: 'Doing' },
        { key: 'waiting',  label: 'Waiting' },
        { key: 'review',   label: 'Review' },
        { key: 'done',     label: 'DONE' },
        { key: 'stale',    label: '停滯' },
        { key: 'overdue',  label: '逾期' },
        { key: 'nomember', label: '無負責人' },
    ];
    const statusHtml = statusOptions
        .map(opt => `<div class="picker-item"><input type="checkbox" value="${opt.key}" checked onchange="applyFilters1();applyFilters2()"> ${opt.label}</div>`)
        .join('');
    document.getElementById('t1-status-picker-items').innerHTML = statusHtml;
    document.getElementById('t2-status-picker-items').innerHTML = statusHtml;

    // Populate archived pickers
    const archivedHtml = `
        <div class="picker-item"><input type="checkbox" id="t1-ack-active" value="active" onchange="applyFilters1()"> 未封存</div>
        <div class="picker-item"><input type="checkbox" id="t1-ack-archived" value="archived" onchange="applyFilters1()"> 已封存</div>
        <div class="picker-item"><input type="checkbox" id="t1-ack-all" value="all" onchange="applyFilters1()"> 全部</div>
    `;
    document.getElementById('t1-archived-picker-items').innerHTML = archivedHtml;
    document.getElementById('t1-ack-active').checked = true;

    const archivedHtml2 = `
        <div class="picker-item"><input type="checkbox" id="t2-ack-active" value="active" onchange="applyFilters2()"> 未封存</div>
        <div class="picker-item"><input type="checkbox" id="t2-ack-archived" value="archived" onchange="applyFilters2()"> 已封存</div>
        <div class="picker-item"><input type="checkbox" id="t2-ack-all" value="all" onchange="applyFilters2()"> 全部</div>
    `;
    document.getElementById('t2-archived-picker-items').innerHTML = archivedHtml2;
    document.getElementById('t2-ack-active').checked = true;

    // Populate task type picker (Tab 2 only)
    const taskTypeHtml = `
        <div class="picker-item"><input type="checkbox" value="parent" checked onchange="applyFilters2()"> 父任務</div>
        <div class="picker-item"><input type="checkbox" value="child" checked onchange="applyFilters2()"> 子任務</div>
        <div class="picker-item"><input type="checkbox" value="standalone" checked onchange="applyFilters2()"> 獨立任務</div>
    `;
    document.getElementById('t2-tasktype-picker-items').innerHTML = taskTypeHtml;

    // 需求 #3: 初始化父子結構泳道篩選下拉
    const swimOptions = Object.entries(RAW.swimlanesMap)
        .map(([id, name]) => `<option value="${id}">${name}</option>`)
        .join('');
    document.getElementById('t1-risk-swim-filter').innerHTML = '<option value="">全部主題</option>' + swimOptions;
    document.getElementById('t1-parent-swim-filter').innerHTML = '<option value="">全部主題</option>' + swimOptions;
    const t2ParentSwimEl = document.getElementById('t2-parent-swim-filter');
    if (t2ParentSwimEl) t2ParentSwimEl.innerHTML = '<option value="">全部主題</option>' + swimOptions;

    // Close-outside-click handler for all dropdowns
    document.addEventListener('click', (e) => {
        const dropdownIds = [
            't1-list-picker-dropdown', 't1-swim-picker-dropdown', 't1-label-picker-dropdown',
            't1-status-picker-dropdown', 't1-archived-picker-dropdown',
            't2-swim-picker-dropdown', 't2-label-picker-dropdown', 't2-member-picker-dropdown',
            't2-status-picker-dropdown', 't2-archived-picker-dropdown', 't2-tasktype-picker-dropdown'
        ];
        for (let id of dropdownIds) {
            const el = document.getElementById(id);
            if (el && !el.contains(e.target) && !e.target.closest('.picker-btn')) {
                el.classList.remove('open');
            }
        }
    });

    // Initial apply (改動 1: Tab 2 延遲初始化)
    applyFilters1();
}

// ==================== Picker Utility ====================

function makePicker(dropdownId, btnId, itemsId, placeholder) {
    const dropdown = document.getElementById(dropdownId);
    const btn = document.getElementById(btnId);

    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('open');
    });

    return { dropdown, btn };
}

// ==================== 🏆 成果亮點 Tab ====================

function initMilestonesTab() {
    // 顯示正確存放路徑（資料夾名稱）
    const hint = document.getElementById('ms-path-hint');
    if (hint && MILESTONE_NOTES_DIR)
        hint.textContent = MILESTONE_NOTES_DIR + '/milestone_notes.json';

    // 從 milestone_notes.json（Python 注入）seed localStorage
    // 規則：只在 localStorage 尚未有此 key 時才寫入（不覆蓋使用者已編輯的內容）
    try {
        Object.entries(MILESTONE_NOTES).forEach(([id, data]) => {
            if (data.note !== undefined && !localStorage.getItem('ms_note_' + id))
                localStorage.setItem('ms_note_' + id, data.note);
            if (data.link !== undefined && !localStorage.getItem('ms_link_' + id))
                localStorage.setItem('ms_link_' + id, data.link);
        });
    } catch(e) {}

    // 填入主題下拉選單
    const swimSet = new Set(MILESTONES.map(c => c.swimlane));
    const ordered = SWIM_ORDER.filter(s => swimSet.has(s))
        .concat([...swimSet].filter(s => !SWIM_ORDER.includes(s)));
    const sel = document.getElementById('ms-swim-filter');
    ordered.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s; opt.textContent = s;
        sel.appendChild(opt);
    });
    renderMilestones();
}

function _filterMilestones() {
    const startVal = document.getElementById('ms-date-start')?.value || '';
    const endVal   = document.getElementById('ms-date-end')?.value   || '';
    const swimVal  = document.getElementById('ms-swim-filter')?.value || '';
    return MILESTONES.filter(c => {
        if (swimVal && c.swimlane !== swimVal) return false;
        if (startVal && c.endAt && c.endAt.slice(0,10) < startVal) return false;
        if (endVal   && c.endAt && c.endAt.slice(0,10) > endVal)   return false;
        return true;
    });
}

function _groupMilestonesBySwim(cards) {
    // 依 SWIM_ORDER 排序各主題
    const map = {};
    cards.forEach(c => {
        if (!map[c.swimlane]) map[c.swimlane] = [];
        map[c.swimlane].push(c);
    });
    const ordered = SWIM_ORDER.filter(s => map[s]);
    Object.keys(map).forEach(s => { if (!ordered.includes(s)) ordered.push(s); });
    const result = {};
    ordered.forEach(s => { result[s] = map[s]; });
    return result;
}

function _msGetNote(id) {
    try { return localStorage.getItem('ms_note_' + id) || ''; } catch(e) { return ''; }
}
function _msGetLink(id) {
    try { return localStorage.getItem('ms_link_' + id) || ''; } catch(e) { return ''; }
}

function msSaveNote(id) {
    const el = document.getElementById('ms-note-input-' + id);
    if (!el) return;
    try { localStorage.setItem('ms_note_' + id, el.value); } catch(e) {}
    _msRefreshNote(id);
}

function msEditNote(id) {
    document.getElementById('ms-note-display-' + id).style.display = 'none';
    const inp = document.getElementById('ms-note-input-' + id);
    inp.style.display = '';
    inp.focus();
    inp.setSelectionRange(inp.value.length, inp.value.length);
}

function msBlurNote(id) {
    msSaveNote(id);
}

function _msRefreshNote(id) {
    const note = _msGetNote(id);
    const inp  = document.getElementById('ms-note-input-' + id);
    const disp = document.getElementById('ms-note-display-' + id);
    if (!inp || !disp) return;
    inp.style.display = 'none';
    if (note) {
        disp.innerHTML = `<div class="ms-note-text" onclick="msEditNote('${id}')">${note.replace(/\n/g,'<br>')}</div>`;
    } else {
        disp.innerHTML = `<div class="ms-note-placeholder" onclick="msEditNote('${id}')">💬 點擊新增說明</div>`;
    }
    disp.style.display = '';
}

function msSaveLink(id) {
    const inp = document.getElementById('ms-link-input-' + id);
    if (!inp) return;
    let url = inp.value.trim();
    if (url && !url.match(/^https?:\/\//)) url = 'https://' + url;
    try { localStorage.setItem('ms_link_' + id, url); } catch(e) {}
    _msRefreshLink(id);
}

function msClearLink(id) {
    try { localStorage.removeItem('ms_link_' + id); } catch(e) {}
    _msRefreshLink(id);
}

function _msRefreshLink(id) {
    const link = _msGetLink(id);
    const area = document.getElementById('ms-link-area-' + id);
    if (!area) return;
    if (link) {
        area.innerHTML = `
            <a href="${link}" target="_blank" class="ms-link-btn">🔗 查看簡報 →</a>
            <span class="ms-link-clear" onclick="msClearLink('${id}')">✕</span>`;
    } else {
        area.innerHTML = `
            <input id="ms-link-input-${id}" class="ms-link-input"
                   placeholder="🔗 貼入簡報連結…"
                   onblur="msSaveLink('${id}')"
                   onkeydown="if(event.key==='Enter')msSaveLink('${id}')">`;
    }
}

function _msBuildNotesJSON() {
    const result = {};
    MILESTONES.forEach(c => {
        const note = _msGetNote(c.id);
        const link = _msGetLink(c.id);
        if (note || link) result[c.id] = { note, link, title: c.title };
    });
    // 保留歷史資料（不在目前卡片中的 entry）
    Object.entries(MILESTONE_NOTES).forEach(([id, data]) => {
        if (!result[id]) result[id] = data;
    });
    return JSON.stringify(result, null, 2);
}

function _msSaveFeedback() {
    const btn = document.getElementById('ms-save-btn');
    if (!btn) return;
    btn.textContent = '✅ 已儲存！';
    setTimeout(() => { btn.textContent = '💾 儲存補充資料'; }, 2500);
}

function _msFallbackDownload(jsonStr) {
    const blob = new Blob([jsonStr], { type: 'application/json;charset=utf-8' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'milestone_notes.json';
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
}

async function saveMilestoneNotes() {
    const jsonStr = _msBuildNotesJSON();
    if (window.showSaveFilePicker) {
        try {
            const handle = await window.showSaveFilePicker({
                suggestedName: 'milestone_notes.json',
                types: [{ description: 'JSON 檔案', accept: { 'application/json': ['.json'] } }]
            });
            const writable = await handle.createWritable();
            await writable.write(jsonStr);
            await writable.close();
            _msSaveFeedback();
        } catch(e) {
            if (e.name !== 'AbortError') _msFallbackDownload(jsonStr);
            // AbortError = 使用者按取消，不做任何事
        }
    } else {
        // 不支援 showSaveFilePicker（Firefox 等）→ 直接下載
        _msFallbackDownload(jsonStr);
        _msSaveFeedback();
    }
}

function _msStatusBadge(c) {
    if (c.isDone) return `<span class="ms-status-badge ms-done">✅ 已完成</span>`;
    if (c.list === 'Doing')   return `<span class="ms-status-badge ms-doing">▶ Doing${c.isStale ? ` · 停滯${c.staleDays}天` : ''}</span>`;
    if (c.list === 'Waiting') return `<span class="ms-status-badge ms-waiting">⏸ Waiting</span>`;
    if (c.list === 'Review / 使用者Test') return `<span class="ms-status-badge ms-review">🔍 Review</span>`;
    return `<span class="ms-status-badge ms-other">${c.list}</span>`;
}

function _msDateLine(c) {
    if (c.isDone && c.endAtDisplay !== '—')
        return `完成：${c.endAtDisplay}`;
    if (c.dueAtDisplay)
        return `預計：${c.dueAtDisplay}`;
    if (c.lastActDisplay !== '—')
        return `最後活動：${c.lastActDisplay}`;
    return '';
}

function renderMilestones() {
    const filtered = _filterMilestones();
    document.getElementById('ms-count').textContent = `共 ${filtered.length} 個里程碑`;

    const content = document.getElementById('ms-content');
    if (!content) return;

    if (filtered.length === 0) {
        content.innerHTML = `<div class="ms-empty">目前沒有符合條件的里程碑卡片<br><small>請在 Wekan 卡片上加入「${MILESTONE_LABEL}」標籤</small></div>`;
        return;
    }

    const groups = _groupMilestonesBySwim(filtered);
    let html = '';
    Object.entries(groups).forEach(([swim, cards]) => {
        html += `<div class="ms-swim-header">── 主題：${swim}（${cards.length} 個里程碑）</div>`;
        cards.forEach(c => {
            const note    = _msGetNote(c.id);
            const link    = _msGetLink(c.id);
            const membersStr = c.members.length ? '👤 ' + c.members.join('・') : '👤 未指定';
            const dateLine   = _msDateLine(c);

            const noteDisplayHtml = note
                ? `<div class="ms-note-text" onclick="msEditNote('${c.id}')">${note.replace(/\n/g,'<br>')}</div>`
                : `<div class="ms-note-placeholder" onclick="msEditNote('${c.id}')">💬 點擊新增說明</div>`;

            const linkHtml = link
                ? `<a href="${link}" target="_blank" class="ms-link-btn">🔗 查看簡報 →</a>
                   <span class="ms-link-clear" onclick="msClearLink('${c.id}')">✕</span>`
                : `<input id="ms-link-input-${c.id}" class="ms-link-input"
                          placeholder="🔗 貼入簡報連結…"
                          onblur="msSaveLink('${c.id}')"
                          onkeydown="if(event.key==='Enter')msSaveLink('${c.id}')">`;

            html += `
            <div class="ms-card${c.isDone ? ' ms-card-done' : ''}">
                <div class="ms-card-title">
                    <div class="ms-card-title-left">🏆 ${cardLink(c.id, c.title)}</div>
                    ${_msStatusBadge(c)}
                </div>
                <div class="ms-card-meta-row">
                    <span class="ms-card-members">${membersStr}</span>
                    ${dateLine ? `<span class="ms-card-date">${dateLine}</span>` : ''}
                </div>
                ${c.desc ? `<div class="ms-card-desc">↳ ${c.desc}</div>` : ''}
                <div class="ms-note-area">
                    <div id="ms-note-display-${c.id}">${noteDisplayHtml}</div>
                    <textarea id="ms-note-input-${c.id}" class="ms-note-input"
                        style="display:none"
                        onblur="msBlurNote('${c.id}')"
                    >${note}</textarea>
                </div>
                <div class="ms-link-area" id="ms-link-area-${c.id}">${linkHtml}</div>
            </div>`;
        });
    });

    content.innerHTML = html;
}

// ==================== Main Tab Switch ====================

function switchMainTab(name) {
    const tabs = document.querySelectorAll('.main-panel');
    const btns = document.querySelectorAll('.main-tab-btn');

    tabs.forEach(t => t.classList.remove('active'));
    btns.forEach(b => b.classList.remove('active'));

    if (name === 'overview') {
        document.getElementById('main-panel-overview').classList.add('active');
        btns[0].classList.add('active');
    } else if (name === 'personal') {
        document.getElementById('main-panel-personal').classList.add('active');
        btns[1].classList.add('active');
        if (!tab2Initialized) {
            tab2Initialized = true;
            applyFilters2();
        }
    } else if (name === 'ai') {
        document.getElementById('main-panel-ai').classList.add('active');
        btns[2].classList.add('active');
        if (!tab3Initialized) {
            tab3Initialized = true;
            initAITab();
        }
    } else if (name === 'milestones') {
        document.getElementById('main-panel-milestones').classList.add('active');
        btns[3].classList.add('active');
        if (!tab4Initialized) {
            tab4Initialized = true;
            initMilestonesTab();
        }
    }
}

// ==================== AI 分析 Tab ====================

function _groupBySwimlane(cards) {
    const map = {};
    cards.forEach(c => {
        if (!map[c.swimlane]) map[c.swimlane] = [];
        map[c.swimlane].push(c);
    });
    return map;
}

function initAITab() {
    renderAIPreview();
    const saved = localStorage.getItem('ai_analysis_notes');
    if (saved) {
        document.getElementById('ai-notes').value = saved;
    }
    // 預設顯示「檢視」模式
    setAIMode('view');
    // 初始化操作流程引導（記憶展開/收合狀態）
    initWorkflowGuide();
    // 若有記憶的資料夾名稱，顯示一鍵確認橫幅
    loadRecallDir();
}

// 簡易 Markdown → HTML 轉換（支援 ##標題、**粗體**、- 列表、--- 分隔線、段落）
function simpleMarkdown(md) {
    if (!md || !md.trim()) return '';
    let html = md
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm,  '<h2>$1</h2>')
        .replace(/^# (.+)$/gm,   '<h1>$1</h1>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g,    '<em>$1</em>')
        .replace(/^---+$/gm,      '<hr>')
        .replace(/^[-•] (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
        .replace(/<\/ul>\s*<ul>/g, '')
        .split(/\n{2,}/)
        .map(block => {
            if (/^<(h[123]|ul|hr|li)/.test(block.trim())) return block;
            return `<p>${block.replace(/\n/g,'<br>')}</p>`;
        })
        .join('');
    return html;
}

let _currentAIMode = 'view';
function setAIMode(mode) {
    _currentAIMode = mode;
    const textarea  = document.getElementById('ai-notes');
    const viewDiv   = document.getElementById('ai-notes-view');
    const placeholder = document.getElementById('ai-notes-placeholder');
    const btnView   = document.getElementById('ai-mode-view');
    const btnEdit   = document.getElementById('ai-mode-edit');
    const content   = textarea.value.trim();

    btnView.classList.toggle('active', mode === 'view');
    btnEdit.classList.toggle('active', mode === 'edit');

    if (mode === 'view') {
        textarea.style.display  = 'none';
        if (content) {
            viewDiv.innerHTML = simpleMarkdown(textarea.value);
            viewDiv.style.display = 'block';
            placeholder.style.display = 'none';
        } else {
            viewDiv.style.display = 'none';
            placeholder.style.display = 'block';
        }
    } else {
        viewDiv.style.display    = 'none';
        placeholder.style.display = 'none';
        textarea.style.display   = 'block';
        textarea.focus();
    }
}

function renderAIPreview() {
    const box = document.getElementById('ai-preview-box');
    if (!box) return;
    const sections = [
        { data: AI_DONE,  icon: '✅', label: '本週完成',
           row: c => `${c.title}<span class="ai-card-meta">（${c.members.join('、')||'無負責人'}）</span>`,
           showDesc: true },
        { data: AI_NEW,   icon: '📥', label: '本週新增',
           row: c => `${c.title}<span class="ai-card-meta">（${c.members.join('、')||'無負責人'}，${c.list}）</span>`,
           showDesc: false },
        { data: AI_RISK,  icon: '⚠️', label: '目前風險',
           row: c => {
               const t = [];
               if (c.isOverdue) t.push('逾期');
               if (c.isDueSoon) t.push(`⚡ 即將到期：${c.dueAtDisplay}`);
               if (c.isStale)   t.push(`停滯${c.staleDays}天`);
               return `${c.title}<span class="ai-card-meta">（${t.join('、')}）</span>`;
           }, showDesc: false },
        { data: AI_DOING, icon: '▶️', label: 'Doing 中',
           row: c => `${c.title}<span class="ai-card-meta">（${c.members.join('、')||'無負責人'}，${c.isStale?`停滯${c.staleDays}天`:'活躍'}）</span>`,
           showDesc: false },
    ];
    let html = '';
    sections.forEach(s => {
        const groups = _groupBySwimlane(s.data);
        html += `<div class="ai-section"><div class="ai-section-title">${s.icon} ${s.label}（${s.data.length} 張）</div>`;
        if (s.data.length === 0) {
            html += `<div class="ai-empty">無資料</div>`;
        } else {
            Object.entries(groups).forEach(([swim, cards]) => {
                html += `<div class="ai-swim-group"><span class="ai-swim-name">主題：${swim}</span>`;
                cards.forEach(c => {
                    html += `<div class="ai-card-row">• ${s.row(c)}</div>`;
                    if (s.showDesc && c.desc) {
                        html += `<div class="ai-card-desc">↳ ${c.desc}</div>`;
                    }
                });
                html += `</div>`;
            });
        }
        html += `</div>`;
    });
    box.innerHTML = html;
}

function buildAICopyText() {
    const fmtDesc = desc => desc ? `\n      └ ${desc}` : '';
    const fmt = (cards, rowFn) => {
        if (cards.length === 0) return '  （無）\n';
        const groups = _groupBySwimlane(cards);
        let s = '';
        Object.entries(groups).forEach(([swim, items]) => {
            s += `主題：${swim}\n`;
            items.forEach(c => { s += `  - ${rowFn(c)}${fmtDesc(c.desc)}\n`; });
        });
        return s;
    };
    return [
        `【本週完成 ${AI_DONE.length} 張】`,
        fmt(AI_DONE,  c => `${c.title}（負責人：${c.members.join('、')||'無'}）`),
        `【本週新增 ${AI_NEW.length} 張】`,
        fmt(AI_NEW,   c => `${c.title}（負責人：${c.members.join('、')||'無'}，欄位：${c.list}）`),
        `【目前風險 ${AI_RISK.length} 張】`,
        fmt(AI_RISK,  c => {
            const t = [];
            if (c.isOverdue) t.push('逾期');
            if (c.isDueSoon) t.push(`⚡ 即將到期：${c.dueAtDisplay}`);
            if (c.isStale)   t.push(`停滯${c.staleDays}天`);
            return `${c.title}（${t.join('、')}）`;
        }),
        `【Doing 中 ${AI_DOING.length} 張】`,
        fmt(AI_DOING, c => `${c.title}（負責人：${c.members.join('、')||'無'}，${c.isStale?`停滯${c.staleDays}天`:'活躍'}）`),
        '---',
        '請根據以上資料：',
        '1. 總結本週團隊推展的主要方向',
        '2. 說明完成任務的意義與進展',
        '3. 結合風險現況，建議下週應優先推進的方向',
    ].join('\n');
}

function copyAIData() {
    navigator.clipboard.writeText(buildAICopyText()).then(() => {
        const btn = document.getElementById('ai-copy-btn');
        btn.textContent = '✅ 已複製！';
        setTimeout(() => { btn.textContent = '📋 複製 AI 分析資料'; }, 1500);
    });
}

// 從 Python 注入的設定

function _buildAISaveFilename() {
    const now = new Date();
    const pad = n => String(n).padStart(2,'0');
    const dateStr = `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}`;
    const timeStr = `${pad(now.getHours())}${pad(now.getMinutes())}`;
    return `${AI_FILENAME_PREFIX}_${dateStr}_${timeStr}.md`;
}

function _buildAISaveContent(filename) {
    const raw = document.getElementById('ai-notes').value;
    // 從檔名解析日期時間顯示
    const m = filename.match(/_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})/);
    const stamp = m ? `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}` : '';
    return `# AI 週報分析  ${stamp}\n\n${raw}`;
}

async function saveAIToFile() {
    const content = document.getElementById('ai-notes').value.trim();
    if (!content) {
        alert('尚無分析內容，請先載入或輸入分析內容後再儲存。');
        return;
    }

    const btn      = document.getElementById('ai-save-btn');
    const filename = _buildAISaveFilename();
    const text     = _buildAISaveContent(filename);

    const markSaved = (label) => {
        setWorkflowStep(6, true);
        const hint = document.getElementById('ai-save-hint');
        if (hint) {
            hint.innerHTML =
                `<span style="color:#2e7d32;font-weight:600">✅ 已儲存：</span>` +
                `<code style="font-size:0.95em;color:#1a4f7a;background:#e8f2fc;` +
                `padding:1px 6px;border-radius:3px;">${label}</code>`;
        }
        btn.textContent = '✅ 已儲存！';
        setTimeout(() => { btn.textContent = '💾 儲存本週分析'; }, 3000);
    };

    // 優先：使用已選取的專案資料夾 → 直接寫入 AI分析結果/ 子資料夾（無需另存視窗）
    if (_projDirHandle) {
        try {
            const resultsDir = await _projDirHandle.getDirectoryHandle(AI_SAVE_FOLDER, { create: true });
            const fh = await resultsDir.getFileHandle(filename, { create: true });
            const writable = await fh.createWritable();
            await writable.write(text);
            await writable.close();
            markSaved(`${AI_SAVE_FOLDER}/${filename}`);
            return;
        } catch(e) {
            if (e.name === 'AbortError') return;
            console.warn('直接儲存失敗，改用另存視窗：', e);
            // fallthrough
        }
    }

    // 次選：showSaveFilePicker（專案資料夾未選取時，開啟另存視窗）
    if (window.showSaveFilePicker) {
        try {
            const handle = await window.showSaveFilePicker({
                suggestedName: filename,
                types: [{ description: 'Markdown 檔案', accept: { 'text/markdown': ['.md'] } }]
            });
            const writable = await handle.createWritable();
            await writable.write(text);
            await writable.close();
            markSaved(filename);
            return;
        } catch(e) {
            if (e.name === 'AbortError') return;
            // fallthrough to Blob
        }
    }

    // Fallback：Blob 下載（Firefox / Safari）
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    markSaved(filename + '（下載）');
}

let _aiNoteTimer = null;
function saveAINotes() {
    clearTimeout(_aiNoteTimer);
    _aiNoteTimer = setTimeout(() => {
        const val = document.getElementById('ai-notes').value;
        localStorage.setItem('ai_analysis_notes', val);
        // 若切換到檢視模式時即時更新
        if (_currentAIMode === 'view') setAIMode('view');
    }, 500);
}

// ==================== AI Prompt 設定 & 資料夾橋接 ====================

let _projDirHandle = null;
let _promptModified = false;
let _pollTimer = null;
let _requestGeneratedAt = null;

// ── 操作流程引導：收合/展開 ──────────────────────────────
function toggleWorkflowGuide() {
    const wrap = document.getElementById('ai-wf-steps-wrap');
    const icon = document.getElementById('ai-wf-toggle-icon');
    const hint = document.querySelector('.ai-wf-toggle-hint');
    if (!wrap) return;
    const isOpen = wrap.style.display !== 'none';
    wrap.style.display = isOpen ? 'none' : 'flex';
    if (icon) icon.textContent = isOpen ? '▸' : '▾';
    if (hint) hint.textContent = isOpen ? '點擊展開' : '熟悉後可收合';
    localStorage.setItem('ai_wf_guide_open', isOpen ? '0' : '1');
}

function initWorkflowGuide() {
    const saved = localStorage.getItem('ai_wf_guide_open');
    if (saved === '0') {
        const wrap = document.getElementById('ai-wf-steps-wrap');
        const icon = document.getElementById('ai-wf-toggle-icon');
        const hint = document.querySelector('.ai-wf-toggle-hint');
        if (wrap) wrap.style.display = 'none';
        if (icon) icon.textContent = '▸';
        if (hint) hint.textContent = '點擊展開';
    }
}

// ── 資料夾記憶：recall 橫幅 ────────────────────────────────
function loadRecallDir() {
    const savedName = localStorage.getItem('ai_proj_dir_name');
    if (!savedName || _projDirHandle) return;
    const bar   = document.getElementById('ai-recall-bar');
    const label = document.getElementById('ai-recall-name');
    if (!bar || !label) return;
    label.textContent = savedName;
    bar.style.display = 'flex';
}

// ── IndexedDB：持久化儲存 FileSystemDirectoryHandle ──────────
const _IDB_NAME  = 'wekan_dashboard_v1';
const _IDB_STORE = 'handles';

function _idbOpen() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(_IDB_NAME, 1);
        req.onupgradeneeded = e => e.target.result.createObjectStore(_IDB_STORE);
        req.onsuccess  = e  => resolve(e.target.result);
        req.onerror    = () => reject(req.error);
    });
}

async function _idbPutHandle(handle) {
    try {
        const db = await _idbOpen();
        await new Promise((res, rej) => {
            const tx = db.transaction(_IDB_STORE, 'readwrite');
            tx.objectStore(_IDB_STORE).put(handle, 'project_dir');
            tx.oncomplete = res;
            tx.onerror = () => rej(tx.error);
        });
        db.close();
    } catch(e) { console.warn('idb put failed', e); }
}

async function _idbGetHandle() {
    try {
        const db = await _idbOpen();
        const handle = await new Promise((res, rej) => {
            const tx  = db.transaction(_IDB_STORE, 'readonly');
            const req = tx.objectStore(_IDB_STORE).get('project_dir');
            req.onsuccess = () => res(req.result || null);
            req.onerror   = () => rej(req.error);
        });
        db.close();
        return handle;
    } catch(e) { return null; }
}

// ── 一鍵確認：從 IndexedDB 恢復 handle，只需點擊「允許」 ─────
async function confirmRecallDir() {
    const handle = await _idbGetHandle();
    if (handle && handle.requestPermission) {
        try {
            const perm = await handle.requestPermission({ mode: 'readwrite' });
            if (perm === 'granted') {
                let isRoot = false;
                try { await handle.getFileHandle('update_dashboard.py'); isRoot = true; } catch(e) {}
                _projDirHandle = handle;
                updateDirBadge(isRoot ? 'ok' : 'warn', handle.name);
                setWorkflowStep(1, true);
                localStorage.setItem('ai_proj_dir_name', handle.name);
                dismissRecallBar();
                _loadPromptMeta().then(meta => { if (meta) _renderPromptMeta(meta); });
                return;
            }
        } catch(e) { console.warn('requestPermission 失敗，改用 picker', e); }
    }
    // Fallback：IndexedDB 無紀錄或授權失敗，開啟完整選取器
    await pickProjectDirectory();
    dismissRecallBar();
}

function dismissRecallBar() {
    const bar = document.getElementById('ai-recall-bar');
    if (bar) bar.style.display = 'none';
}

// ── 自動輪詢：偵測 Cowork 分析完成 ────────────────────────
function startPolling() {
    stopPolling();
    if (!_projDirHandle) return;
    const statusEl = document.getElementById('ai-request-status');
    if (statusEl) {
        statusEl.textContent = '⏳ 等待 Cowork 分析完成… (每 8 秒自動偵測)';
        statusEl.style.color = '#888';
    }
    _pollTimer = setInterval(checkForNewAnalysis, 8000);
}

function stopPolling() {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
}

async function checkForNewAnalysis() {
    if (!_projDirHandle || !_requestGeneratedAt) return;
    try {
        const resultsDir = await _projDirHandle.getDirectoryHandle(AI_SAVE_FOLDER);
        let latestFile = null, latestTime = 0;
        for await (const [, handle] of resultsDir.entries()) {
            if (handle.kind !== 'file') continue;
            const file = await handle.getFile();
            if (file.name.endsWith('.md') && file.lastModified > latestTime) {
                latestTime = file.lastModified;
                latestFile = file;
            }
        }
        if (latestFile && latestFile.lastModified > _requestGeneratedAt.getTime()) {
            stopPolling();
            setWorkflowStep(3, true);
            await _autoLoadFile(latestFile);
        }
    } catch(e) { /* 資料夾尚未存在，繼續等待 */ }
}

async function _autoLoadFile(file) {
    const raw   = await file.text();
    const lines = raw.split('\n');
    const content = lines[0].startsWith('# AI 週報分析')
        ? lines.slice(2).join('\n').trimStart()
        : raw;
    document.getElementById('ai-notes').value = content;
    saveAINotes();
    setAIMode('view');
    setWorkflowStep(4, true);
    setWorkflowStep(5, true);
    const statusEl = document.getElementById('ai-request-status');
    if (statusEl) {
        statusEl.textContent = '✅ 偵測到新分析結果，已自動載入！';
        statusEl.style.color = '#2e7d32';
    }
    const loadBtn = document.querySelector('.ai-load-btn');
    if (loadBtn) {
        loadBtn.textContent = '✅ 已自動載入';
        setTimeout(() => { loadBtn.textContent = '🔄 載入最新'; }, 3000);
    }
}

function initPromptEditor() {
    const ta = document.getElementById('ai-prompt-textarea');
    if (ta && !ta.value) {
        ta.value = typeof AI_PROMPT_TEMPLATE !== 'undefined' ? AI_PROMPT_TEMPLATE : '';
    }
}

function togglePromptSection() {
    const body = document.getElementById('ai-prompt-section-body');
    const icon = document.getElementById('ai-prompt-toggle-icon');
    if (!body) return;
    const isOpen = body.style.display !== 'none';
    body.style.display = isOpen ? 'none' : 'block';
    if (icon) icon.textContent = isOpen ? '▸' : '▾';
    if (!isOpen) initPromptEditor();
}

function onPromptInput() {
    _promptModified = true;
}

// ── 步驟狀態追蹤 ──────────────────────────────────────────
const _wfStepDone = { 1: false, 2: false, 4: false };

function setWorkflowStep(step, done) {
    _wfStepDone[step] = done;
    const el = document.getElementById('wf-status-' + step);
    if (!el) return;
    if (done) {
        el.textContent = '✅';
        el.className = 'ai-wf-status done';
    } else {
        el.textContent = '⬜';
        el.className = 'ai-wf-status';
    }
    // 步驟 2 完成 → 步驟 3 顯示「等待中」提示
    if (step === 2) {
        const s3 = document.getElementById('wf-status-3');
        if (s3) {
            s3.textContent = done ? '⏳' : '⬜';
            s3.className = done ? 'ai-wf-status waiting' : 'ai-wf-status';
        }
    }
}

async function pickProjectDirectory() {
    if (!window.showDirectoryPicker) {
        alert('⚠️ 您的瀏覽器不支援 File System Access API。\n請使用 Chrome 或 Edge 開啟儀表板。');
        return null;
    }
    try {
        const handle = await window.showDirectoryPicker({ mode: 'readwrite', id: 'wekan-project' });
        // 驗證是否為專案根目錄（尋找 update_dashboard.py）
        let isRoot = false;
        try {
            await handle.getFileHandle('update_dashboard.py');
            isRoot = true;
        } catch(e) { /* 不在根目錄 */ }

        if (!isRoot) {
            const ok = confirm(
                `⚠️ 這個資料夾可能不是專案根目錄！\n\n` +
                `您選的是：「${handle.name}」\n` +
                `找不到 update_dashboard.py。\n\n` +
                `正確作法：請選擇「0.進度儀錶板with AI」本身，\n` +
                `不要選進去的子資料夾（如「AI prompt」）。\n\n` +
                `確定要使用此資料夾嗎？`
            );
            if (!ok) return null;
        }
        _projDirHandle = handle;
        updateDirBadge(isRoot ? 'ok' : 'warn', handle.name);
        setWorkflowStep(1, true);
        // 記憶資料夾名稱（localStorage）+ handle 本體（IndexedDB）
        localStorage.setItem('ai_proj_dir_name', handle.name);
        _idbPutHandle(handle);  // 供下次一鍵確認用
        dismissRecallBar();
        // 讀取 prompt 版本 meta
        _loadPromptMeta().then(meta => { if (meta) _renderPromptMeta(meta); });
        return _projDirHandle;
    } catch(e) {
        if (e.name !== 'AbortError') console.error('選擇資料夾失敗：', e);
        return null;
    }
}

function updateDirBadge(state, name) {
    const badge = document.getElementById('ai-dir-badge');
    if (!badge) return;
    if (state === 'ok') {
        badge.textContent = `✅ ${name}`;
        badge.style.color = '#2e7d32';
    } else if (state === 'warn') {
        badge.textContent = `⚠️ ${name}（非根目錄？）`;
        badge.style.color = '#e65100';
    } else {
        badge.textContent = '📁 尚未選擇資料夾';
        badge.style.color = '#888';
    }
}

async function ensureDirHandle() {
    if (_projDirHandle) return _projDirHandle;
    return await pickProjectDirectory();
}

// ── Prompt 版本追蹤 ─────────────────────────────────────────
function _fmtDT(date) {
    const p = n => String(n).padStart(2,'0');
    return `${date.getFullYear()}-${p(date.getMonth()+1)}-${p(date.getDate())} ${p(date.getHours())}:${p(date.getMinutes())}`;
}

async function _loadPromptMeta() {
    if (!_projDirHandle) return null;
    try {
        const fh   = await _projDirHandle.getFileHandle('ai_prompt_meta.json');
        const file = await fh.getFile();
        return JSON.parse(await file.text());
    } catch(e) { return null; }
}

async function _savePromptMeta(meta) {
    if (!_projDirHandle) return;
    try {
        const fh = await _projDirHandle.getFileHandle('ai_prompt_meta.json', { create: true });
        const w  = await fh.createWritable();
        await w.write(JSON.stringify(meta, null, 2));
        await w.close();
    } catch(e) { console.warn('儲存 prompt meta 失敗', e); }
}

function _renderPromptMeta(meta) {
    const badge  = document.getElementById('ai-prompt-meta');
    const hBtn   = document.getElementById('ai-prompt-history-btn');
    const hPanel = document.getElementById('ai-prompt-history-panel');
    if (!meta || !badge) return;
    badge.textContent = `v${meta.version} · 上次修改：${meta.saved_at}`;
    badge.style.display = 'inline-flex';
    if (hBtn) hBtn.style.display = 'inline-flex';
    if (hPanel && meta.history && meta.history.length > 0) {
        // 版次從 (version - history.length + 1) 開始
        const startV = meta.version - meta.history.length + 1;
        hPanel.innerHTML = meta.history.map((t, i) =>
            `<div class="ai-ph-row ${i === meta.history.length-1 ? 'ai-ph-current' : ''}">` +
            `<span class="ai-ph-ver">v${startV + i}</span>` +
            `<span class="ai-ph-time">${t}</span>` +
            `${i === meta.history.length-1 ? '<span class="ai-ph-tag">目前</span>' : ''}` +
            `</div>`
        ).reverse().join('');  // 最新在最上方
    }
}

function togglePromptHistory() {
    const panel = document.getElementById('ai-prompt-history-panel');
    if (!panel) return;
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

async function savePromptTemplate() {
    const ta = document.getElementById('ai-prompt-textarea');
    if (!ta) return;
    const content = ta.value;
    const dir = await ensureDirHandle();
    if (!dir) return;
    try {
        // ① 儲存 prompt 本體（ai_prompt_template.md）
        const fh = await dir.getFileHandle('ai_prompt_template.md', { create: true });
        const w  = await fh.createWritable();
        await w.write(content);
        await w.close();
        _promptModified = false;

        // ② 更新版本 meta
        const nowDT = new Date();
        const now   = _fmtDT(nowDT);
        const prev  = await _loadPromptMeta() || { version: 0, history: [] };
        const meta  = {
            version: prev.version + 1,
            saved_at: now,
            history: [...(prev.history || []).slice(-19), now]
        };
        await _savePromptMeta(meta);
        _renderPromptMeta(meta);

        // ③ 儲存版本快照到 AI prompt/ 子資料夾
        const pad = n => String(n).padStart(2, '0');
        const ts  = `${nowDT.getFullYear()}${pad(nowDT.getMonth()+1)}${pad(nowDT.getDate())}` +
                    `_${pad(nowDT.getHours())}${pad(nowDT.getMinutes())}`;
        const snapFilename = `prompt_v${meta.version}_${ts}.md`;
        const snapHeader   = `# Prompt v${meta.version} · ${now}\n\n`;
        try {
            const promptDir = await dir.getDirectoryHandle('AI prompt', { create: true });
            const sfh = await promptDir.getFileHandle(snapFilename, { create: true });
            const sw  = await sfh.createWritable();
            await sw.write(snapHeader + content);
            await sw.close();
        } catch(e) { console.warn('版本快照寫入失敗：', e); }

        const btn = document.querySelector('.ai-prompt-btn-save');
        if (btn) {
            btn.textContent = `✅ 已儲存（v${meta.version}）`;
            setTimeout(() => { btn.textContent = '💾 儲存 Prompt 到本機'; }, 2500);
        }
    } catch(e) {
        alert('儲存 Prompt 失敗：' + e.message);
    }
}

function getCurrentPrompt() {
    const ta = document.getElementById('ai-prompt-textarea');
    if (ta && ta.value) return ta.value;
    return typeof AI_PROMPT_TEMPLATE !== 'undefined' ? AI_PROMPT_TEMPLATE : '';
}

async function generateAIRequest() {
    const statusEl = document.getElementById('ai-request-status');
    const btn = document.querySelector('.ai-action-primary');
    const setStatus = (msg, color) => {
        if (statusEl) { statusEl.textContent = msg; statusEl.style.color = color || '#555'; }
    };

    setStatus('⏳ 正在準備…', '#888');
    const dir = await ensureDirHandle();
    if (!dir) { setStatus('❌ 請先選擇專案資料夾', '#c62828'); return; }

    const now  = new Date();
    const pad  = n => String(n).padStart(2, '0');
    const today = `${now.getFullYear()}/${pad(now.getMonth()+1)}/${pad(now.getDate())}`;
    const ts    = `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}`;

    const template  = getCurrentPrompt();
    const wekanData = buildAICopyText();
    const fullPrompt = template
        .replace('{{TODAY}}', today)
        .replace('{{WEKAN_DATA}}', wekanData);

    const requestObj = {
        generated_at:    now.toISOString(),
        today:           today,
        prompt:          fullPrompt,
        prompt_template: template,
        data_only:       wekanData,
        output_filename: `${AI_FILENAME_PREFIX}_${ts}.md`,
        output_folder:   AI_SAVE_FOLDER,
        ready:           true
    };

    try {
        const fh = await dir.getFileHandle('ai_request.json', { create: true });
        const writable = await fh.createWritable();
        await writable.write(JSON.stringify(requestObj, null, 2));
        await writable.close();
        setStatus('✅ 請求已產生！請切換到 Cowork 說「分析」', '#2e7d32');
        setWorkflowStep(2, true);
        _requestGeneratedAt = new Date();
        startPolling();
        if (btn) {
            btn.textContent = '🤖 請求已產生 ✅';
            setTimeout(() => { btn.textContent = '🤖 產生分析請求'; }, 4000);
        }
    } catch(e) {
        setStatus('❌ 寫入失敗：' + e.message, '#c62828');
    }
}

async function loadLatestAnalysis() {
    const dir = await ensureDirHandle();
    if (!dir) return;

    try {
        let resultsDir;
        try {
            resultsDir = await dir.getDirectoryHandle(AI_SAVE_FOLDER);
        } catch(e) {
            alert(
                `找不到「${AI_SAVE_FOLDER}」資料夾。\n\n` +
                `目前選取的資料夾是：「${dir.name}」\n\n` +
                `請確認：\n` +
                `① 步驟一有選取「0.進度儀錶板with AI」根目錄\n` +
                `  （不要選子資料夾，如「AI prompt」）\n` +
                `② 點「⚙️ Prompt 設定」→「📁 選擇專案資料夾」重新選取\n` +
                `③ 確認根目錄下有「${AI_SAVE_FOLDER}」資料夾`
            );
            return;
        }

        let latestFile = null;
        let latestTime = 0;
        for await (const [name, handle] of resultsDir.entries()) {
            if (handle.kind === 'file' && name.endsWith('.md')) {
                const file = await handle.getFile();
                if (file.lastModified > latestTime) {
                    latestTime = file.lastModified;
                    latestFile = file;
                }
            }
        }

        if (!latestFile) {
            alert(`「${AI_SAVE_FOLDER}」資料夾中尚無 .md 分析檔案。`);
            return;
        }

        const raw   = await latestFile.text();
        const lines = raw.split('\n');
        const content = lines[0].startsWith('# AI 週報分析')
            ? lines.slice(2).join('\n').trimStart()
            : raw;

        document.getElementById('ai-notes').value = content;
        saveAINotes();
        setAIMode('view');
        setWorkflowStep(4, true);
        setWorkflowStep(5, true);

        const loadBtn = document.querySelector('.ai-load-btn');
        if (loadBtn) {
            loadBtn.textContent = `✅ 已載入 ${latestFile.name}`;
            setTimeout(() => { loadBtn.textContent = '🔄 載入最新'; }, 3000);
        }
    } catch(e) {
        alert('載入分析結果失敗：' + e.message);
    }
}

// ==================== Sub-Tab Switch ====================

// 需求 #4: 展開/折疊父任務組
// ==================== 父子結構：遞迴分組排序 ====================

// 父任務狀態 Tab 切換（Feature C-3）
function switchParentStatusTab(tabName, statusIdx) {
    const container = document.getElementById(tabName + '-parent-container');
    if (!container) return;
    // 切換 tab 按鈕 active
    container.querySelectorAll('.parent-status-tab-bar .sub-tab-btn').forEach((b, i) => {
        b.classList.toggle('active', i === statusIdx);
    });
    // 切換 panel
    container.querySelectorAll('.parent-status-panel').forEach((p, i) => {
        p.classList.toggle('active', i === statusIdx);
    });
}

// 欄位分組順序（優先待處理，完成放最下）
const CHILD_LIST_ORDER = ['Doing','Waiting','Review / 使用者Test','Ready to GO','準備中','Backlog','Closed','DONE'];

// 取得欄位排序權重（未知欄位放中間）
function listRank(listName) {
    const idx = CHILD_LIST_ORDER.indexOf(listName);
    return idx === -1 ? CHILD_LIST_ORDER.length - 2 : idx;
}

// 組內排序
function sortCardsInGroup(cards, listName) {
    return [...cards].sort((a, b) => {
        let da, db;
        if (listName === 'DONE') {
            da = a.endAt ? new Date(a.endAt) : new Date(a.dateLastActivity || 0);
            db = b.endAt ? new Date(b.endAt) : new Date(b.dateLastActivity || 0);
        } else {
            da = new Date(a.dateLastActivity || 0);
            db = new Date(b.dateLastActivity || 0);
        }
        return db - da; // 新 → 舊
    });
}

// 遞迴渲染子任務（帶分組標題，depth 控制縮排）
function renderChildrenRecursive(parentId, childrenMap, depth) {
    const children = childrenMap[parentId] || [];
    if (children.length === 0) return '';

    // 依欄位分組
    const groups = {};
    children.forEach(c => {
        const key = c.list || '未知';
        if (!groups[key]) groups[key] = [];
        groups[key].push(c);
    });

    // 依 CHILD_LIST_ORDER 排序分組
    const sortedLists = Object.keys(groups).sort((a, b) => listRank(a) - listRank(b));

    const indentPx = depth * 20;
    const indentStyle = `padding-left:${indentPx + 8}px`;
    let html = '';

    sortedLists.forEach(listName => {
        const groupCards = sortCardsInGroup(groups[listName], listName);

        // 分組標題列
        html += `<tr class="child-list-group-header">
            <td colspan="7" style="${indentStyle}">
                <span class="child-depth-marker">${'│ '.repeat(depth)}</span>▶ ${listName} (${groupCards.length})
            </td>
        </tr>`;

        // 組內卡片
        groupCards.forEach(c => {
            const staleClass = c.isStale ? 'stale-badge' : 'active-badge';
            const staleLabel = c.isDone ? '完成' : (c.isStale ? `停滯${c.staleDays}天` : '活躍');
            const hasGrandChildren = (childrenMap[c.id] || []).length > 0;
            const titlePrefix = hasGrandChildren ? '📁 ' : '';
            html += `<tr>
                <td style="padding-left:${indentPx + 12}px">${c.swimlane || '—'}</td>
                <td>${titlePrefix}${cardLink(c.id, c.title)}</td>
                <td><span class="badge">${c.list}</span></td>
                <td>${c.members.join(', ') || '—'}</td>
                <td>${(c.dateLastActivity || '').slice(0, 10)}</td>
                <td>${c.staleDays != null ? c.staleDays : '—'}</td>
                <td><span class="badge ${staleClass}">${staleLabel}</span></td>
            </tr>`;
            // 遞迴展開孫任務
            if (hasGrandChildren) {
                html += renderChildrenRecursive(c.id, childrenMap, depth + 1);
            }
        });
    });

    return html;
}

// toggleGroup：父任務點擊展開/收合
function toggleGroup(el, groupKey, parentId) {
    const body = el.nextElementSibling;
    const isOpen = body.style.display !== 'none';

    if (!isOpen && body.innerHTML === '') {
        if (parentId) {
            // 父任務群組：遞迴渲染所有後代
            const rows = renderChildrenRecursive(parentId, currentChildrenMap, 0);
            body.innerHTML = `<table><thead><tr>
                <th>主題</th><th>卡片名稱</th><th>欄位</th><th>負責人</th>
                <th>最後活動日</th><th>停滯天數</th><th>狀態</th>
            </tr></thead><tbody>${rows || '<tr><td colspan="7" style="color:#999;text-align:center">無子任務</td></tr>'}</tbody></table>`;
        } else {
            // 獨立卡片群組：平面渲染（原邏輯）
            const children = parentGroupData[groupKey] || [];
            children.sort((a, b) => new Date(b.dateLastActivity || 0) - new Date(a.dateLastActivity || 0));
            const rows = children.map(c => {
                const staleClass = c.isStale ? 'stale-badge' : 'active-badge';
                const staleLabel = c.isDone ? '完成' : (c.isStale ? `停滯${c.staleDays}天` : '活躍');
                return `<tr>
                    <td>${c.swimlane || '—'}</td>
                    <td>${cardLink(c.id, c.title)}</td>
                    <td><span class="badge">${c.list}</span></td>
                    <td>${c.members.join(', ') || '—'}</td>
                    <td>${(c.dateLastActivity || '').slice(0, 10)}</td>
                    <td>${c.staleDays != null ? c.staleDays : '—'}</td>
                    <td><span class="badge ${staleClass}">${staleLabel}</span></td>
                </tr>`;
            }).join('');
            body.innerHTML = `<table><thead><tr>
                <th>主題</th><th>卡片名稱</th><th>欄位</th><th>負責人</th>
                <th>最後活動日</th><th>停滯天數</th><th>狀態</th>
            </tr></thead><tbody>${rows || '<tr><td colspan="7" style="color:#999;text-align:center">無資料</td></tr>'}</tbody></table>`;
        }
    }

    body.style.display = isOpen ? 'none' : '';
    const arrow = el.querySelector('.pg-arrow');
    if (arrow) arrow.textContent = isOpen ? '▶' : '▼';
}

// 改動 A4: switchNewDone 函式
function switchNewDone(tab, name) {
    ['new','done','activity','compare'].forEach(n => {
        const panel = document.getElementById(tab + '-nd-' + n);
        const btn = document.getElementById(tab + '-nd-btn-' + n);
        if (panel) panel.style.display = n === name ? '' : 'none';
        if (btn) btn.classList.toggle('active', n === name);
    });
    // 主題對照：lazy render
    if (name === 'compare') {
        const tabN = tab === 't1' ? 1 : 2;
        _renderNDCompareIfNeeded(tabN);
    }
}

// 主題對照 lazy render flag + 排序覆寫（localStorage 持久化）
let _ndCmpDirty = { 1: true, 2: true };
let _ndCmpOrderOverride = (function() {
    try { return JSON.parse(localStorage.getItem('ndCmpSwimOrder') || 'null'); }
    catch(e) { return null; }
})();

// ── Drag & Drop handlers ──────────────────────────────────
let _ndDragSrcRow = null;

function _ndDragStart(e) {
    _ndDragSrcRow = e.currentTarget;
    e.dataTransfer.effectAllowed = 'move';
    setTimeout(() => { if (_ndDragSrcRow) _ndDragSrcRow.style.opacity = '0.4'; }, 0);
}

function _ndDragEnd(e) {
    e.currentTarget.style.opacity = '';
    document.querySelectorAll('.nd-cmp-row').forEach(r => r.classList.remove('drag-over'));
    _ndDragSrcRow = null;
}

function _ndDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (_ndDragSrcRow && e.currentTarget !== _ndDragSrcRow) {
        document.querySelectorAll('.nd-cmp-row').forEach(r => r.classList.remove('drag-over'));
        e.currentTarget.classList.add('drag-over');
    }
}

function _ndDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

function _ndDrop(e, tabN) {
    e.preventDefault();
    const tgt = e.currentTarget;
    tgt.classList.remove('drag-over');
    if (!_ndDragSrcRow || _ndDragSrcRow === tgt) return;

    // 讀取目前所有列的主題順序
    const container = _ndDragSrcRow.closest('.nd-cmp-table');
    if (!container) return;
    const rows = Array.from(container.querySelectorAll('.nd-cmp-row[data-swim]'));
    const swims = rows.map(r => r.dataset.swim);

    const srcIdx = rows.indexOf(_ndDragSrcRow);
    const tgtIdx = rows.indexOf(tgt);
    if (srcIdx < 0 || tgtIdx < 0) return;

    // 移動
    swims.splice(tgtIdx, 0, swims.splice(srcIdx, 1)[0]);

    // 儲存並重繪
    _ndCmpOrderOverride = swims;
    try { localStorage.setItem('ndCmpSwimOrder', JSON.stringify(swims)); } catch(ex) {}

    _ndCmpDirty[1] = true;
    _ndCmpDirty[2] = true;
    _renderNDCompareIfNeeded(tabN);
}

// ─────────────────────────────────────────────────────────

function toggleNDPipeline(headEl) {
    const row = headEl.closest('.nd-cmp-row');
    if (!row) return;
    const pipeline = row.querySelector('.nd-cmp-pipeline');
    const arrow    = headEl.querySelector('.nd-cmp-expand-arrow');
    if (!pipeline) return;
    const isOpen = pipeline.style.display !== 'none';
    pipeline.style.display = isOpen ? 'none' : '';
    if (arrow) arrow.textContent = isOpen ? '▶' : '▼';
}

function _renderNDCompareIfNeeded(tabN) {
    if (!_ndCmpDirty[tabN]) return;
    _ndCmpDirty[tabN] = false;
    const cards = tabN === 1 ? filteredCards1 : filteredCards2;
    const dates  = tabN === 1 ? t1FilterDates  : t2FilterDates;
    if (!cards || !dates.startDt) return;
    const { startDt, endDt } = dates;

    const newCards = cards.filter(c => {
        const ct = c.createdAt ? new Date(c.createdAt) : null;
        return ct && ct >= startDt && ct <= endDt && !c.archived;
    });
    const doneCards = cards.filter(c => {
        const et = c.endAt ? new Date(c.endAt) : null;
        return c.isDone && et && et >= startDt && et <= endDt;
    });

    const wrap = document.getElementById('t' + tabN + '-nd-cmp-wrap');
    if (wrap) wrap.innerHTML = _buildNDCompareHTML(newCards, doneCards, tabN, cards);
}

function _buildNDCompareHTML(newCards, doneCards, tabN, allCards) {
    // 取兩側主題聯集
    const swimSet = new Set([...newCards.map(c => c.swimlane), ...doneCards.map(c => c.swimlane)]);
    let swims = Array.from(swimSet);

    // 排序：localStorage 覆寫 > SWIM_ORDER > 字母
    if (_ndCmpOrderOverride && _ndCmpOrderOverride.length > 0) {
        const ordered = [];
        _ndCmpOrderOverride.forEach(s => { if (swims.includes(s)) ordered.push(s); });
        swims.forEach(s => { if (!ordered.includes(s)) ordered.push(s); });
        swims = ordered;
    } else if (SWIM_ORDER.length > 0) {
        swims.sort((a, b) => {
            const ia = SWIM_ORDER.indexOf(a), ib = SWIM_ORDER.indexOf(b);
            return (ia < 0 ? 9999 : ia) - (ib < 0 ? 9999 : ib);
        });
    } else {
        swims.sort();
    }

    // 依主題分組
    const bySwimNew  = {};
    const bySwimDone = {};
    newCards.forEach(c  => { (bySwimNew[c.swimlane]  = bySwimNew[c.swimlane]  || []).push(c); });
    doneCards.forEach(c => { (bySwimDone[c.swimlane] = bySwimDone[c.swimlane] || []).push(c); });

    const cardRow = c => {
        const members = c.members && c.members.length ? c.members.join('、') : '無負責人';
        return `<div class="nd-cmp-card">${cardLink(c.id, c.title)}<span class="nd-cmp-card-member">（${members}）</span></div>`;
    };

    // Pipeline 卡片清單（allCards = 篩選後全部卡片，不限日期）
    const pipeBySwim = {};
    if (allCards) {
        allCards.forEach(c => {
            if (!pipeBySwim[c.swimlane]) pipeBySwim[c.swimlane] = { doing:[], waiting:[], review:[] };
            if (c.isDoing)   pipeBySwim[c.swimlane].doing.push(c);
            if (c.isWaiting) pipeBySwim[c.swimlane].waiting.push(c);
            if (c.isReview)  pipeBySwim[c.swimlane].review.push(c);
        });
    }

    // Pipeline 欄 HTML helper
    const pipeColHTML = (cards, type) => {
        const hdrClass = type === 'doing' ? 'doing-hdr' : type === 'waiting' ? 'waiting-hdr' : 'review-hdr';
        const icon     = type === 'doing' ? '🔄'        : type === 'waiting' ? '⏳'           : '👁';
        const label    = type === 'doing' ? 'Doing'     : type === 'waiting' ? 'Waiting'      : 'Review';
        const hdr = `<div class="nd-cmp-pipe-col-hdr ${hdrClass}">${icon} ${label} (${cards.length})</div>`;
        return hdr + (cards.length ? cards.map(cardRow).join('') : '<div class="nd-cmp-empty">無</div>');
    };

    let rowsHtml = '';
    swims.forEach(swim => {
        const nc = bySwimNew[swim]  || [];
        const dc = bySwimDone[swim] || [];
        const newCellHTML  = nc.length ? nc.map(cardRow).join('') : '<div class="nd-cmp-empty">本週無新增</div>';
        const doneCellHTML = dc.length ? dc.map(cardRow).join('') : '<div class="nd-cmp-empty">本週無完成</div>';

        // Pipeline badge（數字）
        const pipe = pipeBySwim[swim] || { doing:[], waiting:[], review:[] };
        const dN = pipe.doing.length, wN = pipe.waiting.length, rN = pipe.review.length;
        const badgeHtml = `<div class="nd-cmp-pipe-badges">
            <span class="nd-cmp-pipe-badge doing${dN===0?' zero':''}">Doing ${dN}</span>
            <span class="nd-cmp-pipe-badge waiting${wN===0?' zero':''}">Waiting ${wN}</span>
            <span class="nd-cmp-pipe-badge review${rN===0?' zero':''}">Review ${rN}</span>
        </div>`;

        // Pipeline 展開區（預設隱藏）
        const pipelineHTML = `<div class="nd-cmp-pipeline" style="display:none">
            <div class="nd-cmp-pipe-cols">
                <div class="nd-cmp-pipe-col">${pipeColHTML(pipe.doing,   'doing'  )}</div>
                <div class="nd-cmp-pipe-col">${pipeColHTML(pipe.waiting, 'waiting')}</div>
                <div class="nd-cmp-pipe-col">${pipeColHTML(pipe.review,  'review' )}</div>
            </div>
        </div>`;

        rowsHtml += `<div class="nd-cmp-row" data-swim="${swim}" draggable="true"
            ondragstart="_ndDragStart(event)"
            ondragend="_ndDragEnd(event)"
            ondragover="_ndDragOver(event)"
            ondragleave="_ndDragLeave(event)"
            ondrop="_ndDrop(event,${tabN})">
            <div class="nd-cmp-row-head" onclick="toggleNDPipeline(this)">
                <span class="nd-cmp-drag-handle" ondragstart="event.stopPropagation()" onclick="event.stopPropagation()">⠿</span>
                <span class="nd-cmp-swim-name">${swim}</span>
                ${badgeHtml}
                <span class="nd-cmp-expand-arrow">▶</span>
            </div>
            ${pipelineHTML}
            <div class="nd-cmp-row-body">
                <div class="nd-cmp-cell">${doneCellHTML}</div>
                <div class="nd-cmp-cell">${newCellHTML}</div>
            </div>
        </div>`;
    });
    if (!rowsHtml) rowsHtml = '<div style="padding:12px;color:#aaa;font-style:italic;text-align:center;">本期無資料</div>';

    return `<div class="nd-cmp-table">
        <div class="nd-cmp-hdr-row">
            <div class="nd-cmp-hdr-drag"></div>
            <div class="nd-cmp-hdr-cell done-hdr">✅ 本週完成（${doneCards.length} 張）</div>
            <div class="nd-cmp-hdr-cell new-hdr">📥 本週新增（${newCards.length} 張）</div>
        </div>
        ${rowsHtml}
    </div>`;
}

// 改動 C5: switchTab1 - 只對 lazy 的分頁呼叫 renderT1Panel
function switchTab1(name) {
    const panels = ['newdone', 'doing', 'risk', 'parent', 'all'];
    document.querySelectorAll('#main-panel-overview .sub-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('#main-panel-overview .sub-tab-btn').forEach(b => b.classList.remove('active'));

    if (panels.includes(name)) {
        t1SubTab = name;
        document.getElementById(`t1-panel-${name}`).classList.add('active');
        event.target.classList.add('active');
        if (name === 'all' || name === 'parent') {
            renderT1Panel(name);
        }
    }
}

// 改動 C6: switchTab2 - 只對 lazy 的分頁呼叫 renderT2Panel
function switchTab2(name) {
    const panels = ['newdone', 'all', 'parent'];
    document.querySelectorAll('#main-panel-personal .sub-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('#main-panel-personal .sub-tab-btn').forEach(b => b.classList.remove('active'));

    if (panels.includes(name)) {
        t2SubTab = name;
        document.getElementById(`t2-panel-${name}`).classList.add('active');
        event.target.classList.add('active');
        if (name === 'all' || name === 'parent') {
            renderT2Panel(name);
        }
    }
}

// ==================== 改動 2: 子分頁 Lazy Render 函式 ====================

// 改動 C3: renderT1Panel - 只對 lazy 的分頁渲染
function renderT1Panel(name) {
    if (!t1DirtyPanels.has(name)) return;
    const { startDt, endDt } = t1FilterDates;
    if (!startDt) return;
    t1DirtyPanels.delete(name);
    if (name === 'all') renderAll1(filteredCards1);
    else if (name === 'parent') renderParentGroups('t1', filteredCards1);
}

// 改動 C4: renderT2Panel - 只對 lazy 的分頁渲染
function renderT2Panel(name) {
    if (!t2DirtyPanels.has(name)) return;
    const { startDt, endDt } = t2FilterDates;
    if (!startDt) return;
    t2DirtyPanels.delete(name);
    if (name === 'all') renderAll2(filteredCards2);
    else if (name === 'parent') renderParentGroups('t2', filteredCards2);
}

// 需求 #1: 風險分頁子分頁切換
function switchRiskSubTab(name) {
    riskSubTab = name;
    const panels = document.querySelectorAll('#t1-panel-risk .sub-panel');
    const btns = document.querySelectorAll('#t1-panel-risk .sub-tab-btn');

    panels.forEach(p => p.classList.remove('active'));
    btns.forEach(b => b.classList.remove('active'));

    const panelMap = { overview: 'risk-subpanel-overview', swim: 'risk-subpanel-swim', newrisk: 'risk-subpanel-newrisk', duesoon: 'risk-subpanel-duesoon' };
    if (panelMap[name]) document.getElementById(panelMap[name]).classList.add('active');
    if (event && event.target) event.target.classList.add('active');
}

// KPI 卡片統一跳轉函式
function jumpToKPI(type) {
    switchMainTab('overview');
    if (type === 'done') {
        // → 本週動態 > 本週完成 mini-tab
        _switchTab1Direct('newdone');
        _activateNewDoneMiniTab('t1', 'done');
    } else if (type === 'new') {
        // → 本週動態 > 本週新增 mini-tab
        _switchTab1Direct('newdone');
        _activateNewDoneMiniTab('t1', 'new');
    } else if (type === 'newrisk') {
        // → 風險與停滯 > 本週新風險 sub-panel
        _switchTab1Direct('risk');
        _switchRiskSubTabDirect('newrisk');
    } else if (type === 'duesoon') {
        // → 風險與停滯 > 即將到期 sub-panel
        _switchTab1Direct('risk');
        _switchRiskSubTabDirect('duesoon');
    } else if (type === 'doing') {
        // → Doing 明細
        _switchTab1Direct('doing');
    }
    // 捲動到子分頁區域
    setTimeout(() => {
        const el = document.getElementById('t1-sub-tab-bar') || document.querySelector('#main-panel-overview .sub-tab-bar');
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
}

// 不依賴 event 的 Tab1 切換（供 jumpToKPI 呼叫）
function _switchTab1Direct(name) {
    const panels = ['newdone', 'doing', 'risk', 'parent', 'all'];
    document.querySelectorAll('#main-panel-overview .sub-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('#main-panel-overview .sub-tab-btn').forEach(b => b.classList.remove('active'));
    if (panels.includes(name)) {
        t1SubTab = name;
        document.getElementById(`t1-panel-${name}`).classList.add('active');
        // 點亮對應按鈕（依 onclick 內容比對）
        const btn = [...document.querySelectorAll('#main-panel-overview > .sub-tab-bar .sub-tab-btn')]
            .find(b => b.getAttribute('onclick') && b.getAttribute('onclick').includes(`'${name}'`));
        if (btn) btn.classList.add('active');
        if (name === 'all' || name === 'parent') renderT1Panel(name);
    }
}

// 不依賴 event 的風險子分頁切換
function _switchRiskSubTabDirect(name) {
    riskSubTab = name;
    document.querySelectorAll('#t1-panel-risk .sub-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('#t1-panel-risk .sub-tab-btn').forEach(b => b.classList.remove('active'));
    const panel = document.getElementById(`risk-subpanel-${name}`);
    if (panel) panel.classList.add('active');
    const btn = [...document.querySelectorAll('#t1-panel-risk .sub-tab-btn')]
        .find(b => b.getAttribute('onclick') && b.getAttribute('onclick').includes(`'${name}'`));
    if (btn) btn.classList.add('active');
}

// 不依賴 event 的 mini-tab 切換（供 jumpToKPI 呼叫）
function _activateNewDoneMiniTab(tab, type) {
    // 觸發 switchNewDone 但不依賴 event
    const btnId = `${tab}-nd-btn-${type}`;
    const btn = document.getElementById(btnId);
    if (btn) {
        // 更新 active 樣式
        document.querySelectorAll(`#${tab}-panel-newdone .mini-tab-btn`).forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }
    // 觸發渲染（重用 switchNewDone 邏輯，偽造 event）
    const prevEvent = window.event;
    try { switchNewDone(tab, type); } catch(e) {}
}

function jumpToDueSoon() {
    jumpToKPI('duesoon');
}

// 需求 #1 & #3: 風險泳道篩選
function applyRiskSwimFilter() {
    riskSwimFilter = document.getElementById('t1-risk-swim-filter').value;
    updateRiskTables(filteredCards1);
}


// 需求 #3: 父子結構泳道篩選
function applyParentSwimFilter(tabName) {
    const swimSel = document.getElementById(tabName+'-parent-swim-filter');
    const swimVal = swimSel ? swimSel.value : '';
    const cards = tabName==='t1' ? filteredCards1 : filteredCards2;
    const filtered = swimVal ? cards.filter(c=>c.swimlane===swimVal) : cards;
    renderParentGroups(tabName, filtered);
}

// ==================== Swimlane Ordering ====================

// SWIM_ORDER 從 team_config.json board.swimlanes_order 讀取
// 空陣列 = 依 Wekan JSON 原始順序；有值 = 依指定順序排列

function swimRank(name) {
    if (SWIM_ORDER.length === 0) return 9999;   // 空 = 不強制排序
    const i = SWIM_ORDER.indexOf(name);
    return i >= 0 ? i : 9999;
}

// 主題交替底色（方案 A）：依 SWIM_ORDER 位置奇偶決定
// 偶數索引 = 白色（無額外 class），奇數索引 = 淡藍色（row-alt-bg）
const SWIM_COLOR_MAP = {};
(SWIM_ORDER.length > 0
    ? SWIM_ORDER
    : [...new Set(RAW.cards.map(c => c.swimlane))]
).forEach((s, i) => { SWIM_COLOR_MAP[s] = i % 2; });
function getSwimRowClass(swimlane) {
    return SWIM_COLOR_MAP[swimlane] === 1 ? 'row-alt-bg' : '';
}
function toggleActGroup(el) { el.parentElement.classList.toggle('collapsed'); }

function sortBySwim(cards) {
    return [...cards].sort((a,b) => {
        const rA = swimRank(a.swimlane||'');
        const rB = swimRank(b.swimlane||'');
        if(rA !== rB) return rA - rB;
        return new Date(a.createdAt) - new Date(b.createdAt);
    });
}

// ==================== Filtering ====================

function getChecked(selector) {
    return Array.from(document.querySelectorAll(selector))
        .filter(cb => cb.checked)
        .map(cb => cb.value);
}

function applyFilters1() {
    const startDt = new Date(document.getElementById('t1-date-start').value);
    const endDt = new Date(document.getElementById('t1-date-end').value);
    endDt.setHours(23, 59, 59, 999);

    const checkedLists = getChecked('#t1-list-picker-items input[type="checkbox"]');
    const checkedSwims = getChecked('#t1-swim-picker-items input[type="checkbox"]');
    const checkedLabels = getChecked('#t1-label-picker-items input[type="checkbox"]');
    const checkedStatuses = getChecked('#t1-status-picker-items input[type="checkbox"]');
    const checkedArchived = getChecked('#t1-archived-picker-items input[type="checkbox"]');

    filteredCards1 = RAW.cards.filter(c => {
        // List filter
        if (checkedLists.length > 0 && !checkedLists.includes(c.listId)) return false;

        // Swim filter
        if (checkedSwims.length > 0 && !checkedSwims.includes(c.swimlaneId)) return false;

        // Label filter（有標籤的卡片才比對；全選=不限）
        if (checkedLabels.length > 0 && c.labels.length > 0) {
            const hasLabel = c.labels.some(lbl => checkedLabels.some(lid => RAW.labelsMap[lid] === lbl));
            if (!hasLabel) return false;
        }

        // Status filter（全選7項=不限）
        if (checkedStatuses.length > 0 && checkedStatuses.length < 7) {
            const hasStatus = checkedStatuses.some(st => {
                if (st === 'doing') return c.isDoing;
                if (st === 'waiting') return c.isWaiting;
                if (st === 'review') return c.isReview;
                if (st === 'done') return c.isDone;
                if (st === 'stale') return c.isStale;
                if (st === 'overdue') return c.isOverdue;
                if (st === 'nomember') return c.noMember;
                return false;
            });
            if (!hasStatus) return false;
        }

        // Archived filter
        if (checkedArchived.length > 0) {
            const hasArch = checkedArchived.some(a => {
                if (a === 'active') return !c.archived;
                if (a === 'archived') return c.archived;
                if (a === 'all') return true;
                return false;
            });
            if (!hasArch) return false;
        } else {
            return !c.archived;
        }

        return true;
    });

    updateKPI(filteredCards1, startDt, endDt);
    updateCharts(filteredCards1, startDt, endDt);

    // 改動 C1: 輕量子分頁即時渲染（Method Y）
    t1FilterDates = { startDt, endDt };
    _ndCmpDirty[1] = true;
    renderNewDone1(filteredCards1, startDt, endDt);
    renderDoing1(filteredCards1);
    updateRiskTables(filteredCards1);
    updateTabBadges1(filteredCards1, startDt, endDt);
    // 重量子分頁標記 dirty，等使用者點擊再渲染
    t1DirtyPanels = new Set(['all', 'parent']);
    t1AllPage = 1;
    // 若目前在重量子分頁，立即渲染
    if (t1DirtyPanels.has(t1SubTab)) {
        renderT1Panel(t1SubTab);
    }
    renderFilterChips1(startDt, endDt, checkedLists, checkedSwims, checkedLabels, checkedStatuses);
}

function applyFilters2() {
    const startDt = new Date(document.getElementById('t2-date-start').value);
    const endDt = new Date(document.getElementById('t2-date-end').value);
    endDt.setHours(23, 59, 59, 999);

    const checkedSwims = getChecked('#t2-swim-picker-items input[type="checkbox"]');
    const checkedLabels = getChecked('#t2-label-picker-items input[type="checkbox"]');
    const checkedMembers = getChecked('#t2-member-picker-items input[type="checkbox"]');
    const checkedStatuses = getChecked('#t2-status-picker-items input[type="checkbox"]');
    const checkedArchived = getChecked('#t2-archived-picker-items input[type="checkbox"]');
    const checkedTaskTypes = getChecked('#t2-tasktype-picker-items input[type="checkbox"]');

    filteredCards2 = RAW.cards.filter(c => {
        // Swim filter
        if (checkedSwims.length > 0 && !checkedSwims.includes(c.swimlaneId)) return false;

        // Label filter（有標籤的卡片才比對；全選=不限）
        if (checkedLabels.length > 0 && c.labels.length > 0) {
            const hasLabel = c.labels.some(lbl => checkedLabels.some(lid => RAW.labelsMap[lid] === lbl));
            if (!hasLabel) return false;
        }

        // Member filter
        if (checkedMembers.length > 0) {
            const hasMember = c.members.some(m => checkedMembers.some(mid => RAW.users[mid] === m));
            if (!hasMember) return false;
        }

        // Status filter（全選7項=不限）
        if (checkedStatuses.length > 0 && checkedStatuses.length < 7) {
            const hasStatus = checkedStatuses.some(st => {
                if (st === 'doing') return c.isDoing;
                if (st === 'waiting') return c.isWaiting;
                if (st === 'review') return c.isReview;
                if (st === 'done') return c.isDone;
                if (st === 'stale') return c.isStale;
                if (st === 'overdue') return c.isOverdue;
                if (st === 'nomember') return c.noMember;
                return false;
            });
            if (!hasStatus) return false;
        }

        // Archived filter
        if (checkedArchived.length > 0) {
            const hasArch = checkedArchived.some(a => {
                if (a === 'active') return !c.archived;
                if (a === 'archived') return c.archived;
                if (a === 'all') return true;
                return false;
            });
            if (!hasArch) return false;
        } else {
            return !c.archived;
        }

        // Task type filter（全選3項=不限）
        if (checkedTaskTypes.length > 0 && checkedTaskTypes.length < 3) {
            const hasType = checkedTaskTypes.some(tt => {
                if (tt === 'parent') return c.isParentTask;
                if (tt === 'child') return c.isChildTask;
                if (tt === 'standalone') return c.isStandalone;
                return false;
            });
            if (!hasType) return false;
        }

        return true;
    });

    const focusMembers = checkedMembers;
    if (focusMembers.length === 1) {
        updatePersonalFocus(focusMembers[0], filteredCards2, startDt, endDt);
    } else {
        document.getElementById('t2-focus-section').style.display = 'none';
        document.getElementById('t2-focus-placeholder').style.display = 'block';
    }

    // 改動 C2: 輕量子分頁即時渲染（Method Y）
    t2FilterDates = { startDt, endDt };
    _ndCmpDirty[2] = true;
    renderNewDone2(filteredCards2, startDt, endDt);
    updateTabBadges2(filteredCards2, startDt, endDt);
    t2DirtyPanels = new Set(['all', 'parent']);
    t2AllPage = 1;
    if (t2DirtyPanels.has(t2SubTab)) {
        renderT2Panel(t2SubTab);
    }
    renderFilterChips2(startDt, endDt, checkedSwims, checkedLabels, checkedMembers, checkedStatuses);
}

// ==================== Card Link Helper ====================

function cardLink(id, title) {
    if (!WEKAN_URL_BASE) {
        return `<span style="font-weight:500">${title}</span>`;
    }
    return `<a href="${WEKAN_URL_BASE}/${id}" target="_blank" class="card-link" onclick="event.stopPropagation()">${title}</a>`;
}

// 改動 B4: updateTabBadges1 和 updateTabBadges2
function updateTabBadges1(cards, startDt, endDt) {
    const newCount = cards.filter(c => { const d=new Date(c.createdAt); return d>=startDt&&d<=endDt; }).length;
    const doneCount = cards.filter(c => { const d=c.endAt?new Date(c.endAt):null; return c.isDone&&d&&d>=startDt&&d<=endDt; }).length;
    const ACT_EX1 = ['DONE','Closed','Backlog','Goal＆專案資訊'];
    const actCount = cards.filter(c => {
        const d=c.dateLastActivity?new Date(c.dateLastActivity):null;
        if(!d||d<startDt||d>endDt) return false;
        if(ACT_EX1.includes(c.list)) return false;
        const isNew = new Date(c.createdAt)>=startDt;
        const isDoneW = c.isDone&&c.endAt&&new Date(c.endAt)>=startDt;
        return !isNew&&!isDoneW;
    }).length;
    const setBadge = (id, n) => { const el=document.getElementById(id); if(el) el.textContent=n>0?n:''; };
    setBadge('t1-nd-badge-new', newCount);
    setBadge('t1-nd-badge-done', doneCount);
    setBadge('t1-nd-badge-activity', actCount);
    const ndTotal = newCount + doneCount + actCount;
    setBadge('t1-cnt-newdone', ndTotal > 0 ? ndTotal : '');
    setBadge('t1-cnt-doing', cards.filter(c=>c.isDoing).length || '');
    const riskCount = cards.filter(c=>!['DONE','Closed','過往卡片','過往卡片待青','Goal＆專案資訊'].includes(c.list)&&!c.archived&&c.isStale).length;
    setBadge('t1-cnt-risk', riskCount || '');
    setBadge('t1-cnt-parent', cards.filter(c=>c.isParentTask).length || '');
    setBadge('t1-cnt-all', cards.length || '');
}

function updateTabBadges2(cards, startDt, endDt) {
    const newCount = cards.filter(c => { const d=new Date(c.createdAt); return d>=startDt&&d<=endDt; }).length;
    const doneCount = cards.filter(c => { const d=c.endAt?new Date(c.endAt):null; return c.isDone&&d&&d>=startDt&&d<=endDt; }).length;
    const ACT_EX2 = ['DONE','Closed','Backlog','Goal＆專案資訊'];
    const actCount = cards.filter(c => {
        const d=c.dateLastActivity?new Date(c.dateLastActivity):null;
        if(!d||d<startDt||d>endDt) return false;
        if(ACT_EX2.includes(c.list)) return false;
        const isNew = new Date(c.createdAt)>=startDt;
        const isDoneW = c.isDone&&c.endAt&&new Date(c.endAt)>=startDt;
        return !isNew&&!isDoneW;
    }).length;
    const setBadge = (id, n) => { const el=document.getElementById(id); if(el) el.textContent=n>0?n:''; };
    setBadge('t2-nd-badge-new', newCount);
    setBadge('t2-nd-badge-done', doneCount);
    setBadge('t2-nd-badge-activity', actCount);
    const ndTotal = newCount + doneCount + actCount;
    setBadge('t2-cnt-newdone', ndTotal > 0 ? ndTotal : '');
    setBadge('t2-cnt-all', cards.length || '');
    setBadge('t2-cnt-parent', cards.filter(c=>c.isParentTask).length || '');
}

// ==================== KPI Update ====================

function updateKPI(cards, startDt, endDt) {
    const newCount = cards.filter(c => {
        const ct = new Date(c.createdAt);
        return ct >= startDt && ct <= endDt;
    }).length;

    const doneCount = cards.filter(c => {
        const et = c.endAt ? new Date(c.endAt) : null;
        return c.isDone && et && et >= startDt && et <= endDt;
    }).length;

    const doingCount = cards.filter(c => c.isDoing).length;
    const waitingCount = cards.filter(c => c.isWaiting).length;
    const reviewCount = cards.filter(c => c.isReview).length;

    // 本週新風險：受篩選器影響（使用 filtered cards）
    const newRiskCount = cards.filter(c =>
        c.isNewRisk && !c.archived &&
        !['DONE','Closed','過往卡片','過往卡片待青','Goal＆專案資訊'].includes(c.list)
    ).length;

    const dueSoonCount = RAW.cards.filter(c => c.isDueSoon && !c.archived).length;

    const kpiHtml = `
        <div class="kpi-card kpi-clickable" style="border-top:3px solid #43a047;" onclick="jumpToKPI('done')" title="點擊查看本週完成明細">
            <div class="kpi-label">本週完成 <span class="info-tip" data-tip="過去 7 天內移入 DONE 欄位的卡片（以 endAt 計算）">ℹ️</span></div>
            <div class="kpi-value">${doneCount}</div>
        </div>
        <div class="kpi-card kpi-clickable" style="border-top:3px solid #1976d2;" onclick="jumpToKPI('new')" title="點擊查看本週新增明細">
            <div class="kpi-label">本週新增 <span class="info-tip" data-tip="過去 7 天內新建立的卡片（以 createdAt 計算）">ℹ️</span></div>
            <div class="kpi-value">${newCount}</div>
        </div>
        <div class="kpi-card kpi-clickable alert" style="border-top:3px solid #c62828;" onclick="jumpToKPI('newrisk')" title="點擊查看本週新風險明細">
            <div class="kpi-label">本週風險 <span class="info-tip" data-tip="本週才出現的風險卡：本週新逾期（dueAt 在近 7 天到期）＋ 本週才停滯（staleDays 14–20 天）＋ 即將到期；受篩選器影響">ℹ️</span></div>
            <div class="kpi-value">${newRiskCount}</div>
        </div>
        <div class="kpi-card kpi-clickable" style="border-top:3px solid #f57f17;" onclick="jumpToKPI('duesoon')" title="點擊查看即將到期明細">
            <div class="kpi-label">⚡ 即將到期 <span class="info-tip" data-tip="dueAt 在 ${TODAY_DISPLAY} – ${DUE_SOON_END_DISPLAY} 之間的卡片（排除 DONE / Closed；全看板計算，不受篩選器影響；以本儀表板產出日為基準）">ℹ️</span></div>
            <div class="kpi-value">${dueSoonCount}</div>
        </div>
        <div class="kpi-card kpi-clickable" style="border-top:3px solid #7b1fa2;" onclick="jumpToKPI('doing')" title="點擊查看 Doing 明細">
            <div class="kpi-label">Doing</div>
            <div class="kpi-value">${doingCount}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Waiting</div>
            <div class="kpi-value">${waitingCount}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Review</div>
            <div class="kpi-value">${reviewCount}</div>
        </div>
    `;

    document.getElementById('t1-kpi-row').innerHTML = kpiHtml;
}

// ==================== Charts Update ====================

function updateCharts(cards, startDt, endDt) {
    // Chart 1: List Distribution（含所有欄位，包含 DONE / Closed）
    const listCounts = {};
    cards.forEach(c => {
        listCounts[c.list] = (listCounts[c.list] || 0) + 1;
    });

    // 依流程順序排列（從 team_config.json board.lists_order 讀取；空陣列 = 依 Wekan JSON 原始順序）
    const sortedLists = Object.keys(listCounts).sort((a, b) => {
        const ia = LIST_ORDER.indexOf(a);
        const ib = LIST_ORDER.indexOf(b);
        return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    });
    const listLabels = sortedLists;
    const listData = sortedLists.map(l => listCounts[l]);

    // Chart 2: Swimlane Completion
    const swimStats = {};
    RAW.cards.forEach(c => {
        if (!swimStats[c.swimlane]) {
            swimStats[c.swimlane] = { total: 0, done: 0, stale: 0 };
        }
        swimStats[c.swimlane].total++;
        if (c.isDone) swimStats[c.swimlane].done++;
        if (c.isStale) swimStats[c.swimlane].stale++;
    });

    const swimLabels = Object.keys(swimStats);
    const swimDoneData = swimLabels.map(s => Math.round(swimStats[s].done * 100 / swimStats[s].total));
    const swimStaleData = swimLabels.map(s => swimStats[s].stale);

    // Chart 3: Member Workload
    const memberStats = {};
    cards.forEach(c => {
        c.members.forEach(m => {
            if (!memberStats[m]) {
                memberStats[m] = { total: 0, doing: 0, stale: 0 };
            }
            memberStats[m].total++;
            if (c.isDoing) memberStats[m].doing++;
            if (c.isStale) memberStats[m].stale++;
        });
    });

    const memberLabels = Object.keys(memberStats).slice(0, 10);
    const memberTotalData = memberLabels.map(m => memberStats[m].total);
    const memberDoingData = memberLabels.map(m => memberStats[m].doing);
    const memberStaleData = memberLabels.map(m => memberStats[m].stale);

    const chartsHtml = `
        <div class="chart-box">
            <div class="chart-title">流程欄位分布</div>
            <div style="font-size:0.75em;color:#888;margin-bottom:6px;">＊依目前篩選條件，含所有欄位（包含 DONE / Closed）</div>
            <div class="chart-wrapper">
                <canvas id="chart-list"></canvas>
            </div>
        </div>
        <div class="chart-box">
            <div class="chart-title">主題完成率 vs 停滯率</div>
            <div style="font-size:0.75em;color:#888;margin-bottom:6px;">＊全看板資料，不受篩選器影響</div>
            <div class="chart-wrapper">
                <canvas id="chart-swim"></canvas>
            </div>
        </div>
        <div class="chart-box">
            <div class="chart-title">成員工作量分布</div>
            <div style="font-size:0.75em;color:#888;margin-bottom:6px;">＊依目前篩選條件（持有 = 所有未封存卡片；Doing / 停滯 依同篩選條件）</div>
            <div class="chart-wrapper">
                <canvas id="chart-member"></canvas>
            </div>
        </div>
    `;

    document.getElementById('t1-charts-container').innerHTML = chartsHtml;

    setTimeout(() => {
        // List chart
        const ctxList = document.getElementById('chart-list')?.getContext('2d');
        if (ctxList) {
            if (chartListInstance) chartListInstance.destroy();
            chartListInstance = new Chart(ctxList, {
                type: 'bar',
                data: {
                    labels: listLabels,
                    datasets: [{
                        label: '卡片數',
                        data: listData,
                        backgroundColor: '#1d4ed8'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true } }
                }
            });
        }

        // Swim chart
        const ctxSwim = document.getElementById('chart-swim')?.getContext('2d');
        if (ctxSwim) {
            if (chartSwimInstance) chartSwimInstance.destroy();
            chartSwimInstance = new Chart(ctxSwim, {
                type: 'bar',
                data: {
                    labels: swimLabels,
                    datasets: [
                        {
                            label: '完成率 (%)',
                            data: swimDoneData,
                            backgroundColor: '#4caf50',
                            yAxisID: 'y'
                        },
                        {
                            label: '停滯數',
                            data: swimStaleData,
                            backgroundColor: '#f44336',
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: true } },
                    scales: {
                        y: { type: 'linear', position: 'left' },
                        y1: { type: 'linear', position: 'right' }
                    }
                }
            });
        }

        // Member chart
        const ctxMember = document.getElementById('chart-member')?.getContext('2d');
        if (ctxMember) {
            if (chartMemberInstance) chartMemberInstance.destroy();
            chartMemberInstance = new Chart(ctxMember, {
                type: 'bar',
                data: {
                    labels: memberLabels,
                    datasets: [
                        { label: '持有', data: memberTotalData, backgroundColor: '#1d4ed8' },
                        { label: 'Doing', data: memberDoingData, backgroundColor: '#ff9800' },
                        { label: '停滯', data: memberStaleData, backgroundColor: '#f44336' }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: true } },
                    scales: { y: { beginAtZero: true } }
                }
            });
        }

        // Weekly trend
        const ctxTrend = document.getElementById('chart-weekly-trend')?.getContext('2d');
        if (ctxTrend) {
            if (chartTrendInstance) chartTrendInstance.destroy();
            chartTrendInstance = new Chart(ctxTrend, {
                type: 'line',
                data: {
                    labels: RAW.weeklyTrend.map(w => w.label),
                    datasets: [
                        {
                            label: '完成',
                            data: RAW.weeklyTrend.map(w => w.completed),
                            borderColor: '#4caf50',
                            backgroundColor: 'rgba(76,175,80,0.1)',
                            tension: 0.3
                        },
                        {
                            label: '新增',
                            data: RAW.weeklyTrend.map(w => w.new),
                            borderColor: '#ff9800',
                            backgroundColor: 'rgba(255,152,0,0.1)',
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: true } },
                    scales: { y: { beginAtZero: true } }
                }
            });
        }
    }, 100);
}

// ==================== Swimlane Grouping ====================

function toggleSwimGroup(gid) {
    const children = document.querySelectorAll(`.swim-child-${gid}`);
    children.forEach(row => {
        row.style.display = row.style.display === 'none' ? 'table-row' : 'none';
    });
}

// ==================== Table 1 (Overview) ====================

// 風險分析排除 List（從 team_config.json lists_roles 推導：done + closed + info + backlog）
// Ready to GO 欄位：保留風險，但不顯示「無負責人」badge（尚未接手屬正常）
function isRiskCard(c) {
    if (RISK_EXCLUDE_LISTS.includes(c.list)) return false;
    if (c.archived) return false;
    return true;
}

// ── 風險摘要卡（Feature A-1）─────────────────────────────
function buildRiskSummary(riskCards) {
    const total = riskCards.length;
    if (total === 0) {
        return '<div class="risk-summary ok"><span class="risk-summary-title">✅ 目前篩選範圍內無風險卡片</span></div>';
    }

    const n0 = riskCards.filter(c => c.isOverdue).length;
    const n1 = riskCards.filter(c => c.isDueSoon).length;
    const n2 = riskCards.filter(c => c.isStale).length;
    const n3 = riskCards.filter(c => c.noMember).length;

    // 主題集中度（top 2）
    const swimCount = {};
    riskCards.forEach(c => { swimCount[c.swimlane] = (swimCount[c.swimlane] || 0) + 1; });
    const topSwims = Object.entries(swimCount).sort((a, b) => b[1] - a[1]).slice(0, 2);

    // 成員集中度（top 2，排除「無負責人」卡片）
    const memberCount = {};
    riskCards.forEach(c => {
        c.members.forEach(m => { memberCount[m] = (memberCount[m] || 0) + 1; });
    });
    const topMembers = Object.entries(memberCount).sort((a, b) => b[1] - a[1]).slice(0, 2);

    const swimStr = topSwims.map(([s, n]) => `<strong>${s}</strong>（${n} 張）`).join('、');
    const memberStr = topMembers.length
        ? topMembers.map(([m, n]) => `<strong>${m}</strong>（${n} 張）`).join('、') + ' 有最多待處理風險'
        : '所有風險卡片皆有負責人';

    return `<div class="risk-summary warn">
        <span class="risk-summary-title">⚠️ 風險摘要 <span style="font-weight:400;font-size:0.88em;color:#8d6e63;">（依目前篩選條件）</span></span>
        <div class="risk-summary-row">
            <span class="risk-summary-label">總計</span>
            <span>共 <strong>${total}</strong> 個風險卡片（逾期 ${n0} ｜ 即將到期 ${n1} ｜ 停滯 ${n2} ｜ 無負責人 ${n3}）</span>
        </div>
        ${topSwims.length ? `<div class="risk-summary-row"><span class="risk-summary-label">集中在</span><span>${swimStr}</span></div>` : ''}
        <div class="risk-summary-row"><span class="risk-summary-label">成員</span><span>${memberStr}</span></div>
    </div>`;
}

function updateRiskTables(cards) {
    // Ready to GO 卡片不因「無負責人」進入風險（未接手屬正常），但停滯/逾期/即將到期仍保留
    const riskCards = cards.filter(c => {
        if (!isRiskCard(c)) return false;
        if (c.isStale || c.isOverdue || c.isDueSoon) return true;
        if (c.noMember && !READY_LISTS.includes(c.list)) return true;
        return false;
    });

    // 更新風險摘要卡
    const summaryEl = document.getElementById('risk-summary-box');
    if (summaryEl) summaryEl.innerHTML = buildRiskSummary(riskCards);

    // 總覽風險：逾期(0) → 即將到期(1) → 停滯(2,天數遞減) → 無負責人(3，Ready to GO 排除)
    const riskTypeRank = c => c.isOverdue ? 0 : c.isDueSoon ? 1 : c.isStale ? 2 :
        (c.noMember && !READY_LISTS.includes(c.list)) ? 3 : 4;
    const sortedRisk = riskCards.sort((a, b) => {
        const rankDiff = riskTypeRank(a) - riskTypeRank(b);
        if (rankDiff !== 0) return rankDiff;
        // 同為即將到期：dueAt 由近到遠
        if (a.isDueSoon && b.isDueSoon) return new Date(a.dueAt) - new Date(b.dueAt);
        // 同為停滯：天數由多到少
        if (a.isStale && b.isStale) return (b.staleDays || 0) - (a.staleDays || 0);
        return 0;
    });

    function buildRiskBadges(c) {
        const badges = [];
        if (c.isOverdue)  badges.push('<span class="badge" style="background:#ffebee;color:#c62828;">逾期</span>');
        if (c.isDueSoon)  badges.push(`<span class="badge badge-due-soon">⚡ ${c.dueAtDisplay}</span>`);
        if (c.isStale)    badges.push('<span class="badge badge-stale">停滯</span>');
        if (c.noMember && !READY_LISTS.includes(c.list))
            badges.push('<span class="badge" style="background:#fff3e0;color:#e65100;">無負責</span>');
        return badges.join(' ') || '-';
    }

    let riskOverviewHtml = '';
    sortedRisk.forEach(c => {
        const clProgress = c.hasChecklist ? `${c.clDone}/${c.clTotal} (${c.clPct}%)` : '-';
        riskOverviewHtml += `<tr class="${getSwimRowClass(c.swimlane)}">
            <td>${c.swimlane}</td>
            <td>${cardLink(c.id, c.title)}</td>
            <td>${c.dueAtDisplay || '-'}</td>
            <td>${c.staleDays || '-'}</td>
            <td><span class="badge">${c.list}</span></td>
            <td>${c.members.join(', ') || '無'}</td>
            <td>${c.dateLastActivity.split('T')[0] || '-'}</td>
            <td>${clProgress}</td>
            <td>${buildRiskBadges(c)}</td>
        </tr>`;
    });
    document.getElementById('t1-risk-overview-table').querySelector('tbody').innerHTML = riskOverviewHtml;

    // 泳道篩選：依 riskSwimFilter，排序同上
    const swimmingRisk = riskSwimFilter ? sortedRisk.filter(c => c.swimlaneId === riskSwimFilter) : sortedRisk;
    let riskSwimHtml = '';
    swimmingRisk.forEach(c => {
        const clProgress = c.hasChecklist ? `${c.clDone}/${c.clTotal} (${c.clPct}%)` : '-';
        riskSwimHtml += `<tr class="${getSwimRowClass(c.swimlane)}">
            <td>${c.swimlane}</td>
            <td>${cardLink(c.id, c.title)}</td>
            <td>${c.dueAtDisplay || '-'}</td>
            <td>${c.staleDays || '-'}</td>
            <td><span class="badge">${c.list}</span></td>
            <td>${c.members.join(', ') || '無'}</td>
            <td>${c.dateLastActivity.split('T')[0] || '-'}</td>
            <td>${clProgress}</td>
            <td>${buildRiskBadges(c)}</td>
        </tr>`;
    });
    document.getElementById('t1-risk-swim-table').querySelector('tbody').innerHTML = riskSwimHtml;

    // 本週新風險分頁：受篩選器影響（使用 filteredCards1）
    const newRiskCards = cards.filter(c =>
        c.isNewRisk && !c.archived &&
        !['DONE','Closed','過往卡片','過往卡片待青','Goal＆專案資訊'].includes(c.list)
    ).sort((a, b) => {
        const riskTypeRank = c => c.isOverdue ? 0 : c.isDueSoon ? 1 : c.isStale ? 2 : 3;
        const rankDiff = riskTypeRank(a) - riskTypeRank(b);
        if (rankDiff !== 0) return rankDiff;
        if (a.isDueSoon && b.isDueSoon) return new Date(a.dueAt) - new Date(b.dueAt);
        return 0;
    });
    let newRiskHtml = '';
    newRiskCards.forEach(c => {
        newRiskHtml += `<tr class="${getSwimRowClass(c.swimlane)}">
            <td>${c.swimlane}</td>
            <td>${cardLink(c.id, c.title)}</td>
            <td>${c.dueAtDisplay ? `<strong>${c.dueAtDisplay}</strong>` : '-'}</td>
            <td><span class="badge">${c.list}</span></td>
            <td>${c.members.join(', ') || '無'}</td>
            <td>${c.dateLastActivity.split('T')[0] || '-'}</td>
            <td>${buildRiskBadges(c)}</td>
        </tr>`;
    });
    if (!newRiskHtml) newRiskHtml = '<tr><td colspan="7" style="text-align:center;color:#999">本週目前無新出現的風險卡片</td></tr>';
    const newRiskTbl = document.getElementById('t1-risk-newrisk-table');
    if (newRiskTbl) newRiskTbl.querySelector('tbody').innerHTML = newRiskHtml;

    // 即將到期分頁：使用全看板 RAW.cards（不受篩選器影響），與 KPI 9 對齊
    const dueSoonCards = RAW.cards.filter(c => isRiskCard(c) && c.isDueSoon && !c.archived)
        .sort((a, b) => new Date(a.dueAt) - new Date(b.dueAt));
    let dueSoonHtml = '';
    dueSoonCards.forEach(c => {
        dueSoonHtml += `<tr class="${getSwimRowClass(c.swimlane)}">
            <td>${c.swimlane}</td>
            <td>${cardLink(c.id, c.title)}</td>
            <td><strong>${c.dueAtDisplay || '-'}</strong></td>
            <td><span class="badge">${c.list}</span></td>
            <td>${c.members.join(', ') || '無'}</td>
            <td>${c.dateLastActivity.split('T')[0] || '-'}</td>
            <td>${buildRiskBadges(c)}</td>
        </tr>`;
    });
    if (!dueSoonHtml) dueSoonHtml = '<tr><td colspan="7" style="text-align:center;color:#999">目前無即將到期的卡片</td></tr>';
    const dueSoonTbl = document.getElementById('t1-risk-duesoon-table');
    if (dueSoonTbl) dueSoonTbl.querySelector('tbody').innerHTML = dueSoonHtml;
}

// ==================== 改動 2: updateTables1 拆解函式 ====================

function renderNewDone1(cards, startDt, endDt) {
    // 本週新增／完成／有異動：三欄並排
    const newCards = sortBySwim(cards.filter(c => {
        const ct = new Date(c.createdAt);
        return ct >= startDt && ct <= endDt;
    }));
    let newHtml = '';
    newCards.forEach(c => {
        newHtml += `<tr class="${getSwimRowClass(c.swimlane)}">
            <td>${c.swimlane||'—'}</td>
            <td>${cardLink(c.id, c.title)}</td>
            <td><span class="badge">${c.list}</span></td>
            <td>${c.members.join(', ') || '無'}</td>
            <td>${c.createdAt.split('T')[0]}</td>
        </tr>`;
    });
    document.getElementById('t1-newdone-new-table').querySelector('tbody').innerHTML = newHtml;

    const doneCards = sortBySwim(cards.filter(c => {
        const et = c.endAt ? new Date(c.endAt) : null;
        return c.isDone && et && et >= startDt && et <= endDt;
    }));
    let doneHtml = '';
    doneCards.forEach(c => {
        const et = new Date(c.endAt);
        doneHtml += `<tr class="${getSwimRowClass(c.swimlane)}">
            <td>${c.swimlane||'—'}</td>
            <td>${cardLink(c.id, c.title)}</td>
            <td>${c.members.join(', ') || '無'}</td>
            <td>${et.toISOString().split('T')[0]}</td>
        </tr>`;
    });
    document.getElementById('t1-newdone-done-table').querySelector('tbody').innerHTML = doneHtml;

    // 本週有異動：依欄位分群（Review→Doing→準備中→Waiting→Ready to GO），群組內依 dateLastActivity 由新到舊
    const actCards1 = cards.filter(c => {
        if (!c.dateLastActivity) return false;
        if (ACT_EXCLUDE.includes(c.list)) return false;
        const dt = new Date(c.dateLastActivity);
        return dt >= startDt && dt <= endDt;
    });
    // 依 list 分群，群組內依 dateLastActivity 由新到舊
    const actByList1 = {};
    actCards1.forEach(c => {
        if (!actByList1[c.list]) actByList1[c.list] = [];
        actByList1[c.list].push(c);
    });
    Object.values(actByList1).forEach(arr => arr.sort((a, b) => new Date(b.dateLastActivity) - new Date(a.dateLastActivity)));
    let actWrapHtml1 = '';
    if (actCards1.length === 0) {
        actWrapHtml1 = '<p style="text-align:center;color:#999;padding:16px;">本週無異動卡片</p>';
    } else {
        ACT_GROUP_ORDER.forEach(listName => {
            const gc = actByList1[listName] || [];
            const collapsed = gc.length === 0 ? ' collapsed' : '';
            let rowsHtml = '';
            gc.forEach(c => {
                rowsHtml += `<tr>
                    <td>${c.swimlane||'—'}</td>
                    <td>${cardLink(c.id,c.title)}</td>
                    <td><span class="badge">${c.list}</span></td>
                    <td>${c.members.join(', ')||'—'}</td>
                    <td>${(c.dateLastActivity||'').slice(0,10)}</td>
                </tr>`;
            });
            actWrapHtml1 += `<div class="act-group-card${collapsed}">
                <div class="act-group-hdr" onclick="toggleActGroup(this)">
                    <span class="act-group-arrow">▼</span>
                    <span>▌ ${listName}（${gc.length}）</span>
                </div>
                <div class="act-group-body">
                    <table class="act-group-table">
                        <thead><tr><th>主題</th><th>卡片名稱</th><th>欄位</th><th>負責人</th><th>最後活動日</th></tr></thead>
                        <tbody>${rowsHtml}</tbody>
                    </table>
                </div>
            </div>`;
        });
    }
    const actWrap1 = document.getElementById('t1-nd-act-wrap');
    if(actWrap1) actWrap1.innerHTML = actWrapHtml1;
}

function renderDoing1(cards) {
    // Doing 明細：扁平清單
    const doingCards = cards.filter(c => c.isDoing);
    let doingHtml = '';
    doingCards.forEach(c => {
        const staleBadge = c.isStale ? `<span class="badge badge-stale">停滯${c.staleDays}天</span>` :
                          '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">活躍</span>';
        const dueSoonBadge = c.isDueSoon ? `<span class="badge badge-due-soon">⚡ ${c.dueAtDisplay}</span>` : '';
        doingHtml += `<tr class="${getSwimRowClass(c.swimlane)}">
            <td>${c.swimlane}</td>
            <td>${cardLink(c.id, c.title)}</td>
            <td>${c.staleDays || '-'}</td>
            <td><span class="badge badge-doing">${c.list}</span></td>
            <td>${c.members.join(', ') || '無'}</td>
            <td>${c.dateLastActivity.split('T')[0] || '-'}</td>
            <td>${dueSoonBadge}${staleBadge}</td>
        </tr>`;
    });
    document.getElementById('t1-doing-table').querySelector('tbody').innerHTML = doingHtml;
}

function renderAll1(cards) {
    // 改動 3: 分頁邏輯
    const total = cards.length;
    const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
    if (t1AllPage > totalPages) t1AllPage = totalPages;
    const pageCards = cards.slice((t1AllPage - 1) * PAGE_SIZE, t1AllPage * PAGE_SIZE);

    const sortedAll = sortBySwim(pageCards);
    let allHtml = '';
    sortedAll.forEach(c => {
        const staleBadge = c.isStale ? `<span class="badge badge-stale">停滯${c.staleDays}天</span>` :
                          '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">活躍</span>';
        const clProgress = c.hasChecklist ? `${c.clDone}/${c.clTotal} (${c.clPct}%)` : '-';
        const labelsStr = c.labels.length > 0 ? c.labels.join(', ') : '-';
        allHtml += `<tr class="${getSwimRowClass(c.swimlane)}">
            <td>${c.swimlane}</td>
            <td>${cardLink(c.id, c.title)}</td>
            <td>${c.members.join(', ') || '無'}</td>
            <td>${c.createdAt.split('T')[0]}</td>
            <td>${c.dateLastActivity.split('T')[0] || '-'}</td>
            <td>${staleBadge}</td>
            <td>${clProgress}</td>
            <td>${labelsStr}</td>
        </tr>`;
    });

    const pageHtml = `<div style="display:flex;align-items:center;gap:12px;padding:8px 0;font-size:13px;">
        <button onclick="t1AllPage=Math.max(1,t1AllPage-1);renderAll1(filteredCards1)" ${t1AllPage<=1?'disabled':''}>‹ 上一頁</button>
        <span>第 ${t1AllPage} / ${totalPages} 頁（共 ${total} 筆）</span>
        <button onclick="t1AllPage=Math.min(${totalPages},t1AllPage+1);renderAll1(filteredCards1)" ${t1AllPage>=totalPages?'disabled':''}>下一頁 ›</button>
    </div>`;

    document.getElementById('t1-all-table').querySelector('tbody').innerHTML = allHtml;
    const pagerEl = document.getElementById('t1-all-pager');
    if (pagerEl) pagerEl.innerHTML = pageHtml;
}

function updateTables1(cards, startDt, endDt) {
    // 舊邏輯已移至各函式，此函式已不被調用（由 renderT1Panel 替代）
}

// 改動 4: renderParentGroups — 遞迴分組排序 + 父任務狀態 Tab 版（Feature C-1 + C-3）
function renderParentGroups(tabName, cards) {
    const containerId = tabName + '-parent-container';
    const container = document.getElementById(containerId);
    if (!container) return;

    // 建立全域 childrenMap（供 toggleGroup 遞迴使用）
    const childrenMap = {};
    cards.forEach(c => {
        if (c.parentId) {
            if (!childrenMap[c.parentId]) childrenMap[c.parentId] = [];
            childrenMap[c.parentId].push(c);
        }
    });
    currentChildrenMap = childrenMap;

    // 計算某父任務的所有後代數量（遞迴）
    function countDescendants(id) {
        const kids = childrenMap[id] || [];
        return kids.reduce((sum, c) => sum + 1 + countDescendants(c.id), 0);
    }
    function countDone(id) {
        const kids = childrenMap[id] || [];
        return kids.reduce((sum, c) => sum + (c.isDone ? 1 : 0) + countDone(c.id), 0);
    }

    // 頂層父任務：有子任務且自身無 parentId
    const parentCards = cards.filter(c => c.isParentTask);
    const standaloneCards = cards.filter(c => c.isStandalone);

    if (parentCards.length === 0 && standaloneCards.length === 0) {
        container.innerHTML = '<p style="color:#999;padding:16px">無資料</p>';
        return;
    }

    // 依父任務自身欄位分群
    const statusGroups = {};
    parentCards.forEach(p => {
        const key = p.list || '未知';
        if (!statusGroups[key]) statusGroups[key] = [];
        statusGroups[key].push(p);
    });

    // 決定預設 active tab（優先 Doing，若無則找第一個非 0）
    const hasStandalone = standaloneCards.length > 0;
    const standaloneIdx = CHILD_LIST_ORDER.length; // 獨立卡片 tab 排最後
    let defaultIdx = 0; // CHILD_LIST_ORDER[0] = 'Doing'
    const doingCount = (statusGroups['Doing'] || []).length;
    if (doingCount === 0) {
        const firstNonZero = CHILD_LIST_ORDER.findIndex(s => (statusGroups[s] || []).length > 0);
        if (firstNonZero >= 0) {
            defaultIdx = firstNonZero;
        } else if (hasStandalone) {
            defaultIdx = standaloneIdx;
        }
    }

    // ── Tab Bar ─────────────────────────────────────────────
    let tabBarHtml = `<div class="parent-status-tab-bar" style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:0;border-bottom:2px solid #e0e0e0;padding-bottom:0">`;

    CHILD_LIST_ORDER.forEach((status, idx) => {
        const count = (statusGroups[status] || []).length;
        const isDone = (status === 'DONE');
        const isZero = (count === 0);
        const isActive = (idx === defaultIdx);
        let cls = 'sub-tab-btn';
        if (isDone) cls += ' pst-done';
        if (isZero) cls += ' pst-zero';
        if (isActive) cls += ' active';
        const onclickAttr = isZero ? '' : ` onclick="switchParentStatusTab('${tabName}',${idx})"`;
        tabBarHtml += `<button class="${cls}"${onclickAttr}>${status} (${count})</button>`;
    });

    // 獨立卡片 Tab
    if (hasStandalone) {
        const isActive = (defaultIdx === standaloneIdx);
        let cls = 'sub-tab-btn' + (isActive ? ' active' : '');
        tabBarHtml += `<button class="${cls}" onclick="switchParentStatusTab('${tabName}',${standaloneIdx})">獨立卡片 (${standaloneCards.length})</button>`;
    }
    tabBarHtml += `</div>`;

    // ── Panels ──────────────────────────────────────────────
    let panelsHtml = '';
    CHILD_LIST_ORDER.forEach((status, idx) => {
        const isActive = (idx === defaultIdx);
        const groupParents = statusGroups[status] || [];
        panelsHtml += `<div class="parent-status-panel${isActive ? ' active' : ''}">`;

        if (groupParents.length === 0) {
            panelsHtml += `<p style="color:#bbb;padding:12px 4px">此狀態目前無父任務</p>`;
        } else {
            groupParents.forEach(p => {
                const total = countDescendants(p.id);
                if (total === 0) return;
                const done = countDone(p.id);
                const groupKey = tabName + '__' + p.id;
                panelsHtml += `<div class="parent-group">
                    <div class="parent-group-header" onclick="toggleGroup(this,'${groupKey}','${p.id}')" style="cursor:pointer">
                        <span class="pg-arrow">▶</span>
                        父任務：${p.title}（${total} 項）[完成率：${done}/${total}]
                    </div>
                    <div class="parent-group-body" style="display:none"></div>
                </div>`;
            });
        }
        panelsHtml += `</div>`;
    });

    // 獨立卡片 Panel
    if (hasStandalone) {
        const isActive = (defaultIdx === standaloneIdx);
        const groupKey = tabName + '__standalone';
        parentGroupData[groupKey] = standaloneCards;
        const done = standaloneCards.filter(c => c.isDone).length;
        panelsHtml += `<div class="parent-status-panel${isActive ? ' active' : ''}">
            <div class="parent-group">
                <div class="parent-group-header" onclick="toggleGroup(this,'${groupKey}',null)" style="cursor:pointer">
                    <span class="pg-arrow">▶</span>
                    獨立卡片（${standaloneCards.length} 項）[完成率：${done}/${standaloneCards.length}]
                </div>
                <div class="parent-group-body" style="display:none"></div>
            </div>
        </div>`;
    }

    container.innerHTML = tabBarHtml + panelsHtml;
}

function updateT1ParentTable(cards, swimFilter) {
    renderParentGroups('t1', cards);
}

// ==================== Personal Focus ====================

// 需求 #4: 個人泳道改為受篩選器控制 + 完成率
function updatePersonalFocus(memberId, filteredCards, startDt, endDt) {
    const memberName = RAW.users[memberId] || memberId;
    const memberSwims = {};

    // 只顯示在選取時間範圍內有異動（dateLastActivity 落在區間）的卡片
    // 個人泳道專注分析：包含 DONE / Closed（完成工作需要呈現），排除 backlog + info
    const hasDateFilter = !isNaN(startDt) && !isNaN(endDt);
    filteredCards.forEach(c => {
        const hasMem = c.members.some(m => RAW.users[memberId] === m);
        if (!hasMem) return;
        if (FOCUS_EXCLUDE.includes(c.list)) return;
        if (hasDateFilter) {
            const at = c.dateLastActivity ? new Date(c.dateLastActivity) : null;
            if (!at || at < startDt || at > endDt) return;
        }
        if (!memberSwims[c.swimlane]) memberSwims[c.swimlane] = [];
        memberSwims[c.swimlane].push(c);
    });

    let focusHtml = '';
    Object.entries(memberSwims).forEach(([swim, swCards]) => {
        // 計算完成率
        const done = swCards.filter(c => c.isDone).length;
        const total = swCards.length;
        const swimRowCls = getSwimRowClass(swim);
        focusHtml += `<div class="focus-row ${swimRowCls}" onclick="toggleFocusRow(this)"><strong>泳道：${swim}</strong> (${total} 項) [完成率：${done}/${total}]</div>`;
        focusHtml += `<div class="focus-children ${swimRowCls}">`;
        swCards.forEach(c => {
            const statusBadge = c.isDone ? '<span class="badge badge-done">DONE</span>' :
                               c.isDoing ? '<span class="badge badge-doing">Doing</span>' :
                               c.isWaiting ? '<span class="badge" style="background:#fff3e0;color:#e65100">Waiting</span>' :
                               c.isReview ? '<span class="badge" style="background:#f3e5f5;color:#6a1b9a">Review</span>' : '';
            focusHtml += `<div class="focus-child-row"><strong>${cardLink(c.id, c.title)}</strong> | ${c.list} | 停${c.staleDays || '0'}天 ${statusBadge}</div>`;
        });
        focusHtml += `</div>`;
    });

    document.getElementById('t2-focus-section').style.display = 'block';
    document.getElementById('t2-focus-placeholder').style.display = 'none';
    document.querySelector('.focus-title').textContent = `👤 個人泳道專注分析 — ${memberName}（本期有異動卡片）`;
    document.getElementById('t2-focus-content').innerHTML = focusHtml;
}

function toggleFocusRow(el) {
    const children = el.nextElementSibling;
    if (children && children.classList.contains('focus-children')) {
        children.classList.toggle('open');
        el.classList.toggle('expanded');
    }
}

// ==================== Table 2 (Personal) ====================

// ==================== 改動 2: updateTables2 拆解函式 ====================

function renderNewDone2(cards, startDt, endDt) {
    // 需求 #5: 本週新增／完成：左右並排扁平，按專案排序
    const newCards = sortBySwim(cards.filter(c => {
        const ct = new Date(c.createdAt);
        return ct >= startDt && ct <= endDt;
    }));
    let newHtml = '';
    newCards.forEach(c => {
        newHtml += `<tr class="${getSwimRowClass(c.swimlane)}">
            <td>${c.swimlane}</td>
            <td>${cardLink(c.id, c.title)}</td>
            <td><span class="badge">${c.list}</span></td>
            <td>${c.members.join(', ') || '無'}</td>
            <td>${c.createdAt.split('T')[0]}</td>
        </tr>`;
    });
    document.getElementById('t2-newdone-new-table').querySelector('tbody').innerHTML = newHtml;

    const doneCards = sortBySwim(cards.filter(c => {
        const et = c.endAt ? new Date(c.endAt) : null;
        return c.isDone && et && et >= startDt && et <= endDt;
    }));
    let doneHtml = '';
    doneCards.forEach(c => {
        const et = new Date(c.endAt);
        doneHtml += `<tr class="${getSwimRowClass(c.swimlane)}">
            <td>${c.swimlane}</td>
            <td>${cardLink(c.id, c.title)}</td>
            <td>${c.members.join(', ') || '無'}</td>
            <td>${et.toISOString().split('T')[0]}</td>
        </tr>`;
    });
    document.getElementById('t2-newdone-done-table').querySelector('tbody').innerHTML = doneHtml;

    // 本週有異動：依欄位分群（Review→Doing→準備中→Waiting→Ready to GO），群組內依 dateLastActivity 由新到舊
    const actCards2 = cards.filter(c => {
        const at = c.dateLastActivity ? new Date(c.dateLastActivity) : null;
        if (!at || at < startDt || at > endDt) return false;
        if (ACT_EXCLUDE2.includes(c.list)) return false;
        const ct = new Date(c.createdAt);
        const isNew = ct >= startDt && ct <= endDt;
        const et = c.endAt ? new Date(c.endAt) : null;
        const isDoneThisWeek = c.isDone && et && et >= startDt && et <= endDt;
        return !isNew && !isDoneThisWeek;
    });
    // 依 list 分群，群組內依 dateLastActivity 由新到舊
    const actByList2 = {};
    actCards2.forEach(c => {
        if (!actByList2[c.list]) actByList2[c.list] = [];
        actByList2[c.list].push(c);
    });
    Object.values(actByList2).forEach(arr => arr.sort((a, b) => new Date(b.dateLastActivity) - new Date(a.dateLastActivity)));
    let actWrapHtml2 = '';
    if (actCards2.length === 0) {
        actWrapHtml2 = '<p style="text-align:center;color:#999;padding:16px;">本週無異動卡片</p>';
    } else {
        ACT_GROUP_ORDER2.forEach(listName => {
            const gc = actByList2[listName] || [];
            const collapsed = gc.length === 0 ? ' collapsed' : '';
            let rowsHtml = '';
            gc.forEach(c => {
                rowsHtml += `<tr>
                    <td>${c.swimlane}</td>
                    <td>${cardLink(c.id, c.title)}</td>
                    <td><span class="badge">${c.list}</span></td>
                    <td>${c.members.join(', ') || '無'}</td>
                    <td>${c.dateLastActivity.split('T')[0]}</td>
                </tr>`;
            });
            actWrapHtml2 += `<div class="act-group-card${collapsed}">
                <div class="act-group-hdr" onclick="toggleActGroup(this)">
                    <span class="act-group-arrow">▼</span>
                    <span>▌ ${listName}（${gc.length}）</span>
                </div>
                <div class="act-group-body">
                    <table class="act-group-table">
                        <thead><tr><th>主題</th><th>卡片名稱</th><th>欄位</th><th>負責人</th><th>最後活動日</th></tr></thead>
                        <tbody>${rowsHtml}</tbody>
                    </table>
                </div>
            </div>`;
        });
    }
    const actWrap2 = document.getElementById('t2-nd-act-wrap');
    if(actWrap2) actWrap2.innerHTML = actWrapHtml2;
}

function renderAll2(cards) {
    // 改動 3: 分頁邏輯
    const total = cards.length;
    const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
    if (t2AllPage > totalPages) t2AllPage = totalPages;
    const pageCards = cards.slice((t2AllPage - 1) * PAGE_SIZE, t2AllPage * PAGE_SIZE);

    const sortedAll = sortBySwim(pageCards);
    let allHtml = '';
    sortedAll.forEach(c => {
        const staleBadge = c.isStale ? `<span class="badge badge-stale">停滯${c.staleDays}天</span>` :
                          '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">活躍</span>';
        const clProgress = c.hasChecklist ? `${c.clDone}/${c.clTotal} (${c.clPct}%)` : '-';
        const labelsStr = c.labels.length > 0 ? c.labels.join(', ') : '-';
        allHtml += `<tr class="${getSwimRowClass(c.swimlane)}">
            <td>${c.swimlane}</td>
            <td>${cardLink(c.id, c.title)}</td>
            <td>${c.members.join(', ') || '無'}</td>
            <td>${c.createdAt.split('T')[0]}</td>
            <td>${c.dateLastActivity.split('T')[0] || '-'}</td>
            <td>${staleBadge}</td>
            <td>${clProgress}</td>
            <td>${labelsStr}</td>
        </tr>`;
    });

    const pageHtml = `<div style="display:flex;align-items:center;gap:12px;padding:8px 0;font-size:13px;">
        <button onclick="t2AllPage=Math.max(1,t2AllPage-1);renderAll2(filteredCards2)" ${t2AllPage<=1?'disabled':''}>‹ 上一頁</button>
        <span>第 ${t2AllPage} / ${totalPages} 頁（共 ${total} 筆）</span>
        <button onclick="t2AllPage=Math.min(${totalPages},t2AllPage+1);renderAll2(filteredCards2)" ${t2AllPage>=totalPages?'disabled':''}>下一頁 ›</button>
    </div>`;

    document.getElementById('t2-all-table').querySelector('tbody').innerHTML = allHtml;
    const pagerEl = document.getElementById('t2-all-pager');
    if (pagerEl) pagerEl.innerHTML = pageHtml;
}

function updateTables2(cards, startDt, endDt) {
    // 舊邏輯已移至各函式，此函式已不被調用（由 renderT2Panel 替代）
}

function updateT2ParentTable(cards, swimFilter) {
    renderParentGroups('t2', cards);
}

// ==================== 需求 #7: 篩選狀態提示列 ====================

function renderFilterChips1(startDt, endDt, lists, swims, labels, statuses) {
    // 只顯示灰色計數文字，不顯示 Chip 標籤列
    const parts = [];
    if (startDt && endDt) {
        parts.push(`${startDt.toISOString().split('T')[0]} ~ ${endDt.toISOString().split('T')[0]}`);
    }
    const listNames = lists.map(lid => RAW.listsMap[lid] || lid);
    const swimNames = swims.map(sid => RAW.swimlanesMap[sid] || sid);
    if (listNames.length) parts.push(`欄位：${listNames.join('、')}`);
    if (swimNames.length) parts.push(`主題：${swimNames.join('、')}`);
    const label = document.getElementById('t1-card-count-label');
    if (label) {
        label.textContent = parts.length
            ? `顯示 ${filteredCards1.length} 張卡片（${parts.join('｜')}）`
            : `顯示全部 ${filteredCards1.length} 張卡片`;
    }
}

function renderFilterChips2(startDt, endDt, swims, labels, members, statuses) {
    // 只顯示灰色計數文字，不顯示 Chip 標籤列
    const parts = [];
    if (startDt && endDt) {
        parts.push(`${startDt.toISOString().split('T')[0]} ~ ${endDt.toISOString().split('T')[0]}`);
    }
    const swimNames = swims.map(sid => RAW.swimlanesMap[sid] || sid);
    const memberNames = members.map(mid => RAW.users[mid] || mid);
    if (swimNames.length) parts.push(`主題：${swimNames.join('、')}`);
    if (memberNames.length) parts.push(`成員：${memberNames.join('、')}`);
    const label = document.getElementById('t2-card-count-label');
    if (label) {
        label.textContent = parts.length
            ? `顯示 ${filteredCards2.length} 張卡片（${parts.join('｜')}）`
            : `顯示全部 ${filteredCards2.length} 張卡片`;
    }
}

function clearChip1(type) {
    // 實作邏輯：根據 type 清除對應篩選條件
    // 簡化版：直接清除所有篩選並重新套用
    applyFilters1();
}

function clearChip2(type) {
    applyFilters2();
}

function clearAllChips1() {
    document.querySelectorAll('#t1-list-picker-items input').forEach(cb => cb.checked = false);
    document.querySelectorAll('#t1-swim-picker-items input').forEach(cb => cb.checked = false);
    document.querySelectorAll('#t1-label-picker-items input').forEach(cb => cb.checked = false);
    document.querySelectorAll('#t1-status-picker-items input').forEach(cb => cb.checked = false);
    applyFilters1();
}

function clearAllChips2() {
    document.querySelectorAll('#t2-swim-picker-items input').forEach(cb => cb.checked = false);
    document.querySelectorAll('#t2-label-picker-items input').forEach(cb => cb.checked = false);
    document.querySelectorAll('#t2-member-picker-items input').forEach(cb => cb.checked = false);
    document.querySelectorAll('#t2-status-picker-items input').forEach(cb => cb.checked = false);
    applyFilters2();
}

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', () => {
    initFilters();
});
