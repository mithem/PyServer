import numpy as np
from tabulate import tabulate
import signal
import json

calculation_times = []


def print_stats():
    a = np.array(calculation_times)
    a *= 1000  # milliseconds
    try:
        calc_times = {
            "requests/responses": len(a),
            "avg": np.average(a),
            "max": np.max(a),
            "min": np.min(a),
            "median": np.median(a)
        }
        print("\n\nCalculation times (ms):\n")
        print(tabulate([calc_times.values()], tuple(calc_times.keys())))
        with open("statistics.json", "w+") as f:
            json.dump(
                {"calculation_times": {"stats": calc_times, "raw": calculation_times}}, f)
    except ValueError:
        print("No statistics.")
