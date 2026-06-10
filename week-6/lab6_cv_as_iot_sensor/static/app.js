function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

let API_BASE = '';
let WS = null;
let wsReconnectTimer = null;
let currentFilters = ['resize','grayscale','threshold','edge'];
let activeEventFilter = 'ALL';
let editingCameraId = null;

function initBackendUrl() {
    const isLocalFile = location.protocol === 'file:';
    const isOtherPort = location.port !== '8001' && location.port !== '8000';
    if (isLocalFile || isOtherPort) {
        API_BASE = localStorage.getItem('lab6_backend_url') || 'http://localhost:8001';
    } else {
        API_BASE = '';
    }
    const input = document.getElementById('backendUrlInput');
    if (input) {
        input.value = API_BASE || (location.protocol + '//' + location.host);
    }
}

function saveBackendUrl() {
    const input = document.getElementById('backendUrlInput');
    if (input) {
        let val = input.value.trim().replace(/\/$/, '');
        if (val) {
            localStorage.setItem('lab6_backend_url', val);
            API_BASE = val;
            showToast('Backend Config', 'Đã lưu Backend: ' + val);
            connectWS();
            refreshServerInfo();
            refreshDashboard();
        }
    }
}

function connectWS() {
    let wsUrl;
    if (API_BASE) {
        const baseProto = API_BASE.startsWith('https') ? 'wss:' : 'ws:';
        const host = API_BASE.replace(/^https?:\/\//, '');
        wsUrl = `${baseProto}//${host}/ws`;
    } else {
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${proto}//${location.host}/ws`;
    }
    
    if (WS) try { WS.close(); } catch(e) {}
    
    try {
        WS = new WebSocket(wsUrl);
        WS.onopen = () => {
            document.getElementById('wsBadge').textContent = 'WebSocket: connected';
            document.getElementById('wsBadge').className = 'badge badge-green';
        };
        WS.onmessage = (ev) => {
            try {
                const data = JSON.parse(ev.data);
                if (data.type === 'new_image') {
                    showToast(data.event?.event_type || 'New Image', data.event?.explanation || '');
                    if (data.raw_image_url) {
                        const rawUrl = data.raw_image_url.startsWith('http') ? data.raw_image_url : (API_BASE + data.raw_image_url);
                        document.getElementById('raw').src = rawUrl + '?t=' + Date.now();
                    }
                    if (data.processed_image_url) {
                        const procUrl = data.processed_image_url.startsWith('http') ? data.processed_image_url : (API_BASE + data.processed_image_url);
                        document.getElementById('processed').src = procUrl + '?t=' + Date.now();
                    }
                    document.getElementById('out').textContent = JSON.stringify(data, null, 2);
                    if (data.detections && data.detections.length > 0) {
                        showToast('Detection', data.detections.map(d=>d.label+' '+d.confidence).join(', '));
                    }
                    refreshDashboard();
                } else if (data.type === 'motion_result') {
                    showToast('Motion ' + (data.motion_detected === true ? 'Detected' : 'None'), 'Score: ' + (data.score || '?'));
                    refreshDashboard();
                } else if (data.type === 'camera_list_updated') {
                    showToast('Camera List Updated', 'Danh sách camera đã được cập nhật.');
                    refreshCamSelect();
                    refreshCameras();
                }
            } catch(e) {}
        };
        WS.onclose = () => {
            document.getElementById('wsBadge').textContent = 'WebSocket: reconnecting...';
            document.getElementById('wsBadge').className = 'badge';
            wsReconnectTimer = setTimeout(connectWS, 3000);
        };
        WS.onerror = () => WS.close();
    } catch(err) {
        document.getElementById('wsBadge').textContent = 'WebSocket: error';
        document.getElementById('wsBadge').className = 'badge badge-red';
        wsReconnectTimer = setTimeout(connectWS, 5000);
    }
}

let toastTimer = null;
function showToast(title, msg) {
    document.getElementById('toastTitle').textContent = title;
    document.getElementById('toastMsg').textContent = msg;
    document.getElementById('toast').classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => document.getElementById('toast').classList.remove('show'), 4000);
}

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        if (btn.dataset.tab === 'cameras') refreshCameras();
        if (btn.dataset.tab === 'stats') refreshStats();
    });
});

