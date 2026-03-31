# API Reference

Base URL: `http://localhost:8000/api/v1`

All endpoints return JSON. Protected endpoints require an `Authorization: Bearer <token>` header or an httpOnly cookie (set automatically on login).

---

## Authentication

### POST `/auth/register`
Register a new user account. All new users are assigned the `patient` role.

**Rate limit:** 5 requests/minute

**Request Body:**
```json
{
  "email": "patient@example.com",
  "password": "securepass123",
  "full_name": "John Doe"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "email": "patient@example.com",
  "full_name": "John Doe",
  "role": "patient",
  "is_active": true
}
```

### POST `/auth/login`
Authenticate and receive a JWT token. Also sets an httpOnly cookie.

**Rate limit:** 10 requests/minute

**Request Body:**
```json
{
  "email": "patient@example.com",
  "password": "securepass123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "patient@example.com",
    "full_name": "John Doe",
    "role": "patient",
    "is_active": true
  }
}
```

### POST `/auth/logout`
Clear the auth cookie.

**Response (200):**
```json
{"detail": "Logged out"}
```

### GET `/auth/me`
Get the current authenticated user's profile. **Requires:** authentication.

**Response (200):**
```json
{
  "id": "uuid",
  "email": "patient@example.com",
  "full_name": "John Doe",
  "role": "patient",
  "is_active": true
}
```

### GET `/auth/users`
List all users with optional role filter. **Requires:** admin role.

**Query Parameters:**
- `role` (string, optional) — Filter: `patient`, `nurse`, `doctor`, `admin`
- `limit` (int, default 20) — Page size (1-100)
- `offset` (int, default 0) — Pagination offset

**Response (200):**
```json
{
  "users": [
    {
      "id": "uuid",
      "email": "nurse@example.com",
      "full_name": "Jane Smith",
      "role": "nurse",
      "is_active": true
    }
  ],
  "total": 15
}
```

### PUT `/auth/users/{user_id}/role`
Update a user's role. Cannot change your own role. **Requires:** admin role.

**Request Body:**
```json
{
  "role": "nurse"
}
```

### PUT `/auth/users/{user_id}/deactivate`
Deactivate a user account. **Requires:** admin role.

### PUT `/auth/users/{user_id}/activate`
Reactivate a user account. **Requires:** admin role.

---

## Patients

### POST `/patients`
Register a new patient profile. **Requires:** nurse, doctor, or admin role.

**Request Body:**
```json
{
  "full_name": "John Doe",
  "date_of_birth": "1990-05-15",
  "gender": "male",
  "blood_type": "O+",
  "height_cm": 175.0,
  "weight_kg": 80.0,
  "allergies": "penicillin, sulfa",
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_phone": "+1234567890",
  "user_id": "uuid (optional — links to a user account)"
}
```

> **Note:** `allergies` is a string field (not an array). `emergency_contact_name` and `emergency_contact_phone` are flat fields (not a nested object).

**Response (201):**
```json
{
  "id": "uuid",
  "full_name": "John Doe",
  "date_of_birth": "1990-05-15",
  "gender": "male",
  "blood_type": "O+",
  "height_cm": 175.0,
  "weight_kg": 80.0,
  "allergies": "penicillin, sulfa",
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_phone": "+1234567890",
  "user_id": "uuid",
  "created_at": "2026-03-24T10:00:00",
  "updated_at": "2026-03-24T10:00:00"
}
```

### GET `/patients`
List all patients with pagination. **Requires:** nurse, doctor, or admin role.

**Query Parameters:**
- `limit` (int, default 20) — Page size (1-100)
- `offset` (int, default 0) — Pagination offset

### GET `/patients/{patient_id}`
Get patient details. **Requires:** authentication. Patients can only view their own linked record; nurses, doctors, and admins can view any.

### PUT `/patients/{patient_id}`
Update patient info. **Requires:** nurse, doctor, or admin role.

### DELETE `/patients/{patient_id}`
Delete a patient record. **Requires:** admin role.

### GET `/patients/{patient_id}/history`
Get patient visit history (triage assessments, symptom checks, vitals). **Requires:** authentication. Patients can only view their own history.

**Query Parameters:**
- `limit` (int, default 20) — Page size (1-100)
- `offset` (int, default 0) — Pagination offset
- `record_type` (string, optional) — Filter: `triage`, `symptom_check`, `vitals`

