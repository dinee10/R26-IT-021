# Intelligent Ayurvedic Herbal Plant Identification and Economic Analysis in Sri Lanka

**Group R-26-IT-021**  
**Faculty of Computing, SLIIT**  

**Project Title:** Intelligent Ayurvedic Herbal Plant Identification and Economic Analysis in Sri Lanka

**Team Members:**
- **M P Munasinghe** – Herbal Knowledge Intelligence System (RAG-based AI assistant)
- **D G T K Wickramasinghe** – AI-Driven Cultivation Recommendation System
- **H D Sachintha** – Mobile-Based Ayurvedic Plant Detection using Image Recognition
- **P A H K Pattiya Arachchi** – Explainable AI System for Medicinal Plant Quality Assessment

---

## Abstract

The declining availability of traditional Ayurvedic knowledge, the rising demand for medicinal plants, and the challenges faced by farmers in selecting suitable crops have created a need for intelligent digital decision-support systems. This research presents an integrated AI-powered platform for medicinal plant identification, cultivation guidance, knowledge retrieval, and quality assessment in the Sri Lankan context.

The proposed system combines computer vision, explainable AI, retrieval-augmented generation, and machine learning to support farmers, Ayurvedic practitioners, students, and manufacturers. It includes a mobile-based plant recognition module, a conversational herbal knowledge assistant, an AI-based cultivation recommendation system, and a quality assessment model that classifies plant condition using image analysis. By improving plant selection, cultivation planning, and access to reliable herbal information, the system contributes to sustainable agricultural practices, economic productivity, and preservation of indigenous medical knowledge.

---

## Problem Statement

Sri Lanka possesses a rich heritage of traditional Ayurvedic medicine and a diverse range of medicinal plant species; however, this knowledge is rapidly decreasing due to limited digital access, low awareness among younger generations, and the ageing population of traditional practitioners. Farmers also face significant losses because they often choose crops without adequate information about soil suitability, climate conditions, market demand, and cultivation requirements. In addition, inconsistent plant quality and the lack of accessible, context-aware guidance reduce productivity and increase dependence on imported raw materials.

This creates a clear need for an intelligent and user-friendly system that can support plant recognition, cultivation planning, educational guidance, and quality assessment using AI-driven decision support.

---

## Research Objectives

The primary objectives of this study are as follows:

1. To design and implement an AI-based system for identifying medicinal plants using image data and plant characteristics.
2. To provide a conversational knowledge assistant that enables users to access Ayurvedic plant information quickly and accurately.
3. To develop a cultivation recommendation component that recommends suitable crops based on environmental, soil, and economic factors.
4. To integrate explainable visual quality assessment for evaluating plant health and maturity.
5. To support sustainable agricultural decision-making for farmers and stakeholders in the medicinal plant industry.

---

## Research Questions

1. How can AI techniques improve medicinal plant identification in Sri Lanka?
2. How can a conversational system provide reliable and context-aware Ayurvedic knowledge?
3. How can cultivation recommendations support farmers in selecting profitable and suitable crops?
4. How can explainable AI improve trust and usability in plant quality assessment?

---

## Scope of the Study

This project focuses on the development of an integrated AI-based ecosystem for medicinal plant-related decision support. The scope includes:

- Image-based identification of medicinal plants using deep learning
- Retrieval-augmented conversational AI for herbal knowledge support
- Cultivation planning based on land conditions, climate, soil, and budget
- Quality assessment of plant health using explainable AI methods
- A mobile and web-based user interface for access by farmers, students, and practitioners

The research is targeted towards Sri Lankan medicinal plants and is designed to be practical, scalable, and suitable for future extension.

---

## Proposed Solution

The system is designed as a four-module architecture:

1. **Mobile-Based Plant Detection Module** – Uses a CNN-based model to identify medicinal plants from leaf and flower images.
2. **Herbal Knowledge Intelligence Module** – Provides contextual answers through a RAG-based AI assistant that combines a knowledge base with retrieval-based reasoning.
3. **AI-Driven Cultivation Recommendation Module** – Recommends suitable plants based on soil type, rainfall, humidity, temperature, budget, and land size.
4. **Explainable Quality Assessment Module** – Uses ResNet50 and Grad-CAM to evaluate whether a plant is healthy, diseased, or overmature and presents visual explanations to the user.

