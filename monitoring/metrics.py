import boto3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import load_config

def publish_cloudwatch_metric(metric_name, value, unit="Count"):
    """
    Publishes a custom metric to Amazon CloudWatch under the 'SentinelFinOps' namespace.
    """
    config = load_config()
    region = config["aws"]["default_region"]
    try:
        cw = boto3.client("cloudwatch", region_name=region)
        cw.put_metric_data(
            Namespace="SentinelFinOps",
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Dimensions": [
                        {
                            "Name": "Environment",
                            "Value": "Production"
                        }
                    ],
                    "Value": float(value),
                    "Unit": unit
                }
            ]
        )
        return True
    except Exception as e:
        print(f"Error publishing metric {metric_name} to CloudWatch: {e}")
        return False

def track_scan(completed=1, failed=0):
    publish_cloudwatch_metric("ScansCompleted", completed)
    if failed > 0:
        publish_cloudwatch_metric("ScansFailed", failed)

def track_remediation(completed=1, failed=0, savings=0.0):
    publish_cloudwatch_metric("RemediationsCompleted", completed)
    if failed > 0:
        publish_cloudwatch_metric("RemediationsFailed", failed)
    if savings > 0.0:
        publish_cloudwatch_metric("SavingsGenerated", savings, unit="None")

def track_accounts(count):
    publish_cloudwatch_metric("AccountCount", count)

def track_idempotent_skip():
    publish_cloudwatch_metric("IdempotentSkips", 1)

def track_lock_acquired():
    publish_cloudwatch_metric("LocksAcquired", 1)

def track_lock_denied():
    publish_cloudwatch_metric("LockDenied", 1)

def track_lock_released():
    publish_cloudwatch_metric("LockReleased", 1)

def track_lock_recovered():
    publish_cloudwatch_metric("LockRecovered", 1)