**Response (200):**
```json
{
  "patient_id": "uuid",
  "patient_name": "John Doe",
  "records": [
    {
      "id": "uuid",
      "record_type": "triage",
      "summary": "Urgent — Severe headache (priority 3)",
      "details": {
        "chief_complaint": "Severe headache",
        "priority_level": 3,
        "priority_label": "Urgent",
        "pain_scale": 6,
        "vitals": {
          "heart_rate": 75,
          "temperature_c": 36.8
        }
      },
      "created_at": "2026-03-24T14:30:00"
    }
  ],
  "total": 12
}
```

---

## Triage

### POST `/triage`
Submit a triage assessment and receive a priority classification. **Requires:** authentication.

**Request Body:**
```json
{
  "patient_id": "uuid (optional — omit for anonymous triage)",
  "patient_name": "John Doe",
  "chief_complaint": "Severe chest pain radiating to left arm",
  "symptoms": ["chest_pain", "shortness_of_breath", "sweating"],
  "symptom_duration": "30 minutes",
  "vitals": {
    "heart_rate": 110,
    "blood_pressure_systolic": 160,
    "blood_pressure_diastolic": 95,
    "temperature_c": 37.2,
    "respiratory_rate": 24,
    "oxygen_saturation": 94
  },
  "pain_scale": 9,
  "age": 55,
  "notes": "Patient appears distressed"
}
```

**Response (200):**
```json
{
  "id": "uuid (null if no patient_id provided)",
  "patient_name": "John Doe",
  "priority_level": 1,
  "priority_label": "Resuscitation",
  "priority_color": "red",
  "recommended_action": "Immediate cardiac evaluation. Activate code team.",
  "flags": ["symptom_chest_pain", "elevated_heart_rate", "low_o2_sat", "severe_pain"],
  "vitals_summary": {
    "heart_rate": "110 bpm — Tachycardia",
    "blood_pressure": "160/95 mmHg — Elevated",
    "temperature": "37.2°C — Normal",
    "oxygen_saturation": "94% — Low"
  }
}
```

### GET `/triage/queue`
View the current triage queue sorted by priority. **Requires:** nurse, doctor, or admin role.

**Query Parameters:**
- `status` (string, default "waiting") — Filter: `waiting`, `in_progress`, `completed`

**Response (200):**
```json
{
  "queue": [
    {
      "id": "uuid",
      "patient_id": "uuid",
      "patient_name": "John Doe",
      "priority_level": 1,
      "priority_label": "Resuscitation",
      "priority_color": "red",
      "chief_complaint": "Severe chest pain",
      "created_at": "2026-03-24T10:15:00",
      "wait_time_minutes": 2
    }
  ],
  "total": 5
}
```

### PUT `/triage/{triage_id}/status`
Update a triage record's status. **Requires:** nurse, doctor, or admin role.

**Query Parameters:**
- `status` (string, required) — New status: `waiting`, `in_progress`, `completed`

---

## Symptoms

### POST `/symptoms/check`
Analyze reported symptoms against 100+ conditions and suggest possible matches. **Requires:** authentication.

**Request Body:**
```json
{
  "patient_id": "uuid (optional — omit for anonymous check)",
  "symptoms": ["headache", "fever", "body_aches", "fatigue"],
  "duration_days": 3,
  "severity": "moderate",
  "age": 35,
  "additional_info": ""
}
```

> **Severity values:** `mild`, `moderate`, `severe`

**Response (200):**
```json
{
  "id": "uuid (null if no patient_id provided)",
  "possible_conditions": [
    {
      "condition": "Influenza",
      "probability": "high",
      "description": "Viral infection affecting the respiratory system",
      "category": "respiratory"
    },
    {
      "condition": "COVID-19",
      "probability": "moderate",
      "description": "Coronavirus respiratory illness",
      "category": "infectious"
    }
  ],
  "recommended_action": "Consult a healthcare provider for proper evaluation.",
  "urgency": "moderate",
  "disclaimer": "This is not a medical diagnosis. Please consult a healthcare professional for proper evaluation and treatment."
}
```

### GET `/symptoms/conditions`
List all known conditions in the symptom checker database. **No authentication required.**

**Query Parameters:**
- `category` (string, optional) — Filter by category: `respiratory`, `cardiac`, `gastrointestinal`, `neurological`, `musculoskeletal`, `infectious`, `dermatological`, `urological`, `endocrine`, `psychiatric`, `ophthalmological`, `ent`

