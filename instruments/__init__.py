import os
import logging
from .generator import Generator
from .oscilloscope import Oscilloscope

logger = logging.getLogger(__name__)
VISA_DLL = 'C:/Windows/System32/visa32.dll'

def _check_system_deps():
    if not os.path.exists(VISA_DLL):
        logger.warning(
            f"ВНИМАНИЕ: DLL-файл VISA не найден по пути {VISA_DLL}. "
            "Убедитесь, что установлены драйверы NI-VISA или Keysight VISA."
        )
    else:
        logger.debug("Системная DLL VISA обнаружена.")

_check_system_deps()