# Intelligent Ayurvedic Herbal Plant Identification and Economic Analysis in Sri Lanka

**Group R-26-IT-021**  
**Faculty of Computing, SLIIT**  

**Project Title:** Intelligent Ayurvedic Herbal Plant Identification and Economic Analysis in Sri Lanka

**Team Members:**
- **M P Munasinghe**  – Herbal Knowledge Intelligence System (RAG-based AI Assistant)
- **D G T K Wickramasinghe**  – AI-Driven Cultivation Recommendation System
- **H D Sachintha**  – Mobile-Based Ayurvedic Plant Detection using Image Recognition
- **P A H K Pattiya Arachchi**  – Explainable AI System for Medicinal Plant Quality Assessment


---

## Abstract

Sri Lanka is home to over 1,400 medicinal plant species used in Ayurveda for more than 3,000 years. However, indigenous knowledge is rapidly disappearing, farmers face significant income loss due to poor plant selection and quality issues, and the younger generation has limited access to reliable information. 

This project develops an **integrated AI-powered ecosystem** that addresses the entire medicinal plant value chain — from accurate plant identification and quality assessment to knowledge dissemination and cultivation recommendations with economic analysis. The system combines Computer Vision (CNN & ResNet50), Explainable AI (Grad-CAM), Retrieval-Augmented Generation (RAG), and Machine Learning to support farmers, Ayurvedic practitioners, students, and manufacturers.

---

## Problem Statement

- Rapid loss of traditional Ayurvedic knowledge (most practitioners aged 55+)
- Less than 30% of the population can identify common medicinal plants
- High crop failure rates (15-25%) and income loss (30-60%) for farmers
- Inconsistent raw material quality and heavy reliance on imports (LKR 2.3 Billion annually)
- Lack of accessible, multilingual, and context-aware digital tools

---

## Proposed Solution

An integrated platform consisting of four interconnected modules:

1. **Mobile-Based Plant Detection** – CNN model for real-time identification of Sri Lankan Ayurvedic plants from leaf/flower images.
2. **Herbal Knowledge Intelligence System** – Context-aware RAG-based conversational AI assistant supporting English and Sinhala.
3. **AI-Driven Cultivation Recommendation System** – Recommends suitable & profitable medicinal plants based on soil, climate, and market data.
4. **Explainable AI Quality Assessment** – Evaluates plant suitability (Healthy / Diseased / Overmature) using ResNet50 + Grad-CAM heatmaps.

---

## Key Features

- **Multi-modal AI** combining image recognition, quality assessment, and conversational intelligence
- **Explainable AI** using Grad-CAM heatmaps for transparency
- **Context-aware conversations** with session memory
- **Multilingual support** (English & Sinhala)
- **Farmer-friendly recommendations** with economic analysis
- **Scalable architecture** for adding new plants and features

---

## Technologies Used

| Module | Technologies |
|--------|--------------|
| Plant Detection | CNN, TensorFlow / PyTorch, OpenCV, Mobile (Flutter/React Native) |
| Knowledge Assistant | RAG, OpenAI embeddings (`text-embedding-3-large`), ChromaDB, GPT-4.0-mini, Flask |
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
