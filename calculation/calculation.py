import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import t
import logging

logger = logging.getLogger(__name__)

def calculate_unity_gain_bandwidth(freqs, gains_db, alpha=0.05):
    """
    Нахождение параметров a и c из уравнения a*lg(f/c) и их доверительных интервалов.
    """
    if len(freqs) < 2:
        return None

    def model_func(f, a, c):
        return a * (np.log10(f) - np.log10(c))

    p0 = [-20, freqs.mean()]

    try:
        # popt: оптимальные значения [a, c]
        # pcov: матрица ковариации, из которой берем ошибки
        popt, pcov = curve_fit(model_func, freqs, gains_db, p0=p0)
        
        a_fit, c_fit = popt
        
        # Стандартные ошибки параметров
        perr = np.sqrt(np.diag(pcov))
        
        # Квантиль t-распределения Стьюдента для интервала
        dof = len(freqs) - 2  # степени свободы
        t_crit = t.ppf(1 - alpha / 2, dof)
        
        # Доверительные интервалы
        a_interval = (a_fit - t_crit * perr[0], a_fit + t_crit * perr[0])
        c_interval = (max(1e-3, c_fit - t_crit * perr[1]), c_fit + t_crit * perr[1])
        
        return {
            'a': a_fit,
            'a_conf': a_interval,
            'c': c_fit,
            'c_conf': c_interval
        }
    
    except Exception as e:
        logger.error(f"Ошибка при выполнении аппроксимации curve_fit: {e}")
        return None
    