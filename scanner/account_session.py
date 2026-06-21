import boto3
import time
from datetime import datetime, timezone
from botocore.config import Config

# In-memory session cache: account_id -> (boto3_session, expiration_datetime)
session_cache = {}

def assume_member_role(account_id):
    """
    Assume SentinelFinOpsExecutionRole in the target account.
    Caches sessions and only refreshes them if they have expired or are about to expire (within 2 minutes).
    Uses STS AssumeRole with 3 retry attempts and exponential backoff.
    """
    now = datetime.now(timezone.utc)
    
    # Check cache
    if account_id in session_cache:
        session, expiry = session_cache[account_id]
        # Check if expiration is at least 2 minutes (120 seconds) in the future
        if (expiry - now).total_seconds() > 120:
            return session

    role_arn = f"arn:aws:iam::{account_id}:role/SentinelFinOpsExecutionRole"
    role_session_name = "SentinelFinOpsScanSession"
    
    # Timeout configuration to prevent hangs
    config = Config(connect_timeout=5, read_timeout=5)
    sts = boto3.client("sts", config=config)
    
    attempts = 3
    backoff = [1, 2, 4]
    
    for i in range(attempts):
        try:
            print("Assuming role...")
            response = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName=role_session_name,
                DurationSeconds=900
            )
            
            credentials = response["Credentials"]
            expiry = credentials["Expiration"]  # Datetime object (tz-aware UTC)
            
            session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"]
            )
            
            # Cache the session
            session_cache[account_id] = (session, expiry)
            print("Role assumed successfully")
            return session
        except Exception as e:
            if i < attempts - 1:
                time.sleep(backoff[i])
            else:
                print(f"Unable to assume role: {e}")
                
    return None
