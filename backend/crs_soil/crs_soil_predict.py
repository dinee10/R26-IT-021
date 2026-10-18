from __future__ import annotations

from flask import jsonify, request

from .crs_soil_model import SoilClassifierService


def register_soil_routes(bp):
    @bp.route('/predict-soil', methods=['POST'])
    def predict_soil():
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'available': False,
                'model_available': False,
                'message': 'No soil image was uploaded.',
                'soil_type': None,
                'confidence': None,
                'soil_analysis': None,
            }), 400

        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({
                'success': False,
                'available': False,
                'model_available': False,
                'message': 'No soil image was uploaded.',
                'soil_type': None,
                'confidence': None,
                'soil_analysis': None,
            }), 400

        service = SoilClassifierService()
        result = service.predict(image_file)
        return jsonify(result)
