# utils.py

def format_date(date_str_or_ts):
    """Format date from ISO or timestamp to DD/MM/YYYY"""
    from datetime import datetime
    try:
        if isinstance(date_str_or_ts, (int, float)):
            return datetime.utcfromtimestamp(date_str_or_ts).strftime("%Y-%m-%d")
        return datetime.fromisoformat(date_str_or_ts.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return ""

def convert_bool(value):
    """Convert boolean to Yes/No"""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return "Yes" if str(value).lower() == "true" else "No"

def convert_autorenew(value):
    """Convert autorenew boolean to On/Off"""
    if isinstance(value, bool):
        return "On" if value else "Off"
    return "On" if str(value).lower() == "true" else "Off"
