import functools

def setup(*args, **kwargs):
    pass

def setup_api_key(*args, **kwargs):
    return True

def check_api_key_status(*args, **kwargs):
    return {
        'has_api_key': True,
        'api_key_preview': 'dummy***key',
        'tier': 'community',
        'limits': {'per_minute': 60}
    }

def accept_license_terms(*args, **kwargs):
    pass

def optimize_execution(*args, **kwargs):
    """
    Dummy decorator for optimize_execution.
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*wargs, **wkwargs):
            return f(*wargs, **wkwargs)
        return wrapper

    if len(args) == 1 and callable(args[0]):
        # Called as @optimize_execution without parentheses
        return decorator(args[0])
    
    # Called as @optimize_execution(...) with arguments
    return decorator

# Alias — some vnstock_data modules import agg_execution from vnai
agg_execution = optimize_execution
