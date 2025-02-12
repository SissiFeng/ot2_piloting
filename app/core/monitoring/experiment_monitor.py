class ExperimentMonitor:
    def __init__(self):
        self.metrics = PrometheusMetrics()
        
    def track_experiment(self, experiment_data):
        # 记录实验指标
        self.metrics.record_experiment_metrics(experiment_data)
