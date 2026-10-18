from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / 'data'
ORIGINAL_DATA_PATH = DATA_DIR / 'medicinal_plant_cultivation.csv'
EXPANDED_DATA_PATH = DATA_DIR / 'medicinal_plant_cultivation_expanded.csv'
MODEL_PATH = BASE_DIR / 'cultivation' / 'models' / 'recommendation_model.joblib'
PREPROCESSOR_PATH = BASE_DIR / 'cultivation' / 'preprocessing' / 'recommendation_preprocessor.joblib'
FEATURES_PATH = BASE_DIR / 'cultivation' / 'preprocessing' / 'feature_columns.json'
METRICS_PATH = BASE_DIR / 'cultivation' / 'models' / 'recommendation_metrics.json'
TARGET_COLUMN = 'plant_name'

NUMERIC_COLUMNS = [
    'temperature_c',
    'rainfall_mm',
    'humidity_pct',
    'soil_ph',
    'budget_lkr',
]
CATEGORICAL_COLUMNS = [
    'soil_type',
    'growing_space',
    'irrigation_method',
    'growing_season',
    'growing_duration',
]
FEATURE_COLUMNS = NUMERIC_COLUMNS + CATEGORICAL_COLUMNS


def load_original_dataset() -> pd.DataFrame:
    return pd.read_csv(ORIGINAL_DATA_PATH)


def _split_values(raw_value):
    if pd.isna(raw_value):
        return []
    return [item.strip() for item in str(raw_value).split(';') if item.strip()]


def _float_range(min_value, max_value, factor):
    if max_value == min_value:
        return float(min_value)
    return float(min_value + (max_value - min_value) * factor)


def build_expanded_dataset() -> pd.DataFrame:
    """Create a valid ML training table from the existing plant profile dataset.

    The original file describes each plant's agronomic compatibility range rather than
    historical user outcomes. To train a classification model, this function expands the
    per-plant ranges into multiple condition examples while keeping all values inside
    each plant's scientifically reasonable limits.
    """
    df = load_original_dataset()
    rows = []

    for _, row in df.iterrows():
        soil_choices = _split_values(row['soil_types'])
        irrigation_choices = _split_values(row['irrigation'])
        space_choices = _split_values(row['growing_spaces'])
        month_choices = _split_values(row['planting_months'])
        duration_choices = _split_values(row['growing_durations'])

        if not soil_choices:
            soil_choices = ['Loamy']
        if not irrigation_choices:
            irrigation_choices = ['Hand watering']
        if not space_choices:
            space_choices = ['1-5 perches']
        if not month_choices:
            month_choices = ['January']
        if not duration_choices:
            duration_choices = ['Medium']

        factors = [0.2, 0.5, 0.8, 1.0]
        for idx, factor in enumerate(factors):
            soil_type = soil_choices[idx % len(soil_choices)]
            irrigation_value = irrigation_choices[idx % len(irrigation_choices)]
            space_value = space_choices[idx % len(space_choices)]
            season_value = month_choices[idx % len(month_choices)]
            duration_value = duration_choices[idx % len(duration_choices)]

            temp_min = float(row['temperature_min_c'])
            temp_max = float(row['temperature_max_c'])
            rainfall_min = float(row['rainfall_min_mm'])
            rainfall_max = float(row['rainfall_max_mm'])
            humidity_min = float(row['humidity_min_pct'])
            humidity_max = float(row['humidity_max_pct'])
            ph_min = float(row['soil_ph_min'])
            ph_max = float(row['soil_ph_max'])
            budget_base = int(row['minimum_budget_lkr'])

            rows.append(
                {
                    'source_plant': row['plant_name'],
                    'plant_name': row['plant_name'],
                    'temperature_c': round(_float_range(temp_min, temp_max, factor), 1),
                    'rainfall_mm': round(_float_range(rainfall_min, rainfall_max, factor), 1),
                    'humidity_pct': round(_float_range(humidity_min, humidity_max, factor), 1),
                    'soil_ph': round(_float_range(ph_min, ph_max, factor), 2),
                    'soil_type': soil_type,
                    'growing_space': space_value,
                    'budget_lkr': int(round(budget_base * (0.85 + (factor * 0.35)))),
                    'irrigation_method': irrigation_value,
                    'growing_season': season_value,
                    'growing_duration': duration_value,
                }
            )

    expanded = pd.DataFrame(rows)
    expanded = expanded[FEATURE_COLUMNS + [TARGET_COLUMN, 'source_plant']]
    expanded.to_csv(EXPANDED_DATA_PATH, index=False)
    return expanded


def _build_preprocessor():
    numeric_transformer = Pipeline(
        steps=[
            ('imputer', SimpleImputer(strategy='median')),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ('numeric', numeric_transformer, NUMERIC_COLUMNS),
            ('categorical', categorical_transformer, CATEGORICAL_COLUMNS),
        ],
        remainder='drop',
    )


