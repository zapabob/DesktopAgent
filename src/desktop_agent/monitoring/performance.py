class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
    
    def track(self, metric_name, value):
        self.metrics[metric_name] = value
        return f"Tracked {metric_name}: {value}" 