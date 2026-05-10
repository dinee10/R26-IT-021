# Herbal Plant Detector Project Guide

This project has two parts:

- `backend`: Flask API and TensorFlow model prediction.
- `frontend`: Flutter mobile app for uploading up to 5 leaf/seed images.

## Important Accuracy Note

No real plant detector can guarantee 100% accuracy. Plant images vary by age, lighting, disease, camera quality, background, and whether the picture shows leaf, seed, flower, or full plant. This app improves reliability by accepting up to 5 images and averaging predictions, but it must still show confidence and a safety warning.

Use the app for education and plant identification support only. Herbal benefits are not medical advice.

## Final Folder Structure

```text
R26-IT-021/
  backend/
    app/
      main.py
      routes/
        api.py
      services/
        predictor.py
    ml/
      dataset/
        plant_dataset_raw/
          Aloe_barbadensis_miller/
            image1.jpg
            image2.jpg
          Azadirachta_indica/
            image1.jpg
      exports/
        herb_model.keras
        herb_model.tflite
        labels.json
      metadata/
        benefits.json
      models/
      scripts/
        train_model.py
      requirements.txt
    requirements.txt
    run.py
  frontend/
    lib/
      main.dart
      models/
        prediction_result.dart
      screens/
        detector_screen.dart
      services/
        herb_api.dart
```

## Dataset Setup

1. Download the Kaggle dataset:
   `https://www.kaggle.com/datasets/ai4a-lab/herb-plant-classification-dataset`

2. Extract it so every class is one folder:

```text
backend/ml/dataset/plant_dataset_raw/
  Aloe_barbadensis_miller/
  Andrographis_paniculata/
  Azadirachta_indica/
```

The Kaggle page says the dataset has 91 herb classes and 6,104 JPG/JPEG images. If folder names contain spaces, you can keep them, but using underscores is cleaner for API output.

## Backend Setup

Use Python 3.11 if possible. TensorFlow may not install correctly on Python 3.13.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r ml\requirements.txt
cd ..
python backend\ml\scripts\train_model.py --epochs 25 --fine-tune-epochs 10
python backend\run.py
```

For better close-up leaf accuracy after adding more training images, retrain with the stronger EfficientNetV2 backbone:

```powershell
python backend\ml\scripts\train_model.py --model efficientnetv2 --epochs 35 --fine-tune-epochs 15
```

Backend URLs:

- `GET http://127.0.0.1:5000/api/health`
- `POST http://127.0.0.1:5000/api/predict`

For `/api/predict`, send multipart form-data with field name `images`. You can upload 1 to 5 images.

## Flutter Setup

```powershell
cd frontend
flutter pub get
flutter run
```

If Chrome opens `chrome-error://chromewebdata/` or shows an unsafe localhost/frame message, Flutter's Chrome debug launcher did not connect correctly. Run the app as a web server and open the printed URL manually:

```powershell
flutter run -d web-server --web-hostname 127.0.0.1
```

Flutter will print a local URL like this:

```text
http://127.0.0.1:62763
```

If you want to reuse a fixed port and Flutter says the port is already in use, stop the old Flutter run first by pressing `q` in its terminal, or use a different port:

```powershell
flutter run -d web-server --web-hostname 127.0.0.1 --web-port 62764
```

For Chrome or Edge web debugging on the same computer, use:

```powershell
flutter run -d chrome
```

For Android emulator, the app uses:

```dart
http://10.0.2.2:5000
```

For a real phone on the same Wi-Fi network, run with your computer IP:

```powershell
flutter run --dart-define=API_BASE_URL=http://YOUR_COMPUTER_IP:5000
```

Example:

```powershell
flutter run --dart-define=API_BASE_URL=http://192.168.1.10:5000
```

## Herbal Benefits Data

Edit:

```text
backend/ml/metadata/benefits.json
```

Add one object for each class name. The key must match the dataset folder/class name exactly:

```json
{
  "Azadirachta_indica": {
    "common_name": "Neem",
    "scientific_name": "Azadirachta indica",
    "traditional_uses": [
      "Traditionally used for skin and oral-care preparations."
    ],
    "preparation_notes": [
      "Traditional preparations vary by region and should be verified with a qualified herbal expert."
    ],
    "safety_warning": "Do not consume concentrated extracts without professional advice.",
    "medical_disclaimer": "This app is for educational plant identification only and is not medical advice."
  }
}
```

## How the 5-Image Detection Works

1. Flutter uploads selected images as `images`.
2. Flask opens every image and resizes it to `224x224`.
3. TensorFlow predicts each image.
4. The backend averages the probabilities.
5. The API returns the best plant, confidence, top 5 predictions, benefits, and safety note.

## Improving Accuracy

- Use clear photos with one plant per image.
- For each plant class, add many close-up leaf images with different angles, lighting, backgrounds, and leaf ages.
- Keep the dataset balanced. If Neem has 200 images and Aloe has 20, the model will usually favor Neem.
- Retrain after adding new images so `herb_model.keras`, `herb_model.tflite`, and `labels.json` match the dataset.
- Train with real mobile images, not only clean internet images.
- Add seed images to the training dataset if seed detection is required.
- Balance weak classes. The Kaggle dataset has some classes with very few images.
- Keep a separate test set and report test accuracy, precision, recall, and confusion matrix.
- Reject low-confidence predictions instead of forcing an answer.
- The API uses multi-crop prediction for close-up leaves, so centered leaf photos usually produce better confidence than distant plant photos.

## Recommended Research Wording

Use wording like:

"The system identifies medicinal/herbal plant species from uploaded leaf or seed images and provides educational information about traditional uses and safety precautions. The model output includes confidence values and is not intended for medical diagnosis or treatment recommendation."
