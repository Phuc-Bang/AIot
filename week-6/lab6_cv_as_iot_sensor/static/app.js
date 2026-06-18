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
                        updateImageSrcIfChanged('raw', data.raw_image_url);
                    }
                    if (data.processed_image_url) {
                        updateImageSrcIfChanged('processed', data.processed_image_url);
                    }
                    document.getElementById('out').textContent = JSON.stringify(data, null, 2);
                    if (data.detections && data.detections.length > 0) {
                        showToast('Detection', data.detections.map(d=>d.label+' '+d.confidence).join(', '));
                    }
                    refreshDashboard();
                } else if (data.type === 'motion_result') {
                    showToast(
                        data.person_motion_detected ? 'Person Motion Detected' : 'No Person Motion',
                        (data.reason_code || 'UNKNOWN') + ' | Score: ' + (data.motion_score ?? data.score ?? '?')
                    );
                    document.getElementById('out').textContent = JSON.stringify(data, null, 2);
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
        if (btn.dataset.tab === 'gallery') {
            refreshGalleryCamSelect();
            refreshGallery();
        }
        if (btn.dataset.tab === 'stats') refreshStats();
    });
});

function getPipelineConfig() {
    const hogHitThreshold = parseFloat(document.getElementById('detectConf').value);
    return {
        filters: currentFilters,
        threshold_value: parseInt(document.getElementById('thresholdVal').value) || 120,
        canny_low: parseInt(document.getElementById('cannyLow').value) || 80,
        canny_high: parseInt(document.getElementById('cannyHigh').value) || 160,
        resize_width: parseInt(document.getElementById('resizeW').value) || 320,
        resize_height: parseInt(document.getElementById('resizeH').value) || 240,
        hog_hit_threshold: Number.isFinite(hogHitThreshold) ? hogHitThreshold : 0.0,
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

function startPreviewStream(btn) {
    const box = btn.closest('.cam-thumb');
    const img = box ? box.querySelector('.stream-thumb') : null;
    if (!img) return;
    const cid = img.dataset.camId;
    img.src = `${API_BASE}/video_feed?camera_id=${encodeURIComponent(cid)}&t=${Date.now()}`;
    img.style.display = 'block';
    const placeholder = box.querySelector('.preview-placeholder');
    if (placeholder) placeholder.style.display = 'none';
    btn.textContent = 'Restart preview';
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
                        <div class="preview-placeholder small text-secondary" style="padding:36px 12px;text-align:center;">Preview paused</div>
                        <img class="stream-thumb" data-cam-id="${escapeHTML(c.camera_id)}" src="" style="width:100%;display:none;" />
                        <button class="sm secondary" onclick="startPreviewStream(this)" style="position:absolute;right:8px;bottom:8px;">Preview</button>
                        <div class="cam-label"><span class="cam-status-dot ${escapeHTML(c.status)}"></span>${escapeHTML(c.label)}</div>
                    </div>
                </div>`;
                grid.appendChild(div);
            });
        }
        // Populate dashboard multi-camera preview
        const previewGrid = document.getElementById('camPreviewGrid');
        if (previewGrid) {
            const previewExisting = Array.from(previewGrid.children).map(el => el.dataset.cameraId).filter(Boolean);
            if (previewExisting.length !== newIds.length || previewExisting.some((id, i) => id !== newIds[i])) {
                previewGrid.innerHTML = '';
                cams.slice(0, 4).forEach(c => {
                    const div = document.createElement('div');
                    div.className = 'card-shell';
                    div.dataset.cameraId = c.camera_id;
                    div.style.cssText = 'margin-bottom:8px;';
                    div.innerHTML = `<div class="card-core" style="padding:8px;">
                        <div class="media-container cam-thumb" style="min-height:140px;">
                            <div class="preview-placeholder small text-secondary" style="padding:42px 12px;text-align:center;">Preview paused</div>
                            <img class="stream-thumb" data-cam-id="${escapeHTML(c.camera_id)}" src="" style="width:100%;display:none;" />
                            <button class="sm secondary" onclick="startPreviewStream(this)" style="position:absolute;right:8px;bottom:8px;">Preview</button>
                            <div class="cam-label"><span class="cam-status-dot ${escapeHTML(c.status)}"></span>${escapeHTML(c.label)}</div>
                        </div>
                    </div>`;
                    previewGrid.appendChild(div);
                });
                if (cams.length > 4) {
                    const more = document.createElement('p');
                    more.className = 'small text-secondary';
                    more.style.cssText = 'text-align:center;padding:8px;';
                    more.textContent = `+ ${cams.length - 4} cameras more in Camera Manager tab`;
                    previewGrid.appendChild(more);
                }
                if (!cams.length) {
                    previewGrid.innerHTML = '<p class="small text-secondary" style="padding:12px;text-align:center;">Register cameras in Camera Manager tab.</p>';
                }
            }
        }
    } catch(e) { console.warn('refreshCameras error:', e); }
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
        
        let currentCamObj = null;
        cams.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.camera_id;
            opt.textContent = `${c.label} (${c.source})`;
            sel.appendChild(opt);
            if (c.camera_id === currentVal) {
                currentCamObj = c;
            }
        });
        
        if (currentCamObj) {
            sel.value = currentVal;
            // Nếu camera đang phát stream nhưng cấu hình nguồn bị thay đổi từ client khác, restart stream
            const streamImg = document.getElementById('stream');
            if (streamImg && streamImg.src && streamImg.src.includes('/video_feed')) {
                const oldSource = streamImg.dataset.activeSource;
                if (oldSource !== undefined && oldSource !== currentCamObj.source) {
                    startStream();
                }
            }
        } else if (currentVal) {
            // Camera đang chọn đã bị xóa
            const streamImg = document.getElementById('stream');
            if (streamImg && streamImg.src && streamImg.src.includes('/video_feed')) {
                stopStream();
                showToast('Stream Stopped', 'Camera đang phát đã bị xóa khỏi hệ thống.');
            }
        }
    } catch(e) {}
    refreshGalleryCamSelect();
}

function startStream() {
    const cid = getSelectedCamera();
    if (!cid) { showToast('Error', 'No camera selected'); return; }
    const streamImg = document.getElementById('stream');
    streamImg.src = API_BASE + '/video_feed?camera_id=' + cid + '&t=' + Date.now();
    streamImg.dataset.activeCameraId = cid;
    
    // Lưu source hiện tại từ select box
    const sel = document.getElementById('camSelect');
    const opt = sel.options[sel.selectedIndex];
    if (opt) {
        const match = opt.textContent.match(/\(([^)]+)\)$/);
        if (match) {
            streamImg.dataset.activeSource = match[1];
        }
    }
}

function stopStream() {
    const streamImg = document.getElementById('stream');
    streamImg.src = '';
    delete streamImg.dataset.activeSource;
    delete streamImg.dataset.activeCameraId;
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
        if (d.raw_image_url) updateImageSrcIfChanged('raw', d.raw_image_url);
        if (d.processed_image_url) updateImageSrcIfChanged('processed', d.processed_image_url);
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
    const seconds = document.getElementById('motionSeconds').value || 3;
    const debug = document.getElementById('debugMotionCheck')?.checked ? 'true' : 'false';
    let url = API_BASE + `/motion-capture?seconds=${seconds}&method=${method}&min_area=${minArea}&debug=${debug}`;
    if (cid) url += '&camera_id=' + cid;
    try {
        const r = await fetch(url);
        const d = await r.json();
        const q = d.quality || {};
        const summary = {
            person_motion_detected: d.person_motion_detected,
            reason_code: d.reason_code,
            motion_score: d.motion_score,
            person_count: d.person_count || 0,
            best_overlap_ratio: d.best_overlap_ratio || 0,
            brightness: q.brightness,
            blur_score: q.blur_score,
            warnings: q.warnings || [],
        };
        document.getElementById('out').textContent = JSON.stringify({summary, response: d}, null, 2);
        if (d.raw_image_url) updateImageSrcIfChanged('raw', d.raw_image_url);
        if (d.processed_image_url) updateImageSrcIfChanged('processed', d.processed_image_url);
        showToast(d.person_motion_detected ? 'Person Motion Detected' : 'No Person Motion', d.reason_code || '');
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
        if (d.raw_image_url) updateImageSrcIfChanged('raw', d.raw_image_url);
        if (d.processed_image_url) updateImageSrcIfChanged('processed', d.processed_image_url);
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
        if (d.raw_image_url) updateImageSrcIfChanged('raw', d.raw_image_url);
        if (d.processed_image_url) updateImageSrcIfChanged('processed', d.processed_image_url);
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

        if (latest.raw_image_url) updateImageSrcIfChanged('raw', latest.raw_image_url);
        if (latest.processed_image_url) updateImageSrcIfChanged('processed', latest.processed_image_url);

        document.getElementById('metadataTable').innerHTML = tableFromRows(meta.items, ['image_id','timestamp','source_type','width','height','brightness','processing_status']);
        document.getElementById('eventTable').innerHTML = tableFromRows(ev.items, ['event_type','timestamp','severity','score','explanation']);
        document.getElementById('detectionTable').innerHTML = tableFromRows(det.items, ['label','confidence','timestamp','bbox_x','bbox_y','bbox_w','bbox_h']);
    } catch (e) {
        console.warn('Dashboard sync error:', e);
    }
}



async function refreshServerInfo() {
    try {
        const r = await fetch(API_BASE + '/health');
        const h = await r.json();
        document.getElementById('serverBadge').textContent = 'Server: OK v' + h.version;
        document.getElementById('serverBadge').className = 'badge badge-green';
        if (h.detection) {
            document.getElementById('detectionBadge').textContent = 'Detection: ' + (h.detection_mode || 'OpenCV HOG Person');
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

function updateImageSrcIfChanged(imgId, newRelativeOrAbsoluteUrl) {
    const img = document.getElementById(imgId);
    if (!img || !newRelativeOrAbsoluteUrl) return;
    const newFullUrl = getImageUrl(newRelativeOrAbsoluteUrl);
    
    if (!img.src || img.src === window.location.href || img.src.endsWith('/')) {
        img.src = newFullUrl + '?t=' + Date.now();
        return;
    }
    
    try {
        const currentUrlObj = new URL(img.src);
        currentUrlObj.search = '';
        const cleanCurrentUrl = currentUrlObj.toString();
        
        const newUrlObj = new URL(newFullUrl, window.location.origin + window.location.pathname);
        newUrlObj.search = '';
        const cleanNewUrl = newUrlObj.toString();
        
        if (cleanCurrentUrl !== cleanNewUrl) {
            img.src = newFullUrl + '?t=' + Date.now();
        }
    } catch(e) {
        img.src = newFullUrl + '?t=' + Date.now();
    }
}

async function testCamera() {
    const source = document.getElementById('newCamSource').value.trim() || '0';
    const resultEl = document.getElementById('camTestResult');
    resultEl.textContent = 'Testing...';
    resultEl.style.color = 'var(--text-secondary)';
    try {
        const r = await fetch(API_BASE + `/cameras/test?source=${encodeURIComponent(source)}`);
        const d = await r.json();
        if (d.status === 'ok') {
            resultEl.innerHTML = `<span style="color:var(--accent-green);">&#10003; ${d.message}</span>`;
        } else {
            resultEl.innerHTML = `<span style="color:var(--accent-red);">&#10007; ${d.message}</span>`;
        }
    } catch(e) {
        resultEl.innerHTML = `<span style="color:var(--accent-red);">&#10007; Connection failed: ${e.message}</span>`;
    }
    setTimeout(() => { if(resultEl.textContent) resultEl.textContent = ''; }, 5000);
}

