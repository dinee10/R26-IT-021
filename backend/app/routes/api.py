from flask import Blueprint, request, jsonify
from math import isfinite

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "message": "Backend is working"})

@bp.route('/ask', methods=['POST'])
def ask():
    """Placeholder for RAG Chatbot - You will implement this in your branch"""
    data = request.get_json()
    query = data.get('query', '') if data else ''
    
    return jsonify({
        "answer": "This is a placeholder response. RAG functionality will be added in feature/rag branch.",
        "query": query,
        "sources": []
    })


PLANTS = [
    {
        "name": "Tulsi",
        "soils": ["Loamy", "Silty"],
        "spaces": ["Small pot or container", "Small garden"],
        "sunlight": ["Partial", "Full"],
        "rainfall": (40, 180),
        "temperature": (20, 35),
        "durations": ["Short", "Medium"],
    },
    {
        "name": "Turmeric",
        "soils": ["Loamy", "Silty"],
        "spaces": ["Medium garden", "Large garden", "Farm or large field"],
        "sunlight": ["Partial"],
        "rainfall": (100, 300),
        "temperature": (20, 35),
        "durations": ["Medium", "Long"],
    },
    {
        "name": "Aloe vera",
        "soils": ["Sandy", "Loamy"],
        "spaces": ["Small pot or container", "Small garden"],
        "sunlight": ["Partial", "Full"],
        "rainfall": (10, 100),
        "temperature": (18, 40),
        "durations": ["Short", "Medium", "Long"],
    },
    {
        "name": "Ashwagandha",
        "soils": ["Sandy", "Loamy"],
        "spaces": ["Medium garden", "Large garden", "Farm or large field"],
        "sunlight": ["Full"],
        "rainfall": (20, 150),
        "temperature": (20, 35),
        "durations": ["Medium", "Long"],
    },
    {
        "name": "Neem",
        "soils": ["Sandy", "Loamy", "Silty"],
        "spaces": ["Large garden", "Farm or large field"],
        "sunlight": ["Full"],
        "rainfall": (40, 250),
        "temperature": (20, 40),
        "durations": ["Long"],
    },
    {
        "name": "Ginger",
        "soils": ["Loamy", "Silty"],
        "spaces": ["Small garden", "Medium garden", "Large garden"],
        "sunlight": ["Partial"],
        "rainfall": (100, 300),
        "temperature": (20, 32),
        "durations": ["Medium"],
    },
    {
        "name": "Lemongrass",
        "soils": ["Loamy", "Sandy"],
        "spaces": ["Small garden", "Medium garden", "Large garden"],
        "sunlight": ["Full"],
        "rainfall": (60, 250),
        "temperature": (20, 35),
        "durations": ["Short", "Medium"],
    },
    {
        "name": "Mint",
        "soils": ["Loamy", "Silty"],
        "spaces": ["Small pot or container", "Small garden"],
        "sunlight": ["Low", "Partial"],
        "rainfall": (60, 250),
        "temperature": (15, 30),
        "durations": ["Short", "Medium"],
    },
    {
        "name": "Cinnamon",
        "soils": ["Loamy", "Silty"],
        "spaces": ["Large garden", "Farm or large field"],
        "sunlight": ["Partial", "Full"],
        "rainfall": (100, 300),
        "temperature": (20, 35),
        "durations": ["Long"],
    },
    {
        "name": "Gotu kola",
        "soils": ["Silty", "Loamy"],
        "spaces": ["Small pot or container", "Small garden", "Medium garden"],
        "sunlight": ["Low", "Partial"],
        "rainfall": (100, 350),
        "temperature": (20, 32),
        "durations": ["Short", "Medium"],
    },
]

