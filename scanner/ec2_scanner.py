import boto3
from scanner.config import AWS_REGION

def get_instances(session=None, region=None):
    target_region = region if region else AWS_REGION
    if session:
        ec2 = session.client("ec2", region_name=target_region)
    else:
        ec2 = boto3.client("ec2", region_name=target_region)

    response = ec2.describe_instances()

    instances = []

    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:

            instance_name = "Unknown"
            if "Tags" in instance:
                for tag in instance["Tags"]:
                    if tag.get("Key") == "Name":
                        instance_name = tag.get("Value")
                        break

            instances.append({
                "instance_id": instance["InstanceId"],
                "instance_type": instance["InstanceType"],
                "instance_name": instance_name,
                "tags": instance.get("Tags", [])
            })

    return instances