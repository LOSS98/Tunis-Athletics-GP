from flask import render_template, request, jsonify
from config import Config
import pandas as pd
import os
import numpy as np
import traceback
from utils.raza_calculation import calculate_raza, calculate_performance
def register_routes(bp):
    @bp.route('/raza')
    def raza():
        return render_template('public/raza.html')
    @bp.route('/api/raza-data')
    def get_raza_data():
        try:
            if not os.path.exists(Config.RAZA_TABLE_PATH):
                print(f"RAZA table not found at: {Config.RAZA_TABLE_PATH}")
                return jsonify([])
            df = pd.read_excel(Config.RAZA_TABLE_PATH)
            data = df.to_dict('records')
            for row in data:
                for key, value in row.items():
                    if pd.isna(value):
                        row[key] = None
                    elif isinstance(value, np.integer):
                        row[key] = int(value)
                    elif isinstance(value, np.floating):
                        row[key] = float(value)
            print(f"Successfully loaded {len(data)} RAZA table entries")
            return jsonify(data)
        except Exception as e:
            print(f"Error in get_raza_data: {str(e)}")
            traceback.print_exc()
            return jsonify([])
    @bp.route('/api/calculate-raza', methods=['POST'])
    def calculate_raza_api():
        try:
            if not request.is_json:
                return jsonify({'error': 'Invalid request format, expected JSON'}), 400
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            gender = data.get('gender')
            event = data.get('event')
            athlete_class = data.get('class')
            performance_raw = data.get('performance')
            if not all([gender, event, athlete_class]):
                return jsonify({'error': 'Missing required fields (gender, event, class)'}), 400
            try:
                performance = float(performance_raw) if performance_raw is not None else 0
                if performance <= 0:
                    return jsonify({'error': 'Performance must be a positive number'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid performance value - must be a number'}), 400
            return calculate_raza(gender, event, athlete_class, performance)
        except Exception as e:
            print(f"Error in calculate_raza_api: {str(e)}")
            traceback.print_exc()
            return jsonify({'error': f'Server error: {str(e)}'}), 500
    @bp.route('/api/calculate-performance', methods=['POST'])
    def calculate_performance_api():
        try:
            if not request.is_json:
                return jsonify({'error': 'Invalid request format, expected JSON'}), 400
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            gender = data.get('gender')
            event = data.get('event')
            athlete_class = data.get('class')
            raza_score_raw = data.get('raza_score')
            if not all([gender, event, athlete_class]):
                return jsonify({'error': 'Missing required fields (gender, event, class)'}), 400
            try:
                raza_score = float(raza_score_raw) if raza_score_raw is not None else 0
                if raza_score <= 0:
                    return jsonify({'error': 'RAZA score must be a positive number'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid RAZA score value - must be a number'}), 400
            return calculate_performance(gender, event, athlete_class, raza_score)
        except Exception as e:
            print(f"Error in calculate_performance_api: {str(e)}")
            traceback.print_exc()
            return jsonify({'error': f'Server error: {str(e)}'}), 500