def _build_model(name: str):
    models = {
        'random_forest': RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            class_weight='balanced',
            n_jobs=-1,
        ),
        'decision_tree': DecisionTreeClassifier(
            random_state=42,
            class_weight='balanced',
        ),
        'gradient_boosting': GradientBoostingClassifier(
            random_state=42,
        ),
    }
    return models[name]


def train_and_evaluate_models():
    dataset = build_expanded_dataset()
    X = dataset[FEATURE_COLUMNS]
    y = dataset[TARGET_COLUMN]

    # Keep every plant class represented in both sets. The expanded records are
    # synthetic variants of each plant profile, so holding out entire plants would
    # test classes the classifier was never trained to recognize.
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    results = []
    for model_name in ['random_forest', 'decision_tree', 'gradient_boosting']:
        preprocessor = _build_preprocessor()
        model = _build_model(model_name)
        pipeline = Pipeline(
            steps=[('preprocessor', preprocessor), ('classifier', model)]
        )

        pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)

        metrics = {
            'model': model_name,
            'accuracy': round(float(accuracy_score(y_test, predictions)), 4),
            'precision_weighted': round(float(precision_score(y_test, predictions, average='weighted', zero_division=0)), 4),
            'recall_weighted': round(float(recall_score(y_test, predictions, average='weighted', zero_division=0)), 4),
            'f1_weighted': round(float(f1_score(y_test, predictions, average='weighted', zero_division=0)), 4),
            'confusion_matrix': confusion_matrix(y_test, predictions, labels=sorted(y.unique())).tolist(),
        }
        results.append(metrics)

    best_name = max(results, key=lambda item: item['f1_weighted'])['model']
    best_model = _build_model(best_name)
    final_preprocessor = _build_preprocessor()
    final_pipeline = Pipeline(steps=[('preprocessor', final_preprocessor), ('classifier', best_model)])
    final_pipeline.fit(X, y)

    joblib.dump(final_pipeline, MODEL_PATH)
    joblib.dump(final_preprocessor, PREPROCESSOR_PATH)
    with FEATURES_PATH.open('w', encoding='utf-8') as file:
        json.dump(FEATURE_COLUMNS, file, indent=2)

    with METRICS_PATH.open('w', encoding='utf-8') as file:
        json.dump({'results': results, 'best_model': best_name}, file, indent=2)

    return {
        'best_model': best_name,
        'results': results,
        'feature_columns': FEATURE_COLUMNS,
        'model_path': str(MODEL_PATH),
    }


def load_model_bundle():
    if not MODEL_PATH.exists() or not PREPROCESSOR_PATH.exists():
        train_and_evaluate_models()

    model = joblib.load(MODEL_PATH)
    feature_columns = json.loads(FEATURES_PATH.read_text(encoding='utf-8'))
    return model, feature_columns


def predict_top_plants(input_payload: dict):
    model, feature_columns = load_model_bundle()
    records = []

    income_raw = input_payload.get('budgetAmount')
    if income_raw in (None, ''):
        budget_lkr = 0
    else:
        try:
            budget_lkr = float(income_raw)
        except (TypeError, ValueError):
            budget_lkr = 0

    currency = (input_payload.get('budgetCurrency') or 'LKR').upper()
    currency_map = {'LKR': 1.0, 'USD': 160.0, 'EUR': 180.0, 'GBP': 210.0, 'INR': 1.9, 'AUD': 100.0, 'CAD': 116.0, 'JPY': 1.1}
    budget_lkr = budget_lkr * currency_map.get(currency, 1.0)

    row = {
        'temperature_c': float(input_payload.get('temperature', 25)),
        'rainfall_mm': float(input_payload.get('rainfall', 120)),
        'humidity_pct': float(input_payload.get('humidity', 65)),
        'soil_ph': float(input_payload.get('soilPh', 6.5)),
        'soil_type': (input_payload.get('soilType') or 'Unknown').strip() or 'Unknown',
        'growing_space': (input_payload.get('growingSpace') or '1-5 perches').strip() or '1-5 perches',
        'budget_lkr': int(round(budget_lkr)),
        'irrigation_method': (input_payload.get('irrigationMethod') or 'Hand watering').strip() or 'Hand watering',
        'growing_season': (input_payload.get('growingSeason') or 'January').strip() or 'January',
        'growing_duration': (input_payload.get('growingDuration') or 'Medium').strip() or 'Medium',
    }

    records.append(row)
    frame = pd.DataFrame(records, columns=feature_columns)
    probabilities = model.predict_proba(frame)
    top_indices = probabilities[0].argsort()[-5:][::-1]
    classes = model.named_steps['classifier'].classes_

    output = []
    for idx in top_indices:
        class_name = classes[idx]
        confidence = float(probabilities[0][idx])
        percentage = round(confidence * 100.0, 2)
        output.append({
            'plant_name': class_name,
            'confidence': round(confidence, 6),
            'score': percentage,
            'probability_percent': percentage,
        })

    return output


if __name__ == '__main__':
    result = train_and_evaluate_models()
    print(json.dumps(result, indent=2))
