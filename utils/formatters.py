STANDARD_SCALES = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]

def auto_scale_channel(scope, channel):
    """Подбирает оптимальный масштаб для канала на основе текущего VPP."""
    v_raw = scope.get_vpp(channel)
    if v_raw <= 0: return
    
    # Цель: сигнал на 5 делений из 8
    target = v_raw / 5.0
    best_scale = next((s for s in STANDARD_SCALES if s >= target), STANDARD_SCALES[-1])
    
    scale_str = f"{int(best_scale*1000)}mV" if best_scale < 1 else f"{int(best_scale)}V"
    scope.set_channel_scale(channel, scale_str)

def format_time_scale(seconds):
    if seconds >= 1:
        return f"{seconds:.1f}s"
    elif seconds >= 1e-3:
        return f"{seconds * 1e3:.1f}ms"
    elif seconds >= 1e-6:
        return f"{seconds * 1e6:.1f}us"
    else:
        return f"{seconds * 1e9:.1f}ns"