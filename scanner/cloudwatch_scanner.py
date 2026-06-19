import boto3
from datetime import datetime, timedelta, timezone

ec2 = boto3.client("ec2")
cloudwatch = boto3.client("cloudwatch")

response = ec2.describe_instances()

print("\n=== CPU Utilization Report ===\n")

for reservation in response["Reservations"]:
    for instance in reservation["Instances"]:

        instance_id = instance["InstanceId"]

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)

        metrics = cloudwatch.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[
                {
                    "Name": "InstanceId",
                    "Value": instance_id
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=["Average"]
        )

        datapoints = metrics["Datapoints"]

        if datapoints:
            avg_cpu = sum(d["Average"] for d in datapoints) / len(datapoints)
        else:
            avg_cpu = 0

        print(f"Instance: {instance_id}")
        print(f"Average CPU: {avg_cpu:.2f}%")
        print("-" * 40)