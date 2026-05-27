import time
from calculation import calculate_unity_gain_bandwidth
import numpy as np
import matplotlib.pyplot as plt

# Имитируем массив данных эксперимента
freqs = np.logspace(5, 7, 10)
gains_db = -20 * (np.log10(freqs) - np.log10(1.5e6))

# Замеряем чистую математику (Ваш модуль calculation.py)
start_math = time.perf_counter()
calculate_unity_gain_bandwidth(freqs, gains_db)
end_math = time.perf_counter()

math_time_actual = end_math - start_math  # Реальное время работы SciPy на вашем ПК

# Имитируем временные затраты на железо для 10 точек частот
visa_queries_count = 10 * 2  # Считать Vin и Vout для каждой частоты
simulated_visa_time = visa_queries_count * 0.040  # 40 мс на один запрос query()

# Имитируем работу Smart Scaling (допустим, шкала переключилась 3 раза за эксперимент)
simulated_smart_scaling_time = 3 * 0.150  # 150 мс на команду изменения масштаба реле

# Общее время
total_time = math_time_actual + simulated_visa_time + simulated_smart_scaling_time

# Переводим в проценты
p_visa = (simulated_visa_time / total_time) * 100
p_scale = (simulated_smart_scaling_time / total_time) * 100
p_math = (math_time_actual / total_time) * 100

# Построение круговой диаграммы
labels = ['Ожидание ответов приборов (VISA I/O)', 'Работа Smart Scaling (Реле)', 'Математическое ядро (Python/SciPy)']
sizes = [p_visa, p_scale, p_math]
colors = ['#ff9999','#66b3ff','#99ff99']
explode = (0, 0, 0.2)  # Выносим сектор математики, чтобы подчеркнуть его малость

plt.figure(figsize=(8, 6))
plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.2f%%', startangle=140)
plt.title('Распределение временных затрат измерительного цикла')
plt.savefig('time_bottleneck_chart.png', dpi=300)
plt.show()