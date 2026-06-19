import boto3
from datetime import datetime, timedelta, timezone

ec2 = boto3.client("ec2")
cloudwatch = boto3.client("cloudwatch")

IDLE_THRESHOLD = 5.0

# Temporary pricing table
INSTANCE_PRICES = {
    "t2.micro": 0.0116,
    "t3.micro": 0.0104,
    "t2.small": 0.023,
    "t3.small": 0.0208
}

response = ec2.describe_instances()

print("\n=== SentinelFinOps Cost Report ===\n")

for reservation in response["Reservations"]:
    for instance in reservation["Instances"]:

        instance_id = instance["InstanceId"]
        instance_type = instance["InstanceType"]

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

        hourly_cost = INSTANCE_PRICES.get(instance_type, 0)
        monthly_cost = hourly_cost * 24 * 30

        print(f"Instance ID: {instance_id}")
        print(f"Type: {instance_type}")
        print(f"CPU Usage: {avg_cpu:.2f}%")
        print(f"Estimated Monthly Cost: ${monthly_cost:.2f}")

        if avg_cpu < IDLE_THRESHOLD:
            print(" STATUS: IDLE")
            print(f" Potential Savings: ${monthly_cost:.2f}/month")
        else:
            print("STATUS: ACTIVE")

        print("-" * 50)