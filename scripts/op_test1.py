import time
import numpy as np
from instruments import Generator, Oscilloscope
from calculation import calculate_unity_gain_bandwidth
from plotting.bode_plot import plot_bode
import logging
import os
from datetime import datetime

log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_filename = os.path.join(log_dir, f"measurement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'), # Лог в файл
        logging.StreamHandler() # Лог в консоль
    ]
)

logger = logging.getLogger(__name__)

FREQUENCIES = [100e3, 200e3, 300e3, 500e3, 1e6, 2e6]
CH_IN, CH_OUT = 1, 2
V_AMPLITUDE = 0.6  # Амплитуда генератора (VPP)
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

def setup_instruments(scope, gen):
    logger.info(f"Инициализация оборудования: {gen.idn}, {scope.idn}")
    try:
        gen.reset()
        gen.set_waveform(CH_IN, 'SINE')
        gen.set_amplitude(V_AMPLITUDE, unit='VPP')
        gen.output_on()
        gen.set_load_impedance(10000.0)
        logger.info("Генератор настроен.")

        scope.write(":STOP")
        scope.set_channel_display(CH_IN, True)
        scope.set_channel_display(CH_OUT, True)
        scope.set_probe_attenuation(CH_IN, 10)
        scope.set_probe_attenuation(CH_OUT, 10)

        scope.set_channel_scale(1, "100mV")
        scope.set_channel_scale(2, "100mV")

        scope.write(":TRIGger:SINGle:SOURce CH1")
        scope.write(":TRIGger:SINGle:EDGE:LEVel 0")
        scope.write(":TRIGger:SINGle:MODe AUTO")

        scope.write(":ACQuire:MODE AVERage")
        scope.write(":ACQuire:AVERage:NUM 16")
        logger.info("Осциллограф настроен.")

    except Exception as e:
        logger.error(f"Ошибка при настройке приборов: {e}")
        raise

def run_measurement_cycle(scope, gen, frequencies):
    results = []
    for freq in frequencies:
        logger.info(f"Запуск теста на частоте {freq/1e6:.3f} МГц")
        gen.set_frequency(freq)
        time.sleep(3.0)
                
        time_scale = (1 / freq) * 0.2
        scope.set_horizontal_scale(format_time_scale(time_scale))
        time.sleep(2.0)

        auto_scale_channel(scope, CH_OUT)
        time.sleep(2.0)

        scope.setup_trigger()

        scope.write(":RUN")
        time.sleep(1.5)

        v_in = scope.get_vpp(CH_IN)
        v_out = scope.get_vpp(CH_OUT)

        if v_in > 0:
            gain_db = 20 * np.log10(v_out / v_in)
            logger.info(f"Результат: Vin={v_in:.3f}V, Vout={v_out:.3f}V, Gain={gain_db:.2f}dB")
            results.append({'freq': freq, 'v_in': v_in, 'v_out': v_out, 'gain': gain_db})
        else:
            logger.warning(f"Пропуск частоты {freq/1e6:.3f} МГц: амплитуда на входе 0")

    return results


def main():
    rm = Oscilloscope._get_rm()
    resources = rm.list_resources()
    logger.debug(f"Доступные приборы: {resources}")

    if len(resources) < 2:
        logger.error(f"Ошибка: Найдено приборов: {len(resources)}. Требуется минимум 2 (Генератор и Осциллограф).")
        logger.warning("Проверьте USB-кабели и питание приборов.")
        return

    
    gen_addr = resources[0]
    scope_addr = resources[1]

    try:
        with Oscilloscope(scope_addr) as scope, Generator(gen_addr) as gen:
            setup_instruments(scope, gen)
            raw_data = run_measurement_cycle(scope, gen, FREQUENCIES)
            freqs = np.array([r['freq'] for r in raw_data])
            gains = np.array([r['gain'] for r in raw_data])

            mask = gains < -2.0
            if np.any(mask):
                f_t, slope, intercept = calculate_unity_gain_bandwidth(freqs[mask], gains[mask])

                plot_bode(freqs, gains, f_t, slope, intercept)
                logger.info("--- ИТОГОВЫЕ РЕЗУЛЬТАТЫ ---")
                logger.info(f"Эксперимент завершен успешно. f_T = {f_t/1e6:.3f} МГц")
                logger.debug(f"Наклон (Slope): {slope:.2f} дБ/дек")
                if abs(slope + 20) > 5:
                    logger.warning(f"Аномальный наклон: {slope:.2f} дБ/дек. Ожидалось около -20.")
                for row in raw_data:
                    logger.info(f"{row['freq']:10.0f} | {row['v_in']:8.3f} | {row['v_out']:8.3f} | {row['gain']:8.2f}")
            else:
                logger.error("Расчет f_T невозможен: ни одна точка не попала под фильтр (gain < -2dB).")
                print("Недостаточно данных для расчета. Проверьте диапазон частот.")
    
    except Exception as e:
        logger.error("Критический сбой программы", exc_info=True)

if __name__ == "__main__":
    main()