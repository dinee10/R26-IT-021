from flask import Blueprint, request, jsonify
from math import isfinite
from conversation_rag import ask_question, clear_conversation

api = Blueprint('api', __name__)

@api.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    query = data.get('query', '').strip()
    session_id = data.get('session_id', 'default')
    user_context = data.get('user_context', {})

    if not query:
        return jsonify({"error": "Query is required"}), 400

    try:
        result = ask_question(
            user_question=query,
            session_id=session_id,
            user_context=user_context
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route('/clear', methods=['POST'])
def clear():
    data = request.get_json()
    session_id = data.get('session_id', 'default')
    clear_conversation(session_id)
    return jsonify({"message": "Conversation history cleared"})


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

PLANT_DETAILS = {
    'Tulsi': ('Loamy, well-drained soil', 'Partial to full sunlight', 'Water when the topsoil feels dry', 'Sow seeds or plant a healthy cutting', 'Compost every 4 to 6 weeks', '3 to 4 months for regular leaf harvest', 'Harvest leaves and soft stems regularly'),
    'Turmeric': ('Rich, loose loamy soil', 'Partial sunlight', 'Keep soil evenly moist, never waterlogged', 'Plant healthy rhizome pieces 5 cm deep', 'Use compost or balanced fertilizer during growth', '8 to 10 months', 'Harvest when leaves turn yellow and dry'),
    'Aloe vera': ('Sandy, fast-draining soil', 'Partial to full sunlight', 'Water deeply but allow soil to dry between watering', 'Plant offsets or leaf-rooted pups', 'Light compost feed twice a year', '8 to 12 months for mature leaves', 'Cut outer leaves close to the base'),
    'Ashwagandha': ('Sandy loam with good drainage', 'Full sunlight', 'Water lightly; avoid standing water', 'Sow seeds directly in prepared soil', 'Add compost before planting and once during growth', '5 to 6 months', 'Harvest roots when leaves dry and berries mature'),
    'Neem': ('Sandy or loamy soil', 'Full sunlight', 'Water young plants regularly; mature trees need less', 'Plant fresh seeds or a nursery sapling', 'Compost once or twice yearly', '3 to 5 years for useful seed harvest', 'Collect mature seeds and prune leaves as needed'),
    'Ginger': ('Moist, rich loamy soil', 'Partial sunlight', 'Keep soil moist with regular watering', 'Plant pieces of healthy ginger rhizome', 'Compost and organic fertilizer every 6 weeks', '8 to 10 months', 'Lift rhizomes after leaves yellow'),
    'Lemongrass': ('Loamy or sandy soil', 'Full sunlight', 'Water regularly while establishing', 'Plant rooted divisions or stem cuttings', 'Add compost every 2 to 3 months', '4 to 6 months for first harvest', 'Cut outer stalks near the base'),
    'Mint': ('Moist loamy or silty soil', 'Low to partial sunlight', 'Keep soil consistently moist', 'Plant stem cuttings or rooted runners', 'Use light compost monthly', '2 to 3 months', 'Pick leaves and tips often to encourage growth'),
    'Cinnamon': ('Deep, fertile loamy soil', 'Partial to full sunlight', 'Water regularly during dry periods', 'Plant seeds or a healthy nursery sapling', 'Use compost twice yearly', '2 to 3 years for first bark harvest', 'Harvest mature bark carefully from branches'),
    'Gotu kola': ('Moist silty or loamy soil', 'Low to partial sunlight', 'Keep soil moist without flooding', 'Plant runners or stem cuttings', 'Add compost every 4 to 6 weeks', '2 to 3 months', 'Harvest leaves and runners regularly'),
}


def _choice_value(value):
    return (value or '').split(' - ', 1)[0].strip()


def _plant_details(name, reason):
    details = PLANT_DETAILS[name]
    return {
        'whySuitable': reason + '.',
        'soilRequirement': details[0],
        'sunlightRequirement': details[1],
        'wateringRequirement': details[2],
        'plantingMethod': details[3],
        'fertilizerCare': details[4],
        'growingPeriod': details[5],
        'sellingPrice': 'Varies by harvest size, quality, and your local market price.',
        'harvestingInformation': details[6],
    }


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
        soil_ph = data.get('soilPh')
        soil_ph = None if soil_ph in (None, '') else float(soil_ph)
    except (TypeError, ValueError):
        return jsonify({'error': 'Weather, budget, and soil pH values must be numeric'}), 400
    numeric_values = (temperature, rainfall, humidity, budget)
    if not all(isfinite(value) for value in numeric_values) or budget < 0:
        return jsonify({'error': 'Weather and budget values must be valid and non-negative'}), 400
    if soil_ph is not None and (not isfinite(soil_ph) or soil_ph < 0 or soil_ph > 14):
        return jsonify({'error': 'Soil pH must be between 0 and 14'}), 400

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
        if soil_ph is not None:
            if soil_ph < 6.5 and plant['name'] in ['Turmeric', 'Ginger', 'Gotu kola']:
                score += 1
                matches.append('soil pH')
            elif 6.5 <= soil_ph <= 7.5 and plant['name'] in ['Tulsi', 'Aloe vera', 'Lemongrass']:
                score += 1
                matches.append('soil pH')
        scored.append((score, plant['name'], matches))

    scored.sort(key=lambda item: (-item[0], item[1]))
    recommendations = []
    for score, name, matches in scored[:5]:
        reason = 'Matches your ' + ', '.join(matches[:3])
        recommendation = {'name': name, 'score': score, 'reason': reason}
        recommendation.update(_plant_details(name, reason))
        recommendations.append(recommendation)
    best = recommendations[0]
    return jsonify({'bestPlant': best, 'recommendations': recommendations})