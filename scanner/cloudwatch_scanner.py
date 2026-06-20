import boto3
from datetime import datetime, timedelta, timezone
from scanner.config import AWS_REGION

cloudwatch = boto3.client(
    "cloudwatch",
    region_name=AWS_REGION
)

def get_average_cpu(instance_id):

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

    if not datapoints:
        return 0

    return sum(
        d["Average"] for d in datapoints
    ) / len(datapoints)