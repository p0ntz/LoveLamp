"""
Module containing practical functions.
"""

def gcd(*numbers) -> float:
    """
    Calculate the greatest common divisor of an arbitrary amount of numbers according to 
    Euclid's algorithm and the fact that gcd(a, b, c) = gcd(gcd(a,b), c). 
    Numbers can be ints or floats.

    Returns:
        float: Greatest common divider.
    """
    
    scale_fac = _scale_to_int(numbers)

    ints = _element_scale(numbers, scale_fac)
    curr_gcd = ints[0]
    
    for i in range(1, len(ints)):
        curr_gcd = _gcd_two(curr_gcd, ints[i])
    
    return curr_gcd / scale_fac

def _gcd_two(a: int, b: int) -> int:
    """
    Helper function, calculates gcd of two integers using Euclid's algorithm.

    Args:
        a (int): First number.
        b (int): Second number.

    Returns:
        int: Greatest common divisor.
    """
    while b:
        a, b = round(a, 3), round(b, 3)     # Rounding neccessary for numeric stability
        a, b = b, a % b
    return a
    
def _scale_to_int(floats) -> int:
    """
    Finds the smallest scaling factor divisible by 10 that effectively removes all decimal points.

    Args:
        floats (collection): Collection of floats.

    Returns:
        int: Scale factor.
    """
    
    scale_fac = 1
    
    while not _all_ints(floats):
        scale_fac = scale_fac*10
        floats = _element_scale(floats, 10)
    
    return scale_fac

def _all_ints(elements) -> bool:
    """
    Investigates whether all elements in the collection is effectively an int (no decimals).
    
    Args:
        elements (collection): The collection to be tested.

    Returns:
        bool: True if no element has decimals, False otherwise.
    """
    
    for e in elements:
        if e % 1 != 0:
            return False
    return True

def _element_scale(elements, scale_fac: int) -> list:
    """
    Elementwise scaling of collection elements by scale_fac.

    Args:
        elements (collection): Collection to be scaled.
        scale_fac (int): Scaling factor.

    Returns:
        list: Same elements but scaled.
    """
    result = list()
    for e in elements:
        result.append(e*scale_fac)
    return result