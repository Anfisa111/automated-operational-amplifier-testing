import pyvisa
from typing import Tuple
from .base import InstrumentBase
import logging

logger = logging.getLogger(__name__)

class Generator(InstrumentBase):
    VALID_WAVEFORMS = ['SINE', 'SQUARE', 'PULSE', 'RAMP', 'ARB', 'NOISE', 'DC']
    VALID_MODES = ['CONTINUE', 'AM', 'PM', 'FM', 'FSK', 'Line', 'Log']
    VALID_AMPLITUDE_UNITS = ['VPP', 'VRMS', 'DBM']

    def __init__(self, resource_name: str, timeout: int = 30000, default_channel: int = 1):
        super().__init__(resource_name, timeout)
        self.channel = default_channel

    def _configure(self) -> 'Generator':
        try:
            self.write(f":CHANnel{self.channel}:MODE CONTINUE")
            logger.info(f"Генератор сигналов (канал {self.channel}) сконфигурирован")
        except Exception as e:
            logger.error(f"Ошибка при базовой конфигурации: {e}")
        return self

    def connect(self) -> 'Generator':
        super().connect()
        try:
            self._configure()
            return self
        except Exception as e:
            logger.error(f"Прибор подключен, но возникла ошибка конфигурации: {e}")
            self.disconnect()
            raise

    def reset(self) -> 'Generator':
        try:
            self.write("*RST")
            logger.info("Выполнен сброс к заводским настройкам")
            return self
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка при выполнении команды *RST: {e}")
            raise

    def set_channel(self, channel: int) -> 'Generator':
        if channel not in [1, 2]:
            raise ValueError("Канал должен быть 1 или 2")
        
        try:
            self.channel = channel
            return self
        except pyvisa.VisaIOError as e:
            logger.error(f"Не удалось установить канал")
            raise

    def set_frequency(self, frequency: float) -> 'Generator':
        min_freq = 1e-6
        if not isinstance(frequency, (int, float)):
            raise TypeError("Частота должна быть числом")
        if frequency <= min_freq:
            raise ValueError(f"Частота должна быть больше 1 мкГц, получено: {frequency}")
        
        try:
            self.write(f":CHANnel{self.channel}:BASE:FREQuency {frequency}")
            logger.debug(f"Канал {self.channel}: установлена частота {frequency} Гц")
            return self
        except pyvisa.VisaIOError as e:
            logger.error(f"Не удалось установить частоту {frequency} Гц: {e}")
            raise
    
    def set_amplitude(self, amplitude: float, unit: str = 'VPP') -> 'Generator':
        if not isinstance(amplitude, (int, float)):
            raise TypeError("Амплитуда должна быть числом")
        if amplitude < 0:
            raise ValueError(f"Амплитуда не может быть отрицательной: {amplitude}")
        
        unit = unit.upper()
        if unit not in self.VALID_AMPLITUDE_UNITS:
            raise ValueError(f"Недопустимая единица измерения. Допустимые: {self.VALID_AMPLITUDE_UNITS}")
        
        try:
            self.write(f":CHANnel{self.channel}:AMPLitude:UNIT {unit}")
            self.write(f":CHANnel{self.channel}:BASE:AMPLitude {amplitude}")
            logger.info (f"Канал {self.channel}: установлена амплитуда {amplitude} {unit}")
            return self
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка VISA при установке амплитуды: {e}")
            raise
    
    def set_offset(self, offset: float) -> 'Generator':
        """Установить смещение в Volts"""
        if not isinstance(offset, (int, float)):
            raise TypeError("Смещение должно быть числом")
        
        try:
            self.write(f":CHANnel{self.channel}:BASE:OFFSet {offset}")
            logger.info(f"Канал {self.channel}: установлено смещение {offset} В")
            return self
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка VISA при установке смещения: {e}")
            raise
    
    def set_phase(self, phase: float) -> 'Generator':
        if not isinstance(phase, (int, float)):
            raise TypeError("Фаза должна быть числом")
        
        if not -360 <= phase <= 360:
            raise ValueError("Фаза должна быть в диапазоне [-360, 360]")
        
        try:
            self.write(f":CHANnel{self.channel}:BASE:PHASE {phase}")
            return self
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка VISA при установке фазы: {e}")
            raise

    def set_waveform(self, waveform: str) -> 'Generator':
        if not isinstance(waveform, str):
            raise TypeError("Форма сигнала должна быть строкой")
        
        waveform = waveform.upper()
        if waveform not in self.VALID_WAVEFORMS:
            raise ValueError(f"Недопустимая форма сигнала. Допустимые: {self.VALID_WAVEFORMS}")
        
        try:
            self.write(f":CHANnel{self.channel}:BASE:WAVE {waveform}")
            logger.info(f"Канал {self.channel}: установлена форма сигнала {waveform}")
            return self
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка VISA при выборе формы сигнала: {e}")
            raise
    
    def set_load_impedance(self, impedance: float) -> 'Generator':
        if not isinstance(impedance, (int, float)):
            raise TypeError("Импеданс должен быть числом")
        if not 1 <= impedance <= 10000:
            raise ValueError("Импеданс нагрузки должен быть в диапазоне [1, 10000] Ом")
        
        try:
            self.write(f":CHANnel{self.channel}:LOAD {impedance}")
            logger.info(f"Канал {self.channel}: установлен импеданс нагрузки {impedance} Ом")
            return self
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка VISA при установке импеданса: {e}")
            raise

    def output_on(self) -> 'Generator':
        try:
            self.write(f":CHANnel{self.channel}:OUTPut ON")
            logger.info(f"Канал {self.channel}: выход включен")
            return self
        except pyvisa.VisaIOError as e:
            logger.error(f"Не удалось включить выход канала {self.channel}: {e}")
            raise
    
    def output_off(self) -> 'Generator':
        try:
            self.write(f":CHANnel{self.channel}:OUTPut OFF")
            logger.info(f"Канал {self.channel}: выход выключен")
            return self
        except pyvisa.VisaIOError as e:
            logger.error(f"Не удалось выключить выход канала {self.channel}: {e}")
            raise
    
    def get_frequency(self) -> float:
        try:
            freq_str = self.query(f":CHANnel{self.channel}:BASE:FREQuency?").strip()
            frequency = float(freq_str)
            logger.info(f"Канал {self.channel}: текущая частота - {frequency} Гц")
            return frequency
        except pyvisa.VisaIOError as e:
            logger.error(f"Не удалось считать частоту: {e}")
            raise
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка преобразования данных частоты: {e}")
            raise
    
    def get_amplitude(self) -> Tuple[float, str]:
        """Получить текущую амплитуду и единицы измерения"""
        try:
            unit = self.query(f":CHANnel{self.channel}:AMPLitude:UNIT?").strip()
            amp_str = self.query(f":CHANnel{self.channel}:BASE:AMPLitude?").strip()
            amplitude = float(amp_str)
            logger.info(f"Канал {self.channel}: амплитуда -> {amplitude} {unit}")
            return amplitude, unit
        except pyvisa.VisaIOError as e:
            logger.error(f"Не удалось считать амплитуду: {e}")
            raise
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка преобразования данных амплитуды: {e}")
            raise
    
    def get_waveform(self) -> str:
        try:
            waveform = self.query(f":CHANnel{self.channel}:BASE:WAVE?").strip()
            logger.info(f"Канал {self.channel}: текущая форма сигнала -> {waveform}")
            return waveform
        except pyvisa.VisaIOError as e:
            logger.error(f"Не удалось считать форму: {e}")
            raise
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при получении формы: {e}")
            raise
    
    def get_channel(self) -> int:
            logger.info(f"Текущий канал: {self.channel}")
            return self.channel

    def get_offset(self) -> float:
        try:
            offset_str = self.query(f":CHANnel{self.channel}:BASE:OFFSet?").strip()
            offset = float(offset_str)
            logger.info(f"Канал {self.channel}: смещение -> {offset} В")
            return offset
        except pyvisa.VisaIOError as e:
            logger.error(f"Не удалось считать смещение: {e}")
            raise
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка преобразования значения смещения: {e}")
            raise

    def get_current_settings(self) -> dict:
        try:
            return {
            'channel': self.get_channel(),
            'frequency': self.get_frequency(),
            'amplitude': self.get_amplitude(),
            'waveform': self.get_waveform(),
            'offset': self.get_offset(),
        }
        except Exception as e:
            logger.error(f"Не удалось собрать полные настройки генератора: {e}")
            raise
