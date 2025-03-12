import math
import random

def position_pairs(arr: list[tuple], cmp=lambda x, y: x < y):
    """
    Returns a list of boolean values, where each value indicates whether the comparisons of the two elements in the
    tuple in order AB and BA were consistent.

    :param arr: List of tuples, where each tuple contains two elements to compare.
    :param cmp: Comparison function (Lambda) that compares two elements.

    :return: List of boolean values, where each value indicates whether the comparisons of the two elements in the
    tuple in order AB and BA were consistent.
    """
    a: list[bool] = []

    for element in arr:
        ab_result = cmp(element[0], element[1])
        ba_result = cmp(element[1], element[0])
        a.append(ab_result is not ba_result)

    return a
