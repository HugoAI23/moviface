"""Permite importar los módulos del proyecto (en la raíz de /moviface)
desde las pruebas ubicadas en /moviface/test.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
