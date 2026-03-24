from app.schemas.symptom import (
    PossibleCondition,
    SymptomCheckRequest,
    SymptomCheckResponse,
)

# Condition database: maps symptom combinations to possible conditions.
# Each entry: (required_symptoms, condition_name, description, category)
CONDITION_DATABASE: list[tuple[set[str], str, str, str]] = [
    # === RESPIRATORY (15) ===
    ({"fever", "cough", "fatigue", "body_aches"}, "Influenza", "Viral infection with fever, cough, and body aches lasting 1-2 weeks", "respiratory"),
    ({"fever", "cough", "shortness_of_breath"}, "Pneumonia", "Lung infection causing cough, fever, and breathing difficulty", "respiratory"),
    ({"cough", "runny_nose", "sore_throat"}, "Common Cold", "Upper respiratory viral infection with mild symptoms", "respiratory"),
    ({"shortness_of_breath", "wheezing", "cough"}, "Asthma Exacerbation", "Airway narrowing causing wheezing and breathing difficulty", "respiratory"),
    ({"sore_throat", "fever", "swollen_glands"}, "Strep Throat", "Bacterial throat infection requiring antibiotic treatment", "respiratory"),
    ({"fever", "cough", "shortness_of_breath", "fatigue"}, "COVID-19", "Coronavirus infection with respiratory and systemic symptoms", "respiratory"),
    ({"cough", "fever", "night_sweats", "weight_loss"}, "Tuberculosis", "Bacterial lung infection requiring prolonged antibiotic treatment", "respiratory"),
    ({"shortness_of_breath", "chest_pain", "cough"}, "Pulmonary Embolism", "Blood clot in the lung requiring emergency treatment", "respiratory"),
    ({"sneezing", "runny_nose", "itchy_eyes"}, "Allergic Rhinitis", "Nasal allergy causing sneezing and congestion", "respiratory"),
    ({"cough", "mucus", "shortness_of_breath"}, "Bronchitis", "Inflammation of the bronchial tubes causing persistent cough", "respiratory"),
    ({"shortness_of_breath", "fatigue", "cough"}, "COPD Exacerbation", "Worsening of chronic obstructive pulmonary disease", "respiratory"),
    ({"sore_throat", "hoarseness", "cough"}, "Laryngitis", "Inflammation of the voice box causing hoarseness", "respiratory"),
    ({"snoring", "fatigue", "headache"}, "Sleep Apnea", "Breathing interruptions during sleep causing daytime fatigue", "respiratory"),
    ({"cough", "wheezing", "chest_tightness"}, "Reactive Airway Disease", "Airway hyperresponsiveness with wheezing and cough", "respiratory"),
    ({"fever", "facial_pain", "nasal_congestion"}, "Sinusitis", "Sinus infection causing facial pressure and congestion", "respiratory"),

    # === CARDIAC (10) ===
    ({"chest_pain", "shortness_of_breath", "sweating"}, "Possible Cardiac Event", "Chest pain with sweating and shortness of breath requires immediate evaluation", "cardiac"),
    ({"chest_pain", "shortness_of_breath"}, "Angina", "Chest pain due to reduced blood flow to the heart", "cardiac"),
    ({"shortness_of_breath", "fatigue", "swelling"}, "Heart Failure", "Heart unable to pump blood efficiently causing fluid buildup", "cardiac"),
    ({"palpitations", "dizziness", "shortness_of_breath"}, "Arrhythmia", "Irregular heartbeat causing palpitations and dizziness", "cardiac"),
    ({"chest_pain", "fever", "fatigue"}, "Pericarditis", "Inflammation of the heart lining causing sharp chest pain", "cardiac"),
    ({"leg_swelling", "shortness_of_breath", "fatigue"}, "Deep Vein Thrombosis", "Blood clot in deep veins causing swelling and pain", "cardiac"),
    ({"dizziness", "fainting", "fatigue"}, "Hypotension", "Low blood pressure causing dizziness and fainting", "cardiac"),
    ({"headache", "dizziness", "blurred_vision"}, "Hypertensive Crisis", "Dangerously high blood pressure requiring immediate treatment", "cardiac"),
    ({"palpitations", "anxiety", "tremor"}, "Supraventricular Tachycardia", "Rapid heart rate originating above the ventricles", "cardiac"),
    ({"chest_pain", "shortness_of_breath", "fatigue"}, "Myocarditis", "Inflammation of the heart muscle, often from viral infection", "cardiac"),

    # === GASTROINTESTINAL (15) ===
    ({"nausea", "vomiting", "diarrhea"}, "Gastroenteritis", "Stomach and intestinal inflammation, often viral", "gastrointestinal"),
    ({"abdominal_pain", "nausea", "fever"}, "Appendicitis", "Inflammation of the appendix requiring medical evaluation", "gastrointestinal"),
    ({"abdominal_pain", "bloating", "nausea"}, "Gastritis", "Stomach lining inflammation causing pain and nausea", "gastrointestinal"),
    ({"heartburn", "chest_pain", "difficulty_swallowing"}, "GERD", "Gastroesophageal reflux causing heartburn and acid regurgitation", "gastrointestinal"),
    ({"abdominal_pain", "diarrhea", "bloating"}, "Irritable Bowel Syndrome", "Chronic digestive condition with pain and altered bowel habits", "gastrointestinal"),
    ({"bloody_stool", "abdominal_pain", "diarrhea"}, "Inflammatory Bowel Disease", "Chronic inflammation of the digestive tract (Crohn's or UC)", "gastrointestinal"),
    ({"nausea", "vomiting", "abdominal_pain"}, "Gallstones", "Hardened deposits in the gallbladder causing pain after meals", "gastrointestinal"),
    ({"abdominal_pain", "jaundice", "fever"}, "Cholecystitis", "Gallbladder inflammation requiring medical evaluation", "gastrointestinal"),
    ({"constipation", "abdominal_pain", "bloating"}, "Bowel Obstruction", "Blockage preventing normal passage of intestinal contents", "gastrointestinal"),
    ({"nausea", "abdominal_pain", "loss_of_appetite"}, "Hepatitis", "Liver inflammation causing nausea and abdominal discomfort", "gastrointestinal"),
    ({"abdominal_pain", "fever", "jaundice"}, "Pancreatitis", "Pancreas inflammation causing severe abdominal pain", "gastrointestinal"),
    ({"diarrhea", "fever", "abdominal_cramps"}, "Food Poisoning", "Illness from contaminated food causing GI symptoms", "gastrointestinal"),
    ({"difficulty_swallowing", "chest_pain", "weight_loss"}, "Esophagitis", "Inflammation of the esophagus causing swallowing difficulty", "gastrointestinal"),
    ({"rectal_bleeding", "constipation", "abdominal_pain"}, "Hemorrhoids", "Swollen veins in the rectum causing bleeding and discomfort", "gastrointestinal"),
    ({"nausea", "vomiting", "weight_loss"}, "Peptic Ulcer", "Sore in the stomach or duodenal lining causing pain and nausea", "gastrointestinal"),

    # === NEUROLOGICAL (12) ===
    ({"headache", "nausea", "light_sensitivity"}, "Migraine", "Severe headache often with nausea and sensitivity to light", "neurological"),
    ({"headache", "fever", "stiff_neck"}, "Meningitis", "Serious infection of brain membranes requiring emergency care", "neurological"),
    ({"dizziness", "nausea", "balance_problems"}, "Vertigo", "Inner ear or neurological condition causing spinning sensation", "neurological"),
    ({"numbness", "weakness", "slurred_speech"}, "Stroke", "Brain blood supply disruption requiring immediate emergency care", "neurological"),
    ({"headache", "confusion", "vision_changes"}, "Concussion", "Mild traumatic brain injury from head impact", "neurological"),
    ({"tremor", "stiffness", "balance_problems"}, "Parkinson's Disease", "Progressive nervous system disorder affecting movement", "neurological"),
    ({"seizure", "confusion", "loss_of_consciousness"}, "Epileptic Seizure", "Abnormal brain electrical activity causing convulsions", "neurological"),
    ({"headache", "vision_changes", "nausea"}, "Increased Intracranial Pressure", "Elevated pressure inside the skull requiring evaluation", "neurological"),
    ({"numbness", "tingling", "weakness"}, "Peripheral Neuropathy", "Nerve damage causing numbness and tingling in extremities", "neurological"),
    ({"memory_loss", "confusion", "difficulty_concentrating"}, "Cognitive Impairment", "Decline in mental function requiring evaluation", "neurological"),
    ({"facial_pain", "headache", "eye_pain"}, "Trigeminal Neuralgia", "Nerve disorder causing intense facial pain", "neurological"),
    ({"fatigue", "numbness", "vision_changes"}, "Multiple Sclerosis", "Autoimmune disease affecting the brain and spinal cord", "neurological"),

    # === MUSCULOSKELETAL (10) ===
    ({"joint_pain", "swelling", "stiffness"}, "Arthritis Flare", "Joint inflammation causing pain, swelling, and reduced mobility", "musculoskeletal"),
    ({"back_pain", "numbness", "weakness"}, "Sciatica", "Nerve compression causing back pain radiating to legs", "musculoskeletal"),
    ({"muscle_pain", "fatigue", "stiffness"}, "Fibromyalgia", "Chronic widespread muscle pain with fatigue and tenderness", "musculoskeletal"),
    ({"joint_pain", "fever", "rash"}, "Rheumatic Fever", "Inflammatory condition following strep infection affecting joints and heart", "musculoskeletal"),
    ({"back_pain", "stiffness", "fatigue"}, "Ankylosing Spondylitis", "Chronic spine inflammation causing pain and stiffness", "musculoskeletal"),
    ({"joint_pain", "swelling", "redness"}, "Gout", "Uric acid crystal deposits causing sudden severe joint pain", "musculoskeletal"),
    ({"neck_pain", "headache", "stiffness"}, "Cervical Spondylosis", "Age-related neck disc degeneration causing pain and stiffness", "musculoskeletal"),
    ({"shoulder_pain", "stiffness", "weakness"}, "Rotator Cuff Injury", "Shoulder tendon damage causing pain and limited movement", "musculoskeletal"),
    ({"knee_pain", "swelling", "instability"}, "Meniscus Tear", "Knee cartilage tear causing pain and instability", "musculoskeletal"),
    ({"muscle_pain", "swelling", "bruising"}, "Muscle Strain", "Overstretched or torn muscle fibers from injury", "musculoskeletal"),

    # === INFECTIOUS (10) ===
    ({"fever", "rash", "fatigue"}, "Viral Infection", "General viral illness with systemic symptoms", "infectious"),
    ({"fever", "chills", "body_aches", "fatigue"}, "Systemic Infection", "Body-wide infection requiring medical evaluation", "infectious"),
    ({"fever", "rash", "joint_pain"}, "Dengue Fever", "Mosquito-borne viral infection with fever and rash", "infectious"),
    ({"fever", "chills", "sweating", "headache"}, "Malaria", "Parasitic infection transmitted by mosquitoes", "infectious"),
    ({"fever", "swollen_glands", "fatigue", "sore_throat"}, "Mononucleosis", "Viral infection causing prolonged fatigue and swollen glands", "infectious"),
    ({"fever", "cough", "rash", "red_eyes"}, "Measles", "Highly contagious viral infection with distinctive rash", "infectious"),
    ({"fever", "muscle_pain", "headache"}, "Lyme Disease", "Tick-borne bacterial infection causing flu-like symptoms", "infectious"),
    ({"fever", "abdominal_pain", "diarrhea"}, "Typhoid Fever", "Bacterial infection from contaminated food or water", "infectious"),
    ({"fever", "fatigue", "weight_loss"}, "HIV/AIDS", "Viral infection affecting the immune system", "infectious"),
    ({"wound_redness", "swelling", "fever"}, "Cellulitis", "Bacterial skin infection causing redness and swelling", "infectious"),

    # === DERMATOLOGICAL (8) ===
    ({"rash", "itching", "swelling"}, "Allergic Reaction", "Immune response to allergen causing skin symptoms", "dermatological"),
    ({"rash", "dry_skin", "itching"}, "Eczema", "Chronic skin condition causing dry, itchy, inflamed patches", "dermatological"),
    ({"rash", "scaling", "joint_pain"}, "Psoriasis", "Autoimmune skin condition causing scaly, inflamed patches", "dermatological"),
    ({"rash", "blisters", "pain"}, "Shingles", "Viral reactivation causing painful blistering rash", "dermatological"),
    ({"itching", "rash", "redness"}, "Contact Dermatitis", "Skin inflammation from direct contact with irritant or allergen", "dermatological"),
    ({"skin_lesion", "bleeding", "color_change"}, "Skin Cancer Concern", "Abnormal skin growth requiring dermatological evaluation", "dermatological"),
    ({"hives", "itching", "swelling"}, "Urticaria", "Raised itchy welts on the skin from allergic response", "dermatological"),
    ({"hair_loss", "scalp_itching", "rash"}, "Scalp Dermatitis", "Inflammatory scalp condition causing flaking and hair loss", "dermatological"),

    # === UROLOGICAL (8) ===
    ({"painful_urination", "frequent_urination", "fever"}, "Urinary Tract Infection", "Bacterial infection of the urinary system", "urological"),
    ({"flank_pain", "blood_in_urine", "nausea"}, "Kidney Stones", "Mineral deposits in the kidneys causing severe pain", "urological"),
    ({"frequent_urination", "urgency", "pelvic_pain"}, "Overactive Bladder", "Bladder condition causing sudden urge to urinate", "urological"),
    ({"painful_urination", "discharge", "pelvic_pain"}, "Sexually Transmitted Infection", "Infection transmitted through sexual contact requiring treatment", "urological"),
    ({"blood_in_urine", "frequent_urination", "pelvic_pain"}, "Bladder Cancer Concern", "Abnormal bladder cells requiring urological evaluation", "urological"),
    ({"flank_pain", "fever", "painful_urination"}, "Pyelonephritis", "Kidney infection requiring antibiotic treatment", "urological"),
    ({"difficulty_urinating", "weak_stream", "frequent_urination"}, "Benign Prostatic Hyperplasia", "Enlarged prostate causing urinary difficulties in men", "urological"),
    ({"testicular_pain", "swelling", "nausea"}, "Testicular Torsion", "Twisted testicle cutting blood supply — surgical emergency", "urological"),

    # === ENDOCRINE (8) ===
    ({"excessive_thirst", "frequent_urination", "fatigue"}, "Diabetes", "Blood sugar regulation disorder requiring management", "endocrine"),
    ({"weight_gain", "fatigue", "cold_intolerance"}, "Hypothyroidism", "Underactive thyroid causing metabolic slowdown", "endocrine"),
    ({"weight_loss", "anxiety", "tremor"}, "Hyperthyroidism", "Overactive thyroid causing increased metabolism", "endocrine"),
    ({"fatigue", "dizziness", "weight_loss"}, "Adrenal Insufficiency", "Inadequate adrenal hormone production", "endocrine"),
    ({"excessive_thirst", "confusion", "nausea"}, "Diabetic Ketoacidosis", "Dangerous diabetes complication requiring emergency care", "endocrine"),
    ({"tremor", "sweating", "confusion"}, "Hypoglycemia", "Dangerously low blood sugar requiring immediate treatment", "endocrine"),
    ({"bone_pain", "fatigue", "kidney_stones"}, "Hyperparathyroidism", "Overactive parathyroid glands affecting calcium levels", "endocrine"),
    ({"fatigue", "weight_gain", "depression"}, "Cushing's Syndrome", "Excess cortisol production causing weight gain and fatigue", "endocrine"),

    # === PSYCHIATRIC (6) ===
    ({"sadness", "fatigue", "loss_of_interest"}, "Major Depression", "Persistent depressive disorder affecting mood and daily function", "psychiatric"),
    ({"anxiety", "palpitations", "shortness_of_breath"}, "Panic Attack", "Sudden episode of intense fear with physical symptoms", "psychiatric"),
    ({"insomnia", "anxiety", "irritability"}, "Generalized Anxiety Disorder", "Chronic excessive worry affecting daily life", "psychiatric"),
    ({"mood_swings", "insomnia", "racing_thoughts"}, "Bipolar Disorder", "Mood disorder with alternating manic and depressive episodes", "psychiatric"),
    ({"flashbacks", "nightmares", "anxiety"}, "PTSD", "Trauma-related disorder with intrusive memories and hypervigilance", "psychiatric"),
    ({"confusion", "hallucinations", "agitation"}, "Delirium", "Acute confusion state requiring urgent medical evaluation", "psychiatric"),

    # === OPHTHALMOLOGICAL (4) ===
    ({"eye_pain", "redness", "vision_changes"}, "Acute Glaucoma", "Sudden eye pressure increase requiring emergency treatment", "ophthalmological"),
    ({"eye_redness", "discharge", "itching"}, "Conjunctivitis", "Eye infection or inflammation causing redness and discharge", "ophthalmological"),
    ({"vision_changes", "floaters", "light_flashes"}, "Retinal Detachment", "Retina separation from eye wall — surgical emergency", "ophthalmological"),
    ({"eye_pain", "light_sensitivity", "blurred_vision"}, "Uveitis", "Eye inflammation causing pain and vision changes", "ophthalmological"),

    # === ENT (4) ===
    ({"ear_pain", "fever", "hearing_loss"}, "Otitis Media", "Middle ear infection causing pain and hearing changes", "ent"),
    ({"ear_pain", "dizziness", "tinnitus"}, "Meniere's Disease", "Inner ear disorder causing vertigo and hearing issues", "ent"),
    ({"nosebleed", "facial_pain", "nasal_congestion"}, "Epistaxis", "Nosebleed possibly from dryness, trauma, or underlying condition", "ent"),
    ({"difficulty_swallowing", "sore_throat", "drooling"}, "Peritonsillar Abscess", "Pus collection near tonsils requiring drainage", "ent"),
]

