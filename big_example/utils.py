import datetime

def get_current_timestamp() -> str:
    """
    Returns the current timestamp as a string.
    """
    return datetime.datetime.now().isoformat()
