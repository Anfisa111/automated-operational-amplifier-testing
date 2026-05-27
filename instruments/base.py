import pyvisa
import time
import logging
from abc import abstractmethod
from typing import Optional, Type, Any

logger = logging.getLogger(__name__)

class InstrumentBase:
    _rm = None
    _dll_path = 'C:/Windows/System32/visa32.dll'
    
    @classmethod
    def get_rm(cls) -> pyvisa.ResourceManager:
        if cls._rm is None:
            try:
                cls._rm = pyvisa.ResourceManager(cls._dll_path)
                logger.debug(f"ResourceManager создан с DLL: {cls._dll_path}")
            except Exception as e:
                logger.error(f"Ошибка загрузки VISA DLL: {e}")
                try:
                    cls._rm = pyvisa.ResourceManager()
                except Exception as final_e:
                    logger.critical(f"VISA библиотека не найдена! Проверьте установку драйверов: {final_e}")
                    raise
        return cls._rm
    
    def __init__(self, resource_name: str, timeout: int = 10000):
        self.resource_name = resource_name
        self.timeout = timeout
        self.instrument = None
        self.idn = None
        self.rm = self.get_rm()

    def connect(self) -> 'InstrumentBase':
        if self.instrument is not None:
            return self
        
        try:
            self.instrument = self.rm.open_resource(self.resource_name)
            self.instrument.timeout = self.timeout
            
            time.sleep(0.2)
            self.idn = self.instrument.query("*IDN?")
            logger.info(f"Подключены к {self.idn}")
            
            self._configure()
            
            return self
        
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка связи VISA при подключении к {self.resource_name}: {e}")
            self.cleanup()
            raise
        except ValueError as e:
            logger.error(f"Неверные параметры ресурса {self.resource_name}: {e}")
            raise

    @abstractmethod
    def _configure(self):
        pass

    def write(self, command: str) -> None:
        if self.instrument is None:
            raise ConnectionError(f"Прибор {self.resource_name} не подключен")
        
        try:
            self.instrument.write(command)
            logger.debug(f"WRITE: {command}")
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка отправки команды '{command}': {e}")
            raise
    
    def query(self, command: str) -> str:
        if self.instrument is None:
            raise ConnectionError(f"{self.resource_name} is not connected")
        
        try:
            raw_response = self.instrument.query(command)
            if raw_response is None:
                raise pyvisa.VisaIOError("Прибор вернул пустой ответ")
            
            response = raw_response.strip()
            logger.debug(f"QUERY: {command} -> {response}")
            return response
        except pyvisa.VisaIOError as e:
            logger.error(f"Ошибка при запросе '{command}': {e}")
            raise

    def disconnect(self) -> None:
        if self.instrument:
            try:
                self.instrument.close()
                logger.info(f"Отключен прибор {self.resource_name}")
            
            except Exception as e:
                logger.warning(f"Ошибка при отключении прибора: {e}")

            finally:
                self.instrument = None

    def cleanup(self) -> None:
        self.disconnect()
            
    def __enter__(self) -> 'InstrumentBase':
        return self.connect()
    
    def __exit__(self,
                 _exc_type: Optional[Type[BaseException]],
                 _exc_val: Optional[BaseException],
                 _exc_tb: Any
    ) -> None:
        self.disconnect()
