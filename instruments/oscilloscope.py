from .base import InstrumentBase
from typing import Optional, Tuple, List, Dict, Union, Any
import numpy as np
import time

class Oscilloscope(InstrumentBase):
    def __init__(self, resource_name: str, timeout: int = 30000):
        super().__init__(resource_name, timeout)

        self.model: Optional[str] = None
        self.serial_number: Optional[str] = None
        self.firmware_version: Optional[str] = None
        self.max_sample_rate: Optional[float] = None
        self.max_bandwith: Optional[float] = None

    def _configure(self):
        self.write("*CLS")
        self.write(":AUToscale OFF")
        self.write(":SYSTem:AUToset OFF")
        self.set_trigger_sweep("NORMAL")

        self.set_timebase_scale(1e-3)
        self.set_channel_enable(1, True)
        self.set_channel_scale(1, 1.0)
        self.set_channel_offset(1, 0.0)
        self.set_trigger_mode("EDGE")
        self.set_trigger_source("CH1")
        self.set_trigger_level(0.0)

        self._identify_model()
        print(f"Осциллограф {self.model} сконфигурирован")

    def _identify_model(self):
        try:
            idn_parts = self.idn.split(',')
            if len(idn_parts) >= 4:
                self.model = idn_parts[1].strip()
                self.serial_number = idn_parts[2].strip()
                self.firmware_version = idn_parts[3].strip()

                print(f"Модель: {self.model}")
                print(f"Серийный номер: {self.serial_number}")
                print(f"Версия ПО: {self.firmware_version}")
        except Exception as e:
            print(f"Не удалось определить параметры осциллографа: {e}")

    def set_channel_enable(self, channel: int, enable: bool) -> 'Oscilloscope':
        state = "ON" if enable else "OFF"
        self.write(f":CH{channel}:DISPlay {state}") #?
        print(f"Канал {channel}: {'включен' if enable else 'выключен'}")
        return self
    
    def set_channel_scale(self, channel: int, scale: float) -> 'Oscilloscope':
        #установка масштаба по вертикали (В/дел)
        self.write(f":CH{channel}:SCALe {scale}V")
        print(f"Канал {channel}: масштаб {scale} В/дел")
        return self
    
    def set_channel_offset(self, channel: int, offset: float) -> 'Oscilloscope':
        #установка смещения по вертикали
        self.write(f":CH{channel}:OFFSet {offset}")
        print(f"Канал {channel}: смещение {offset} В")
        return self
    
    def set_channel_coupling(self, channel: int, coupling: str) -> 'Oscilloscope':
        #установка вида связи канала
        if coupling.upper() not in ['AC', 'DC', 'GND']:
            raise ValueError("Связь должна быть 'AC', 'DC' или 'GND'")
        
        self.write(f":CH{channel}:COUPling {coupling.upper()}")
        print(f"Канал {channel}: связь {coupling}")
        return self
    
    def set_timebase_scale(self, scale: float) -> 'Oscilloscope': #?
        # Установка масштаба временной развертки
        self.write(f":TIMebase:SCALe {scale}")
        print(f"Временная развертка: {scale} сек/дел")
        return self

    def set_timebase_position(self, position: float) -> 'Oscilloscope':
        # установка позиции временной развертки
        self.write(f":TIMebase:POSition {position}")
        print(f"Позиция развертки: {position} сек")
        return self
    
    def set_sample_rate(self, sample_rate: float) -> 'Oscilloscope':
        # установка частоты дискретизации
        self.write(f":ACQuire:SRATe {sample_rate}")
        print(f"Частота дискретизации: {sample_rate} Гц")
        return self
    
    def set_trigger_mode(self, mode: 'str') -> 'Oscilloscope':
        # установка режима триггера
        self.write(f":TRIGger:MODE {mode}")
        print(f"Режим триггера: {mode}")
        return self
    
    def set_trigger_source(self, source: str) -> 'Oscilloscope':
        # установка источника триггера
        self.write(f":TRIGger:EDGE:SOURce {source}")
        print(f"Источник триггера: {source}")
        return self
    
    def set_trigger_level(self, level: float) -> 'Oscilloscope':
        # установка уровня триггера
        self.write(f":TRIGger:EDGE:LEVel {level}")
        print(f"Уровень триггера: {level} В")
        return self
    
    def set_trigger_slope(self, slope: str) -> 'Oscilloscope':
        # установка фронта триггера
        self.write(f":TRIGger:EDGE:SLOPe {slope}")
        print(f"Фронт триггера: {slope}")
        return self

    def measure_amplitude(self, channel: int) -> float:
        self.write(f":MEASure:SOURce CH{channel}")
        self.write(":MEASure:VAMPlitude")
        self.query("*OPC?") #?
        result = self.query(":MEASure:VAMPlitude?")
        try:
            amplitude = float(result)
            print(f"канал {channel}: амплитуда = {amplitude} В")
            return amplitude
        except ValueError:
            print(f"Ошибка парсинга амплитуды: {result}")
            return 0.0
        
    def measure_frequency(self, channel: int) -> float:
        self.write(f"MEASure:SOURce CH{channel}")
        self.write(":MEASure:FREQuency")
        self.query("*OPC")
        result = self.query(":MEASure:FREQuency?")
        try:
            frequency = float(result)
            print(f"Канал {channel}: частота = {frequency} Гц")
            return frequency
        except ValueError:
            print(f"Ошибка парсинга частоты: {result}")
            return 0.0
        
    def measure_vrms(self, channel: int) -> float:
        # Измерение среднеквадратичного значения напряжения
        self.write(f":MEASure:SOURce CH{channel}")
        self.write(":MEASure:VRMS")
        self.query("*OPC")
        result = self.query(":MEASure:VRMS?")
        try:
            vrms = float(result)
            print(f"Канал {channel}: Vrms = {vrms} Гц")
            return vrms
        except ValueError:
            print(f"Ошибка парсинга Vrms: {result}")
            return 0.0
        
    def measure_phase_difference(self, channel1: int, channel2: int) -> float:
        # Измерение разности фаз между двумя каналами
        self.write(f":MEASure:SOURce CH{channel1}")
        self.write(f":MEASure:RPHase CH{channel2}")
        self.query("*OPC")
        result = self.query(":MEASure:RPHase?")
        try:
            phase = float(result)
            print(f"Фаза CH{channel1} - CH{channel2} = {phase}")
            return phase
        except ValueError:
            print(f"Ошибка парсинга фазы: {result}")
            return 0.0
        
    def get_waveform(self, channel: int) -> Tuple[np.ndarray, np.ndarray]:
        self.write(f":WAVeform:SOURce CH{channel}")
        self.write(":WAVeform:FORMat WORD") #16-битные данные
        self.write(":WAVeform:BYTeorder LSBFirst") #Порядок байт

        raw_data = self.query_binary_values(":WAVeform:DATA?", datatype='h') #запрашиваем данные
        # Получаем параметры масштабирования
        x_incr = float(self.query(":WAVeform:XINCrement?"))
        x_orig = float(self.query(":WAVeform:XORigin?"))
        y_incr = float(self.query(":WAVeform:YINCrement?"))
        y_orig = float(self.query(":WAVeform:YORigin?"))

        # Создаем временную ось
        time_data = np.arange(len(raw_data)) * x_incr + x_orig
        # Масштабируем данные по напряжению
        voltage_data = np.arange(len(raw_data)) * y_incr + y_orig

        print(f"Получена осциллограмма с CH{channel}: {len(voltage_data)} точек")
        return time_data, voltage_data
    
    def set_trigger_sweep(self, sweep: str) -> 'Oscilloscope':
        valid_sweep = ["AUTO", "NORMAL", "SINGLE"]
        if sweep.upper() not in valid_sweep:
            raise ValueError(f"Режим развертки должен быть одним из {valid_sweep}")
        
        self.write(f":TRIGger:SINGle:SWEEp {sweep.upper()}")
        print(f"Режим развертки триггера: {sweep}")
        return self

    def measure_gain(self, input_channel: int, output_channel: int) -> float:
        vin = self.measure_vrms(input_channel)
        vout = self.measure_vrms(output_channel)
        if vin == 0:
            print(f"Входной сигнал равен нулю")
            return 0.0
        gain = vout / vin
        print(f"Коэффициент усиления: Vin={vin:.3f} В, Vout={vout:.3f} В, Gain={gain:.2f}")
        return gain
    
    def measure_frequency_response(self, input_channel: int, output_channel: int, frequencies: List[float]) -> List[Tuple[float, float]]:
        results = []
        for freq in frequencies:
            time.sleep(0.1)
            vin = self.measure_vrms(input_channel)
            vout = self.measure_vrms(output_channel)

            if vin > 0:
                gain = vout / vin
                gain_db = 20 * np.log10(gain) if gain > 0 else -np.inf #???
            else:
                gain = 0.0
                gain_db = -np.inf
            results.append((freq, gain, gain_db))
            print(f"Частота {freq:.1f} Гц: Vin={vin:.3f}В, Vout={vout:.3f}В, Gain={gain:.2f} ({gain_db:.1f} dB)")
            return results
    
    def run(self) -> 'Oscilloscope':
        self.write(":RUN")
        print(f"Запущен захват сигнала")
        return self
    
    def stop(self) -> 'Oscilloscope':
        self.write(":STOP")
        print(f"Остановлен захват сигнала")
        return self

    def save_screenshot(self, filename:str, format: str = "PNG") -> bool:
        try:
            self.write(f":DISPlay:DATA? {format}")
            image_data = self.instrument.read_raw()
            with open(filename, 'wb') as f:
                f.write(image_data)
            print(f"Скриншот сохранен: {filename}")
            return True
        except Exception as e:
            print(f"Ошибка сохранения скриншота: {filename}")
            return False
