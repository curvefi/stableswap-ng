from math import log


def approx(x1: int, x2: int, precision: int, abs_precision=None):
    if precision >= 1:
        return True
    result = False
    if abs_precision is not None:
        result = abs(x2 - x1) <= abs_precision
    else:
        abs_precision = 0
    if x2 == 0:
        return abs(x1) <= abs_precision
    elif x1 == 0:
        return abs(x2) <= abs_precision
    return result or (abs(log(x1 / x2)) <= precision)


def get_asset_types_in_pool(pool):
    if "asset_type" in pool._immutables.__dict__.keys():
        return [pool._immutables.asset_type]
    return pool._immutables.asset_types
