import matplotlib.pyplot as plt
import numpy as np

def plot_bode(frequencies, gains, f_t, slope, intercept, save_path='bode_plot.png'):
    """
    Строит диаграмму Боде (АЧХ) на основе экспериментальных данных и аппроксимации.
    """
    plt.figure(figsize=(10, 6))
    
    # 1. Экспериментальные точки
    plt.semilogx(frequencies, gains, 'ro', label='Экспериментальные данные')
    
    # 2. Линия аппроксимации
    # Генерируем частотную сетку от мин. частоты до 1.5 * f_t для наглядности
    f_min = min(frequencies)
    f_max = max(f_t * 1.5, max(frequencies))
    f_plot = np.logspace(np.log10(f_min), np.log10(f_max), 100)
    gain_plot = slope * np.log10(f_plot) + intercept
    
    plt.semilogx(f_plot, gain_plot, 'b--', alpha=0.7, 
                 label=f'Аппроксимация ({slope:.1f} дБ/дек)')
    
    # 3. Линия 0 дБ и отметка f_T
    plt.axhline(0, color='black', linewidth=1, linestyle='-')
    plt.axvline(f_t, color='green', linestyle=':', linewidth=2, 
                label=f'f_T ≈ {f_t/1e6:.3f} МГц')
    
    # Оформление
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title('Амплитудно-частотная характеристика (АЧХ) ОУ', fontsize=14)
    plt.xlabel('Частота (Гц)', fontsize=12)
    plt.ylabel('Усиление (дБ)', fontsize=12)
    plt.legend()
    
    # Сохранение и показ
    plt.savefig(save_path, dpi=300)
    print(f"График успешно сохранен в: {save_path}")
    plt.show()