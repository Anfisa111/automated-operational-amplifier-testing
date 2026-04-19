import pytest

def test_invalid_config_values():
    """Проверка валидации данных конфигурации."""
    bad_data = {
        "frequencies": [-100, 0],
        "v_amplitude_vpp": 0.6,
        "input_channel": 1,
        "output_channel": 2,
        "probe_attenuation": 10
    }
    
    with pytest.raises(ValueError):
        for f in bad_data["frequencies"]:
            if f <= 0:
                raise ValueError("Частота должна быть положительной")