async function refreshGallery() {
    const sel = document.getElementById('galleryCamSelect');
    const camId = sel ? sel.value : '';
    let url = API_BASE + '/images?limit=50';
    if (camId) url += '&camera_id=' + encodeURIComponent(camId);
    try {
        const r = await fetch(url);
        const data = await r.json();
        const grid = document.getElementById('galleryGrid');
        if (!data.items || !data.items.length) {
            grid.innerHTML = '<p class="small text-secondary" style="padding:24px;text-align:center;">Chưa có ảnh nào. Chụp snapshot hoặc upload ảnh từ Dashboard.</p>';
            return;
        }
        let html = '';
        for (const item of data.items) {
            const rawUrl = getImageUrl(item.image_path ? '/' + item.image_path.replace(/\\/g,'/') : '');
            const thumbUrl = rawUrl;
            const ts = item.timestamp || '';
            const note = item.note || '';
            html += `<div class="gallery-item" onclick="openGalleryZoom('${escapeHTML(rawUrl)}', '${escapeHTML(item.processed_path ? '/' + item.processed_path.replace(/\\/g,'/') : '')}', '${escapeHTML(item.image_id || '')}', '${escapeHTML(item.camera_id || '')}', '${escapeHTML(ts)}', '${escapeHTML(item.width||'')}', '${escapeHTML(item.height||'')}', '${escapeHTML(item.brightness||'')}', '${escapeHTML(note)}')">
                <img src="${escapeHTML(thumbUrl)}" loading="lazy" onerror="this.parentElement.style.display='none'" />
                <div class="gallery-info">
                    <strong>${escapeHTML(item.image_id || '')}</strong>
                    ${escapeHTML(ts)} | ${escapeHTML(item.width||'?')}x${escapeHTML(item.height||'?')}
                    ${note ? '<br>' + escapeHTML(note) : ''}
                </div>
            </div>`;
        }
        grid.innerHTML = html;
    } catch(e) {
        document.getElementById('galleryGrid').innerHTML = '<p class="small text-secondary" style="padding:24px;text-align:center;">Error loading gallery.</p>';
    }
}

