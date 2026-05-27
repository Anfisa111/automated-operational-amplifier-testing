from .base import InstrumentBase
import pyvisa
import time
import re
import logging
import numpy as np

logger = logging.getLogger(__name__)

class Oscilloscope(InstrumentBase):
    def __init__(self, resource_name: str, timeout: int = 10000):
        super().__init__(resource_name, timeout)

    def connect(self) -> 'Oscilloscope':
        try:
            super().connect()
            self.instrument.read_termination = '\n'
            self.instrument.write_termination = '\n'
            return self
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка протокола при настройке терминации: {e}")
            raise

    def set_channel_display(self, channel: int, state: bool) -> None:
        """Включить/выключить отображение канала (CH1-CH4)."""
        if not isinstance(channel, int) or not isinstance(state, bool):
            raise TypeError("channel должен быть int, state должен быть bool")
        
        try:
            cmd = f":CH{channel}:DISPlay {'ON' if state else 'OFF'}"
            self.write(cmd)
        except pyvisa.VisaIOError as e:
            logger.error(f"Не удалось изменить отображение CH{channel}: {e}")
            raise

    def set_channel_scale(self, channel: int, scale: str) -> None:
        """Установить масштаб (например, '100mV', '2V')."""
        if not isinstance(scale, str):
            raise TypeError("Масштаб (scale) должен быть строкой, например '100mV'")
        
        try:
            self.write(f":CH{channel}:SCALe {scale}")
            time.sleep(0.1)
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка при установке масштаба CH{channel}: {e}")
            raise

    def set_channel_coupling(self, channel: int, coupling: str) -> None:
        """Установить режим связи канала: AC, DC или GND."""
        if not isinstance(coupling, str) or coupling.upper() not in ['AC', 'DC', 'GND']:
            raise ValueError(f"Недопустимый тип связи: {coupling}. Ожидается AC, DC или GND.")
        
        try:
            self.write(f":CH{channel}:COUPling {coupling.upper()}")
            time.sleep(0.1)
            self.query("*OPC?")
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка при установке режима связи для CH{channel}: {e}")
            raise
        
    def set_probe_attenuation(self, channel: int, attenuation: int) -> None:
        """Установить делитель щупа (1, 10)."""
        if attenuation not in [1, 10]:
            raise ValueError(f"Нетипичный делитель щупа: {attenuation}X. Проверьте настройки.")
        
        try:
            self.write(f":CH{channel}:PROBe {attenuation}X")
            logger.debug(f"CH{channel} attenuation set to {attenuation}X")
        except pyvisa.VisaIOError as e:
            logger.error(f"Не удалось установить делитель щупа на CH{channel}: {e}")
            raise

    # --- Временная база и триггер ---
    def set_horizontal_scale(self, scale: str) -> None:
        """Установить развертку времени (например, '1.0ms', '200us')."""
        if not isinstance(scale, str):
            raise TypeError("Развертка времени должна быть строкой (напр. '1.0ms')")
        
        try:
            self.write(f":HORIzontal:SCALe {scale}")
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка при изменении временной развертки: {e}")
            raise

    def setup_trigger(self, source: str = "CH1", mode: str = "AUTO", level: float = 0.0) -> None:
        """Настроить триггер."""
        if not isinstance(level, (int, float)):
            raise TypeError("Уровень триггера должен быть числом")
        
        try:
            self.write(f":TRIGger:SINGle:EDGE:SOURce {source}")
            self.write(f":TRIGger:SINGle:MODe {mode}")
            self.write(f":TRIGger:SINGle:EDGE:LEVel {level}")
        except pyvisa.VisaIOError as e:
            logger.error(f"Сбой при настройке триггера ({source}, {mode}): {e}")
            raise

    # --- Управление состоянием ---
    def run(self) -> None:
        """Запустить сбор данных."""
        try:
            self.write(":RUNning RUN")
            logger.debug("Сбор данных запущен")
        except pyvisa.VisaIOError as e:
            logger.error(f"Не удалось запустить сбор данных (RUN): {e}")
            raise

    def stop(self) -> None:
        """Остановить сбор данных."""
        try:
            self.write(":RUNning STOP")
            logger.debug("Сбор данных остановлен")
        except pyvisa.VisaIOError as e:
            logger.error(f"Не удалось остановить сбор данных (STOP): {e}")
            raise 

    def clear(self) -> None:
        """Очистить буфер ввода-вывода осциллографа."""
        try:
            if self.instrument:
                self.instrument.clear()
        except pyvisa.VisaIOError as e:
            logger.warning(f"Не удалось очистить буфер осциллографа: {e}")

    # --- Получение данных ---
    def get_vpp(self, channel: int) -> float:
        try:
            # Делаем 3 запроса и берем медиану
            values = []
            for _ in range(3):
                raw_response = self.query(f":MEASUrement:CH{channel}:PKPK?")
                match = re.search(r"([-+]?\d*\.\d+|\d+)", raw_response)
                if match:
                    value = float(match.group(1))
                    if "mV" in raw_response:
                        value /= 1000.0
                    values.append(value)
                time.sleep(0.05)
            
            if not values:
                return 0.0
                
            return float(np.median(values))
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка связи при замере Vpp на CH{channel}: {e}")
            return 0.0
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка парсинга данных Vpp на CH{channel}: {e}")
            return 0.0
        