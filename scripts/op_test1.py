import time
import json
import pyvisa
import numpy as np
from utils.logger import setup_logging
from utils.formatters import auto_scale_channel
from utils.formatters import format_time_scale
from instruments.generator import Generator
from instruments.oscilloscope import Oscilloscope
from calculation import calculate_unity_gain_bandwidth
from plotting.bode_plot import plot_bode
from typing import NamedTuple
import logging

logger = logging.getLogger(__name__)

class ExperimentConfig(NamedTuple):
    frequencies: list
    v_amp: float
    ch_in: int
    ch_out: int
    probe_attenuation: int

class InstrumentsConfig(NamedTuple):
    gen_addr: str
    scope_addr: str

class ProcessingConfig(NamedTuple):
    gain_threshold: float

def load_config(config_path="configs/config.json"):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Конфигурационный файл {config_path} не найден!")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON в {config_path}: {e}")
        raise

def setup_instruments(scope, gen, exp_cfg: ExperimentConfig):
    logger.info(f"Инициализация оборудования: {gen.idn}, {scope.idn}")
    try:
        gen.reset()
        gen.set_waveform('SINE')
        gen.set_amplitude(exp_cfg.v_amp, unit='VPP')
        gen.output_on()
        gen.set_load_impedance(10000.0)
        logger.info("Генератор настроен.")

        scope.write(":STOP")
        scope.set_channel_display(exp_cfg.ch_in, True)
        scope.set_channel_display(exp_cfg.ch_out, True)
        scope.set_probe_attenuation(exp_cfg.ch_in, exp_cfg.probe_attenuation)
        scope.set_probe_attenuation(exp_cfg.ch_out, exp_cfg.probe_attenuation)

        scope.set_channel_scale(exp_cfg.ch_in, "100mV")
        scope.set_channel_scale(exp_cfg.ch_out, "100mV")

        scope.write(":TRIGger:SINGle:SOURce CH1")
        scope.write(":TRIGger:SINGle:EDGE:LEVel 0")
        scope.write(":TRIGger:SINGle:MODe AUTO")

        scope.write(":ACQuire:MODE AVERage")
        scope.write(":ACQuire:AVERage:NUM 16")
        logger.info("Осциллограф настроен.")

    except Exception as e:
        logger.error(f"Ошибка при настройке приборов: {e}")
        raise

def run_measurement_cycle(scope, gen, exp_cfg: ExperimentConfig):
    results = []
    for freq in exp_cfg.frequencies:
        logger.info(f"Запуск теста на частоте {freq/1e6:.3f} МГц")
        gen.set_frequency(freq)
        time.sleep(3.0)
                
        time_scale = (1 / freq) * 0.2
        scope.set_horizontal_scale(format_time_scale(time_scale))
        time.sleep(2.0)

        auto_scale_channel(scope, exp_cfg.ch_out)
        time.sleep(2.0)

        scope.setup_trigger()

        scope.write(":RUN")
        time.sleep(1.5)

        v_in = scope.get_vpp(exp_cfg.ch_in)
        v_out = scope.get_vpp(exp_cfg.ch_out)

        if v_in > 1e-6 and v_out > 1e-6:
            gain_db = 20 * np.log10(v_out / v_in)
            logger.info(f"Результат: Vin={v_in:.3f}V, Vout={v_out:.3f}V, Gain={gain_db:.2f}dB")
            results.append({'freq': freq, 'v_in': v_in, 'v_out': v_out, 'gain': gain_db})
        else:
            logger.warning(f"Пропуск частоты {freq/1e6:.3f} МГц: амплитуда на входе 0")

    return results


def main():
    setup_logging()
    config = load_config()
    exp_cfg = ExperimentConfig(
        frequencies=config['experiment']['frequencies'],
        v_amp=config['experiment']['v_amplitude_vpp'],
        ch_in=config['experiment']['input_channel'],
        ch_out=config['experiment']['output_channel'],
        probe_attenuation=config['experiment']['probe_attenuation']
    )

    instr_cfg = InstrumentsConfig(
        gen_addr=config['instruments']['generator_addr'],
        scope_addr=config['instruments']['scope_addr'],
    )

    processing_cfg = ProcessingConfig(
        gain_threshold=config['processing']['gain_threshold_db']
    )


    rm = Oscilloscope._get_rm()
    resources = rm.list_resources()
    logger.debug(f"Доступные приборы: {resources}")

    if len(resources) < 2:
        logger.error(f"Ошибка: Найдено приборов: {len(resources)}. Требуется минимум 2 (Генератор и Осциллограф).")
        logger.warning("Проверьте USB-кабели и питание приборов.")
        return

    try:
        with Oscilloscope(instr_cfg.scope_addr) as scope, Generator(instr_cfg.gen_addr) as gen:
            setup_instruments(scope, gen, exp_cfg)
            raw_data = run_measurement_cycle(scope, gen, exp_cfg)
            if len(raw_data) < 2:
                logger.error("Слишком мало успешных измерений для построения графика.")
                return
            freqs = np.array([r['freq'] for r in raw_data])
            gains = np.array([r['gain'] for r in raw_data])
            f_t = 0
            slope = 0
            intercept = 0

            mask = gains < processing_cfg.gain_threshold
            if np.any(mask):
                stats = calculate_unity_gain_bandwidth(freqs[mask], gains[mask])
                if stats:
                    f_t = stats['c']
                    slope = stats['a']
                    intercept = -slope * np.log10(f_t)
                else:
                    logger.error(f"Эксперимент прерван. Недостаточно данных для расчета частоты единичного усиления. Рекомендуется увеличить значения частот в конфигурационном файле")
                    return
                
                plot_bode(freqs, gains, f_t, slope, intercept)
                logger.info("--- ИТОГОВЫЕ РЕЗУЛЬТАТЫ ---")
                logger.info(f"Эксперимент завершен успешно. f_T = {f_t/1e6:.3f} МГц")
                f_min, f_max = stats['c_conf']
                logger.info(f"Доверительный интервал (95%): [{f_min/1e6:.3f}; {f_max/1e6:.3f}] МГц")
                logger.debug(f"Наклон (Slope): {slope:.2f} дБ/дек")
                if abs(slope + 20) > 5:
                    logger.warning(f"Аномальный наклон: {slope:.2f} дБ/дек. Ожидалось около -20.")
                for row in raw_data:
                    logger.info(f"{row['freq']:10.0f} | {row['v_in']:8.3f} | {row['v_out']:8.3f} | {row['gain']:8.2f}")
            else:
                logger.error("Расчет f_T невозможен: ни одна точка не попала под фильтр (gain < -2dB).")
                print("Недостаточно данных для расчета. Проверьте диапазон частот.")
    
    except FileNotFoundError as e:
        logger.error(f"Файл конфигурации не найден: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка в формате JSON-конфигурации: {e}")
    except pyvisa.VisaIOError as e:
        logger.error(f"Критическая ошибка оборудования VISA: {e}")
    except Exception as e:
        logger.error("Критический сбой программы", exc_info=True)

if __name__ == "__main__":
    main()