function openGalleryZoom(rawUrl, processedPath, imageId, cameraId, ts, w, h, brightness, note) {
    document.getElementById('galleryZoomImg').src = rawUrl + '?t=' + Date.now();
    const metaEl = document.getElementById('galleryZoomMeta');
    metaEl.innerHTML = `<strong>${imageId}</strong> | ${cameraId} | ${ts} | ${w}x${h} | Brightness: ${brightness}${note ? ' | ' + note : ''}`;
    const dlRaw = document.getElementById('galleryDownloadRaw');
    dlRaw.href = rawUrl;
    const dlProc = document.getElementById('galleryDownloadProcessed');
    if (processedPath) {
        dlProc.href = getImageUrl(processedPath);
        dlProc.style.display = 'inline-flex';
    } else {
        dlProc.style.display = 'none';
    }
    document.getElementById('galleryZoomOverlay').style.display = 'flex';
}

async function refreshGalleryCamSelect() {
    try {
        const r = await fetch(API_BASE + '/cameras');
        const cams = await r.json();
        const sel = document.getElementById('galleryCamSelect');
        sel.innerHTML = '<option value="">All Cameras</option>';
        cams.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.camera_id;
            opt.textContent = `${c.label} (${c.source})`;
            sel.appendChild(opt);
        });
    } catch(e) {}
}

