"""
Module containing some tuples with RGB values between 0 and 255, each describing a
color at maximum brightness. Also contains some supporting functions for color manipulation.
"""

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
PURPLE = (255, 0, 255)
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 50, 0)
PINK = (255, 30, 30)
YELLOWORANGE = (255, 100, 0)
ORANGERED = (255, 25, 0)
CERISE = (255, 0, 50)
REDPURPLE = (255, 0, 150)
OFF = (0, 0, 0)

def color_mix(c1: tuple, c2: tuple) -> tuple:
    """
    Returns RGB tuple of the resulting mix from inputted colors.

    Args:
        c1 (tuple): Color 1
        c2 (tuple): Color 2

    Returns:
        tuple: Maximum brightness color consisting of a mix of c1 and c2
            (derived from elementwise mean and normalized)
    """
    
    cm = tuple(int(a + b) for a, b in zip(c1, c2))      #Elementwise sum
    cm = tuple(int(a*255/max(cm)) for a in cm)          #Normalization to 255
    return cm

def dim(fac, color):
    """
    
    Dims a color with specified factor.

    Args:
        fac (float): Factor by which the color should be dimmed.
        color (tuple): Color that should be dimmed.
        
    Returns:
        tuple: RGB tuple of dimmed color.
    """
    dimmed_color = tuple(int(a*fac) for a in color)
    return dimmed_color