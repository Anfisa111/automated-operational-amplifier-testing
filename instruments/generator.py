import pyvisa
from typing import Optional, Tuple
import time
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
        # self.instrument.write("*RST")
        try:
            self.write(f":CHANnel{self.channel}:MODE CONTINUE")
            logger.info(f"Генератор сигналов (канал {self.channel}) сконфигурирован")
        except Exception as e:
            logger.error(f"Ошибка при базовой конфигурации: {e}")
        return self

    def connect(self) -> 'Generator':
        super().connect()
        self._configure()
        return self

    def reset(self) -> 'Generator':
        self.write("*RST")
        logger.info("Выполнен сброс к заводским настройкам")
        return self

    def set_channel(self, channel: int) -> 'Generator':
        if channel not in [1, 2]:
            raise ValueError("Channel must be 1 or 2")
        self.channel = channel
        return self

    def set_frequency(self, frequency: float) -> 'Generator':
        min_freq = 1e-6
        if frequency <= min_freq:
            raise ValueError("Частота должна быть больше 1 мкГц")
        
        self.write(f":CHANnel{self.channel}:BASE:FREQuency {frequency}")
        logger.debug(f"Канал {self.channel}: установлена частота {frequency} Гц")
        return self
    
    def set_amplitude(self, amplitude: float, unit: str = 'VPP') -> 'Generator':
        unit = unit.upper()
        if unit not in self.VALID_AMPLITUDE_UNITS:
            raise ValueError(f"Недопустимая единица измерения. Допустимые: {self.VALID_AMPLITUDE_UNITS}")
        self.write(f":CHANnel{self.channel}:AMPLitude:UNIT {unit}")
        self.write(f":CHANnel{self.channel}:BASE:AMPLitude {amplitude}")
        logger.info (f"Канал {self.channel}: установлена амплитуда {amplitude} {unit}")
        return self
    
    def set_offset(self, offset) -> 'Generator':
        """Установить смещение в Volts"""
        self.write(f":CHANnel{self.channel}:BASE:OFFSet {offset}")
        logger.info(f"Канал {self.channel}: установлено смещение {offset} В")
        return self
    
    def set_phase(self, phase: float) -> 'Generator':
        if not -360 <= phase <= 360:
            raise ValueError("Фаза должна быть в диапазоне [-360, 360]")
        self.write(f":CHANnel{self.channel}:BASE:PHASE {phase}")
        return self

    def set_waveform(self, waveform: str) -> 'Generator':
        waveform = waveform.upper()
        if waveform not in self.VALID_WAVEFORMS:
            raise ValueError(f"Недопустимая форма сигнала. Допустимые: {self.VALID_WAVEFORMS}")
        self.write(f":CHANnel{self.channel}:BASE:WAVE {waveform}")
        logger.info(f"Канал {self.channel}: установлена форма сигнала {waveform}")
        return self
    
    def set_load_impedance(self, impedance: float) -> 'Generator':
        if not 1 <= impedance <= 10000:
            raise ValueError("Импеданс нагрузки должен быть в диапазоне [1, 10000] Ом")
        self.write(f":CHANnel{self.channel}:LOAD {impedance}")
        logger.info(f"Канал {self.channel}: установлен импеданс нагрузки {impedance} Ом")
        return self

    def output_on(self) -> 'Generator':
        self.write(f":CHANnel{self.channel}:OUTPut ON")
        logger.info(f"Канал {self.channel}: выход включен")
        return self
    
    def output_off(self) -> 'Generator':
        self.write(f":CHANnel{self.channel}:OUTPut OFF")
        logger.info(f"Канал {self.channel}: выход выключен")
        return self
    
    def get_frequency(self) -> float:
        freq_str = self.query(f":CHANnel{self.channel}:BASE:FREQuency?").strip()
        frequency = float(freq_str)
        logger.info(f"Канал {self.channel}: текущая частота - {frequency} Гц")
        return frequency
    
    def get_amplitude(self) -> Tuple[float, str]:
        """Получить текущую амплитуду и единицы измерения"""
        unit = self.query(f":CHANnel{self.channel}:AMPLitude:UNIT?").strip()
        amp_str = self.query(f":CHANnel{self.channel}:BASE:AMPLitude?").strip()
        amplitude = float(amp_str)
        logger.info(f"Канал {self.channel}: амплитуда -> {amplitude} {unit}")
        return amplitude, unit
    
    def get_waveform(self) -> str:
        waveform = self.query(f":CHANnel{self.channel}:BASE:WAVE?").strip()
        logger.info(f"Канал {self.channel}: текущая форма сигнала -> {waveform}")
        return waveform
    
    def get_channel(self) -> int:
        logger.info(f"Текущий канал: {self.channel}")
        return self.channel

    def get_offset(self) -> float:
        offset_str = self.query(f":CHANnel{self.channel}:BASE:OFFSet?").strip()
        offset = float(offset_str)
        logger.info(f"Канал {self.channel}: смещение -> {offset} В")
        return offset

    def get_current_settings(self) -> dict:
        return {
            'channel': self.get_channel(),
            'frequency': self.get_frequency(),
            'amplitude': self.get_amplitude(),
            'waveform': self.get_waveform(),
            'offset': self.get_offset(),
        }