PREFERRED_SEASONS = {
    'Tulsi': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
    'Turmeric': ['May', 'June', 'July', 'August', 'September'],
    'Aloe vera': ['January', 'February', 'March', 'April', 'October', 'November', 'December'],
    'Ashwagandha': ['September', 'October', 'November', 'December'],
    'Neem': ['January', 'February', 'March', 'April', 'May', 'June'],
    'Ginger': ['March', 'April', 'May', 'June', 'July'],
    'Lemongrass': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August'],
    'Mint': ['September', 'October', 'November', 'December', 'January'],
    'Cinnamon': ['May', 'June', 'July', 'August', 'September', 'October'],
    'Gotu kola': ['June', 'July', 'August', 'September', 'October'],
}

CURRENCY_TO_USD = {'LKR': 0.0031, 'USD': 1, 'EUR': 1.08, 'GBP': 1.27, 'INR': 0.012, 'AUD': 0.65, 'CAD': 0.73, 'JPY': 0.0067}


def _choice_value(value):
    return (value or '').split(' - ', 1)[0].strip()


@bp.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json(silent=True) or {}
    required = ('temperature', 'rainfall', 'humidity', 'soilType', 'growingSpace',
                'budgetAmount', 'budgetCurrency', 'irrigationMethod', 'sunlight',
                'growingSeason', 'growingDuration')
    missing = [field for field in required if data.get(field) in (None, '')]
    if missing:
        return jsonify({'error': 'Missing required fields', 'fields': missing}), 400

    try:
        temperature = float(data['temperature'])
        rainfall = float(data['rainfall'])
        humidity = float(data['humidity'])
        budget = float(data['budgetAmount'])
    except (TypeError, ValueError):
        return jsonify({'error': 'Weather and budget values must be numeric'}), 400
    if not all(isfinite(value) for value in (temperature, rainfall, humidity, budget)) or budget < 0:
        return jsonify({'error': 'Weather and budget values must be valid and non-negative'}), 400

    soil = _choice_value(data['soilType'])
    space = data['growingSpace']
    sunlight = _choice_value(data['sunlight'])
    duration = _choice_value(data['growingDuration'])
    irrigation = data['irrigationMethod']
    season = data['growingSeason']
    budget_usd = budget * CURRENCY_TO_USD.get(data['budgetCurrency'], 1)
    scored = []
    for plant in PLANTS:
        score = 0
        matches = []
        if soil == 'Not sure' or soil in plant['soils']:
            score += 3
            matches.append('soil')
        if space in plant['spaces']:
            score += 3
            matches.append('growing space')
        if sunlight in plant['sunlight']:
            score += 2
            matches.append('sunlight')
        if plant['temperature'][0] <= temperature <= plant['temperature'][1]:
            score += 2
            matches.append('temperature')
        if plant['rainfall'][0] <= rainfall <= plant['rainfall'][1]:
            score += 2
            matches.append('rainfall')
        if duration in plant['durations']:
            score += 2
            matches.append('growing duration')
        if season in PREFERRED_SEASONS[plant['name']]:
            score += 1
            matches.append('planting month')
        if budget_usd < 30 and any(item in plant['spaces'] for item in ['Small pot or container', 'Small garden']):
            score += 1
            matches.append('budget')
        if budget_usd >= 150 and any(item in plant['spaces'] for item in ['Large garden', 'Farm or large field']):
            score += 1
            matches.append('budget')
        if irrigation == 'Rain only' and rainfall >= plant['rainfall'][0]:
            score += 1
            matches.append('watering method')
        elif irrigation in ['Drip irrigation', 'Sprinkler', 'Hose']:
            score += 1
            matches.append('watering method')
        if humidity >= 60 and 'Silty' in plant['soils']:
            score += 1
        scored.append((score, plant['name'], matches))

    scored.sort(key=lambda item: (-item[0], item[1]))
    recommendations = [
        {'name': name, 'score': score, 'reason': 'Matches your ' + ', '.join(matches[:3])}
        for score, name, matches in scored[:5]
    ]
    return jsonify({'recommendations': recommendations})