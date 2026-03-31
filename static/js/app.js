const API = '/api/v1';
let currentUser = JSON.parse(localStorage.getItem('user') || 'null');

// --- XSS prevention ---
function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;');
}

// --- API helpers ---
async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest', ...options.headers };
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

// --- Loading state helpers ---
function setLoading(btn, loading) {
    if (loading) {
        btn.dataset.originalText = btn.textContent;
        btn.textContent = 'Loading...';
        btn.disabled = true;
        btn.setAttribute('aria-busy', 'true');
    } else {
        btn.textContent = btn.dataset.originalText || btn.textContent;
        btn.disabled = false;
        btn.removeAttribute('aria-busy');
    }
}

// --- Screen management ---
function showScreen(name) {
    $$('.screen').forEach(s => hide(s));
    show($(`#screen-${name}`));
    $$('.nav-tab').forEach(t => t.classList.remove('active'));
    const tab = $(`.nav-tab[data-screen="${name}"]`);
    if (tab) tab.classList.add('active');
    if (name === 'dashboard') loadDashboard();
    if (name === 'patients') loadPatients($('#patient-search')?.value?.trim() || '', 0);
}

// --- Auth ---
async function handleRegister(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
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
        showAlert(err.detail || 'Registration failed', 'danger');
    } finally {
        setLoading(btn, false);
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
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
        showAlert(err.detail || 'Login failed', 'danger');
    } finally {
        setLoading(btn, false);
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
    let html = `<div class="greeting">Welcome back, <strong>${escapeHtml(currentUser.full_name)}</strong></div>`;

    // Quick actions
    html += '<div class="section-title" style="margin-top:16px">Quick Actions</div>';
    html += '<div class="quick-actions">';
    html += '<button class="action-card" onclick="showScreen(\'symptoms\')"><div class="action-icon">🔍</div><div>Symptom Check</div></button>';
    html += '<button class="action-card" onclick="showScreen(\'bmi\')"><div class="action-icon">⚖️</div><div>BMI Calculator</div></button>';
    if (isStaff()) {
        html += '<button class="action-card" onclick="showScreen(\'triage\')"><div class="action-icon">🚨</div><div>Triage</div></button>';
        html += '<button class="action-card" onclick="showScreen(\'vitals\')"><div class="action-icon">💓</div><div>Record Vitals</div></button>';
        html += '<button class="action-card" onclick="showScreen(\'camera\')"><div class="action-icon">📷</div><div>Camera</div></button>';
        html += '<button class="action-card" onclick="showScreen(\'patients\')"><div class="action-icon">👥</div><div>Patients</div></button>';
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
                            <span class="card-title">${escapeHtml(item.patient_name)}</span>
                            <span class="badge badge-${escapeHtml(item.priority_color)}">Level ${escapeHtml(item.priority_level)}</span>
                        </div>
                        <div class="card-meta">${escapeHtml(item.chief_complaint)}</div>
                        <div class="card-meta">Waiting: ${escapeHtml(item.wait_time_minutes)} min</div>
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
                html += `<span class="stat-chip">${escapeHtml(cat)}: ${escapeHtml(count)}</span>`;
            }
            html += '</div>';
        } catch (e) {}
    }

    // Patient view: self-registration + health tips
    if (role === 'patient') {
        if (!hasPatientProfile) {
            html += renderSelfRegistrationCard();
        }
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

    // Bind self-registration form if present
    const selfRegForm = $('#form-self-register');
    if (selfRegForm) {
        selfRegForm.addEventListener('submit', handleSelfRegister);
    }
}

function isStaff() {
    return ['nurse', 'doctor', 'admin'].includes(currentUser?.role);
}

// --- BMI ---
function setBMIUnit(unit) {
    $('#bmi-unit-system').value = unit;
    const metricBtn = $('#bmi-unit-metric');
    const imperialBtn = $('#bmi-unit-imperial');
    const metricFields = $('#bmi-metric-fields');
    const imperialFields = $('#bmi-imperial-fields');
    if (unit === 'imperial') {
        imperialBtn.className = 'btn btn-primary btn-sm';
        metricBtn.className = 'btn btn-outline btn-sm';
        metricFields.classList.add('hidden');
        imperialFields.classList.remove('hidden');
    } else {
        metricBtn.className = 'btn btn-primary btn-sm';
        imperialBtn.className = 'btn btn-outline btn-sm';
        imperialFields.classList.add('hidden');
        metricFields.classList.remove('hidden');
    }
}