URGENCY_MAP = {
    "cardiac": "high",
    "neurological": "moderate",
    "respiratory": "moderate",
    "gastrointestinal": "moderate",
    "infectious": "moderate",
    "musculoskeletal": "low",
    "dermatological": "low",
    "urological": "moderate",
    "endocrine": "moderate",
    "psychiatric": "moderate",
    "ophthalmological": "moderate",
    "ent": "low",
}

EMERGENCY_CONDITIONS = {
    "Possible Cardiac Event", "Meningitis", "Appendicitis", "Stroke",
    "Pulmonary Embolism", "Testicular Torsion", "Diabetic Ketoacidosis",
    "Acute Glaucoma", "Retinal Detachment", "Epileptic Seizure",
    "Hypertensive Crisis", "Delirium",
}


def match_conditions(
    symptoms: list[str],
) -> list[tuple[str, float, str, str]]:
    """Match symptoms against condition database, returning scored results."""
    symptom_set = {s.lower() for s in symptoms}
    matches: list[tuple[str, float, str, str]] = []

    for required, name, description, category in CONDITION_DATABASE:
        overlap = symptom_set & required
        if len(overlap) >= 2 or (len(required) <= 2 and overlap == required):
            score = len(overlap) / len(required)
            matches.append((name, score, description, category))

    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def score_to_probability(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "moderate"
    return "low"


def determine_urgency(
    conditions: list[tuple[str, float, str, str]],
    severity: str,
    duration_days: int,
    age: int,
) -> str:
    """Determine overall urgency based on conditions and context."""
    if not conditions:
        if severity == "severe":
            return "moderate"
        return "low"

    # Check for emergency conditions
    for name, _, _, _ in conditions:
        if name in EMERGENCY_CONDITIONS:
            return "emergency"

    # Get highest urgency from matched categories
    category_urgencies = {"high": 3, "moderate": 2, "low": 1, "emergency": 4}
    max_urgency = "low"
    for _, _, _, category in conditions:
        cat_urgency = URGENCY_MAP.get(category, "low")
        if category_urgencies.get(cat_urgency, 0) > category_urgencies.get(max_urgency, 0):
            max_urgency = cat_urgency

    # Severity modifier
    if severity == "severe" and max_urgency == "low":
        max_urgency = "moderate"

    # Duration modifier — acute onset is more concerning
    if duration_days <= 1 and max_urgency in ("low", "moderate"):
        urgency_levels = ["low", "moderate", "high"]
        idx = urgency_levels.index(max_urgency)
        max_urgency = urgency_levels[min(idx + 1, 2)]

    # Age modifier
    if (age < 5 or age > 70) and max_urgency == "low":
        max_urgency = "moderate"

    return max_urgency


def get_recommended_action(urgency: str) -> str:
    actions = {
        "emergency": "Seek emergency medical care immediately. Call emergency services or go to the nearest emergency room.",
        "high": "See a doctor as soon as possible, ideally within 24 hours.",
        "moderate": "Schedule a doctor's appointment within a few days. Monitor symptoms and seek immediate care if they worsen.",
        "low": "Monitor symptoms at home. Practice self-care and see a doctor if symptoms persist beyond a week or worsen.",
    }
    return actions[urgency]


def check_symptoms(request: SymptomCheckRequest) -> SymptomCheckResponse:
    """Analyze symptoms and return possible conditions with recommendations."""
    matches = match_conditions(request.symptoms)

    possible_conditions = [
        PossibleCondition(
            condition=name,
            probability=score_to_probability(score),
            description=description,
            category=category,
        )
        for name, score, description, category in matches[:5]
    ]

    urgency = determine_urgency(matches, request.severity, request.duration_days, request.age)
    recommended_action = get_recommended_action(urgency)

    return SymptomCheckResponse(
        possible_conditions=possible_conditions,
        recommended_action=recommended_action,
        urgency=urgency,
    )
