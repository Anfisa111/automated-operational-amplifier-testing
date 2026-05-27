import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import t
import logging

logger = logging.getLogger(__name__)

def calculate_unity_gain_bandwidth(freqs, gains_db, alpha=0.05):
    """
    Нахождение параметров a (наклон) и c (частота единичного усиления f_T) 
    из уравнения Gain = a * (log10(f) - log10(c)).
    """
    if len(freqs) < 2:
        return None

    # Модель: a * (log10(f) - log10(c))
    # Здесь 'c' - это и есть f_T (частота, где усиление = 0 дБ)
    def model_func(f, a, c):
        # Защита от log10(0) и log10(отрицательное)
        f_safe = np.maximum(f, 1e-10)  # Минимальная частота 0.1 пГц
        c_safe = max(c, 1e-10)
        return a * (np.log10(f_safe) - np.log10(c_safe))

    # Начальное приближение: наклон -20, частота c около средней из измеренных
    p0 = [-20, np.mean(freqs)]

    try:
        # popt: оптимальные значения [a, c]
        # pcov: матрица ковариации для расчета ошибок
        popt, pcov = curve_fit(model_func, freqs, gains_db, p0=p0)
        
        a_fit, c_fit = popt
        
        # Стандартные ошибки параметров
        perr = np.sqrt(np.diag(pcov))
        
        # Квантиль t-распределения Стьюдента для интервала
        dof = len(freqs) - 2  # степени свободы
        t_crit = t.ppf(1 - alpha / 2, dof)
        
        # Доверительные интервалы
        a_interval = (a_fit - t_crit * perr[0], a_fit + t_crit * perr[0])
        # Защита от отрицательных частот в интервале
        c_interval = (max(1e3, c_fit - t_crit * perr[1]), c_fit + t_crit * perr[1])
        
        # Для совместимости с plot_bode вычисляем стандартный Y-intercept (k)
        # Уравнение прямой: y = a*x + k. 
        # Наша модель: y = a*log(f) - a*log(c). 
        # Значит intercept = -a * log10(c)
        intercept_val = -a_fit * np.log10(c_fit)

        return {
            'f_t': c_fit,           # c_fit — это частота единичного усиления
            'slope': a_fit,         # a_fit — реальный наклон АЧХ
            'intercept': intercept_val, # Для построения прямой на графике
            'f_conf': c_interval,
            'slope_conf': a_interval
        }
    
    except Exception as e:
        logger.error(f"Ошибка при выполнении аппроксимации curve_fit: {e}")
        return None

def get_required_n_min(f_t_samples, delta_target, alpha=0.05):
    """
    Вычисляет n_min на основе имеющейся выборки результатов f_T.
    """
    n_current = len(f_t_samples)
    if n_current < 2:
        return 999  # Пока выборка слишком мала, требуем продолжать замеры
    
    sigma = np.std(f_t_samples, ddof=1)
    if sigma == 0:
        return 2  # Защита от деления на 0
        
    dof = n_current - 1
    t_crit = t.ppf(1 - alpha / 2, df=dof)

    n_min_val = ((t_crit * sigma) / delta_target) ** 2
    return int(np.ceil(n_min_val))