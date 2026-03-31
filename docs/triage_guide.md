# Triage System Guide

## Overview

The AI Nurse triage system uses a 5-level priority scale based on the Australasian Triage Scale (ATS) and Canadian Triage and Acuity Scale (CTAS). It evaluates patient symptoms, vitals, and clinical context to assign an appropriate priority level.

When a triage assessment is submitted with a `patient_id`, the record is persisted and a real-time WebSocket notification (`queue_updated` event) is broadcast to all connected clients via `/ws/triage-queue`.

## Priority Levels

### Level 1 -- Resuscitation (Red)
**Target response time:** Immediate (0 minutes)

Life-threatening conditions requiring immediate intervention.

**Examples:**
- Cardiac arrest
- Respiratory arrest
- Major trauma with active hemorrhage
- Anaphylaxis with airway compromise
- Severe chest pain with cardiac indicators

**Vital sign triggers:**
- Heart rate < 40 or > 150 bpm
- Systolic BP < 80 mmHg
- Oxygen saturation < 85%
- Respiratory rate < 8 or > 40

---

### Level 2 -- Emergency (Orange)
**Target response time:** 10 minutes

Potentially life-threatening conditions or severe pain requiring rapid assessment.

**Examples:**
- Chest pain (non-cardiac ruled out)
- Severe difficulty breathing
- Stroke symptoms (facial droop, arm weakness, speech difficulty)
- Severe allergic reaction without airway compromise
- High-risk abdominal pain
- Acute psychosis or suicidal ideation with plan

**Vital sign triggers:**
- Heart rate < 50 or > 130 bpm
- Systolic BP < 90 or > 200 mmHg
- Oxygen saturation 85-90%
- Temperature > 40.0C
- Pain scale 8-10

---

### Level 3 -- Urgent (Yellow)
**Target response time:** 30 minutes

Serious conditions that are currently stable but need prompt attention.

**Examples:**
- Moderate abdominal pain
- Moderate difficulty breathing (stable vitals)
- High fever (38.5-40.0C) with other symptoms
- Fractures without neurovascular compromise
- Moderate dehydration
- Acute mental health crisis (stable)

**Vital sign triggers:**
- Heart rate 100-130 bpm
- Systolic BP 160-200 mmHg
- Temperature 38.5-40.0C
- Pain scale 5-7

---

### Level 4 -- Semi-Urgent (Green)
**Target response time:** 60 minutes

Less urgent conditions that may worsen without treatment but are not immediately dangerous.

**Examples:**
- Mild abdominal pain
- Earache or sore throat with mild fever
- Minor wound requiring stitches
- Urinary symptoms
- Mild allergic reaction (localized)
- Prescription refill with mild symptoms

---

### Level 5 -- Non-Urgent (Blue)
**Target response time:** 120 minutes

Minor conditions suitable for routine care.

**Examples:**
- Minor cuts and bruises
- Chronic condition follow-up
- Medication refill (no active symptoms)
- Cold symptoms (no fever, no distress)
- Minor rash (non-spreading)

---

## Decision Logic

The triage engine evaluates the following factors in order:

1. **Critical vital signs** -- Any single vital in the critical range triggers Level 1 or 2
2. **Symptom severity** -- Mapped against known high-risk symptom combinations
3. **Pain scale** -- Incorporated as a modifier to symptom severity
4. **Duration** -- Acute onset generally elevates priority
5. **Patient history** -- Known conditions (e.g., cardiac history) may elevate similar presentations
6. **Age modifiers** -- Pediatric (< 5) and geriatric (> 70) patients receive a priority bump for certain conditions

## Triage Queue

The triage queue (`GET /api/v1/triage/queue`) displays patients sorted by:
1. Priority level (ascending -- Level 1 first)
2. Time of submission (ascending -- earlier submissions first within the same priority)

Each queue item includes calculated `wait_time_minutes` based on the time since submission. Queue items can have one of three statuses: `waiting`, `in_progress`, or `completed`.

Staff (nurses, doctors, admins) can update a patient's status via `PUT /api/v1/triage/{id}/status`. Status changes trigger a WebSocket broadcast so all connected clients see the update in real time.

## Important Disclaimers

- The triage system is a **decision support tool**, not a replacement for clinical judgment
- All Level 1 and Level 2 assignments should be reviewed by a qualified healthcare professional immediately
- The system may upgrade but never downgrade a triage level assigned by a clinician
- Edge cases and atypical presentations should always default to a higher priority level