function getPipelineConfig() {
    return {
        filters: currentFilters,
        threshold_value: parseInt(document.getElementById('thresholdVal').value) || 120,
        canny_low: parseInt(document.getElementById('cannyLow').value) || 80,
        canny_high: parseInt(document.getElementById('cannyHigh').value) || 160,
        resize_width: parseInt(document.getElementById('resizeW').value) || 320,
        resize_height: parseInt(document.getElementById('resizeH').value) || 240,
    };
}

function initFilterCheckboxes() {
    let allFilters = ['resize','grayscale','threshold','edge','gaussian_blur','histogram_equalize','sobel_x','sobel_y'];
    (async () => {
        try {
            const r = await fetch(API_BASE + '/config');
            const cfg = await r.json();
            if (cfg.processing && cfg.processing.available_filters) {
                allFilters = cfg.processing.available_filters;
            }
        } catch(e) {}
        renderFilterCheckboxes(allFilters);
    })();
}

function renderFilterCheckboxes(allFilters) {
    const container = document.getElementById('filterCheckboxes');
    container.innerHTML = '';
    allFilters.forEach(f => {
        const label = document.createElement('label');
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = currentFilters.includes(f);
        cb.onchange = () => {
            if (cb.checked) { if(!currentFilters.includes(f)) currentFilters.push(f); }
            else { currentFilters = currentFilters.filter(x => x !== f); }
            if (currentFilters.length === 0) { currentFilters = ['resize']; cb.checked = true; }
            updateFiltersUI();
        };
        label.appendChild(cb);
        label.appendChild(document.createTextNode(' ' + f.replace(/_/g,' ')));
        container.appendChild(label);
    });
}

function updateFiltersUI() {
    document.getElementById('filtersBadge').textContent = currentFilters.length + ' bước';
    document.getElementById('activeFiltersText').textContent = currentFilters.join(', ');
}

async function applyPipelineConfig() {
    const cfg = getPipelineConfig();
    document.getElementById('applyStatus').textContent = 'Applying...';
    try {
        const r = await fetch(API_BASE + '/config', { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(cfg) });
        if (r.ok) {
            document.getElementById('applyStatus').textContent = 'Applied ✓';
        } else {
            document.getElementById('applyStatus').textContent = 'Failed: ' + (await r.text());
        }
    } catch(e) {
        document.getElementById('applyStatus').textContent = 'Error: ' + e.message;
    }
    setTimeout(() => document.getElementById('applyStatus').textContent = '', 3000);
}

function getSelectedCamera() {
    const sel = document.getElementById('camSelect');
    return sel.value || '';
}

async function refreshCameras() {
    try {
        const r = await fetch(API_BASE + '/cameras');
        const cams = await r.json();

        let html = '<table><thead><tr><th>ID</th><th>Source</th><th>Label</th><th>Status</th><th>Last Seen</th><th>Action</th></tr></thead><tbody>';
        for (const c of cams) {
            html += `<tr>
                <td style="font-family:monospace;font-size:11px;">${escapeHTML(c.camera_id)}</td>
                <td>${escapeHTML(c.source)}</td>
                <td>${escapeHTML(c.label)}</td>
                <td><span class="cam-status-dot ${escapeHTML(c.status)}"></span>${escapeHTML(c.status)}</td>
                <td>${escapeHTML(c.last_seen || '-')}</td>
                <td>
                    <button class="sm secondary" onclick="editCamera('${escapeHTML(c.camera_id)}', '${escapeHTML(c.source.replace(/'/g, "\\'"))}', '${escapeHTML(c.label.replace(/'/g, "\\'"))}')"><i class="ph ph-pencil-simple"></i> Sửa</button>
                    <button class="sm secondary red" onclick="removeCamera('${escapeHTML(c.camera_id)}')"><i class="ph ph-trash"></i> Xóa</button>
                </td>
            </tr>`;
        }
        html += '</tbody></table>';
        if (!cams.length) html = '<p class="small text-secondary" style="padding:12px;">Chưa có camera nào. Thêm camera mới ở trên.</p>';
        document.getElementById('cameraTable').innerHTML = html;

        const grid = document.getElementById('allStreamsGrid');
        const existingIds = Array.from(grid.children).map(el => el.dataset.cameraId).filter(Boolean);
        const newIds = cams.map(c => c.camera_id);
        const needsUpdate = existingIds.length !== newIds.length || existingIds.some((id, i) => id !== newIds[i]);
        if (needsUpdate) {
            grid.innerHTML = '';
            cams.forEach(c => {
                const div = document.createElement('div');
                div.className = 'card-shell';
                div.dataset.cameraId = c.camera_id;
                div.innerHTML = `<div class="card-core" style="padding:10px;">
                    <div class="media-container cam-thumb">
                        <img src="${API_BASE}/video_feed?camera_id=${escapeHTML(c.camera_id)}&t=${Date.now()}" style="width:100%;" />
                        <div class="cam-label"><span class="cam-status-dot ${escapeHTML(c.status)}"></span>${escapeHTML(c.label)}</div>
                    </div>
                </div>`;
                grid.appendChild(div);
            });
        }
    } catch(e) {}
}

