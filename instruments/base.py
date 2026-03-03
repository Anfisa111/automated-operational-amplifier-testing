import pyvisa
from abc import ABC, abstractmethod

class InstrumentBase:
    _rm = None
    _dll_path = 'C:/Windows/System32/visa32.dll'
    
    @classmethod
    def _get_rm(cls):
        if cls._rm is None:
            cls._rm = pyvisa.ResourceManager(cls._dll_path)
            print(f"ResourceManager создан с DLL: {cls._dll_path}")
        return cls._rm
    
    def __init__(self, resource_name: str, timeout: int = 10000):
        self.resource_name = resource_name
        self.timeout = timeout
        self.instrument = None
        self.idn = None
        self.rm = self._get_rm()

    def connect(self):
        try:
            self.instrument = self.rm.open_resource(self.resource_name)
            self.instrument.timeout = self.timeout
            
            self.idn = self.instrument.query("*IDN?")
            print(f"Connected to: {self.idn}")

            self.instrument.write("*RST")
            self.instrument.write("*CLS")
            
            self._configure()
            
            return self
        
        except pyvisa.VisaIOError as e:
            print(f"Cannot connect to {self.resource_name}: {e}")
            self.cleanup()
            # self.rm.close()
            raise

    @abstractmethod
    def _configure(self):
        pass

    def write(self, command: str):
        if self.instrument is None:
            raise ConnectionError(f"Прибор {self.resource_name} не подключен")
        
        try:
            self.instrument.write(command)
            print(f"WRITE: {command}")
        except pyvisa.VisaIOError as e:
            print(f"Ошибка отправки команды '{command}': {e}")
            raise
    
    def query(self, command: str) -> str:
        if self.instrument is None:
            raise ConnectionError(f"{self.resource_name} is not connected")
        
        try:
            response = self.instrument.query(command).strip()
            print(f"QUERY: {command} -> {response}")
            return response
        except pyvisa.VisaIOError as e:
            print(f"Error query '{command}': {e}")
            raise

    def disconnect(self):
        if self.instrument is None:
            return
        
        if self.instrument:
            try:
                self.instrument.write("*RST")
                self.instrument.write("*CLS")
                self.instrument.close()
                print(f"Disconnected: {self.resource_name}")
            
            except Exception as e:
                print(f"Error disconnecting: {e}")

            finally:
                self.instrument = None

    def cleanup(self):
            if self.instrument:
                try:
                    self.instrument.close()
                except:
                    pass
                self.instrument = None
            self.connected = False
    def __enter__(self):
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    def __del__(self):
        self.disconnect()