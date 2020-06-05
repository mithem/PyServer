import numpy as np
from tabulate import tabulate
import signal
import json

filename = "statistics.json"

overall_performance = {
    "min": 100000000000.0,
    "max": 0.0,
    "mean": 0.0,
    "len": 0
}

endpoint_performance = {}


def new_statistic(function: str, time: float):
    """Register a new statistic both for the specific endpoint as well as the overall server performance.

    :param function: function serving the endpoint
    :param response_time: (calc) time of the function + serverly in seconds
    :type function: str
    :type time: flloat
    """
    global overall_performance, endpoint_performance

    def refresh_stats(s: dict):
        d = s.copy()
        d["len"] += 1
        if d["len"] > 1:
            d["min"] = d["min"] if d["min"] < t else t
            d["max"] = d["max"] if d["max"] > t else t
            d["mean"] = (d["mean"] * (d["len"] - 1) + t) / d["len"]
        else:
            d["min"] = t
            d["max"] = t
            d["mean"] = t
        return d
    t = time * 1000
    endpoint_performance[function] = refresh_stats(endpoint_performance.get(
        function, {"min": 100000000000.0, "max": 0.0, "mean": 0.0, "len": 0}))
    overall_performance = refresh_stats(overall_performance)


def print_stats():
    """Print statistics saved in this module."""
    if overall_performance["len"] > 0:
        print("\n\nCalculation times (ms):\n")
        print(tabulate([overall_performance.values()],
                       tuple(overall_performance.keys())))
    else:
        print("No statistics.")
    with open(filename, "w+") as f:
        json.dump({"overall_performance": overall_performance,
                   "endpoint_performance": endpoint_performance}, f)
