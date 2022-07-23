import yaml 

def debug(func):
    "Print function signature and return value"
    @functools.wraps(func)
    def wrapper_debug(*args, **kwargs):
        args_list = [repr(a) for a in args]
        kwargs_list = [f" {k}={v!r}" for k,v in kwargs.items()]
        signature = ", ".join(args_list + kwargs_list)
        print(f"Calling {func.__name__}({signature})")
        value = func(*args, **kwargs)
        print(f"{func.__name__!r} returned {value!r}")
        return value
    return wrapper_debug

def set_unit(unit):
    """Register a unit on a function"""
    def decorator_set_unit(func):
        func.unit = unit
        return func
    return decorator_set_unit

def singleton(cls):
    """ make a class a Singleton class (only one istance allowed) """
    @functools.wraps(cls)
    def wrapper_singleton(*args, **kwargs):
        if not wrapper_singleton.istance:
            wrapper_singleton.istance = cls(*args, **kwargs)
        return wrapper_singleton.istance

    wrapper_singleton.istance = None
    return wrapper_singleton