async function addCamera() {
    const source = document.getElementById('newCamSource').value.trim() || '0';
    const label = document.getElementById('newCamLabel').value.trim() || source;
    try {
        await fetch(API_BASE + `/cameras?source=${encodeURIComponent(source)}&label=${encodeURIComponent(label)}`, {method:'POST'});
        showToast('Camera Added', `${label} (${source})`);
        document.getElementById('newCamSource').value = '0';
        document.getElementById('newCamLabel').value = '';
        refreshCameras();
        await refreshCamSelect();
    } catch(e) { showToast('Error', 'Cannot add camera'); }
}

async function removeCamera(cameraId) {
    try {
        await fetch(API_BASE + `/cameras/${cameraId}`, {method:'DELETE'});
        showToast('Camera Removed', cameraId);

        // Nếu camera bị xóa đang phát stream, hãy dừng stream
        const streamImg = document.getElementById('stream');
        if (streamImg && streamImg.src && streamImg.src.includes('camera_id=' + cameraId)) {
            stopStream();
        }

        // Nếu camera bị xóa đang trong chế độ sửa, hãy hủy chế độ sửa
        if (editingCameraId === cameraId) {
            cancelEdit();
        }

        refreshCameras();
        await refreshCamSelect();
    } catch(e) {}
}

function editCamera(id, source, label) {
    editingCameraId = id;
    document.getElementById('newCamSource').value = source;
    document.getElementById('newCamLabel').value = label;

    // Chuyển nút "Thêm camera" thành "Cập nhật"
    const addBtn = document.querySelector('button[onclick="addCamera()"]');
    if (addBtn) {
        addBtn.innerHTML = '<i class="ph ph-check"></i> Cập nhật';
        addBtn.setAttribute('onclick', 'saveCamera()');
    }

    // Thêm nút "Hủy" nếu chưa có
    if (!document.getElementById('cancelEditBtn') && addBtn) {
        const cancelBtn = document.createElement('button');
        cancelBtn.id = 'cancelEditBtn';
        cancelBtn.className = 'secondary';
        cancelBtn.innerHTML = '<i class="ph ph-x"></i> Hủy';
        cancelBtn.onclick = cancelEdit;
        addBtn.parentNode.appendChild(cancelBtn);
    }
}

function cancelEdit() {
    editingCameraId = null;
    document.getElementById('newCamSource').value = '0';
    document.getElementById('newCamLabel').value = '';

    const saveBtn = document.querySelector('button[onclick="saveCamera()"]');
    if (saveBtn) {
        saveBtn.innerHTML = '<i class="ph ph-plus"></i> Thêm camera';
        saveBtn.setAttribute('onclick', 'addCamera()');
    }

    const cancelBtn = document.getElementById('cancelEditBtn');
    if (cancelBtn) {
        cancelBtn.remove();
    }
}

