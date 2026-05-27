import time
import json
import numpy as np
from utils.logger import setup_logging
from utils.formatters2 import auto_scale_channel, format_time_scale_by_freq
from instruments.generator import Generator
from instruments.oscilloscope import Oscilloscope
from instruments.base import InstrumentBase
from calculation.calculation4 import calculate_unity_gain_bandwidth, get_required_n_min
from plotting.bode_plot import plot_bode
from typing import NamedTuple, Any, Optional
import logging
from scipy.stats import t as student_t

logger = logging.getLogger(__name__)

class ExperimentConfig(NamedTuple):
    v_amp: float
    ch_in: int
    ch_out: int
    probe_attenuation: int

class InstrumentsConfig(NamedTuple):
    gen_addr: str
    scope_addr: str

class ProcessingConfig(NamedTuple):
    gain_threshold: float
    delta_target: float

def load_config(config_path: str = "configs/config2.json") -> dict[str, Any]:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Конфигурационный файл {config_path} не найден!")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON в {config_path}: {e}")
        raise

def clean_config_strings(d: Any) -> Any:
    """Рекурсивно удаляет пробелы из ключей и строковых значений конфига."""
    if isinstance(d, dict):
        return {str(k).strip(): clean_config_strings(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [clean_config_strings(i) for i in d]
    elif isinstance(d, str):
        return d.strip()
    return d

def setup_instruments(scope: Oscilloscope, gen: Generator, exp_cfg: ExperimentConfig) -> None:
    logger.info(f"Инициализация оборудования: {gen.idn}, {scope.idn}")
    try:
        gen.reset()
        gen.set_waveform('SINE')
        gen.set_amplitude(exp_cfg.v_amp, unit='VPP')
        gen.output_on()
        gen.set_load_impedance(10000.0)
        logger.info("Генератор настроен.")

        scope.stop()
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
        scope.write(":ACQuire:AVERage:NUM 32")
        time.sleep(0.2)
        logger.info("Осциллограф настроен.")
    except Exception as e:
        logger.error(f"Ошибка при настройке приборов: {e}")
        raise

def run_single_measurement_cycle(scope: Oscilloscope, generator: Generator, 
                                 frequencies: np.ndarray, proc_config: ProcessingConfig,
                                 exp_cfg: ExperimentConfig) -> tuple[Optional[dict], list[dict]]:
    raw_data = []
    for freq in frequencies:
        logger.debug(f"Запуск теста на частоте {freq/1e6:.3f} МГц")
        generator.set_frequency(freq)
        time.sleep(0.5)
        
        time_scale = format_time_scale_by_freq(freq)
        scope.set_horizontal_scale(time_scale)
        time.sleep(1.0)
        
        auto_scale_channel(scope, exp_cfg.ch_in)
        auto_scale_channel(scope, exp_cfg.ch_out)
        time.sleep(0.5)

        scope.setup_trigger(source="CH1", mode="AUTO", level=0.0)
        scope.run()
        time.sleep(1.5)
        
        v_in = scope.get_vpp(exp_cfg.ch_in)
        v_out = scope.get_vpp(exp_cfg.ch_out)
        scope.stop()
        
        if v_in > 1e-6 and v_out > 1e-6:
            gain = v_out / v_in
            gain_db = 20 * np.log10(gain)
        else:
            gain_db = -999
            
        raw_data.append({'freq': freq, 'v_in': v_in, 'v_out': v_out, 'gain': gain_db})
        
    filtered_points = [p for p in raw_data if p['gain'] <= proc_config.gain_threshold]

    if len(filtered_points) >= 2:
        freqs_calc = np.array([p['freq'] for p in filtered_points])
        gains_calc = np.array([p['gain'] for p in filtered_points])
        stats = calculate_unity_gain_bandwidth(freqs_calc, gains_calc)
        if stats:
            return stats, raw_data
    return None, raw_data

def main() -> None:
    setup_logging()
    logger.info("Программа автоматического измерения UGBW ОУ запущена.")
    try:
        config_data = load_config()
        config_data = clean_config_strings(config_data) # 🔥 Ключевое исправление
        
        inst_config = InstrumentsConfig(
            gen_addr=str(config_data["instruments"]["generator_address"]),
            scope_addr=str(config_data["instruments"]["oscilloscope_address"])
        )
        exp_cfg = ExperimentConfig(
            v_amp=float(config_data["experiment"]["v_amplitude"]),
            ch_in=int(config_data["experiment"]["channel_input"]),
            ch_out=int(config_data["experiment"]["channel_output"]),
            probe_attenuation=int(config_data["experiment"]["probe_attenuation"])
        )
        proc_cfg = ProcessingConfig(
            gain_threshold=float(config_data["processing"]["gain_threshold"]),
            delta_target=float(config_data["processing"]["delta_target_hz"])
        )

        if "frequencies" in config_data["experiment"]:
            freq_grid = np.array(config_data["experiment"]["frequencies"], dtype=float)
            logger.info(f"Используется фиксированный набор из {len(freq_grid)} частот.")
        else:
            start = float(config_data["experiment"].get("freq_start_hz", 1e5))
            stop  = float(config_data["experiment"].get("freq_stop_hz", 50e6))
            n_pts = int(config_data["experiment"].get("freq_points", 15))
            freq_grid = np.logspace(np.log10(start), np.log10(stop), n_pts)
            logger.info(f"Сгенерирована логарифмическая сетка: {start/1e6:.1f}-{stop/1e6:.1f} МГц ({n_pts} точек)")

        f_t_results = []
        last_raw_data = []
        MAX_ITERATIONS = 40
        MIN_SAMPLES = 3
        
        logger.info(f"🔌 Попытка подключения к генератору: {inst_config.gen_addr!r}")
        logger.info(f"🔌 Попытка подключения к осциллографу: {inst_config.scope_addr!r}")
        
        rm = InstrumentBase.get_rm()
        resources = rm.list_resources()
        logger.debug(f"Доступные приборы: {resources}")
        if len(resources) < 2:
            logger.error(f"Ошибка: Найдено приборов: {len(resources)}. Требуется минимум 2.")
            return
            
        with Generator(inst_config.gen_addr) as generator, \
             Oscilloscope(inst_config.scope_addr) as scope:
            
            setup_instruments(scope, generator, exp_cfg)
            logger.info("Старт адаптивной серии экспериментов.")
            
            for i in range(MAX_ITERATIONS):
                current_freqs = np.random.permutation(freq_grid)
                logger.info(f"--- Проход #{i+1} (частоты перемешаны) ---")
                
                stats, raw_data = run_single_measurement_cycle(scope, generator, current_freqs, proc_cfg, exp_cfg)
                
                if stats is not None:
                    # Сохраняем f_t для статистики
                    f_t_results.append(stats['f_t'])
                    last_raw_data = raw_data
                    last_stats = stats  # ← Сохраняем последние полные stats
                    
                    # 🔥 Логируем ВСЕ параметры из расчета
                    logger.info(f"✅ Проход успешен:")
                    logger.info(f"   f_T = {stats['f_t']/1e6:.4f} МГц")
                    logger.info(f"   Наклон (slope) = {stats['slope']:.2f} дБ/дек")
                    logger.info(f"   Intercept = {stats['intercept']:.2f} дБ")
                    
                    # Доверительные интервалы (если есть)
                    if 'f_conf' in stats:
                        conf_low, conf_high = stats['f_conf']
                        logger.info(f"   95% ДИ для f_T: [{conf_low/1e6:.4f}, {conf_high/1e6:.4f}] МГц")
                    if 'slope_conf' in stats:
                        slope_low, slope_high = stats['slope_conf']
                        logger.info(f"   95% ДИ для slope: [{slope_low:.2f}, {slope_high:.2f}] дБ/дек")
                    
                    n = len(f_t_results)
                    if n >= MIN_SAMPLES:
                        n_min = get_required_n_min(f_t_results, proc_cfg.delta_target, alpha=0.05)
                        logger.info(f"Статистика: n={n}, n_min={n_min} (целевая Δ≤{proc_cfg.delta_target/1e3:.1f} кГц)")
                        if n >= n_min:
                            logger.info("✅ Условие сходимости выполнено. Досрочная остановка.")
                            break
                else:
                    logger.warning(f"Проход #{i+1} не дал валидного f_T. Повтор...")

            final_n = len(f_t_results)
            if final_n >= MIN_SAMPLES:
                f_t_avg = np.mean(f_t_results)
                f_t_std = np.std(f_t_results, ddof=1)
                final_t_crit = student_t.ppf(1 - 0.05 / 2, df=final_n - 1)
                final_delta = final_t_crit * (f_t_std / np.sqrt(final_n))
                
                logger.info("\n" + "= "*50)
                logger.info("=== ИТОГОВЫЙ ОТЧЕТ СЕРИИ ЗАМЕРОВ ===")
                logger.info(f"Число успешных проходов: {final_n}")
                logger.info(f"Среднее f_T: {f_t_avg/1e6:.4f} МГц")
                logger.info(f"СКО выборки: {f_t_std/1e3:.2f} кГц")
                logger.info(f"Доверительный интервал (P=0.95): ±{final_delta/1e3:.2f} кГц")
                logger.info(f"Результат: f_T = {f_t_avg/1e6:.4f} ± {final_delta/1e6:.4f} МГц")
                logger.info("= "*50)
                
                if last_raw_data and last_stats:
                    freqs_plot = [p['freq'] for p in last_raw_data]
                    gains_plot = [p['gain'] for p in last_raw_data]
                    
                    # ✅ Используем РЕАЛЬНЫЙ наклон из последней аппроксимации
                    f_t_val = max(float(f_t_avg), 1.0)
                    slope_val = last_stats.get('slope', -20.0)  # Реальный или фолбэк
                    intercept_val = last_stats.get('intercept', 20.0 * np.log10(f_t_val))
                    
                    plot_bode(freqs_plot, gains_plot, f_t_val, slope_val, intercept_val)
            else:
                logger.error("Недостаточно успешных замеров для финальной статистики.")
                
    except Exception as e:
        logger.critical(f"Критическая ошибка в работе программы: {e}", exc_info=True)

if __name__ == "__main__":
    main()