function closeGalleryZoom() {
    document.getElementById('galleryZoomOverlay').style.display = 'none';
}

function exportJSON() {
    window.open(API_BASE + '/export/json', '_blank');
}

function exportMetadataCSV() {
    window.open(API_BASE + '/export/metadata/csv', '_blank');
}

function drawBarChart(canvasId, labels, values, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.scale(dpr, dpr);
    const w = rect.width, h = rect.height;
    ctx.clearRect(0, 0, w, h);
    if (!labels || !values || labels.length === 0) {
        ctx.fillStyle = '#71717a';
        ctx.font = '12px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('No data', w/2, h/2);
        return;
    }
    const pad = { top: 16, bottom: 40, left: 16, right: 16 };
    const maxVal = Math.max(...values, 1);
    const barW = Math.min(40, (w - pad.left - pad.right) / labels.length - 4);
    const barGap = 4;
    ctx.textBaseline = 'bottom';
    ctx.font = '10px monospace';
    for (let i = 0; i < labels.length; i++) {
        const x = pad.left + i * (barW + barGap) + barGap/2;
        const barH = (values[i] / maxVal) * (h - pad.top - pad.bottom);
        const y = h - pad.bottom - barH;
        const gradient = ctx.createLinearGradient(x, y, x, h - pad.bottom);
        gradient.addColorStop(0, color || '#06b6d4');
        gradient.addColorStop(1, (color || '#06b6d4') + '44');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x, y, barW, barH, [4,4,0,0]);
        ctx.fill();
        ctx.fillStyle = '#a1a1aa';
        ctx.textAlign = 'center';
        ctx.fillText(labels[i].substring(0, 10), x + barW/2, h - pad.bottom + 14);
        ctx.fillText(values[i], x + barW/2, y - 4);
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
        drawBarChart('chartEventByType',
            (s.event_by_type||[]).map(r=>r.event_type),
            (s.event_by_type||[]).map(r=>r.cnt),
            '#f97316'
        );
        drawBarChart('chartDetByLabel',
            (s.detection_by_label||[]).map(r=>r.label),
            (s.detection_by_label||[]).map(r=>r.cnt),
            '#06b6d4'
        );
    } catch(e) {}
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