---

## Cultivation Recommendation Component

The cultivation recommendation component is a key part of the system and addresses the need for data-driven agricultural planning. The component allows users to enter environmental and farm-related details such as temperature, humidity, rainfall, soil pH, soil type, land size, irrigation method, growing season, and budget. Based on this input, the system applies a trained machine learning model to recommend the most suitable medicinal plants and estimates their profitability and cultivation viability. Soil photos can also be classified into one of the four soil classes included in the bundled image dataset.

This feature supports farmers in making practical planting decisions, reducing crop failure, and improving productivity. The recommendation logic combines both agronomic factors and economic considerations, making the output relevant to real-world cultivation planning.

The platform interface presents this process through a structured cultivation page that guides the user step by step and displays recommendation results clearly. The design emphasises usability, accessibility, and decision support for non-technical users in the agricultural domain.

---

## Methodology

The research follows a practical software engineering and AI development methodology. The workflow includes dataset preparation, model training, system integration, evaluation, and interface design.

- **Data Collection:** Medicinal plant cultivation and agricultural data were gathered from domain sources and structured datasets.
- **Preprocessing:** Data were cleaned, transformed, and prepared for machine learning models.
- **Model Development:** Prediction models were trained and evaluated to identify suitable cultivation conditions and crop recommendations.
- **System Integration:** Model outputs were connected to a Flutter-based frontend and backend services.
- **Validation:** The recommendation results were reviewed for relevance, accuracy, and usability within the application.

---

## Technologies Used

| Module | Technologies |
|--------|--------------|
| Plant Detection | CNN, TensorFlow, OpenCV, Flutter |
| Knowledge Assistant | RAG, ChromaDB, OpenAI embeddings, Flask |
| Cultivation Recommendation | Random Forest, Gradient Boosting, Python, Flask |
| Quality Assessment | ResNet50 (Transfer Learning), Grad-CAM, PyTorch, OpenCV |
| Frontend | Flutter  |
| Other | Python, Google Colab, Git |

---

# Herbal Plant Detector — Backend and Frontend Handoff

This repository currently contains the Flask/TensorFlow backend only. The original
Flutter frontend was deliberately removed on 2026-08-28 so the frontend team's
implementation can be added without keeping two competing applications.

The removed application is documented below as a functional and API reference.
The backend remains in `backend/`; do not replace its trained models, datasets, or
verification data when adding the new frontend.

## Current repository layout

```text
R26-IT-021/
  backend/                 Flask API, ML inference, tests, datasets, and models
  PROJECT_GUIDE.md         Backend, training, and research notes
  README.md                This handoff document
```

The replacement frontend should use `frontend/` as its top-level directory unless
the team has agreed on another location.

## What the removed frontend did

The former client was a Flutter 3/Dart application targeting Android, iOS, web,
Windows, macOS, and Linux. Its direct packages were `http` and `image_picker`.

It presented one responsive "Herbal Plant Detector" screen:

- A two-column layout at widths of 900 px or more and a stacked mobile layout.
- A choice between `plant` (shown as "Leaf / plant") and `seed` (shown as
  "Seed / spice").
- Gallery multi-select and camera capture with previews and per-image removal.
- A maximum of five images. Gallery selection replaced the current set; camera
  capture appended an image and discarded the oldest when five were already held.
- Gallery images were requested at quality 88. A prediction ran automatically
  after selecting or capturing images and could also be started manually.
- Capture guidance: center one leaf, use bright natural light, avoid heavy
  shadows, and submit 3–5 different angles.
- Prediction result: common/scientific name, confidence bar, low-confidence
  warning, per-image preprocessing feedback, traditional uses, preparation notes,
  safety warning, medical disclaimer, and the top five matches.
- Low-confidence results could be submitted for expert review. The user was told
  that EXIF/location/device metadata would be removed and could optionally consent
  to using verified images for future training.
