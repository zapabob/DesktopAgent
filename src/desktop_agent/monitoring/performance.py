<<<<<<< HEAD
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
    
    def track(self, metric_name, value):
        self.metrics[metric_name] = value
=======
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
    
    def track(self, metric_name, value):
        self.metrics[metric_name] = value
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
        return f"Tracked {metric_name}: {value}" 