import math
from typing import Any

def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively replaces NaN, Infinity, -Infinity, and NaT with None or safe primitives for valid JSON.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, tuple):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, set):
        return [sanitize_for_json(v) for v in obj]
    return obj
