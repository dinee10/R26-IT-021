FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements-deploy.txt ./
RUN pip install --no-cache-dir -r requirements-deploy.txt

# Copy only runtime files. Training datasets and duplicate experiment models
# stay out of the deployment image.
COPY app ./app
COPY data ./data
COPY conversation_rag_bilingual_test.py ./
COPY chroma_db_bilingual_refs_test ./chroma_db_bilingual_refs_test
COPY ml/metadata ./ml/metadata
COPY ml/exports/herb_model.keras ./ml/exports/herb_model.keras
COPY ml/exports/labels.json ./ml/exports/labels.json
COPY ml/exports/seed/herb_model.keras ./ml/exports/seed/herb_model.keras
COPY ml/exports/seed/labels.json ./ml/exports/seed/labels.json
COPY ml/exports/flower_retrained/herb_model.keras ./ml/exports/flower_retrained/herb_model.keras
COPY ml/exports/flower_retrained/labels.json ./ml/exports/flower_retrained/labels.json
COPY ml/exports/yolo_organ/best.pt ./ml/exports/yolo_organ/best.pt
COPY ml/quality.plant_identifier.efficientnetv2_b0.keras ./ml/quality.plant_identifier.efficientnetv2_b0.keras
COPY ml/quality.condition_classifier.efficientnetv2_b0.keras ./ml/quality.condition_classifier.efficientnetv2_b0.keras
COPY ml/quality.maturity_classifier.efficientnetv2_b0.keras ./ml/quality.maturity_classifier.efficientnetv2_b0.keras

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 2 --timeout 180 --access-logfile - app.main:app"]
