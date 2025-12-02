def calculate_grade(avg):
    """Return grade letter for numeric average.

    Thresholds:
    - A: >= 80
    - B: >= 70
    - C: >= 60
    - D: >= 50
    - E: otherwise
    """
    try:
        if avg is None:
            return None
        avg = float(avg)
    except Exception:
        return None

    if avg >= 80:
        return "A"
    elif avg >= 70:
        return "B"
    elif avg >= 60:
        return "C"
    elif avg >= 50:
        return "D"
    else:
        return "E"


def calculate_general_remark(avg):
    """Return a short general remark string based on average.
    """
    try:
        if avg is None:
            return None
        avg = float(avg)
    except Exception:
        return None

    if avg >= 80:
        return 'Outstanding performance overall'
    elif avg >= 70:
        return 'Very good work overall'
    elif avg >= 60:
        return 'Good effort, keep improving'
    elif avg >= 50:
        return 'Fair performance, needs more focus'
    else:
        return 'Needs significant improvement'
