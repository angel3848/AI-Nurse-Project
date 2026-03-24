const API = '/api/v1';
let token = localStorage.getItem('token');
let currentUser = JSON.parse(localStorage.getItem('user') || 'null');

// --- API helpers ---
async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API}${path}`, { ...options, headers });
    if (res.status === 204) return null;
    const data = await res.json();
    if (!res.ok) throw { status: res.status, detail: data.detail || 'Request failed' };
    return data;
}

// --- DOM helpers ---
const $ = (sel) => document.querySelector(sel);
const show = (el) => el.classList.remove('hidden');
const hide = (el) => el.classList.add('hidden');

// --- Screen management ---
function showScreen(name) {
    document.querySelectorAll('.screen').forEach(s => hide(s));
    show($(`#screen-${name}`));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    const tab = $(`.nav-tab[data-screen="${name}"]`);
    if (tab) tab.classList.add('active');
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
        token = data.access_token;
        currentUser = data.user;
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(currentUser));
        enterApp();
    } catch (err) {
        showAlert(err.detail, 'danger');
    }
}

function logout() {
    token = null;
    currentUser = null;
    localStorage.removeItem('token');
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
    showScreen('symptoms');
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
        result.innerHTML = `
            <div class="bmi-result">
                <div class="bmi-value">${data.bmi}</div>
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
    if (!patientId) {
        showAlert('Patient ID is required', 'warning');
        return;
    }
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
    // Auth forms
    $('#form-register')?.addEventListener('submit', handleRegister);
    $('#form-login')?.addEventListener('submit', handleLogin);
    $('#btn-logout')?.addEventListener('click', logout);
    $('#link-to-register')?.addEventListener('click', () => showScreen('register'));
    $('#link-to-login')?.addEventListener('click', () => showScreen('login'));

    // Feature forms
    $('#form-bmi')?.addEventListener('submit', handleBMI);
    $('#form-symptoms')?.addEventListener('submit', handleSymptomCheck);
    $('#form-vitals')?.addEventListener('submit', handleVitals);
    $('#form-triage')?.addEventListener('submit', handleTriage);

    // Nav tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => showScreen(tab.dataset.screen));
    });

    // Symptom tags
    renderSymptomTags();

    // Auto-login
    if (token && currentUser) {
        enterApp();
    } else {
        showScreen('login');
    }
});
