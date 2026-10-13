"""Xadrez Wallpaper — partidas lendárias de xadrez no papel de parede do GNOME."""

import os
import sys

__version__ = "1.0.0"

# python-chess vai embutido (não existe nos repositórios do Ubuntu)
_VENDOR = os.path.join(os.path.dirname(__file__), "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)
