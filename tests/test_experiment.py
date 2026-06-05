import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import pyvisa

from instruments.base import InstrumentBase
from instruments.generator import Generator
from instruments.oscilloscope import Oscilloscope
from calculation.calculation4 import calculate_unity_gain_bandwidth, get_required_n_min


class QueryMock:
    """
    Умный мок для метода query. 
    Предотвращает ошибки StopIteration и корректно обрабатывает *IDN? при connect().
    """
    def __init__(self, pkp_values=None, raise_on_pkp=False):
        self.pkp_values = pkp_values or ["1.20V", "1.50V", "1.25V"]
        self.pkp_index = 0
        self.raise_on_pkp = raise_on_pkp

    def __call__(self, command):
        cmd = command.strip().upper()
        if "*IDN?" in cmd:
            return "MOCK,INSTRUMENT,0,1.0"
        if "FREQUENCY?" in cmd:
            return "1000.0"
        if "AMPLITUDE:UNIT?" in cmd:
            return "VPP"
        if "BASE:AMPLITUDE?" in cmd:
            return "5.0"
        if "WAVE?" in cmd:
            return "SINE"
        if "OFFSET?" in cmd:
            return "0.0"
        if "PKPK?" in cmd:
            if self.raise_on_pkp:
                raise pyvisa.VisaIOError("Simulated Timeout")
            val = self.pkp_values[self.pkp_index % len(self.pkp_values)]
            self.pkp_index += 1
            return val
        # Fallback для любых других запросов
        return "0.0"


