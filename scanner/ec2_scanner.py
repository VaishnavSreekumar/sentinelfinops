import boto3

ec2 = boto3.client("ec2")

response = ec2.describe_instances()

print("\n=== EC2 Instances ===\n")

for reservation in response["Reservations"]:
    for instance in reservation["Instances"]:
        print(f"Instance ID: {instance['InstanceId']}")
        print(f"State: {instance['State']['Name']}")
        print(f"Type: {instance['InstanceType']}")
        print("-" * 40)