async function saveCamera() {
    if (!editingCameraId) return;
    const source = document.getElementById('newCamSource').value.trim() || '0';
    const label = document.getElementById('newCamLabel').value.trim() || source;
    try {
        const r = await fetch(API_BASE + `/cameras/${editingCameraId}?source=${encodeURIComponent(source)}&label=${encodeURIComponent(label)}`, {
            method: 'PUT'
        });
        if (r.ok) {
            showToast('Camera Updated', `${label} (${source})`);

            // Nếu camera đang phát stream, khởi động lại stream để áp dụng cấu hình nguồn mới
            const streamImg = document.getElementById('stream');
            if (streamImg && streamImg.src && streamImg.src.includes('camera_id=' + editingCameraId)) {
                startStream();
            }

            cancelEdit();
            refreshCameras();
            await refreshCamSelect();
        } else {
            showToast('Error', 'Cannot update camera');
        }
    } catch(e) {
        showToast('Error', 'Cannot update camera');
    }
}

async function refreshCamSelect() {
    try {
        const r = await fetch(API_BASE + '/cameras');
        const cams = await r.json();
        const sel = document.getElementById('camSelect');
        const currentVal = sel.value;
        sel.innerHTML = '';
        cams.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.camera_id;
            opt.textContent = `${c.label} (${c.source})`;
            sel.appendChild(opt);
        });
        if (currentVal && Array.from(sel.options).some(o => o.value === currentVal)) sel.value = currentVal;
    } catch(e) {}
}

function startStream() {
    const cid = getSelectedCamera();
    if (!cid) { showToast('Error', 'No camera selected'); return; }
    const streamImg = document.getElementById('stream');
    streamImg.src = API_BASE + '/video_feed?camera_id=' + cid + '&t=' + Date.now();
}

function stopStream() {
    const streamImg = document.getElementById('stream');
    streamImg.src = '';
}

async function snapshot() {
    const cid = getSelectedCamera();
    const detect = document.getElementById('detectCheck').checked;
    let url = API_BASE + '/snapshot?';
    if (cid) url += 'camera_id=' + cid + '&';
    url += 'run_detection=' + detect;
    try {
        const r = await fetch(url);
        const d = await r.json();
        document.getElementById('out').textContent = JSON.stringify(d, null, 2);
        if (d.raw_image_url) document.getElementById('raw').src = getImageUrl(d.raw_image_url) + '?t=' + Date.now();
        if (d.processed_image_url) document.getElementById('processed').src = getImageUrl(d.processed_image_url) + '?t=' + Date.now();
        if (d.detections && d.detections.length) showToast('Detection', d.detections.map(x=>x.label+' '+x.confidence).join(', '));
        refreshDashboard();
    } catch(e) { showToast('Error', 'Snapshot failed'); }
}

async function recordVideo() {
    const cid = getSelectedCamera();
    let url = API_BASE + '/record-video?seconds=5';
    if (cid) url += '&camera_id=' + cid;
    try {
        const r = await fetch(url);
        const d = await r.json();
        document.getElementById('out').textContent = JSON.stringify(d, null, 2);
        refreshDashboard();
    } catch(e) { showToast('Error', 'Video recording failed'); }
}

async function motionCapture() {
    const cid = getSelectedCamera();
    const method = document.getElementById('motionMethod').value;
    const minArea = document.getElementById('motionMinArea').value || 800;
    const seconds = document.getElementById('motionSeconds').value || 8;
    let url = API_BASE + `/motion-capture?seconds=${seconds}&method=${method}&min_area=${minArea}`;
    if (cid) url += '&camera_id=' + cid;
    try {
        const r = await fetch(url);
        const d = await r.json();
        document.getElementById('out').textContent = JSON.stringify(d, null, 2);
        if (d.raw_image_url) document.getElementById('raw').src = getImageUrl(d.raw_image_url) + '?t=' + Date.now();
        if (d.processed_image_url) document.getElementById('processed').src = getImageUrl(d.processed_image_url) + '?t=' + Date.now();
        refreshDashboard();
    } catch(e) { showToast('Error', 'Motion capture failed'); }
}

async function uploadImage() {
    const f = document.getElementById('file').files[0];
    if (!f) { alert('Chọn một ảnh.'); return; }
    const fd = new FormData();
    fd.append('file', f);
    try {
        const r = await fetch(API_BASE + '/upload-image?device_id=dashboard&run_detection=false', {method:'POST', body:fd});
        const d = await r.json();
        document.getElementById('out').textContent = JSON.stringify(d, null, 2);
        if (d.raw_image_url) document.getElementById('raw').src = getImageUrl(d.raw_image_url) + '?t=' + Date.now();
        if (d.processed_image_url) document.getElementById('processed').src = getImageUrl(d.processed_image_url) + '?t=' + Date.now();
        refreshDashboard();
    } catch(e) { showToast('Error', 'Upload failed'); }
}