class TestFourTerminalNetworkProject(unittest.TestCase):

    def setUp(self):
        # КРИТИЧЕСКИ ВАЖНО: Сбрасываем кэш ResourceManager перед каждым тестом,
        # чтобы @patch('pyvisa.ResourceManager') гарантированно подменял его.
        InstrumentBase._rm = None

    # ==========================================
    # 1. Тесты математического ядра
    # ==========================================
    def test_calculation_unity_gain_bandwidth(self):
        true_f_t = 1e6
        freqs = np.array([100e3, 200e3, 500e3, 1e6, 2e6])
        gains_db = -20 * (np.log10(freqs) - np.log10(true_f_t))
        
        result = calculate_unity_gain_bandwidth(freqs, gains_db)
        
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['f_t'], true_f_t, places=2)
        self.assertAlmostEqual(result['slope'], -20.0, places=2)

    def test_calculation_student_n_min(self):
        f_t_samples = [1.05e6, 1.06e6, 1.04e6, 1.05e6, 1.05e6]
        delta_target = 100e3
        
        n_min = get_required_n_min(f_t_samples, delta_target)
        
        self.assertIsInstance(n_min, int)
        self.assertLessEqual(n_min, 5)

    # ==========================================
    # 2. Тесты базового класса (base.py)
    # ==========================================
    @patch('pyvisa.ResourceManager')
    def test_instrument_base_connection(self, mock_rm_class):
        mock_session = MagicMock()
        mock_rm_class.return_value.open_resource.return_value = mock_session
        
        instr = InstrumentBase("USB0::0x1234::0x5678::STEST::INSTR")
        instr.connect()
        
        mock_rm_class.return_value.open_resource.assert_called_with("USB0::0x1234::0x5678::STEST::INSTR")
        self.assertIsNotNone(instr.instrument)

    @patch('pyvisa.ResourceManager')
    def test_instrument_base_context_manager_and_cleanup(self, mock_rm_class):
        mock_session = MagicMock()
        mock_rm_class.return_value.open_resource.return_value = mock_session
        
        with InstrumentBase("TEST::INSTR") as instr:
            self.assertIsNotNone(instr.instrument)
        
        mock_session.close.assert_called_once()
        instr.cleanup()

    @patch('pyvisa.ResourceManager')
    def test_instrument_base_write_query_errors(self, mock_rm_class):
        instr = InstrumentBase("TEST::INSTR")
        # Не вызываем connect(), instrument == None
        
        with self.assertRaises(ConnectionError):
            instr.write("CMD")
            
        with self.assertRaises(ConnectionError):
            instr.query("CMD?")

    # ==========================================
    # 3. Тесты генератора (generator.py)
    # ==========================================

    @patch('pyvisa.ResourceManager')
    def test_generator_full_coverage(self, mock_rm_class):
        mock_session = MagicMock()
        mock_session.query = QueryMock()
        mock_rm_class.return_value.open_resource.return_value = mock_session
        
        gen = Generator("TEST::GEN", default_channel=1)
        gen.connect()
        
        # Happy path: setters
        gen.reset()
        gen.set_channel(2)
        gen.set_frequency(1e6)
        gen.set_amplitude(2.5, 'VRMS')
        gen.set_offset(1.0)
        gen.set_phase(90)
        gen.set_waveform('square')
        gen.set_load_impedance(50)
        gen.output_on()
        gen.output_off()
        
        # Happy path: getters
        gen.get_channel()
        gen.get_frequency()
        gen.get_amplitude()
        gen.get_waveform()
        gen.get_offset()
        gen.get_current_settings()
        
        # Error paths (покрытие веток ValueError / TypeError)
        with self.assertRaises(ValueError): gen.set_channel(3)
        with self.assertRaises(TypeError): gen.set_frequency("string")
        with self.assertRaises(ValueError): gen.set_frequency(0)
        with self.assertRaises(TypeError): gen.set_amplitude("string")
        with self.assertRaises(ValueError): gen.set_amplitude(-1)
        with self.assertRaises(ValueError): gen.set_amplitude(1, 'INVALID_UNIT')
        with self.assertRaises(TypeError): gen.set_offset("string")
        with self.assertRaises(TypeError): gen.set_phase("string")
        with self.assertRaises(ValueError): gen.set_phase(400)
        with self.assertRaises(TypeError): gen.set_waveform(123)
        with self.assertRaises(ValueError): gen.set_waveform("INVALID")
        with self.assertRaises(TypeError): gen.set_load_impedance("string")
        with self.assertRaises(ValueError): gen.set_load_impedance(0)

    # ==========================================
    # 4. Тесты осциллографа (oscilloscope.py)
    # ==========================================
    @patch('pyvisa.ResourceManager')
    def test_oscilloscope_get_vpp_median(self, mock_rm_class):
        mock_session = MagicMock()
        mock_session.query = QueryMock(pkp_values=["1.20V", "1.50V", "1.25V"])
        mock_rm_class.return_value.open_resource.return_value = mock_session
        
        osc = Oscilloscope("USB0::0x1111::0x2222::OSC::INSTR")
        osc.connect()
        
        vpp_result = osc.get_vpp(channel=1)
        self.assertEqual(vpp_result, 1.25)

    @patch('pyvisa.ResourceManager')
    def test_oscilloscope_full_coverage(self, mock_rm_class):
        mock_session = MagicMock()
        mock_session.query = QueryMock()
        mock_rm_class.return_value.open_resource.return_value = mock_session
        
        osc = Oscilloscope("TEST::OSC")
        osc.connect()
        
        osc.set_channel_display(1, True)
        osc.set_channel_scale(1, "100mV")
        osc.set_channel_coupling(1, "AC")
        osc.set_probe_attenuation(1, 10)
        osc.set_horizontal_scale("1.0ms")
        osc.setup_trigger("CH1", "AUTO", 0.5)
        osc.run()
        osc.stop()
        osc.clear()
        osc.get_vpp(1)
        
        with self.assertRaises(TypeError): osc.set_channel_display("1", True)
        with self.assertRaises(TypeError): osc.set_channel_scale(1, 100)
        with self.assertRaises(ValueError): osc.set_channel_coupling(1, "INVALID")
        with self.assertRaises(ValueError): osc.set_probe_attenuation(1, 5)
        with self.assertRaises(TypeError): osc.set_horizontal_scale(1)
        with self.assertRaises(TypeError): osc.setup_trigger("CH1", "AUTO", "level")

if __name__ == "__main__":
    unittest.main()