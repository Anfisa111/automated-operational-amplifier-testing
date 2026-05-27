from archive.op_test1 import run_measurement_cycle, ExperimentConfig
from unittest.mock import MagicMock

def test_measurement_cycle_flow():
    """Проверка, что цикл измерений проходит по всем частотам из конфига."""
    mock_scope = MagicMock()
    mock_gen = MagicMock()
    
    # Имитируем ответ осциллографа (Vpp = 0.5V)
    mock_scope.get_vpp.return_value = 0.5
    
    test_cfg = ExperimentConfig(
        frequencies=[1e3, 10e3],
        v_amp=0.6,
        ch_in=1,
        ch_out=2,
        probe_attenuation=10
    )
    
    results = run_measurement_cycle(mock_scope, mock_gen, test_cfg)
    
    assert len(results) == 2
    # Проверяем, что генератор дважды менял частоту
    assert mock_gen.set_frequency.call_count == 2