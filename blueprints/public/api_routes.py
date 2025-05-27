from flask import jsonify
from flask import jsonify
from . import public_bp
from . import routes
from config import Config
import pandas as pd
import os


@public_bp.route('/api/rasa-data')
def rasa_data():
    """Return RASA data for the calculator"""
    try:
        if not os.path.exists(Config.RASA_TABLE_PATH):
            return jsonify([])

        df = pd.read_excel(Config.RASA_TABLE_PATH)

        # Convert DataFrame to list of dictionaries
        data = []
        for _, row in df.iterrows():
            data.append({
                'Event': row['Event'],
                'Gender': row['Gender'],
                'Class': row['Class'],
                'Type': row['Type'],
                'a': float(row['a']),
                'b': float(row['b']),
                'c': float(row['c']),
                'Reference': float(row['Reference'])
            })

        return jsonify(data)
    except Exception as e:
        return jsonify([])