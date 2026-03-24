# AI Nurse Project

A digital nurse powered by AI that provides patient triage, symptom checking, BMI/health metric calculations, and medication reminders. Built with FastAPI.

## Overview

AI Nurse is an intelligent healthcare assistant designed to support patients, nurses, doctors, and hospitals by automating routine nursing tasks and providing real-time health guidance. It acts as a virtual nurse capable of assessing patient symptoms, calculating health metrics, managing medication schedules, and triaging patients based on severity.

## Features

- **Patient Triage** — Assess patient symptoms and assign priority levels (emergency, urgent, semi-urgent, non-urgent) using clinical decision logic
- **Symptom Checking** — Analyze reported symptoms against a medical knowledge base to suggest possible conditions and recommended actions
- **BMI & Health Metrics** — Calculate BMI, interpret height/weight data, and track patient vitals over time
- **Medication Reminders** — Schedule and send medication reminders to patients with dosage and timing information
- **Patient Records** — Store and retrieve patient health data, history, and visit notes
- **Role-Based Access** — Different interfaces and permissions for patients, nurses, doctors, and hospital administrators

## Tech Stack

- **Backend:** Python 3.11+ with FastAPI
- **Database:** PostgreSQL (patient records, medication schedules)
- **Authentication:** OAuth2 with JWT tokens
- **Task Queue:** Celery with Redis (medication reminder scheduling)
- **Documentation:** Auto-generated OpenAPI/Swagger docs

## Project Structure

```
AI_Nurse_Project/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Application configuration
│   ├── models/              # Database models
│   │   ├── patient.py
│   │   ├── medication.py
│   │   └── triage.py
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── patient.py
│   │   ├── symptom.py
│   │   ├── medication.py
│   │   └── triage.py
│   ├── routers/             # API route handlers
│   │   ├── patients.py
│   │   ├── symptoms.py
│   │   ├── medications.py
│   │   ├── triage.py
│   │   └── metrics.py
│   ├── services/            # Business logic
│   │   ├── triage_engine.py
│   │   ├── symptom_checker.py
│   │   ├── bmi_calculator.py
│   │   └── medication_scheduler.py
│   └── utils/               # Shared utilities
│       ├── auth.py
│       └── validators.py
├── tests/
├── alembic/                 # Database migrations
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 15+
- Redis (for medication reminder scheduling)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/angel3848/AI-Nurse-Project.git
   cd AI-Nurse-Project
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and API keys
   ```

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

7. Open the API docs at `http://localhost:8000/docs`

## API Endpoints

### Patients
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/patients` | Register a new patient |
| GET | `/api/v1/patients/{id}` | Get patient details |
| PUT | `/api/v1/patients/{id}` | Update patient info |
| GET | `/api/v1/patients/{id}/history` | Get patient history |

### Triage
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/triage` | Submit a triage assessment |
| GET | `/api/v1/triage/{id}` | Get triage result |
| GET | `/api/v1/triage/queue` | View current triage queue |

### Symptoms
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/symptoms/check` | Analyze symptoms |
| GET | `/api/v1/symptoms/conditions` | List known conditions |

### Health Metrics
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/metrics/bmi` | Calculate BMI |
| POST | `/api/v1/metrics/vitals` | Record patient vitals |
| GET | `/api/v1/metrics/{patient_id}/history` | Get vitals history |

### Medications
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/medications/reminders` | Create a medication reminder |
| GET | `/api/v1/medications/{patient_id}` | Get patient medications |
| PUT | `/api/v1/medications/reminders/{id}` | Update a reminder |
| DELETE | `/api/v1/medications/reminders/{id}` | Cancel a reminder |

## Triage Priority Levels

| Level | Color | Description |
|-------|-------|-------------|
| 1 — Resuscitation | Red | Immediate life-threatening conditions |
| 2 — Emergency | Orange | Potentially life-threatening or time-critical |
| 3 — Urgent | Yellow | Serious but stable, needs prompt attention |
| 4 — Semi-Urgent | Green | Less urgent, can wait |
| 5 — Non-Urgent | Blue | Minor conditions, routine care |

## Target Audience

- **Patients** — Self-service symptom checking, medication reminders, health metric tracking
- **Nurses** — Automated triage assistance, patient queue management, vitals recording
- **Doctors** — Patient history access, triage review, clinical decision support
- **Hospitals** — Operational dashboards, patient flow management, resource allocation

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
