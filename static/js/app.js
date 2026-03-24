const API = '/api/v1';
let currentUser = JSON.parse(localStorage.getItem('user') || 'null');

// --- API helpers ---
async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    const res = await fetch(`${API}${path}`, { ...options, headers, credentials: 'same-origin' });
    if (res.status === 204) return null;
    if (res.status === 401) {
        // Token expired or invalid — redirect to login
        currentUser = null;
        localStorage.removeItem('user');
        showScreen('login');
        hide($('#app-header'));
        hide($('#app-nav'));
        showAlert('Session expired. Please log in again.', 'warning');
        throw { status: 401, detail: 'Session expired' };
    }
    const data = await res.json();
    if (!res.ok) throw { status: res.status, detail: data.detail || 'Request failed' };
    return data;
}

// --- DOM helpers ---
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);
const show = (el) => el.classList.remove('hidden');
const hide = (el) => el.classList.add('hidden');

// --- Screen management ---
function showScreen(name) {
    $$('.screen').forEach(s => hide(s));
    show($(`#screen-${name}`));
    $$('.nav-tab').forEach(t => t.classList.remove('active'));
    const tab = $(`.nav-tab[data-screen="${name}"]`);
    if (tab) tab.classList.add('active');
    if (name === 'dashboard') loadDashboard();
}

// --- Auth ---
async function handleRegister(e) {
    e.preventDefault();
    try {
        await api('/auth/register', {
            method: 'POST',
            body: JSON.stringify({
                email: $('#reg-email').value,
                password: $('#reg-password').value,
                full_name: $('#reg-name').value,
            }),
        });
        showAlert('Account created! Please log in.', 'success');
        showScreen('login');
    } catch (err) {
        showAlert(err.detail, 'danger');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    try {
        const data = await api('/auth/login', {
            method: 'POST',
            body: JSON.stringify({
                email: $('#login-email').value,
                password: $('#login-password').value,
            }),
        });
        currentUser = data.user;
        localStorage.setItem('user', JSON.stringify(currentUser));
        enterApp();
    } catch (err) {
        showAlert(err.detail, 'danger');
    }
}

async function logout() {
    try { await api('/auth/logout', { method: 'POST' }); } catch (e) {}
    currentUser = null;
    localStorage.removeItem('user');
    showScreen('login');
    hide($('#app-header'));
    hide($('#app-nav'));
}

function enterApp() {
    show($('#app-header'));
    show($('#app-nav'));
    $('#user-name').textContent = currentUser.full_name;
    $('#user-role').textContent = currentUser.role;

    // Show/hide tabs based on role
    const isStaff = ['nurse', 'doctor', 'admin'].includes(currentUser.role);
    $$('.staff-only').forEach(el => isStaff ? show(el) : hide(el));

    showScreen('dashboard');
}

// --- Dashboard ---
async function loadDashboard() {
    const container = $('#dashboard-content');
    const role = currentUser.role;
    let html = `<div class="greeting">Welcome back, <strong>${currentUser.full_name}</strong></div>`;

    // Quick actions
    html += '<div class="section-title" style="margin-top:16px">Quick Actions</div>';
    html += '<div class="quick-actions">';
    html += '<button class="action-card" onclick="showScreen(\'symptoms\')"><div class="action-icon">🔍</div><div>Symptom Check</div></button>';
    html += '<button class="action-card" onclick="showScreen(\'bmi\')"><div class="action-icon">⚖️</div><div>BMI Calculator</div></button>';
    if (isStaff()) {
        html += '<button class="action-card" onclick="showScreen(\'triage\')"><div class="action-icon">🚨</div><div>Triage</div></button>';
        html += '<button class="action-card" onclick="showScreen(\'vitals\')"><div class="action-icon">💓</div><div>Record Vitals</div></button>';
        html += '<button class="action-card" onclick="showScreen(\'camera\')"><div class="action-icon">📷</div><div>Camera</div></button>';
    }
    html += '</div>';

    // Staff dashboard: triage queue + stats
    if (isStaff()) {
        try {
            const queue = await api('/triage/queue?status=waiting');
            html += '<div class="section-title" style="margin-top:24px">Triage Queue</div>';
            if (queue.total === 0) {
                html += '<div class="card"><p style="color:var(--gray-500);text-align:center">No patients waiting</p></div>';
            } else {
                html += `<div class="stat-bar"><span class="stat-count">${queue.total}</span> patient${queue.total !== 1 ? 's' : ''} waiting</div>`;
                queue.queue.slice(0, 5).forEach(item => {
                    html += `<div class="card">
                        <div class="card-header">
                            <span class="card-title">${item.patient_name}</span>
                            <span class="badge badge-${item.priority_color}">Level ${item.priority_level}</span>
                        </div>
                        <div class="card-meta">${item.chief_complaint}</div>
                        <div class="card-meta">Waiting: ${item.wait_time_minutes} min</div>
                    </div>`;
                });
                if (queue.total > 5) {
                    html += `<p style="text-align:center;color:var(--gray-500);font-size:13px">+ ${queue.total - 5} more</p>`;
                }
            }
        } catch (e) {
            // Queue not accessible, skip
        }

        // Recent conditions overview
        try {
            const conditions = await api('/symptoms/conditions');
            html += '<div class="section-title" style="margin-top:24px">Condition Database</div>';
            html += '<div class="stat-bar">';
            const categories = {};
            conditions.conditions.forEach(c => {
                categories[c.category] = (categories[c.category] || 0) + 1;
            });
            for (const [cat, count] of Object.entries(categories)) {
                html += `<span class="stat-chip">${cat}: ${count}</span>`;
            }
            html += '</div>';
        } catch (e) {}
    }

    // Patient view: health tips
    if (role === 'patient') {
        html += '<div class="section-title" style="margin-top:24px">Health Tips</div>';
        html += `<div class="card">
            <div class="card-title">Stay Healthy</div>
            <ul style="margin-top:8px;padding-left:20px;color:var(--gray-700);font-size:14px;line-height:1.8">
                <li>Take medications on schedule</li>
                <li>Track your symptoms — early detection saves lives</li>
                <li>Stay hydrated and get adequate rest</li>
                <li>Use the symptom checker if you feel unwell</li>
                <li>Contact your doctor for persistent symptoms</li>
            </ul>
        </div>`;
    }

    container.innerHTML = html;
}

function isStaff() {
    return ['nurse', 'doctor', 'admin'].includes(currentUser?.role);
}

// --- BMI ---
async function handleBMI(e) {
    e.preventDefault();
    try {
        const data = await api('/metrics/bmi', {
            method: 'POST',
            body: JSON.stringify({
                height_cm: parseFloat($('#bmi-height').value),
                weight_kg: parseFloat($('#bmi-weight').value),
            }),
        });
        const result = $('#bmi-result');
        const colorMap = {
            'severe underweight': 'var(--danger)', 'moderate underweight': 'var(--warning)',
            'underweight': 'var(--warning)', 'normal': 'var(--success)',
            'overweight': 'var(--warning)', 'obese class I': 'var(--danger)',
            'obese class II': 'var(--danger)', 'obese class III': 'var(--danger)',
        };
        result.innerHTML = `
            <div class="bmi-result">
                <div class="bmi-value" style="color:${colorMap[data.category] || 'inherit'}">${data.bmi}</div>
                <div class="bmi-category">${data.category}</div>
                <p style="margin-top:12px;color:var(--gray-500);font-size:14px">${data.interpretation}</p>
                <p style="margin-top:8px;font-size:13px;color:var(--gray-500)">
                    Healthy range: ${data.healthy_weight_range.min_kg}–${data.healthy_weight_range.max_kg} kg
                </p>
            </div>
        `;
        show(result);
    } catch (err) {
        showAlert(err.detail, 'danger');
    }
}

// --- Symptom Checker ---
const COMMON_SYMPTOMS = [
    'fever', 'cough', 'headache', 'fatigue', 'body_aches', 'nausea',
    'vomiting', 'diarrhea', 'shortness_of_breath', 'chest_pain',
    'sore_throat', 'runny_nose', 'abdominal_pain', 'dizziness',
    'rash', 'joint_pain', 'back_pain', 'swelling', 'stiff_neck',
    'light_sensitivity', 'sweating', 'wheezing', 'painful_urination',
    'frequent_urination', 'numbness', 'weakness', 'bloating',
    'itching', 'swollen_glands', 'chills', 'balance_problems',
];
let selectedSymptoms = new Set();

function renderSymptomTags() {
    const container = $('#symptom-tags');
    if (!container) return;
    container.innerHTML = COMMON_SYMPTOMS.map(s =>
        `<span class="symptom-tag ${selectedSymptoms.has(s) ? 'selected' : ''}" data-symptom="${s}">
            ${s.replace(/_/g, ' ')}
        </span>`
    ).join('');
    container.querySelectorAll('.symptom-tag').forEach(tag => {
        tag.addEventListener('click', () => {
            const sym = tag.dataset.symptom;
            if (selectedSymptoms.has(sym)) selectedSymptoms.delete(sym);
            else selectedSymptoms.add(sym);
            renderSymptomTags();
        });
    });
}

async function handleSymptomCheck(e) {
    e.preventDefault();
    if (selectedSymptoms.size === 0) {
        showAlert('Please select at least one symptom', 'warning');
        return;
    }
    try {
        const data = await api('/symptoms/check', {
            method: 'POST',
            body: JSON.stringify({
                symptoms: [...selectedSymptoms],
                duration_days: parseInt($('#sym-duration').value),
                severity: $('#sym-severity').value,
                age: parseInt($('#sym-age').value),
            }),
        });
        renderSymptomResults(data);
    } catch (err) {
        showAlert(err.detail, 'danger');
    }
}

function renderSymptomResults(data) {
    const result = $('#symptom-result');
    const urgencyClass = { emergency: 'danger', high: 'danger', moderate: 'warning', low: 'info' };
    let html = `<div class="alert alert-${urgencyClass[data.urgency] || 'info'}">
        Urgency: <strong>${data.urgency.toUpperCase()}</strong> — ${data.recommended_action}
    </div>`;
    if (data.possible_conditions.length > 0) {
        html += '<div class="result-header">Possible Conditions</div>';
        data.possible_conditions.forEach(c => {
            const probColor = { high: 'var(--danger)', moderate: 'var(--warning)', low: 'var(--gray-500)' };
            html += `<div class="condition-item">
                <div class="condition-name">${c.condition}
                    <span class="condition-prob" style="color:${probColor[c.probability]}">(${c.probability})</span>
                </div>
                <div class="condition-desc">${c.description}</div>
            </div>`;
        });
    } else {
        html += '<p style="color:var(--gray-500)">No matching conditions found.</p>';
    }
    html += `<div class="disclaimer">${data.disclaimer}</div>`;
    result.innerHTML = html;
    show(result);
}

// --- Vitals ---
async function handleVitals(e) {
    e.preventDefault();
    const patientId = $('#vitals-patient-id').value.trim();
    if (!patientId) { showAlert('Patient ID is required', 'warning'); return; }
    try {
        const data = await api('/metrics/vitals', {
            method: 'POST',
            body: JSON.stringify({
                patient_id: patientId,
                heart_rate: parseInt($('#v-hr').value),
                blood_pressure_systolic: parseInt($('#v-sys').value),
                blood_pressure_diastolic: parseInt($('#v-dia').value),
                temperature_c: parseFloat($('#v-temp').value),
                respiratory_rate: parseInt($('#v-rr').value),
                oxygen_saturation: parseInt($('#v-spo2').value),
            }),
        });
        renderVitalsResult(data);
    } catch (err) {
        showAlert(typeof err.detail === 'string' ? err.detail : 'Failed to record vitals', 'danger');
    }
}

function renderVitalsResult(data) {
    const result = $('#vitals-result');
    let html = '';
    if (data.alerts.length > 0) {
        html += data.alerts.map(a => `<div class="alert alert-danger">${a}</div>`).join('');
    } else {
        html += '<div class="alert alert-success">All vitals within normal range</div>';
    }
    html += '<div class="vitals-grid">';
    for (const [key, reading] of Object.entries(data.readings)) {
        const label = key.replace(/_/g, ' ').replace('blood pressure ', 'BP ');
        html += `<div class="vital-item">
            <div class="vital-value">${reading.value}</div>
            <div class="vital-label">${label}</div>
            <div class="vital-status ${reading.status}">${reading.status.replace(/_/g, ' ')}</div>
        </div>`;
    }
    html += '</div>';
    result.innerHTML = html;
    show(result);
}

// --- Triage ---
async function handleTriage(e) {
    e.preventDefault();
    try {
        const body = {
            patient_name: $('#tri-name').value,
            chief_complaint: $('#tri-complaint').value,
            symptoms: $('#tri-symptoms').value.split(',').map(s => s.trim()).filter(Boolean),
            symptom_duration: $('#tri-duration').value,
            vitals: {
                heart_rate: parseInt($('#tri-hr').value),
                blood_pressure_systolic: parseInt($('#tri-sys').value),
                blood_pressure_diastolic: parseInt($('#tri-dia').value),
                temperature_c: parseFloat($('#tri-temp').value),
                respiratory_rate: parseInt($('#tri-rr').value),
                oxygen_saturation: parseInt($('#tri-spo2').value),
            },
            pain_scale: parseInt($('#tri-pain').value),
            age: parseInt($('#tri-age').value),
        };
        const pid = $('#tri-patient-id').value.trim();
        if (pid) body.patient_id = pid;
        const data = await api('/triage', { method: 'POST', body: JSON.stringify(body) });
        renderTriageResult(data);
    } catch (err) {
        showAlert(typeof err.detail === 'string' ? err.detail : 'Triage assessment failed', 'danger');
    }
}

function renderTriageResult(data) {
    const result = $('#triage-result');
    const badgeClass = `badge-${data.priority_color}`;
    let html = `
        <div style="text-align:center;padding:16px 0">
            <div class="badge ${badgeClass}" style="font-size:16px;padding:6px 16px">
                Level ${data.priority_level} — ${data.priority_label}
            </div>
            <p style="margin-top:12px;font-size:14px">${data.recommended_action}</p>
        </div>
    `;
    if (data.flags.length > 0) {
        html += '<div style="margin-top:8px"><strong>Flags:</strong></div>';
        html += '<div class="symptom-tags" style="margin-top:4px">';
        data.flags.forEach(f => { html += `<span class="badge badge-red">${f.replace(/_/g, ' ')}</span>`; });
        html += '</div>';
    }
    result.innerHTML = html;
    show(result);
}

// --- Camera ---
let cameraStream = null;

async function startCamera() {
    const video = $('#camera-video');
    const placeholder = $('#camera-placeholder');
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
            audio: false,
        });
        video.srcObject = cameraStream;
        show(video);
        hide(placeholder);
        show($('#camera-controls'));
        hide($('#btn-start-camera'));
    } catch (err) {
        showAlert('Camera access denied. Please allow camera permissions.', 'danger');
    }
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(t => t.stop());
        cameraStream = null;
    }
    const video = $('#camera-video');
    video.srcObject = null;
    hide(video);
    show($('#camera-placeholder'));
    hide($('#camera-controls'));
    show($('#btn-start-camera'));
}