async function uploadWithDetect() {
    const f = document.getElementById('file').files[0];
    if (!f) { alert('Chọn một ảnh.'); return; }
    const fd = new FormData();
    fd.append('file', f);
    try {
        const r = await fetch(API_BASE + '/upload-image?device_id=dashboard&run_detection=true', {method:'POST', body:fd});
        const d = await r.json();
        document.getElementById('out').textContent = JSON.stringify(d, null, 2);
        if (d.raw_image_url) document.getElementById('raw').src = getImageUrl(d.raw_image_url) + '?t=' + Date.now();
        if (d.processed_image_url) document.getElementById('processed').src = getImageUrl(d.processed_image_url) + '?t=' + Date.now();
        if (d.detections && d.detections.length) showToast('Detection', d.detections.map(x=>x.label+' '+x.confidence).join(', '));
        refreshDashboard();
    } catch(e) { showToast('Error', 'Upload+Detect failed'); }
}

function filterEvents(type) {
    activeEventFilter = type;
    refreshDashboard();
}

function tableFromRows(rows, cols, highlight) {
    if (!rows || rows.length === 0) return '<p class="small text-secondary" style="padding:12px;">Chưa có dữ liệu.</p>';
    let html = '<table><thead><tr>';
    for (const c of cols) html += '<th>' + c + '</th>';
    html += '</tr></thead><tbody>';
    for (const row of rows.slice().reverse()) {
        const sev = (row.severity || '').toLowerCase();
        let cls = '';
        if (sev === 'warning') cls = 'warn';
        else if (sev === 'error') cls = 'err';
        else if (sev === 'normal') cls = 'ok';
        html += '<tr>';
        for (const c of cols) {
            let val = row[c] ?? '';
            if (c === 'brightness' && val !== '') val = parseFloat(val).toFixed(1);
            if (c === 'confidence' && val !== '') val = parseFloat(val).toFixed(3);
            html += '<td class="' + cls + '">' + escapeHTML(val) + '</td>';
        }
        html += '</tr>';
    }
    html += '</tbody></table>';
    return html;
}

async function refreshDashboard() {
    try {
        const [latestRes, metaRes, evRes, detRes] = await Promise.all([
            fetch(API_BASE + '/latest'),
            fetch(API_BASE + '/metadata?limit=8'),
            fetch(API_BASE + '/events?limit=8' + (activeEventFilter !== 'ALL' ? '&event_type=' + activeEventFilter : '')),
            fetch(API_BASE + '/detections?limit=8'),
        ]);
        if (!latestRes.ok) throw new Error('Server error');
        const latest = await latestRes.json();
        const meta = await metaRes.json();
        const ev = await evRes.json();
        const det = await detRes.json();

        document.getElementById('metadataCount').textContent = latest.metadata_count || 0;
        document.getElementById('eventCount').textContent = latest.event_count || 0;
        document.getElementById('detectionCount').textContent = latest.detection_count || 0;
        document.getElementById('latestEvent').textContent = (latest.latest_event && latest.latest_event.event_type) ? latest.latest_event.event_type : '-';

        if (latest.raw_image_url) document.getElementById('raw').src = getImageUrl(latest.raw_image_url) + '?t=' + Date.now();
        if (latest.processed_image_url) document.getElementById('processed').src = getImageUrl(latest.processed_image_url) + '?t=' + Date.now();

        document.getElementById('metadataTable').innerHTML = tableFromRows(meta.items, ['image_id','timestamp','source_type','width','height','brightness','processing_status']);
        document.getElementById('eventTable').innerHTML = tableFromRows(ev.items, ['event_type','timestamp','severity','score','explanation']);
        document.getElementById('detectionTable').innerHTML = tableFromRows(det.items, ['label','confidence','timestamp','bbox_x','bbox_y','bbox_w','bbox_h']);
    } catch (e) {
        console.warn('Dashboard sync error:', e);
    }
}

