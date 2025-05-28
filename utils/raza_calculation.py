from flask import jsonify
from pandas.io.pytables import performance_doc

from config import Config
import pandas as pd
import os
import numpy as np
import traceback
from decimal import Decimal, ROUND_DOWN, ROUND_UP


def calculate_raza(gender, event, athlete_class, performance, is_track=True):
    try:
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
                {"error": "No RAZA data found for this combination"}
            ), 404

        raza_row = raza_row.iloc[0]
        a = float(raza_row["a"])
        b = float(raza_row["b"])
        c = float(raza_row["c"])
        print(f"RAZA parameters: a={a}, b={b}, c={c}, performance={performance}")

        if is_track:
            exponent = -np.exp(b - (c / performance))
            score_float = a * np.exp(exponent)
            score = round_down(score_float, decimales=0)
        else:
            exponent = -np.exp(b - c * performance)
            score_float = a * np.exp(exponent)
            score = round_down(score_float, decimales=0)

        print(f"Score before rounding: {score_float}")
        print(f"Final score (rounded down): {score}")

        return jsonify({"raza_score": score})

    except Exception as e:
        print(f"Error in calculate_raza: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Calculation error: {str(e)}"}), 500


def calculate_performance(gender, event, athlete_class, raza_score, is_track=True):
    try:
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
                {"error": "No RAZA data found for this combination"}
            ), 404

        raza_row = raza_row.iloc[0]
        a = float(raza_row["a"])
        b = float(raza_row["b"])
        c = float(raza_row["c"])

        if raza_score <= 0 or raza_score >= a:
            return jsonify({"error": "Invalid RAZA score range"}), 400

        try:
            ratio = a / raza_score
            if ratio <= 1:
                return jsonify(
                    {"error": "Invalid RAZA score for calculation"}
                ), 400

            ln_ratio = np.log(ratio)
            if ln_ratio <= 0:
                return jsonify(
                    {"error": "Invalid RAZA score for calculation"}
                ), 400

            ln_ln_ratio = np.log(ln_ratio)

            if is_track:
                performance = c / (b - ln_ln_ratio)
                performance_rounded = round_down(performance, decimales=2)
            else:
                performance = (b - ln_ln_ratio) / c
                performance_rounded = round_up(performance, decimales=2)

            print(f"Performance before rounding: {performance}")

            print(f"Required {'time' if is_track else 'distance'} (rounded up): {performance_rounded}")
            return jsonify({"performance": performance_rounded})

        except (ValueError, ZeroDivisionError) as e:
            return jsonify(
                {"error": f"Mathematical error in calculation: {str(e)}"}
            ), 400

    except Exception as e:
        print(f"Error in calculate_performance: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Calculation error: {str(e)}"}), 500


def round_down(n, decimales):
    return float(
        Decimal(str(n)).quantize(
            Decimal('0.' + '0' * decimales),
            rounding=ROUND_DOWN
        )
    )


def round_up(n, decimales):
    return float(
        Decimal(str(n)).quantize(
            Decimal('0.' + '0' * decimales),
            rounding=ROUND_UP
        )
    )
