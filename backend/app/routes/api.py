import csv
import sys
from math import isfinite
from pathlib import Path

from flask import Blueprint, jsonify, request

from crs_soil.crs_soil_predict import register_soil_routes

if __package__ in (None, ''):
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from cultivation.train_recommendation import predict_top_plants

bp = Blueprint('api', __name__, url_prefix='/api')
register_soil_routes(bp)
DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'medicinal_plant_cultivation.csv'


def _load_plants():
    """Load the source cultivation dataset used for enriched plant detail responses."""
    with DATA_FILE.open(encoding='utf-8-sig', newline='') as dataset:
        plants = list(csv.DictReader(dataset))
    if not plants:
        raise ValueError('The cultivation dataset is empty.')
    return plants


def _plant_details(plant):
    return {
        'soilRequirement': plant.get('soil_requirement'),
        'wateringRequirement': plant.get('watering_requirement'),
        'plantingMethod': plant.get('planting_method'),
        'fertilizerCare': plant.get('fertilizer_care'),
        'growingPeriod': plant.get('growing_period'),
        'sellingPrice': plant.get('selling_price_lkr'),
        'harvestingInformation': plant.get('harvesting_information'),
    }


def _plant_lookup():
    return {plant['plant_name']: plant for plant in _load_plants()}


@bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'message': 'Backend is working'})


@bp.route('/ask', methods=['POST'])
def ask():
    """Placeholder for RAG Chatbot - You will implement this in your branch."""
    data = request.get_json() or {}
    query = data.get('query', '')
    return jsonify({'answer': 'This is a placeholder response. RAG functionality will be added in feature/rag branch.', 'query': query, 'sources': []})


@bp.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json(silent=True) or {}
    required = (
        'temperature',
        'rainfall',
        'humidity',
        'growingSpace',
        'budgetAmount',
        'budgetCurrency',
        'irrigationMethod',
        'growingSeason',
        'growingDuration',
    )
    missing = [field for field in required if data.get(field) in (None, '')]
    if missing:
        return jsonify({'error': 'Missing required fields', 'fields': missing}), 400

    try:
        temperature = float(data['temperature'])
        rainfall = float(data['rainfall'])
        humidity = float(data['humidity'])
        budget = float(data['budgetAmount'])
        soil_ph = data.get('soilPh')
        soil_ph = None if soil_ph in (None, '') else float(soil_ph)
    except (TypeError, ValueError):
        return jsonify({'error': 'Weather, budget, and soil pH values must be numeric'}), 400

    if not all(isfinite(value) for value in (temperature, rainfall, humidity, budget)) or budget < 0:
        return jsonify({'error': 'Weather and budget values must be valid and non-negative'}), 400
    if soil_ph is not None and (not isfinite(soil_ph) or not 0 <= soil_ph <= 14):
        return jsonify({'error': 'Soil pH must be between 0 and 14'}), 400

    data_with_defaults = dict(data)
    data_with_defaults.setdefault('soilType', 'Unknown')
    data_with_defaults.setdefault('soilPh', 6.5)
    data_with_defaults['temperature'] = temperature
    data_with_defaults['rainfall'] = rainfall
    data_with_defaults['humidity'] = humidity
    data_with_defaults['soilPh'] = soil_ph if soil_ph is not None else 6.5

    try:
        model_predictions = predict_top_plants(data_with_defaults)
    except Exception as exc:  # pragma: no cover - runtime guard for missing training assets
        return jsonify({'error': f'Could not load the trained recommendation model: {exc}'}), 500

    plant_catalog = _plant_lookup()
    recommendations = []
    for entry in model_predictions:
        plant_name = entry['plant_name']
        plant = plant_catalog.get(plant_name)
        confidence = float(entry.get('confidence', 0.0))
        percentage = float(entry.get('probability_percent', confidence * 100.0))
        recommendation = {
            'name': plant_name,
            'score': round(percentage, 2),
            'confidence': round(confidence, 6),
            'probabilityPercent': round(percentage, 2),
            'reason': f'The model assigned a probability of {percentage:.2f}% to this plant for the supplied cultivation conditions.',
            'whySuitable': f'This recommendation is based on the trained cultivation model and the model probability for this plant is {percentage:.2f}%.',
        }
        if plant is not None:
            recommendation.update(_plant_details(plant))
        recommendations.append(recommendation)

    if not recommendations:
        return jsonify({'error': 'No valid plant recommendations were returned by the trained model.'}), 500

    best_plant = recommendations[0]
    return jsonify({'bestPlant': best_plant, 'recommendations': recommendations})