async function handleBMI(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
    try {
        const unitSystem = $('#bmi-unit-system').value;
        let body;
        if (unitSystem === 'imperial') {
            body = {
                unit_system: 'imperial',
                height_ft: parseFloat($('#bmi-height-ft').value),
                height_in: parseFloat($('#bmi-height-in').value) || 0,
                weight_lbs: parseFloat($('#bmi-weight-lbs').value),
            };
        } else {
            body = {
                unit_system: 'metric',
                height_cm: parseFloat($('#bmi-height').value),
                weight_kg: parseFloat($('#bmi-weight').value),
            };
        }
        const data = await api('/metrics/bmi', {
            method: 'POST',
            body: JSON.stringify(body),
        });
        const result = $('#bmi-result');
        const colorMap = {
            'severe underweight': 'var(--danger)', 'moderate underweight': 'var(--warning)',
            'underweight': 'var(--warning)', 'normal': 'var(--success)',
            'overweight': 'var(--warning)', 'obese class I': 'var(--danger)',
            'obese class II': 'var(--danger)', 'obese class III': 'var(--danger)',
        };
        const rangeText = data.unit_system === 'imperial' && data.healthy_weight_range.min_lbs
            ? `${data.healthy_weight_range.min_lbs}–${data.healthy_weight_range.max_lbs} lbs`
            : `${data.healthy_weight_range.min_kg}–${data.healthy_weight_range.max_kg} kg`;
        result.innerHTML = `
            <div class="bmi-result">
                <div class="bmi-value" style="color:${colorMap[data.category] || 'inherit'}">${escapeHtml(data.bmi)}</div>
                <div class="bmi-category">${escapeHtml(data.category)}</div>
                <p style="margin-top:12px;color:var(--gray-500);font-size:14px">${escapeHtml(data.interpretation)}</p>
                <p style="margin-top:8px;font-size:13px;color:var(--gray-500)">
                    Healthy range: ${rangeText}
                </p>
            </div>
        `;
        show(result);
    } catch (err) {
        showAlert(err.detail || 'BMI calculation failed', 'danger');
    } finally {
        setLoading(btn, false);
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
    'palpitations', 'blurred_vision', 'confusion', 'tremor',
    'weight_loss', 'weight_gain', 'night_sweats', 'anxiety',
    'insomnia', 'sadness', 'loss_of_interest', 'ear_pain',
    'eye_pain', 'eye_redness', 'hoarseness', 'difficulty_swallowing',
    'heartburn', 'bloody_stool', 'constipation', 'leg_swelling',
    'fainting', 'seizure', 'slurred_speech', 'vision_changes',
    'excessive_thirst', 'cold_intolerance', 'hair_loss',
    'hives', 'nasal_congestion', 'facial_pain', 'tinnitus',
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
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
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
        showAlert(err.detail || 'Symptom check failed', 'danger');
    } finally {
        setLoading(btn, false);
    }
}

function renderSymptomResults(data) {
    const result = $('#symptom-result');
    const urgencyClass = { emergency: 'danger', high: 'danger', moderate: 'warning', low: 'info' };
    let html = `<div class="alert alert-${urgencyClass[data.urgency] || 'info'}">
        Urgency: <strong>${escapeHtml(data.urgency.toUpperCase())}</strong> — ${escapeHtml(data.recommended_action)}
    </div>`;
    if (data.possible_conditions.length > 0) {
        html += '<div class="result-header">Possible Conditions</div>';
        data.possible_conditions.forEach(c => {
            const probColor = { high: 'var(--danger)', moderate: 'var(--warning)', low: 'var(--gray-500)' };
            html += `<div class="condition-item">
                <div class="condition-name">${escapeHtml(c.condition)}
                    <span class="condition-prob" style="color:${probColor[c.probability]}">(${escapeHtml(c.probability)})</span>
                </div>
                <div class="condition-desc">${escapeHtml(c.description)}</div>
            </div>`;
        });
    } else {
        html += '<p style="color:var(--gray-500)">No matching conditions found.</p>';
    }
    html += `<div class="disclaimer">${escapeHtml(data.disclaimer)}</div>`;
    result.innerHTML = html;
    show(result);
}

// --- Vitals ---
async function handleVitals(e) {
    e.preventDefault();
    const patientId = $('#vitals-patient-id').value.trim();
    if (!patientId) { showAlert('Patient ID is required', 'warning'); return; }
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
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
    } finally {
        setLoading(btn, false);
    }
}

