import numpy as np

def calculate_unity_gain_bandwidth(freqs, gains_db):
    if len(freqs) < 2:
        return 0, 0, 0
    
    n = len(freqs)
    x = np.log10(freqs)
    y = gains_db
    
    # линейная аппроксимация (y = ax + b)
    slope, intercept = np.polyfit(x, y, 1)
    
    # Расчет частоты единичного усиления (точка пересечения с 0 дБ)
    log_ft = -intercept / slope
    f_t = 10**log_ft
    
    return f_t, slope, intercept