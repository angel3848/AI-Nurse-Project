# API Reference

Base URL: `http://localhost:8000/api/v1`

All endpoints return JSON. Protected endpoints require an `Authorization: Bearer <token>` header or an httpOnly cookie (set automatically on login). All responses include an `X-Correlation-ID` header for request tracing.

---

## Authentication

### POST `/auth/register`
Register a new user account. All new users are assigned the `patient` role.

**Rate limit:** 5 requests/minute

**Request Body:**
```json
{
  "email": "patient@example.com",
  "password": "SecurePass1",
  "full_name": "John Doe"
}
```

> **Password requirements:** Minimum 8 characters, maximum 128 characters. Must contain at least one uppercase letter, one lowercase letter, and one digit.

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

Accounts are locked after 5 consecutive failed login attempts for 15 minutes (HTTP 423).

**Rate limit:** 10 requests/minute

**Request Body:**
```json
{
  "email": "patient@example.com",
  "password": "SecurePass1"
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

**Error (423) -- Account locked:**
```json
{
  "detail": "Account is temporarily locked due to too many failed login attempts. Try again later."
}
```

### POST `/auth/logout`
Clear the auth cookie and blacklist the current JWT token.

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

### POST `/auth/forgot-password`
Request a password reset token. Always returns 200 regardless of whether the email exists (prevents user enumeration).

**Rate limit:** 5 requests/minute

**Request Body:**
```json
{
  "email": "patient@example.com"
}
```

**Response (200):**
```json
{
  "detail": "If that email exists, a reset link has been sent"
}
```

> **Note:** The reset token is stored in the database. In production, it would be sent via email (requires SMTP configuration). Tokens expire after 30 minutes.

### POST `/auth/reset-password`
Reset a password using a valid reset token.

**Request Body:**
```json
{
  "token": "reset-token-from-email",
  "new_password": "NewSecurePass1"
}
```

> **Password requirements:** Same as registration -- minimum 8 characters, at least one uppercase letter, one lowercase letter, and one digit.

**Response (200):**
```json
{
  "detail": "Password has been reset successfully"
}
```

**Error (400):**
```json
{
  "detail": "Invalid or expired reset token"
}
```

### GET `/auth/users`
List all users with optional role filter. **Requires:** admin role.

**Query Parameters:**
- `role` (string, optional) -- Filter: `patient`, `nurse`, `doctor`, `admin`
- `limit` (int, default 20) -- Page size (1-100)
- `offset` (int, default 0) -- Pagination offset

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

> **Valid roles:** `patient`, `nurse`, `doctor`, `admin`

### PUT `/auth/users/{user_id}/deactivate`
Deactivate a user account. Blacklists the user's token. **Requires:** admin role.

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
  "allergies": ["penicillin", "sulfa"],
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_phone": "+1234567890",
  "user_id": "uuid (optional -- links to a user account)"
}
```

