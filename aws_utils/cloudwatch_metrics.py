
import boto3
from datetime import datetime, timedelta
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
    network_in: bool = False,
    network_out: bool = False
) -> List[Dict[str, Any]]:
    metrics = []

    for instance_id in instance_ids:
        instance_metrics = {'InstanceId': instance_id}

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
                Statistics=['Sum']
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
                Statistics=['Sum']
            )
            instance_metrics['DiskWriteOps'] = disk_write_metric['Datapoints']

        if network_in:
            network_in_metric = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkIn',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Sum']
            )
            instance_metrics['NetworkIn'] = network_in_metric['Datapoints']

        if network_out:
            network_out_metric = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkOut',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Sum']
            )
            instance_metrics['NetworkOut'] = network_out_metric['Datapoints']

        metrics.append(instance_metrics)

    return metrics
