# API Reference

Base URL: `http://localhost:8000/api/v1`

All endpoints return JSON. Protected endpoints require a `Authorization: Bearer <token>` header.

---

## Authentication

### POST `/auth/login`
Authenticate a user and receive a JWT token.

**Request Body:**
```json
{
  "email": "patient@example.com",
  "password": "securepassword"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid",
    "email": "patient@example.com",
    "role": "patient"
  }
}
```

### POST `/auth/register`
Register a new user account.

**Request Body:**
```json
{
  "email": "patient@example.com",
  "password": "securepassword",
  "full_name": "John Doe",
  "role": "patient",
  "date_of_birth": "1990-05-15"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "email": "patient@example.com",
  "full_name": "John Doe",
  "role": "patient"
}
```

---

## Patients

### POST `/patients`
Register a new patient profile. **Requires:** nurse, doctor, or admin role.

**Request Body:**
```json
{
  "user_id": "uuid",
  "full_name": "John Doe",
  "date_of_birth": "1990-05-15",
  "gender": "male",
  "blood_type": "O+",
  "height_cm": 175.0,
  "weight_kg": 80.0,
  "allergies": ["penicillin"],
  "emergency_contact": {
    "name": "Jane Doe",
    "phone": "+1234567890",
    "relationship": "spouse"
  }
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "full_name": "John Doe",
  "date_of_birth": "1990-05-15",
  "gender": "male",
  "blood_type": "O+",
  "created_at": "2026-03-24T10:00:00Z"
}
```

### GET `/patients/{patient_id}`
Retrieve patient details. **Requires:** authenticated user with access.

**Response (200):**
```json
{
  "id": "uuid",
  "full_name": "John Doe",
  "date_of_birth": "1990-05-15",
  "gender": "male",
  "blood_type": "O+",
  "height_cm": 175.0,
  "weight_kg": 80.0,
  "allergies": ["penicillin"],
  "bmi": 26.1,
  "bmi_category": "overweight",
  "created_at": "2026-03-24T10:00:00Z"
}
```

### GET `/patients/{patient_id}/history`
Retrieve patient visit history and past assessments.

**Query Parameters:**
- `limit` (int, default 20) — Number of records to return
- `offset` (int, default 0) — Pagination offset
- `type` (string, optional) — Filter by record type: `triage`, `symptom_check`, `vitals`

**Response (200):**
```json
{
  "patient_id": "uuid",
  "total": 45,
  "records": [
    {
      "id": "uuid",
      "type": "triage",
      "priority_level": 3,
      "summary": "Urgent — abdominal pain with fever",
      "created_at": "2026-03-20T14:30:00Z",
      "created_by": "Nurse Smith"
    }
  ]
}
```

---

## Triage

### POST `/triage`
Submit a triage assessment. **Requires:** nurse or doctor role.

**Request Body:**
```json
{
  "patient_id": "uuid",
  "chief_complaint": "Severe chest pain radiating to left arm",
  "symptoms": ["chest_pain", "shortness_of_breath", "sweating", "nausea"],
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
  "notes": "Patient appears distressed, clutching chest"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "patient_id": "uuid",
  "priority_level": 1,
  "priority_label": "Resuscitation",
  "priority_color": "red",
  "recommended_action": "Immediate cardiac evaluation. Activate code team.",
  "flags": ["possible_cardiac_event", "elevated_heart_rate", "low_o2_sat"],
  "created_at": "2026-03-24T10:15:00Z",
  "assessed_by": "uuid"
}
```

### GET `/triage/queue`
View the current triage queue sorted by priority. **Requires:** nurse, doctor, or admin role.

**Query Parameters:**
- `status` (string, optional) — Filter: `waiting`, `in_progress`, `completed`

**Response (200):**
```json
{
  "queue": [
    {
      "id": "uuid",
      "patient_name": "John Doe",
      "priority_level": 1,
      "priority_color": "red",
      "chief_complaint": "Severe chest pain",
      "wait_time_minutes": 2,
      "status": "waiting",
      "created_at": "2026-03-24T10:15:00Z"
    }
  ],
  "total_waiting": 12
}
```

---

## Symptoms

### POST `/symptoms/check`
Analyze reported symptoms and suggest possible conditions. Available to all authenticated users.

**Request Body:**
```json
{
  "patient_id": "uuid",
  "symptoms": ["headache", "fever", "body_aches", "fatigue"],
  "duration_days": 3,
  "severity": "moderate",
  "additional_info": "Recently traveled internationally"
}
```

**Response (200):**
```json
{
  "assessment_id": "uuid",
  "possible_conditions": [
    {
      "condition": "Influenza",
      "probability": "high",
      "description": "Viral infection with matching symptom profile"
    },
    {
      "condition": "COVID-19",
      "probability": "moderate",
      "description": "Respiratory virus — recent travel increases risk"
    }
  ],
  "recommended_action": "see_doctor",
  "urgency": "moderate",
  "disclaimer": "This is not a medical diagnosis. Please consult a healthcare professional."
}
```

---

## Health Metrics

### POST `/metrics/bmi`
Calculate BMI from height and weight.

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
  "bmi": 26.1,
  "category": "overweight",
  "healthy_weight_range_kg": {
    "min": 56.7,
    "max": 76.6
  },
  "interpretation": "Your BMI indicates overweight. Consider consulting a healthcare provider for personalized advice."
}
```

### POST `/metrics/vitals`
Record patient vital signs. **Requires:** nurse or doctor role.

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
  "blood_glucose_mg_dl": 95
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
    "temperature_c": {"value": 36.8, "status": "normal"},
    "respiratory_rate": {"value": 16, "status": "normal"},
    "oxygen_saturation": {"value": 98, "status": "normal"},
    "blood_glucose_mg_dl": {"value": 95, "status": "normal"}
  },
  "alerts": [],
  "recorded_at": "2026-03-24T10:30:00Z"
}
```

---

## Medications

### POST `/medications/reminders`
Create a medication reminder for a patient. **Requires:** nurse or doctor role.

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
  "instructions": "Take with food",
  "prescribed_by": "uuid"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "patient_id": "uuid",
  "medication_name": "Metformin",
  "dosage": "500mg",
  "frequency": "twice_daily",
  "next_reminder": "2026-03-24T20:00:00Z",
  "status": "active",
  "created_at": "2026-03-24T10:00:00Z"
}
```

### GET `/medications/{patient_id}`
List all medications for a patient.

**Response (200):**
```json
{
  "patient_id": "uuid",
  "medications": [
    {
      "id": "uuid",
      "medication_name": "Metformin",
      "dosage": "500mg",
      "frequency": "twice_daily",
      "status": "active",
      "adherence_rate": 0.92,
      "next_reminder": "2026-03-24T20:00:00Z"
    }
  ]
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input provided",
    "errors": [
      {
        "field": "weight_kg",
        "message": "Weight must be a positive number"
      }
    ]
  }
}
```

### Status Codes
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request — invalid input |
| 401 | Unauthorized — missing or invalid token |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |
