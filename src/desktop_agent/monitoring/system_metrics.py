<<<<<<< HEAD
import psutil
import logging

def get_cpu_temperature():
    try:
        sensors_data = psutil.sensors_temperatures()
        # マルチプラットフォーム対応
        for key in ['coretemp', 'cpu_thermal', 'k10temp', 'Tdie']:
            if key in sensors_data and len(sensors_data[key]) > 0:
                return sensors_data[key][0].current
        return 0.0
    except Exception as e:
        logging.warning(f"温度取得エラー: {str(e)}")
=======
import psutil
import logging

def get_cpu_temperature():
    try:
        sensors_data = psutil.sensors_temperatures()
        # マルチプラットフォーム対応
        for key in ['coretemp', 'cpu_thermal', 'k10temp', 'Tdie']:
            if key in sensors_data and len(sensors_data[key]) > 0:
                return sensors_data[key][0].current
        return 0.0
    except Exception as e:
        logging.warning(f"温度取得エラー: {str(e)}")
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
        return 0.0 