- A submitted review displayed its short reference ID and allowed status refresh.
  Completed reviews displayed "Expert verified", the expert identification,
  reviewer, and notes; otherwise results displayed "AI identified".
- Loading, backend errors, invalid responses, and a 45-second request timeout were
  handled in the UI.

The old visual language used Material 3, pale green page background, white cards,
dark forest-green result/header areas, rounded 8 px corners, and lime confidence
accents. This is descriptive only; the replacement frontend may use the team's
approved design system.

## Backend setup

Python 3.11 is recommended because TensorFlow compatibility can vary on newer
Python releases.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r ml\requirements.txt
python run.py
```

The API listens on `http://127.0.0.1:5000` by default.

## Live YOLO camera detector

The Scan tab captures a camera frame about once per second and calls
`POST /api/detect-organs`. The endpoint returns normalized bounding boxes for
`leaf`, `seed`, and `flower`. It deliberately reports HTTP 503 until custom
weights are trained, so an untrained generic model is never presented as a
medicinal-plant detector.

Annotate bounding boxes in YOLO format, copy
`backend/yolo_dataset/data.yaml.example` to `data.yaml`, and create matching
`images/{train,val,test}` and `labels/{train,val,test}` directories. Then run:

```powershell
cd backend
pip install -r requirements.txt
python train_yolo_organs.py --epochs 100 --device 0
python run.py
```

For a bootstrap model from the existing object-centred classification images,
generate full-frame labels first:

```powershell
cd backend
python prepare_yolo_dataset.py
python train_yolo_organs.py --data yolo_dataset/data.yaml --epochs 30 --device 0
```

These generated boxes are suitable for prototyping only. Manually annotated
boxes are required to improve localization and performance on cluttered camera
scenes.

The training script copies the best weights to
`backend/ml/exports/yolo_organ/best.pt`, where the live API loads them lazily.

Useful environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `ALLOWED_ORIGINS` | Comma-separated browser origins allowed by CORS | `*` |
| `MAX_UPLOAD_BYTES` | Maximum complete request size in bytes | 25 MiB |
| `EXPERT_REVIEW_KEY` | Secret required by expert-only endpoints | unset |

For production, set `ALLOWED_ORIGINS` to the deployed frontend origins and keep
`EXPERT_REVIEW_KEY` on a trusted server/admin client. Do not embed that key in a
public web or mobile application.

## Frontend API base URL

The removed client used these defaults:

| Runtime | Base URL |
| --- | --- |
| Browser or desktop on the backend computer | `http://127.0.0.1:5000` |
| Android emulator | `http://10.0.2.2:5000` |
| Physical phone | `http://<development-computer-LAN-IP>:5000` |

Its Flutter override was `--dart-define=API_BASE_URL=http://...`. The replacement
should provide an equivalent environment-based setting and must not hard-code a
production address.

## Public API contract

All errors are JSON objects shaped as:

```json
{ "error": "Human-readable message" }
```

### Health check

`GET /api/health`

Returns HTTP 200. `status` is `healthy` when the model is ready and `degraded`
otherwise. The response also contains `message` and a backend-defined `model`
status object.

### Ask (placeholder)

`POST /api/ask` with `Content-Type: application/json`:

```json
{ "query": "What is neem traditionally used for?" }
```

This is currently a placeholder for the RAG feature. It returns `answer`, echoes
`query`, and returns a `sources` array. The old frontend did not expose it.

### Predict a plant or seed

`POST /api/predict` as `multipart/form-data`:

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `images` | repeated file | yes | 1–5 valid images |
| `model_type` | text | no | `plant` or `seed`; defaults to `plant` |

Example response:

```json
{
  "plant": "Turmeric",
  "model_type": "plant",
  "confidence": 0.9721,
  "confidence_percent": 97.21,
  "warning": null,
  "benefits": {
    "common_name": "Turmeric",
    "scientific_name": "Curcuma longa",
    "traditional_uses": ["..."],
    "preparation_notes": ["..."],
    "safety_warning": "...",
    "medical_disclaimer": "..."
  },
  "image_quality": [
    {
      "filename": "leaf.jpg",
      "foreground_cropped": true,
      "warnings": []
    }
  ],
  "top_predictions": [
    {
      "plant": "Turmeric",
      "confidence": 0.9721,
      "confidence_percent": 97.21
    }
  ]
}
```