**Response (200):**
```json
{
  "conditions": [
    {
      "condition": "Influenza",
      "category": "respiratory",
      "description": "Viral infection affecting the respiratory system",
      "required_symptoms": ["body_aches", "cough", "fatigue", "fever"]
    }
  ],
  "total": 105
}
```

---

## Health Metrics

### POST `/metrics/bmi`
Calculate BMI from height and weight. **No authentication required.**

**Request Body:**
```json
{
  "height_cm": 175.0,
  "weight_kg": 80.0
}
```

**Response (200):**
```json
{
  "bmi": 26.12,
  "category": "Overweight",
  "healthy_weight_range": {
    "min_kg": 56.7,
    "max_kg": 76.6
  },
  "interpretation": "Your BMI falls in the overweight range. Consider consulting a healthcare provider for personalized advice."
}
```

### POST `/metrics/vitals`
Record patient vital signs with real-time assessment. Assessments are stored immutably with the record. **Requires:** nurse or doctor role.

**Request Body:**
```json
{
  "patient_id": "uuid",
  "heart_rate": 72,
  "blood_pressure_systolic": 120,
  "blood_pressure_diastolic": 80,
  "temperature_c": 36.8,
  "respiratory_rate": 16,
  "oxygen_saturation": 98,
  "blood_glucose_mg_dl": 95,
  "notes": ""
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "patient_id": "uuid",
  "readings": {
    "heart_rate": {"value": 72, "status": "normal"},
    "blood_pressure": {"value": "120/80", "status": "normal"},
    "temperature": {"value": 36.8, "status": "normal"},
    "respiratory_rate": {"value": 16, "status": "normal"},
    "oxygen_saturation": {"value": 98, "status": "normal"},
    "blood_glucose": {"value": 95, "status": "normal"}
  },
  "alerts": [],
  "notes": "",
  "recorded_by": "uuid",
  "recorded_at": "2026-03-24T10:30:00"
}
```

### GET `/metrics/vitals/{patient_id}`
Get vitals history for a patient. Returns stored assessments (not recomputed). **Requires:** authentication.

**Query Parameters:**
- `limit` (int, default 20) — Page size (1-100)
- `offset` (int, default 0) — Pagination offset

---

## Medications

### POST `/medications/reminders`
Create a medication reminder. **Requires:** nurse or doctor role.

**Request Body:**
```json
{
  "patient_id": "uuid",
  "medication_name": "Metformin",
  "dosage": "500mg",
  "frequency": "twice_daily",
  "times": ["08:00", "20:00"],
  "start_date": "2026-03-24",
  "end_date": "2026-06-24",
  "instructions": "Take with food"
}
```

> **Frequency values:** `once_daily`, `twice_daily`, `three_times_daily`, `four_times_daily`, `as_needed`

**Response (201):**
```json
{
  "id": "uuid",
  "patient_id": "uuid",
  "medication_name": "Metformin",
  "dosage": "500mg",
  "frequency": "twice_daily",
  "times": ["08:00:00", "20:00:00"],
  "start_date": "2026-03-24",
  "end_date": "2026-06-24",
  "instructions": "Take with food",
  "status": "active"
}
```

### GET `/medications/patient/{patient_id}`
List all medications for a patient. **Requires:** authentication.

**Response (200):**
```json
{
  "patient_id": "uuid",
  "medications": [...],
  "total": 3
}
```

### DELETE `/medications/reminders/{reminder_id}`
Cancel a medication reminder. **Requires:** nurse or doctor role.

---

## Audit Log

### GET `/audit`
View audit log entries. **Requires:** admin role.

**Query Parameters:**
- `limit` (int, default 50)
- `offset` (int, default 0)

---

## Error Responses

All errors use FastAPI's standard format:

```json
{
  "detail": "Error message here"
}
```

For validation errors (422):
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "field_name"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

### Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | Deleted (no content) |
| 400 | Bad Request — invalid input or business rule violation |
| 401 | Unauthorized — missing or invalid token |
| 403 | Forbidden — insufficient permissions or ownership violation |
| 404 | Not Found |
| 422 | Validation Error — Pydantic schema validation failed |
| 429 | Rate Limited — too many requests |
| 500 | Internal Server Error |
