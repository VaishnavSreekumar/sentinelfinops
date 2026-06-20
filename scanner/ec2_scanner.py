import boto3

def get_instances():
    ec2 = boto3.client("ec2")

    response = ec2.describe_instances()

    instances = []

    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:

            instances.append({
                "instance_id": instance["InstanceId"],
                "instance_type": instance["InstanceType"]
            })

    return instances