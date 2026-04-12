import time
import numpy as np
from instruments.generator import Generator
from instruments.oscilloscope import Oscilloscope
from calculation.calculation import calculate_unity_gain_bandwidth
from plotting.bode_plot import plot_bode

# --- Настройки эксперимента ---
FREQUENCIES = [6e6, 8e6, 10e6] # Частоты, на которых проводим замеры (Гц)
CH_IN = 1  # Канал входа (сигнал с генератора)
CH_OUT = 2 # Канал выхода (после ОУ)
V_AMPLITUDE = 0.6  # Амплитуда генератора (VPP)
def format_time_scale(seconds):
    """Конвертирует число секунд в строку формата SCPI (например, 0.0001 -> '100us')"""
    if seconds >= 1:
        return f"{seconds:.1f}s"
    elif seconds >= 1e-3:
        return f"{seconds * 1e3:.1f}ms"
    elif seconds >= 1e-6:
        return f"{seconds * 1e6:.1f}us"
    else:
        return f"{seconds * 1e9:.1f}ns"

def main():
    rm = Oscilloscope._get_rm()
    resources = rm.list_resources()
    print(f"Доступные приборы: {resources}")

    if len(resources) < 2:
        print(f"ОШИБКА: Найдено приборов: {len(resources)}. Требуется минимум 2 (Генератор и Осциллограф).")
        print("Проверьте USB-кабели и питание приборов.")
        return # или exit(1)

    
    gen_addr = resources[0]
    scope_addr = resources[1]

    try:
        with Oscilloscope(scope_addr) as scope, Generator(gen_addr) as gen:
            print(f"Подключено к осциллографу: {scope.idn}")
            print(f"Подключено к генератору: {gen.idn}")
            
            # gen.write(":CHANnel:CH1 ON")
            # gen.write(":CHANnel:CH2 ON")
            # gen.write(f":CHANnel1:MODE CONTINUE")
            # gen.write(f":CHANnel2:MODe CONTinue")

            gen.set_waveform(CH_IN, 'SINE')
            gen.set_waveform(CH_OUT, 'SINE')
            gen.set_amplitude(V_AMPLITUDE, unit='VPP')
            gen.output_on()

            scope.write(":STOP")
            scope.set_channel_display(CH_IN, True)
            scope.set_channel_display(CH_OUT, True)
            scope.set_probe_attenuation(CH_IN, 10)
            scope.set_probe_attenuation(CH_OUT, 10)


            scope.set_channel_scale(1, "100mV")
            scope.set_channel_scale(2, "100mV")

            # 3. Настройка триггера (чтобы полосы замерли в синусоиду)
            scope.write(":TRIGger:SINGle:SOURce CH1")   # Синхронизация по входу
            scope.write(":TRIGger:SINGle:EDGE:LEVel 0") # Триггер ровно посередине
            scope.write(":TRIGger:SINGle:MODe AUTO")    # Авто-режим для видимости

            scope.write(":ACQuire:MODE AVERage")
            scope.write(":ACQuire:AVERage:NUM 16") # Усреднение по 16 кадрам
                
            measured_gains = []
            actual_freqs = []
            results_table = []
            
            for freq in FREQUENCIES:
                gen.set_waveform(1, 'SINE')
                gen.set_waveform(2, 'SINE')
                # scope.write(":AUTOset")
                print(f"\nИзмерение на частоте: {freq/1e3:.1f} кГц")
                gen.set_frequency(freq)
                time.sleep(3.0)
                
                time_scale = (1/freq) * 2
                str_time_scale = format_time_scale(time_scale)
                scope.set_horizontal_scale(str_time_scale)
                time.sleep(2.0)

                scope.write(":TRIGger:SINGle:SOURce CH1")
                scope.write(":TRIGger:SINGle:MODe AUTO")
                scope.write(":TRIGger:SINGle:EDGE:LEVel 0")
                
                scope.write(":RUN")
                time.sleep(1.5)

                v_in = scope.get_vpp(CH_IN)
                v_out = scope.get_vpp(CH_OUT)
                
                if v_in > 0:# and v_out > 0:
                    gain_db = 20 * np.log10(v_out / v_in)
                    print(f"Vin: {v_in:.3f}V, Vout: {v_out:.3f}V -> Gain: {gain_db:.2f} dB")
                    results_table.append({
                        'freq': freq,
                        'v_in': v_in,
                        'v_out': v_out,
                        'gain': gain_db
                    })
                    measured_gains.append(gain_db)
                    actual_freqs.append(freq)
                else:
                    print("Предупреждение: Не удалось считать амплитуду.")
                
            if len(measured_gains) >= 2:
                freqs_arr = np.array(actual_freqs)
                gains_arr = np.array(measured_gains)
                # ФИЛЬТР: Берем только те точки, где усиление заметно упало (например, ниже -2 дБ)
                # Это исключит "полку" и резонансный пик на 300 кГц из расчетов наклона
                mask = gains_arr < -2.0
                f_t, slope, intercept = calculate_unity_gain_bandwidth(
                    freqs_arr[mask], 
                    gains_arr[mask]
                )

                plot_bode(
                    frequencies=actual_freqs, 
                    gains=measured_gains, 
                    f_t=f_t, 
                    slope=slope, 
                    intercept=intercept
                )

                print("\n" + "="*30)
                print(f"РЕЗУЛЬТАТ:")
                print(f"Частота единичного усиления (f_T): {f_t/1e6:.3f} МГц")
                print(f"Наклон аппроксимации: {slope:.2f} дБ/дек")
                if abs(slope + 20) > 5:
                    print("Внимание: Наклон сильно отличается от -20 дБ/дек!")
                print("="*30)
                for row in results_table:
                    f_khz = row['freq'] / 1e3
                    print(f"{f_khz:<15.1f} | {row['v_in']:<10.3f} | {row['v_out']:<10.3f} | {row['gain']:<10.2f}")
            else:
                print("Недостаточно данных для расчета.")
            # gen.output_off()

    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()