function capturePhoto() {
    const video = $('#camera-video');
    const canvas = $('#camera-canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
    const gallery = $('#photo-gallery');
    const timestamp = new Date().toLocaleTimeString();

    const photoHtml = `
        <div class="photo-card">
            <img src="${dataUrl}" alt="Capture" class="photo-thumb">
            <div class="photo-info">
                <div class="photo-time">${timestamp}</div>
                <button class="btn btn-small btn-secondary" onclick="downloadPhoto(this)">Save</button>
            </div>
        </div>
    `;
    gallery.insertAdjacentHTML('afterbegin', photoHtml);
    show(gallery);
    showAlert('Photo captured', 'success');
}

function downloadPhoto(btn) {
    const img = btn.closest('.photo-card').querySelector('img');
    const a = document.createElement('a');
    a.href = img.src;
    a.download = `ai-nurse-capture-${Date.now()}.jpg`;
    a.click();
}

function switchCameraFacing() {
    const video = $('#camera-video');
    const currentFacing = video.dataset.facing || 'environment';
    const newFacing = currentFacing === 'environment' ? 'user' : 'environment';
    video.dataset.facing = newFacing;
    stopCamera();
    // Restart with new facing
    navigator.mediaDevices.getUserMedia({
        video: { facingMode: newFacing, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
    }).then(stream => {
        cameraStream = stream;
        video.srcObject = stream;
        show(video);
        hide($('#camera-placeholder'));
        show($('#camera-controls'));
        hide($('#btn-start-camera'));
    }).catch(() => {
        showAlert('Could not switch camera', 'warning');
    });
}

// --- Alerts ---
function showAlert(message, type = 'info') {
    const container = $('#alerts');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    container.appendChild(alert);
    setTimeout(() => alert.remove(), 5000);
}

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    // Auth
    $('#form-register')?.addEventListener('submit', handleRegister);
    $('#form-login')?.addEventListener('submit', handleLogin);
    $('#btn-logout')?.addEventListener('click', logout);
    $('#link-to-register')?.addEventListener('click', () => showScreen('register'));
    $('#link-to-login')?.addEventListener('click', () => showScreen('login'));

    // Features
    $('#form-bmi')?.addEventListener('submit', handleBMI);
    $('#form-symptoms')?.addEventListener('submit', handleSymptomCheck);
    $('#form-vitals')?.addEventListener('submit', handleVitals);
    $('#form-triage')?.addEventListener('submit', handleTriage);

    // Camera
    $('#btn-start-camera')?.addEventListener('click', startCamera);
    $('#btn-capture')?.addEventListener('click', capturePhoto);
    $('#btn-stop-camera')?.addEventListener('click', stopCamera);
    $('#btn-switch-camera')?.addEventListener('click', switchCameraFacing);

    // Nav tabs
    $$('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            if (tab.dataset.screen !== 'camera') stopCamera();
            showScreen(tab.dataset.screen);
        });
    });

    // Pain slider
    const pain = $('#tri-pain');
    const display = $('#tri-pain-display');
    if (pain && display) {
        pain.addEventListener('input', () => { display.textContent = pain.value; });
    }

    // Symptom tags
    renderSymptomTags();

    // Auto-login via cookie — verify session with /auth/me
    if (currentUser) {
        api('/auth/me').then(user => {
            currentUser = user;
            localStorage.setItem('user', JSON.stringify(user));
            enterApp();
        }).catch(() => {
            currentUser = null;
            localStorage.removeItem('user');
            showScreen('login');
        });
    } else {
        showScreen('login');
    }
});