> **Note:** `allergies` is a JSON array of strings (not a plain string). Pass `null` or omit if no allergies.

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
  "allergies": ["penicillin", "sulfa"],
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_phone": "+1234567890",
  "user_id": "uuid",
  "created_at": "2026-03-31T10:00:00",
  "updated_at": "2026-03-31T10:00:00"
}
```

### GET `/patients`
List all patients with pagination and optional search. **Requires:** nurse, doctor, or admin role. Soft-deleted patients are excluded.

**Query Parameters:**
- `limit` (int, default 20) -- Page size (1-100)
- `offset` (int, default 0) -- Pagination offset
- `search` (string, optional, max 200 chars) -- Filter by patient name (case-insensitive partial match)

**Response (200):**
```json
{
  "patients": [
    {
      "id": "uuid",
      "full_name": "John Doe",
      "date_of_birth": "1990-05-15",
      "gender": "male",
      "blood_type": "O+",
      "height_cm": 175.0,
      "weight_kg": 80.0,
      "allergies": ["penicillin", "sulfa"],
      "emergency_contact_name": "Jane Doe",
      "emergency_contact_phone": "+1234567890",
      "user_id": "uuid",
      "created_at": "2026-03-31T10:00:00",
      "updated_at": "2026-03-31T10:00:00"
    }
  ],
  "total": 42
}
```

### POST `/patients/me`
Allow a patient-role user to create their own patient record. Links the record to the authenticated user automatically (no `user_id` field in the request). Returns 409 if a patient record already exists for the user. **Requires:** authentication with `patient` role.

**Request Body:**
```json
{
  "full_name": "John Doe",
  "date_of_birth": "1990-05-15",
  "gender": "male",
  "blood_type": "O+",
  "height_cm": 175.0,
  "weight_kg": 80.0,
  "allergies": ["penicillin"],
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_phone": "+1234567890"
}
```

**Response (201):** Same as `POST /patients`.

**Error (409):**
```json
{
  "detail": "Patient record already exists"
}
```

### GET `/patients/{patient_id}`
Get patient details. **Requires:** authentication. Patients can only view their own linked record; nurses, doctors, and admins can view any.

### PUT `/patients/{patient_id}`
Update patient info. Only provided fields are updated (partial update). **Requires:** nurse, doctor, or admin role.

**Request Body (all fields optional):**
```json
{
  "full_name": "John Doe Updated",
  "blood_type": "A+",
  "height_cm": 176.0,
  "weight_kg": 78.0,
  "allergies": ["penicillin", "ibuprofen"],
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_phone": "+1234567890",
  "user_id": "uuid"
}
```

### DELETE `/patients/{patient_id}`
Soft-delete a patient record (sets `is_deleted = true`). The record is preserved in the database but excluded from all queries. **Requires:** admin role.

**Response:** 204 No Content

### GET `/patients/{patient_id}/history`
Get patient visit history (triage assessments, symptom checks, vitals). **Requires:** authentication. Patients can only view their own history.

**Query Parameters:**
- `limit` (int, default 20) -- Page size (1-100)
- `offset` (int, default 0) -- Pagination offset
- `record_type` (string, optional) -- Filter: `triage`, `symptom_check`, `vitals`

**Response (200):**
```json
{
  "patient_id": "uuid",
  "patient_name": "John Doe",
  "records": [
    {
      "id": "uuid",
      "record_type": "triage",
      "summary": "Urgent -- Severe headache (priority 3)",
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
      "created_at": "2026-03-31T14:30:00"
    }
  ],
  "total": 12
}
```

---

## Triage

### POST `/triage`
Submit a triage assessment and receive a priority classification. **Requires:** authentication.

When a `patient_id` is provided, the record is persisted and a WebSocket notification is broadcast to all connected clients.

**Request Body:**
```json
{
  "patient_id": "uuid (optional -- omit for anonymous triage)",
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
    "heart_rate": "110 bpm -- Tachycardia",
    "blood_pressure": "160/95 mmHg -- Elevated",
    "temperature": "37.2C -- Normal",
    "oxygen_saturation": "94% -- Low"
  }
}
```

### GET `/triage/queue`
View the current triage queue sorted by priority. **Requires:** nurse, doctor, or admin role.

**Query Parameters:**
- `status` (string, default "waiting") -- Filter: `waiting`, `in_progress`, `completed`
- `limit` (int, default 50, max 200) -- Page size
- `offset` (int, default 0) -- Pagination offset

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
      "created_at": "2026-03-31T10:15:00",
      "wait_time_minutes": 2
    }
  ],
  "total": 5
}
```

### PUT `/triage/{triage_id}/status`
Update a triage record's status. Broadcasts a WebSocket notification on change. **Requires:** nurse, doctor, or admin role.

**Query Parameters:**
- `status` (string, required) -- New status: `waiting`, `in_progress`, `completed`

### WebSocket `/ws/triage-queue`
Real-time triage queue updates. Connects via WebSocket and receives JSON messages whenever the queue changes (new triage submitted or status updated).

**Connection:** `ws://localhost:8000/ws/triage-queue?token=optional-jwt`

**Message format (server to client):**
```json
{
  "event": "queue_updated"
}
```

Clients should re-fetch the queue via `GET /triage/queue` when they receive this event. The optional `token` query parameter can be used for authentication verification.

---

## Symptoms

