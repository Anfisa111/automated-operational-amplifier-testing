import time
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Полная и точная сетка таймбейзов для OWON SDS1022
OWON_TIME_SCALES = [
    5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9, 500e-9,
    1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6, 200e-6, 500e-6,
    1e-3, 2e-3, 5e-3, 10e-3, 20e-3, 50e-3, 100e-3, 200e-3, 500e-3,
    1.0, 2.0, 5.0, 10.0
]

# Полный ряд вертикальных шкал (Вольт/деление)
STANDARD_SCALES = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]

def format_time_scale_by_freq(freq: float) -> str:
    """Определяет масштаб времени, чтобы на экране (15 делений) было ~3 периода."""
    period = 1.0 / freq
    target_scale = (period * 3) / 15.0  
    
    # Ищем ближайший подходящий масштаб (сверху)
    best_scale = OWON_TIME_SCALES[-1]
    for s in OWON_TIME_SCALES:
        if s >= target_scale:
            best_scale = s
            break
            
    if best_scale >= 1:
        return f"{best_scale:.1f}s"
    elif best_scale >= 1e-3:
        return f"{best_scale * 1e3:.0f}ms"
    elif best_scale >= 1e-6:
        return f"{best_scale * 1e6:.0f}us"
    else:
        return f"{best_scale * 1e9:.0f}ns"

def auto_scale_channel(scope, channel: int) -> None:
    """
    Интеллектуальный автоскейл по вертикали. 
    Стремится уложить сигнал в 60-80% высоты экрана (примерно 5.5 - 6.5 делений из 8).
    """
    max_attempts = 4
    for attempt in range(max_attempts):
        v_raw = scope.get_vpp(channel)
        
        # Если сигнал "зашкаливает" (перегрузка АЦП) или не виден
        if v_raw <= 0.001 or v_raw > 50.0:
            # На первой попытке прижмем масштаб вверх, чтобы увидеть сигнал
            initial_fallback = "2V" if attempt == 0 else "200mV"
            logger.debug(f"CH{channel} перегружен/отсутствует ({v_raw}V). Сброс на {initial_fallback}")
            scope.set_channel_scale(channel, initial_fallback)
            time.sleep(0.15)
            continue
            
        # Рассчитываем идеальный вольт/деление (экран = 8 делений)
        target_v_per_div = v_raw / 6.0
        
        # Находим оптимальную шкалу из доступных
        best_scale = STANDARD_SCALES[-1]
        for s in STANDARD_SCALES:
            if s >= target_v_per_div:
                best_scale = s
                break
                
        scale_str = f"{int(best_scale*1000)}mV" if best_scale < 1 else f"{int(best_scale)}V"
        scope.set_channel_scale(channel, scale_str)
        time.sleep(0.1) # Даем АЦП стабилизироваться
        break