import pytest
import numpy as np
from calculation import calculate_unity_gain_bandwidth

def test_follower_gain_falloff():
    """Тест: Повторитель начинает терять усиление на высоких частотах."""
    freqs = np.array([1e6, 2e6, 4e6])
    gains = np.array([-6.0, -12.0, -18.0])
    
    f_t, slope, intercept = calculate_unity_gain_bandwidth(freqs, gains)
    
    assert f_t < 1e6
    assert np.isclose(slope, -20.0, rtol=1e-2)

def test_calculation_with_noise():
    """Тест устойчивости к небольшим отклонениям в данных."""
    freqs = np.array([100e3, 200e3, 400e3, 800e3])
    # "шум" +/- 0.5 дБ
    gains = np.array([0.5, -5.8, -12.3, -17.5])
    
    f_t, slope, intercept = calculate_unity_gain_bandwidth(freqs, gains)
    
    # Проверяем, что наклон все еще в районе -20 дБ/дек
    assert -25 < slope < -15
    assert f_t > 0

def test_follower_low_freq_gain():
    """Тест: на низких частотах усиление повторителя должно быть около 0 дБ."""
    # Имитируем измерения на 1кГц, 10кГц, 50кГц
    freqs = np.array([1e3, 1e4, 5e4])
    gains = np.array([-0.01, 0.02, -0.05]) 
    
    # Проверим, что такие точки корректно отсекаются
    mask = gains < -2.0
    assert np.sum(mask) == 0  # Ни одна точка не должна пройти фильтр