### POST `/symptoms/check`
Analyze reported symptoms against 100+ conditions and suggest possible matches. When AI analysis is enabled, includes an additional AI-powered clinical analysis from Claude. **Requires:** authentication.

**Request Body:**
```json
{
  "patient_id": "uuid (optional -- omit for anonymous check)",
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
  "ai_analysis": "Based on the symptoms presented... (only present when AI_ANALYSIS_ENABLED=true)",
  "disclaimer": "This is not a medical diagnosis. Please consult a healthcare professional for proper evaluation and treatment."
}
```

> **AI Analysis:** The `ai_analysis` field is `null` by default. When `AI_ANALYSIS_ENABLED=true` and a valid `ANTHROPIC_API_KEY` is configured, the system sends symptom data to Claude for an additional clinical analysis. If the AI call fails, the response continues without it (graceful degradation).

### GET `/symptoms/conditions`
List all known conditions in the symptom checker database. **No authentication required.**

**Query Parameters:**
- `category` (string, optional) -- Filter by category: `respiratory`, `cardiac`, `gastrointestinal`, `neurological`, `musculoskeletal`, `infectious`, `dermatological`, `urological`, `endocrine`, `psychiatric`, `ophthalmological`, `ent`

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
Calculate BMI from height and weight. Supports both metric and imperial unit systems. **No authentication required.**

**Request Body (metric):**
```json
{
  "height_cm": 175.0,
  "weight_kg": 80.0,
  "unit_system": "metric"
}
```

**Request Body (imperial):**
```json
{
  "height_ft": 5,
  "height_in": 9,
  "weight_lbs": 176.0,
  "unit_system": "imperial"
}
```

**Response (200 -- metric):**
```json
{
  "bmi": 26.1,
  "category": "overweight",
  "healthy_weight_range": {
    "min_kg": 56.7,
    "max_kg": 76.6,
    "min_lbs": null,
    "max_lbs": null
  },
  "interpretation": "Your BMI indicates overweight. Consider consulting a healthcare provider for personalized advice.",
  "unit_system": "metric"
}
```

**Response (200 -- imperial):**
```json
{
  "bmi": 26.0,
  "category": "overweight",
  "healthy_weight_range": {
    "min_kg": 56.7,
    "max_kg": 76.6,
    "min_lbs": 125.0,
    "max_lbs": 168.9
  },
  "interpretation": "Your BMI indicates overweight. Consider consulting a healthcare provider for personalized advice.",
  "unit_system": "imperial"
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
  "recorded_at": "2026-03-31T10:30:00"
}
```

### GET `/metrics/vitals/{patient_id}`
Get vitals history for a patient. Returns stored assessments (not recomputed). **Requires:** authentication. Patients can only access their own vitals.

**Query Parameters:**
- `limit` (int, default 20) -- Page size (1-100)
- `offset` (int, default 0) -- Pagination offset

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
  "start_date": "2026-03-31",
  "end_date": "2026-06-30",
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
  "start_date": "2026-03-31",
  "end_date": "2026-06-30",
  "instructions": "Take with food",
  "status": "active"
}
```

### GET `/medications/reminders/{reminder_id}`
Get a specific medication reminder. **Requires:** authentication.

### PUT `/medications/reminders/{reminder_id}`
Update an active medication reminder. Only provided fields are updated (partial update). **Requires:** nurse or doctor role.

**Request Body (all fields optional):**
```json
{
  "dosage": "1000mg",
  "frequency": "once_daily",
  "times": ["08:00"],
  "instructions": "Take with breakfast",
  "end_date": "2026-09-30"
}
```

**Response (200):** Same format as create response.

### GET `/medications/patient/{patient_id}`
List all medications for a patient. Patients can only access their own medications. **Requires:** authentication.

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
| 400 | Bad Request -- invalid input or business rule violation |
| 401 | Unauthorized -- missing or invalid token |
| 403 | Forbidden -- insufficient permissions or ownership violation |
| 404 | Not Found |
| 409 | Conflict -- resource already exists (e.g., duplicate patient self-registration) |
| 422 | Validation Error -- Pydantic schema validation failed |
| 423 | Locked -- account temporarily locked due to failed login attempts |
| 429 | Rate Limited -- too many requests |
| 500 | Internal Server Error |