function renderVitalsResult(data) {
    const result = $('#vitals-result');
    let html = '';
    if (data.alerts.length > 0) {
        html += data.alerts.map(a => `<div class="alert alert-danger">${escapeHtml(a)}</div>`).join('');
    } else {
        html += '<div class="alert alert-success">All vitals within normal range</div>';
    }
    html += '<div class="vitals-grid">';
    for (const [key, reading] of Object.entries(data.readings)) {
        const label = key.replace(/_/g, ' ').replace('blood pressure ', 'BP ');
        html += `<div class="vital-item">
            <div class="vital-value">${escapeHtml(reading.value)}</div>
            <div class="vital-label">${escapeHtml(label)}</div>
            <div class="vital-status ${escapeHtml(reading.status)}">${escapeHtml(reading.status.replace(/_/g, ' '))}</div>
        </div>`;
    }
    html += '</div>';
    result.innerHTML = html;
    show(result);
}

// --- Triage ---
async function handleTriage(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
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
    } finally {
        setLoading(btn, false);
    }
}

function renderTriageResult(data) {
    const result = $('#triage-result');
    const badgeClass = `badge-${data.priority_color}`;
    let html = `
        <div style="text-align:center;padding:16px 0">
            <div class="badge ${badgeClass}" style="font-size:16px;padding:6px 16px">
                Level ${escapeHtml(data.priority_level)} — ${escapeHtml(data.priority_label)}
            </div>
            <p style="margin-top:12px;font-size:14px">${escapeHtml(data.recommended_action)}</p>
        </div>
    `;
    if (data.flags.length > 0) {
        html += '<div style="margin-top:8px"><strong>Flags:</strong></div>';
        html += '<div class="symptom-tags" style="margin-top:4px">';
        data.flags.forEach(f => { html += `<span class="badge badge-red">${escapeHtml(f.replace(/_/g, ' '))}</span>`; });
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

// --- Patient Management ---
let patientPage = 0;
const PATIENTS_PER_PAGE = 20;
let patientSearchTimeout = null;

async function loadPatients(search = '', offset = 0) {
    const container = $('#patient-list');
    container.innerHTML = '<div class="loading">Loading patients...</div>';
    try {
        let url = `/patients?limit=${PATIENTS_PER_PAGE}&offset=${offset}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        const data = await api(url);
        if (data.patients.length === 0) {
            container.innerHTML = '<div class="card"><p style="color:var(--gray-500);text-align:center">No patients found</p></div>';
        } else {
            container.innerHTML = data.patients.map(p => `
                <div class="patient-card" data-id="${escapeHtml(p.id)}" tabindex="0" role="button" aria-label="View patient ${escapeHtml(p.full_name)}">
                    <div class="patient-card-name">${escapeHtml(p.full_name)}</div>
                    <div class="patient-card-meta">DOB: ${escapeHtml(p.date_of_birth)} &middot; ${escapeHtml(p.gender)}</div>
                </div>
            `).join('');
            container.querySelectorAll('.patient-card').forEach(card => {
                card.addEventListener('click', () => viewPatient(card.dataset.id));
                card.addEventListener('keydown', (e) => { if (e.key === 'Enter') viewPatient(card.dataset.id); });
            });
        }
        renderPatientPagination(data.total, offset);
    } catch (err) {
        container.innerHTML = '<div class="alert alert-danger">Failed to load patients</div>';
    }
}

function renderPatientPagination(total, offset) {
    const pag = $('#patient-pagination');
    if (total <= PATIENTS_PER_PAGE) { pag.innerHTML = ''; return; }
    const page = Math.floor(offset / PATIENTS_PER_PAGE) + 1;
    const totalPages = Math.ceil(total / PATIENTS_PER_PAGE);
    pag.innerHTML = `
        <button ${offset === 0 ? 'disabled' : ''} id="pg-prev">Previous</button>
        <span>Page ${page} of ${totalPages}</span>
        <button ${offset + PATIENTS_PER_PAGE >= total ? 'disabled' : ''} id="pg-next">Next</button>
    `;
    const search = $('#patient-search').value.trim();
    $('#pg-prev')?.addEventListener('click', () => {
        patientPage = Math.max(0, offset - PATIENTS_PER_PAGE);
        loadPatients(search, patientPage);
    });
    $('#pg-next')?.addEventListener('click', () => {
        patientPage = offset + PATIENTS_PER_PAGE;
        loadPatients(search, patientPage);
    });
}

async function viewPatient(id) {
    showScreen('patient-detail');
    const container = $('#patient-detail-content');
    container.innerHTML = '<div class="loading">Loading patient details...</div>';
    try {
        const p = await api(`/patients/${encodeURIComponent(id)}`);
        let html = `
            <div class="patient-detail-header">
                <div class="patient-detail-name">${escapeHtml(p.full_name)}</div>
                <div class="card-meta">ID: ${escapeHtml(p.id)}</div>
            </div>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Date of Birth</div>
                    <div class="detail-value">${escapeHtml(p.date_of_birth)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Gender</div>
                    <div class="detail-value">${escapeHtml(p.gender)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Blood Type</div>
                    <div class="detail-value">${escapeHtml(p.blood_type || 'N/A')}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Allergies</div>
                    <div class="detail-value">${escapeHtml(p.allergies || 'None')}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Emergency Contact</div>
                    <div class="detail-value">${escapeHtml(p.emergency_contact_name || 'N/A')}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Emergency Phone</div>
                    <div class="detail-value">${escapeHtml(p.emergency_contact_phone || 'N/A')}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Created</div>
                    <div class="detail-value">${escapeHtml(new Date(p.created_at).toLocaleDateString())}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Updated</div>
                    <div class="detail-value">${escapeHtml(new Date(p.updated_at).toLocaleDateString())}</div>
                </div>
            </div>
            <button class="btn btn-primary btn-small" style="margin-top:16px" id="btn-view-history" data-patient-id="${escapeHtml(p.id)}">View History</button>
            <div id="patient-history-section" class="history-section"></div>
        `;
        container.innerHTML = html;
        $('#btn-view-history').addEventListener('click', () => loadPatientHistory(p.id));
    } catch (err) {
        container.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.detail || 'Failed to load patient')}</div>`;
    }
}

async function loadPatientHistory(patientId) {
    const section = $('#patient-history-section');
    section.innerHTML = '<div class="loading">Loading history...</div>';
    try {
        const data = await api(`/patients/${encodeURIComponent(patientId)}/history?limit=50`);
        if (data.records.length === 0) {
            section.innerHTML = '<p style="color:var(--gray-500);margin-top:12px;text-align:center">No history records found</p>';
            return;
        }
        let html = `<div class="section-title" style="margin-top:16px">History (${escapeHtml(data.total)} records)</div>`;
        data.records.forEach(r => {
            html += `
                <div class="history-record">
                    <div class="history-record-type">${escapeHtml(r.record_type)}</div>
                    <div class="history-record-summary">${escapeHtml(r.summary)}</div>
                    <div class="history-record-date">${escapeHtml(new Date(r.created_at).toLocaleString())}</div>
                </div>
            `;
        });
        section.innerHTML = html;
    } catch (err) {
        section.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.detail || 'Failed to load history')}</div>`;
    }
}

function openCreatePatientModal() {
    show($('#modal-create-patient'));
    $('#cp-name').focus();
}

function closeCreatePatientModal() {
    hide($('#modal-create-patient'));
    $('#form-create-patient').reset();
}

async function handleCreatePatient(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
    try {
        const body = {
            full_name: $('#cp-name').value.trim(),
            date_of_birth: $('#cp-dob').value,
            gender: $('#cp-gender').value,
        };
        const blood = $('#cp-blood').value.trim();
        if (blood) body.blood_type = blood;
        const allergies = $('#cp-allergies').value.trim();
        if (allergies) body.allergies = allergies;
        const ecName = $('#cp-ec-name').value.trim();
        if (ecName) body.emergency_contact_name = ecName;
        const ecPhone = $('#cp-ec-phone').value.trim();
        if (ecPhone) body.emergency_contact_phone = ecPhone;

        await api('/patients', { method: 'POST', body: JSON.stringify(body) });
        showAlert('Patient created successfully', 'success');
        closeCreatePatientModal();
        loadPatients($('#patient-search').value.trim(), 0);
    } catch (err) {
        showAlert(err.detail || 'Failed to create patient', 'danger');
    } finally {
        setLoading(btn, false);
    }
}

// --- Patient Self-Registration ---
let patientProfileChecked = false;
let hasPatientProfile = false;

async function checkPatientProfile() {
    if (currentUser?.role !== 'patient' || patientProfileChecked) return;
    patientProfileChecked = true;
    try {
        // Check if user has a linked patient record by searching via the users endpoint
        // We attempt to load patients/me — if 404, they need to register
        const res = await fetch(`${API}/patients?limit=1`, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        // Patients can't list patients (403), so we use a different approach:
        // Try to see if user_id is linked to any patient by checking for a 403/404
        hasPatientProfile = false;
    } catch (e) {
        hasPatientProfile = false;
    }
}

function renderSelfRegistrationCard() {
    if (currentUser?.role !== 'patient' || hasPatientProfile) return '';
    return `
        <div class="profile-card" id="patient-profile-card">
            <div class="profile-card-title">Complete Your Profile</div>
            <div class="profile-card-desc">Set up your patient profile to enable personalized care and medical history tracking.</div>
            <button class="btn btn-primary btn-small" onclick="showSelfRegistrationForm()">Complete Profile</button>
        </div>
        <div class="card hidden" id="self-reg-form-container">
            <h4 style="margin-bottom:12px;font-size:16px">Patient Profile</h4>
            <form id="form-self-register" aria-label="Patient self-registration form">
                <div class="form-group">
                    <label for="sr-name">Full Name *</label>
                    <input type="text" id="sr-name" required maxlength="200" value="${escapeHtml(currentUser.full_name)}">
                </div>
                <div class="form-group">
                    <label for="sr-dob">Date of Birth *</label>
                    <input type="date" id="sr-dob" required>
                </div>
                <div class="form-group">
                    <label for="sr-gender">Gender *</label>
                    <select id="sr-gender" required>
                        <option value="">Select gender</option>
                        <option value="male">Male</option>
                        <option value="female">Female</option>
                        <option value="other">Other</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="sr-blood">Blood Type</label>
                    <input type="text" id="sr-blood" placeholder="e.g. A+" maxlength="5">
                </div>
                <div class="form-group">
                    <label for="sr-allergies">Allergies</label>
                    <textarea id="sr-allergies" rows="2" placeholder="e.g. Penicillin, Peanuts" maxlength="1000"></textarea>
                </div>
                <div class="form-group">
                    <label for="sr-ec-name">Emergency Contact Name</label>
                    <input type="text" id="sr-ec-name" maxlength="200">
                </div>
                <div class="form-group">
                    <label for="sr-ec-phone">Emergency Contact Phone</label>
                    <input type="tel" id="sr-ec-phone" maxlength="20">
                </div>
                <button type="submit" class="btn btn-primary">Save Profile</button>
            </form>
        </div>
    `;
}

function showSelfRegistrationForm() {
    hide($('#patient-profile-card'));
    show($('#self-reg-form-container'));
    $('#sr-name').focus();
}

async function handleSelfRegister(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setLoading(btn, true);
    try {
        const body = {
            full_name: $('#sr-name').value.trim(),
            date_of_birth: $('#sr-dob').value,
            gender: $('#sr-gender').value,
        };
        const blood = $('#sr-blood').value.trim();
        if (blood) body.blood_type = blood;
        const allergies = $('#sr-allergies').value.trim();
        if (allergies) body.allergies = allergies;
        const ecName = $('#sr-ec-name').value.trim();
        if (ecName) body.emergency_contact_name = ecName;
        const ecPhone = $('#sr-ec-phone').value.trim();
        if (ecPhone) body.emergency_contact_phone = ecPhone;

        await api('/patients/me', { method: 'POST', body: JSON.stringify(body) });
        hasPatientProfile = true;
        showAlert('Profile saved successfully!', 'success');
        loadDashboard();
    } catch (err) {
        if (err.status === 409) {
            hasPatientProfile = true;
            showAlert('Profile already exists.', 'info');
            loadDashboard();
        } else {
            showAlert(err.detail || 'Failed to save profile', 'danger');
        }
    } finally {
        setLoading(btn, false);
    }
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

    // Patient management
    $('#btn-create-patient')?.addEventListener('click', openCreatePatientModal);
    $('#btn-close-create-patient')?.addEventListener('click', closeCreatePatientModal);
    $('#btn-cancel-create-patient')?.addEventListener('click', closeCreatePatientModal);
    $('#form-create-patient')?.addEventListener('submit', handleCreatePatient);
    $('#btn-back-patients')?.addEventListener('click', () => showScreen('patients'));
    $('#modal-create-patient')?.addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeCreatePatientModal();
    });

    // Patient search with debounce
    const patientSearch = $('#patient-search');
    if (patientSearch) {
        patientSearch.addEventListener('input', () => {
            clearTimeout(patientSearchTimeout);
            patientSearchTimeout = setTimeout(() => {
                patientPage = 0;
                loadPatients(patientSearch.value.trim(), 0);
            }, 300);
        });
    }

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
