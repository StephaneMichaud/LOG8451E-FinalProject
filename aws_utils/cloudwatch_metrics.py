
import boto3
from datetime import datetime
import os
import matplotlib.pyplot as plt
from typing import List, Dict, Any

def get_instance_metrics(
    instance_ids: List[str],
    cloudwatch: boto3.client,
    start_time: datetime,
    end_time: datetime,
    period: int = 300,
    cpu_utilization: bool = False,
    disk_read_ops: bool = False,
    disk_write_ops: bool = False,
) -> List[Dict[str, Any]]:
    metrics = []

    for instance_name in instance_ids.keys():
        instance_id = instance_ids[instance_name]
        instance_metrics = {'InstanceName': instance_name}

        if cpu_utilization:
            cpu_metric = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Average']
            )
            instance_metrics['CPUUtilization'] = cpu_metric['Datapoints']

        if disk_read_ops:
            disk_read_metric = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='DiskReadOps',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Average']
            )
            instance_metrics['DiskReadOps'] = disk_read_metric['Datapoints']

        if disk_write_ops:
            disk_write_metric = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='DiskWriteOps',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Average']
            )
            instance_metrics['DiskWriteOps'] = disk_write_metric['Datapoints']

        metrics.append(instance_metrics)

    return metrics

def plot_metrics(metrics, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    # Get all unique metric types
    metric_types = set()
    for instance_metrics in metrics:
        metric_types.update(instance_metrics.keys())
    metric_types.remove('InstanceName')  # Remove the instance name from metric types

    for metric_type in metric_types:
        plt.figure(figsize=(12, 6))
        for instance_metrics in metrics:
            instance_name = instance_metrics['InstanceName']
            if metric_type in instance_metrics:
                metric_data = instance_metrics[metric_type]
                if metric_data:
                    timestamps = [point['Timestamp'] for point in metric_data]
                    values = [point['Average'] for point in metric_data]
                    plt.plot(timestamps, values, label=instance_name)
        
        plt.title(f"{metric_type} over time")
        plt.xlabel("Time")
        plt.ylabel(metric_type)
        plt.legend()
        plt.grid(True)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Adjust layout to prevent cutting off labels
        plt.tight_layout()
        
        # Save the plot
        plot_filename = f"{metric_type.replace(' ', '_').lower()}.png"
        plot_path = os.path.join(out_dir, plot_filename)
        plt.savefig(plot_path)
        plt.close()
    
        print(f"Stats collected and plots saved in the '{out_dir}' directory")
