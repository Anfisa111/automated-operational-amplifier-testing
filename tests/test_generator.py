import pytest
from unittest.mock import MagicMock
from instruments.generator import Generator

def test_generator_amplitude_command():
    """Проверяем, что генератор отправляет верную команду установки амплитуды."""
    mock_instr = MagicMock()
    
    gen = Generator("USB0::FAKE")
    gen.instrument = mock_instr
    gen.channel = 1
    
    gen.set_amplitude(0.6, unit='VPP')

    mock_instr.write.assert_called_with(":CHANnel1:BASE:AMPLitude 0.6")

def test_generator_scpi_commands():
    """Проверка, что генератор отправляет правильные команды установки частоты."""
    mock_instr = MagicMock()
    gen = Generator("USB0::FAKE")
    gen.instrument = mock_instr
    gen.channel = 1
    
    gen.set_frequency(1500)
    mock_instr.write.assert_called_with(":CHANnel1:BASE:FREQuency 1500")