`top_predictions` contains up to five items. The backend averages predictions
across every submitted image and its internal crops. A confidence below 95%
produces a non-null `warning`. Benefits fall back to safe generic text when the
label has no matching entry in `backend/ml/metadata/benefits.json`.

Likely statuses are HTTP 400 for bad input, 413 for a request over the configured
size, and 503 when the requested model is not ready.

### Submit an expert-verification request

`POST /api/verifications` as `multipart/form-data`:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `images` | repeated file | yes | 1–5 images |
| `ai_identification` | text | yes | Prediction label shown to the user |
| `ai_confidence` | number as text | yes | Send the percentage used by the UI |
| `training_consent` | boolean as text | no | `true`, `1`, or `yes` means consent |

The backend creates a fresh JPEG for every upload, which strips EXIF metadata.
Successful creation returns HTTP 201 and a verification record:

```json
{
  "id": "full-request-id",
  "status": "pending",
  "identification_label": "AI identified",
  "ai_identification": "Turmeric",
  "ai_confidence": 72.5,
  "expert_identification": null,
  "expert_notes": null,
  "reviewer_name": null,
  "training_consent": false,
  "created_at": "ISO-8601 timestamp",
  "reviewed_at": null
}
```

Store the returned `id` if review status must survive app restarts.

### Check verification status

`GET /api/verifications/{id}`

Returns the same verification shape. After review, `status` is `verified`,
`identification_label` is `Expert verified`, and the expert/reviewer fields are
populated. An unknown ID returns HTTP 404.

## Expert-only API

These routes require `X-Expert-Key: <EXPERT_REVIEW_KEY>` and should be accessed
only by a protected reviewer interface or trusted tool:

- `GET /api/expert/verifications` — returns `{ "requests": [...] }`; each pending
  record also has `image_count`.
- `GET /api/expert/verifications/{id}/images/image_1.jpg` — returns a sanitized
  JPEG. Image names follow `image_1.jpg`, `image_2.jpg`, and so on.
- `POST /api/expert/verifications/{id}` — JSON body with required
  `identification`, required `reviewer_name`, and optional `notes`.

Missing or incorrect expert authorization returns HTTP 401.

## Required behavior for the replacement frontend

- Send files under the repeated multipart name `images`, not `image` or an array
  name such as `images[]`.
- Limit prediction and review submissions to five images before making a request.
- Keep `plant` and `seed` as the exact values for `model_type`.
- Treat `confidence_percent` as a percentage from 0 to 100 and `confidence` as a
  fraction from 0 to 1.
- Render backend error messages and handle offline, timeout, 400, 413, and 503
  cases without crashing.
- Always display the medical disclaimer and safety warning with identification
  results. Do not present traditional uses as treatment advice.
- Clearly distinguish AI output from an expert-verified result.
- Ask separately for optional training consent; identification must work without
  consent.
- Do not claim 100% identification accuracy.

## Adding the frontend team's code without conflicts

Before integrating, commit or stash unrelated local work and fetch the team's
branch. Since this repository intentionally removed the old `frontend/`, copy the
team branch's frontend tree directly instead of manually mixing old and new files:

```powershell
git fetch origin
git restore --source origin/<frontend-team-branch> -- frontend
git status
```

Review the restored files, run that frontend's own install/lint/test/build steps,
then commit the replacement together with any required integration adjustments.
If the team's work includes backend changes too, merge or cherry-pick those
commits separately and resolve them deliberately; do not overwrite `backend/data`
or `backend/ml/exports` blindly.

## Backend verification

Run the backend tests after adding the replacement frontend:

```powershell
cd backend
python -m pytest tests
```

At minimum, manually verify health, both prediction model types, validation for
more than five images, expert submission/status refresh, browser CORS, and the
base URL behavior on every supported frontend platform.
