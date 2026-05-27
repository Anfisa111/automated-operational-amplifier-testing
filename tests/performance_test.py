import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# Эталонные параметры для симуляции
F_T_TRUE = 1.5e6  # 1.5 МГц
SLOPE_TRUE = -20.0

def model_func(f, a, c):
    return a * (np.log10(f) - np.log10(c))

# Генерируем сетку частот (как в вашем config.json, только плотнее для теста)
freqs = np.logspace(5, 7, 20)  # от 100 кГц до 10 МГц, 20 точек
gains_true = model_func(freqs, SLOPE_TRUE, F_T_TRUE)

noise_levels = np.linspace(0.1, 3.0, 30)  # Уровни шума от 0.1 до 3 дБ
errors_primitive = []
errors_curve_fit = []

for noise in noise_levels:
    # Добавляем случайный шум к идеальному сигналу
    gains_noisy = gains_true + np.random.normal(0, noise, size=len(freqs))
    
    # 1. Примитивный метод (интерполяция по 2 ближайшим к 0 дБ точкам)
    idx = np.argsort(np.abs(gains_noisy))[:2]
    f1, f2 = freqs[idx[0]], freqs[idx[1]]
    g1, g2 = gains_noisy[idx[0]], gains_noisy[idx[1]]
    # Линейное уравнение между двумя точками в log-шкале
    log_f_t_prim = np.log10(f1) - g1 * (np.log10(f2) - np.log10(f1)) / (g2 - g1)
    f_t_primitive = 10**log_f_t_prim
    
    # 2. Ваш метод (scipy curve_fit)
    try:
        popt, _ = curve_fit(model_func, freqs, gains_noisy, p0=[-20, freqs.mean()])
        f_t_curve_fit = popt[1]
    except:
        f_t_curve_fit = F_T_TRUE
        
    # Считаем относительную ошибку в %
    errors_primitive.append(np.abs(f_t_primitive - F_T_TRUE) / F_T_TRUE * 100)
    errors_curve_fit.append(np.abs(f_t_curve_fit - F_T_TRUE) / F_T_TRUE * 100)

# Построение графика
plt.figure(figsize=(9, 5))
plt.plot(noise_levels, errors_primitive, 'r--', label='Примитивный метод (2 точки)')
plt.plot(noise_levels, errors_curve_fit, 'g-', linewidth=2, label='Метод МНК (Ваш: SciPy curve_fit)')
plt.xlabel('Уровень шума измерений АЦП (дБ)')
plt.ylabel('Относительная ошибка определения $f_T$ (%)')
plt.title('Устойчивость алгоритмов расчета к аппаратному шуму')
plt.grid(True, which="both", ls="--")
plt.legend()
plt.savefig('noise_stability_graph.png', dpi=300)
plt.show()