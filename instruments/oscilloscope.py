import pyvisa
from .base import InstrumentBase
import time
import json
import re
import logging

logger = logging.getLogger(__name__)

class Oscilloscope(InstrumentBase):
    def __init__(self, resource_name: str, timeout: int = 10000):
        super().__init__(resource_name, timeout)

    def connect(self) -> 'Oscilloscope':
        super().connect()
        self.instrument.read_termination = '\n'
        self.instrument.write_termination = '\n'
        return self

    def set_channel_display(self, channel: int, state: bool):
        """Включить/выключить отображение канала (CH1-CH4)."""
        cmd = f":CH{channel}:DISPlay {'ON' if state else 'OFF'}"
        self.write(cmd)

    def set_channel_scale(self, channel: int, scale: str):
        """Установить масштаб (например, '100mV', '2V')."""
        self.write(f":CH{channel}:SCALe {scale}")

    def set_channel_coupling(self, channel: int, coupling: str):
        """Установить режим связи канала: AC, DC или GND."""
        self.write(f":CH{channel}:COUPling {coupling.upper()}")
        time.sleep(0.1)
        self.query("*OPC?")
        
    def set_probe_attenuation(self, channel: int, attenuation: int):
        """Установить делитель щупа (1, 10)."""
        self.write(f":CH{channel}:PROBe {attenuation}X")
        logger.debug(f"CH{channel} attenuation set to {attenuation}X")

    # --- Временная база и триггер ---
    def set_horizontal_scale(self, scale: str):
        """Установить развертку времени (например, '1.0ms', '200us')."""
        self.write(f":HORIzontal:SCALe {scale}")

    def setup_trigger(self, source: str = "CH1", mode: str = "AUTO", level: float = 0.0):
        """Настроить триггер."""
        self.write(f":TRIGger:SINGle:EDGE:SOURce {source}")
        self.write(f":TRIGger:SINGle:MODe {mode}")
        self.write(f":TRIGger:SINGle:EDGE:LEVel {level}")

    # --- Управление состоянием ---
    def run(self):
        """Запустить сбор данных."""
        self.write(":RUNning RUN")

    def stop(self):
        """Остановить сбор данных."""
        self.write(":RUNning STOP") 

    # --- Получение данных ---
    def get_vpp(self, channel: int) -> float:
        try:
            # Команда возвращает число в научной нотации, например '1.020E+00'
            raw_response = self.query(f":MEASUrement:CH{channel}:PKPK?")
            match = re.search(r"([-+]?\d*\.\d+|\d+)", raw_response)
            if not match:
                logger.warning(f"Не удалось распарсить Vpp для CH{channel}: {raw_response}")
                return 0.0
        
            value = float(match.group(1))
            if "mV" in raw_response:
                value /= 1000.0
        
            return value
        except Exception as e:
            logger.error(f"Ошибка измерения Vpp на CH{channel}: {e}")
            return 0.0
        