async function refreshStats() {
    try {
        const r = await fetch(API_BASE + '/stats');
        const s = await r.json();
        document.getElementById('statsGrid').innerHTML = `
            <div class="card-shell bento-col-4"><div class="card-core" style="text-align:center;">
                <div class="metric-glow glow-blue"></div>
                <div class="metric" style="font-size:36px;">${s.total_images || 0}</div>
                <div class="metric-label">Total Images</div>
            </div></div>
            <div class="card-shell bento-col-4"><div class="card-core" style="text-align:center;">
                <div class="metric-glow glow-purple"></div>
                <div class="metric" style="font-size:36px;">${s.total_events || 0}</div>
                <div class="metric-label">Total Events</div>
            </div></div>
            <div class="card-shell bento-col-4"><div class="card-core" style="text-align:center;">
                <div class="metric-glow glow-orange"></div>
                <div class="metric" style="font-size:36px;">${s.total_detections || 0}</div>
                <div class="metric-label">Total Detections</div>
            </div></div>
        `;
        document.getElementById('statsEventTable').innerHTML = tableFromRows(s.event_by_type, ['event_type','cnt']);
        document.getElementById('statsDetTable').innerHTML = tableFromRows(s.detection_by_label, ['label','cnt']);
    } catch(e) {}
}

async function refreshServerInfo() {
    try {
        const r = await fetch(API_BASE + '/health');
        const h = await r.json();
        document.getElementById('serverBadge').textContent = 'Server: OK v' + h.version;
        document.getElementById('serverBadge').className = 'badge badge-green';
        if (h.detection) {
            document.getElementById('detectionBadge').textContent = 'Detection: ONNX';
            document.getElementById('detectionBadge').className = 'badge badge-orange';
        }
        if (h.mqtt) {
            document.getElementById('mqttBadge').textContent = 'MQTT: connected';
            document.getElementById('mqttBadge').className = 'badge badge-green';
        }
    } catch(e) {
        document.getElementById('serverBadge').textContent = 'Server: offline';
        document.getElementById('serverBadge').className = 'badge badge-red';
    }
}

function toggleTheme() {
    const body = document.body;
    const icon = document.getElementById('themeIcon');
    const text = document.getElementById('themeText');
    
    if (body.classList.contains('light-theme')) {
        body.classList.remove('light-theme');
        if (icon) icon.className = 'ph ph-sun';
        if (text) text.textContent = 'Chế độ sáng';
        localStorage.setItem('theme', 'dark');
        showToast('Theme Updated', 'Đã chuyển sang chế độ tối (Dark Theme)');
    } else {
        body.classList.add('light-theme');
        if (icon) icon.className = 'ph ph-moon';
        if (text) text.textContent = 'Chế độ tối';
        localStorage.setItem('theme', 'light');
        showToast('Theme Updated', 'Đã chuyển sang chế độ sáng (Light Theme)');
    }
}

function loadStoredTheme() {
    const storedTheme = localStorage.getItem('theme');
    const body = document.body;
    const icon = document.getElementById('themeIcon');
    const text = document.getElementById('themeText');
    
    if (storedTheme === 'light') {
        body.classList.add('light-theme');
        if (icon) icon.className = 'ph ph-moon';
        if (text) text.textContent = 'Chế độ tối';
    } else {
        body.classList.remove('light-theme');
        if (icon) icon.className = 'ph ph-sun';
        if (text) text.textContent = 'Chế độ sáng';
    }
}

function getImageUrl(path) {
    if (!path) return '';
    return path.startsWith('http') ? path : (API_BASE + path);
}

async function init() {
    loadStoredTheme();
    initBackendUrl();
    initFilterCheckboxes();
    updateFiltersUI();
    connectWS();
    await refreshCamSelect();
    await refreshCameras();
    await refreshServerInfo();
    refreshDashboard();

    const sel = document.getElementById('camSelect');
    if (sel) {
        sel.addEventListener('change', () => {
            const streamImg = document.getElementById('stream');
            if (streamImg && streamImg.src && streamImg.src.includes('/video_feed')) {
                startStream();
            }
        });
    }

    setInterval(refreshDashboard, 5000);
    setInterval(refreshServerInfo, 30000);
    setInterval(refreshCameras, 60000);
}
init();
