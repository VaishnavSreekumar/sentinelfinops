import boto3
from scanner.config import AWS_REGION

def get_unattached_volumes():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    response = ec2.describe_volumes(
        Filters=[
            {
                'Name': 'status',
                'Values': ['available']
            }
        ]
    )
    
    volumes = []
    for vol in response.get("Volumes", []):
        volumes.append({
            "volume_id": vol["VolumeId"],
            "size_gb": vol["Size"],
            "volume_type": vol["VolumeType"],
            "availability_zone": vol["AvailabilityZone"],
            "create_time": vol["CreateTime"],
            "tags": vol.get("Tags", [])
        })
    return volumes

def estimate_ebs_monthly_cost(volume):
    size = volume.get("size_gb", 0)
    vol_type = volume.get("volume_type", "gp3")
    if vol_type == "gp3":
        rate = 0.08
    elif vol_type == "gp2":
        rate = 0.10
    else:
        rate = 0.10
    return size * rate
