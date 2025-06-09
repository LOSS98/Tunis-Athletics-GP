from flask import jsonify
from config import Config
import pandas as pd
import os
import numpy as np
import traceback
from decimal import Decimal, ROUND_DOWN, ROUND_UP
def verify_combination(gender, event, athlete_class):
    try:
        gender = gender_mapping(gender)
        if not os.path.exists(Config.RAZA_TABLE_PATH):
            print(f"RAZA table not found at: {Config.RAZA_TABLE_PATH}")
            return False
        df = pd.read_excel(Config.RAZA_TABLE_PATH)
        mask = (
                (df["Event"] == event)
                & (df["Class"] == athlete_class)
                & (df["Gender"] == gender)
        )
        raza_row = df[mask]
        return not raza_row.empty
    except Exception as e:
        print(f"Error in verify_combination: {str(e)}")
        traceback.print_exc()
        return False
def calculate_raza(gender, event, athlete_class, performance):
    try:
        gender = gender_mapping(gender)
        if not os.path.exists(Config.RAZA_TABLE_PATH):
            return jsonify({"error": "RAZA table not found"}), 404
        df = pd.read_excel(Config.RAZA_TABLE_PATH)
        mask = (
                (df["Event"] == event)
                & (df["Class"] == athlete_class)
                & (df["Gender"] == gender)
        )
        raza_row = df[mask]
        if raza_row.empty:
            return jsonify(
                {"error": f"No RAZA data found for {gender} {event} {athlete_class}"}
            ), 404
        raza_row = raza_row.iloc[0]
        required_cols = ['a', 'b', 'c']
        for col in required_cols:
            if col not in raza_row or pd.isna(raza_row[col]):
                return jsonify({"error": f"Missing or invalid RAZA coefficient '{col}'"}), 400
        a = float(raza_row["a"])
        b = float(raza_row["b"])
        c = float(raza_row["c"])
        if performance <= 0:
            return jsonify({"error": "Performance must be positive"}), 400
        try:
            if event in Config.get_track_events():
                exponent = -np.exp(b - (c / performance))
                score_float = a * np.exp(exponent)
            else:
                exponent = -np.exp(b - c * performance)
                score_float = a * np.exp(exponent)
            score_rounded = int(round_down(score_float, decimales=0))
            score_precise = round(score_float, 3)
            if score_rounded < 0 or score_rounded > 2000:
                return jsonify({"error": "Calculated score out of valid range"}), 400
            return jsonify({
                "raza_score": score_rounded,
                "raza_score_precise": score_precise
            })
        except (OverflowError, ValueError) as e:
            return jsonify({"error": f"Mathematical calculation error: {str(e)}"}), 400
    except Exception as e:
        print(f"Error in calculate_raza: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Calculation error: {str(e)}"}), 500
def calculate_performance(gender, event, athlete_class, raza_score):
    try:
        gender = gender_mapping(gender)
        if not os.path.exists(Config.RAZA_TABLE_PATH):
            return jsonify({"error": "RAZA table not found"}), 404
        df = pd.read_excel(Config.RAZA_TABLE_PATH)
        mask = (
                (df["Event"] == event)
                & (df["Class"] == athlete_class)
                & (df["Gender"] == gender)
        )
        raza_row = df[mask]
        if raza_row.empty:
            return jsonify(
                {"error": f"No RAZA data found for {gender} {event} {athlete_class}"}
            ), 404
        raza_row = raza_row.iloc[0]
        required_cols = ['a', 'b', 'c']
        for col in required_cols:
            if col not in raza_row or pd.isna(raza_row[col]):
                return jsonify({"error": f"Missing or invalid RAZA coefficient '{col}'"}), 400
        a = float(raza_row["a"])
        b = float(raza_row["b"])
        c = float(raza_row["c"])
        if raza_score <= 0 or raza_score >= a:
            return jsonify({"error": f"RAZA score must be between 0 and {int(a)}"}), 400
        try:
            ratio = a / raza_score
            if ratio <= 1:
                return jsonify({"error": "Invalid RAZA score for calculation"}), 400
            ln_ratio = np.log(ratio)
            if ln_ratio <= 0:
                return jsonify({"error": "Invalid RAZA score for calculation"}), 400
            ln_ln_ratio = np.log(ln_ratio)
            if event in Config.get_track_events():
                performance = c / (b - ln_ln_ratio)
                performance_rounded = round_up(performance, decimales=2)
            else:
                performance = (b - ln_ln_ratio) / c
                performance_rounded = round_up(performance, decimales=2)
            if performance_rounded <= 0:
                return jsonify({"error": "Calculated performance is invalid"}), 400
            return jsonify({"performance": performance_rounded})
        except (ValueError, ZeroDivisionError, OverflowError) as e:
            return jsonify({"error": f"Mathematical error in calculation: {str(e)}"}), 400
    except Exception as e:
        print(f"Error in calculate_performance: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Calculation error: {str(e)}"}), 500
def round_down(n, decimales):
    try:
        return float(
            Decimal(str(n)).quantize(
                Decimal('0.' + '0' * decimales),
                rounding=ROUND_DOWN
            )
        )
    except:
        return float(n)
def round_up(n, decimales):
    try:
        return float(
            Decimal(str(n)).quantize(
                Decimal('0.' + '0' * decimales),
                rounding=ROUND_UP
            )
        )
    except:
        return float(n)
def gender_mapping(gender):
    gender_map = {
        'Male': 'Men',
        'Female': 'Women',
        'M': 'Men',
        'F': 'Women',
        'Men': 'Men',
        'Women': 'Women'
    }
    return gender_map.get(gender, gender)
