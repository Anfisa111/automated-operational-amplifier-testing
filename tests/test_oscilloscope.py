import pytest
from unittest.mock import MagicMock
from instruments.oscilloscope import Oscilloscope

def test_oscilloscope_scale_command():
    """Проверка команд установки вертикальной развертки."""
    mock_instr = MagicMock()
    scope = Oscilloscope("USB0::FAKE")
    scope.instrument = mock_instr
    
    scope.set_channel_scale(1, "200mV")
    mock_instr.write.assert_called_with(":CH1:SCALe 200mV")

def test_oscilloscope_vpp_parsing():
    """Тест парсинга научной нотации (1.020E+00 -> 1.02)."""
    mock_instr = MagicMock()
    scope = Oscilloscope("USB0::FAKE")
    scope.instrument = mock_instr
    
    # Имитируем типичный ответ осциллографа
    mock_instr.query.return_value = "1.020E+00"
    
    vpp = scope.get_vpp(1)
    
    assert vpp == 1.02
    mock_instr.query.assert_called_with(":MEASUrement:CH1:PKPK?")

def test_oscilloscope_vpp_error_handling():
    """Тест поведения при пустом ответе или ошибке."""
    mock_instr = MagicMock()
    scope = Oscilloscope("USB0::FAKE")
    scope.instrument = mock_instr
    
    # Имитируем мусор в ответе
    mock_instr.query.return_value = "???"
    
    vpp = scope.get_vpp(1)
    
    assert vpp == 0.0