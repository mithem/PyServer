import json
import random
import sys

import serverly
import serverly.statistics
import serverly.utils


def validate(data: dict, l: int):
    assert data["len"] == l

    assert data["max"] >= data["mean"]
    assert data["max"] >= data["min"]

    assert data["mean"] >= data["min"]


def test_new_statistic():
    serverly.statistics.reset()
    n = random.randint(200, 1000)
    func_names = []
    for i in range(n):
        s = serverly.utils.ranstr()
        func_names.append(s)
        serverly.statistics.new_statistic(s, random.random() * 50)
    for i in func_names:
        validate(serverly.statistics.endpoint_performance[i], 1)
    validate(serverly.statistics.overall_performance, n)


def test_new_statistic_2():
    serverly.statistics.reset()
    n = 2  # random.randint(10, 100)
    print("n:", n)
    _sum = 0
    funcs = {}
    for i in range(n):
        s = serverly.utils.ranstr()
        o = 2  # random.randint(0, 9)
        _sum += o
        funcs[s] = o
        for j in range(o):
            serverly.statistics.new_statistic(s, random.random() * 75)

    assert list(funcs.keys()).sort() == list(
        serverly.statistics.endpoint_performance.keys()).sort()

    for k, v in funcs.items():
        validate(serverly.statistics.endpoint_performance[k], v)
    print(serverly.statistics.overall_performance)
    validate(serverly.statistics.overall_performance, _sum)


def test_print_stats(capsys):
    serverly.statistics.reset()
    serverly.statistics.print_stats()
    out, err = capsys.readouterr()
    print(out, err)
    sys.stdout.write(out)
    sys.stderr.write(err)
    assert "No statistics." in out

    serverly.statistics.new_statistic("hello", 10.0)
    serverly.statistics.print_stats()

    out, err = capsys.readouterr()
    sys.stdout.write(out)
    sys.stderr.write(err)
    for i in ["len", "mean", "max", "min"]:
        assert i in out

    with open(serverly.statistics.filename, "r") as f:
        assert json.load(f) == {"overall_performance": serverly.statistics.overall_performance,
                                "endpoint_performance": serverly.statistics.endpoint_performance}
