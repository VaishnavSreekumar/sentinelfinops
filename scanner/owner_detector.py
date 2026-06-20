import json
import boto3

def get_instance_owner(instance_id):
    """
    Search AWS CloudTrail for the RunInstances event corresponding to the instance.
    Extract the identity of the creator (owner) and return it.
    If owner cannot be determined, return 'Unknown'.
    """
    client = boto3.client("cloudtrail")
    try:
        response = client.lookup_events(
            LookupAttributes=[
                {
                    "AttributeKey": "ResourceName",
                    "AttributeValue": instance_id
                }
            ],
            MaxResults=50
        )
        for event in response.get("Events", []):
            if event.get("EventName") == "RunInstances":
                ct_event_str = event.get("CloudTrailEvent")
                if ct_event_str:
                    try:
                        ct_event = json.loads(ct_event_str)
                        user_identity = ct_event.get("userIdentity", {})
                        identity_type = user_identity.get("type")
                        
                        if identity_type == "IAMUser":
                            return user_identity.get("userName", "Unknown")
                        elif identity_type == "AssumedRole":
                            session_issuer = user_identity.get("sessionContext", {}).get("sessionIssuer", {})
                            role_name = session_issuer.get("userName")
                            if role_name:
                                return role_name
                            
                            arn = user_identity.get("arn", "")
                            if "/" in arn:
                                return arn.split("/")[-1]
                        elif user_identity.get("userName"):
                            return user_identity.get("userName")
                    except Exception:
                        pass
                
                username = event.get("Username")
                if username:
                    return username
                    
    except Exception as e:
        print(f"Error looking up owner for {instance_id}: {e}")
        
    return "Unknown"
