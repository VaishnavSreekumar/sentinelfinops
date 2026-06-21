import boto3
import json
import os
import sys

# Ensure config_loader is importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import load_config

def bootstrap_member_account(account_id):
    """
    Assume OrganizationAccountAccessRole in the target member account,
    create the SentinelFinOpsExecutionRole, and attach the least-privilege scanning and remediation policies.
    """
    config = load_config()
    mgmt_acc = config["aws"]["management_account_id"]
    role_name = config["aws"]["role_name"]
    
    print("-" * 65)
    print(f"Bootstrapping member account: {account_id}")
    
    # 1. Assume administrative access in member account
    sts = boto3.client("sts")
    admin_role_arn = f"arn:aws:iam::{account_id}:role/OrganizationAccountAccessRole"
    
    try:
        assumed = sts.assume_role(
            RoleArn=admin_role_arn,
            RoleSessionName="SentinelFinOpsBootstrapSession",
            DurationSeconds=900
        )
        creds = assumed["Credentials"]
        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"]
        )
    except Exception as e:
        print(f"FAILED: Cannot assume OrganizationAccountAccessRole in {account_id}. Error: {e}")
        return False
        
    # 2. Setup IAM trust relationship policy
    iam = session.client("iam")
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": f"arn:aws:iam::{mgmt_acc}:root"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        # Create execution role
        try:
            iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Execution role assumed by SentinelFinOps scanner and remediation engine."
            )
            print(f"Role '{role_name}' successfully created in member account.")
        except iam.exceptions.EntityAlreadyExistsException:
            print(f"Role '{role_name}' already exists. Updating trust policy...")
            iam.update_assume_role_policy(
                RoleName=role_name,
                PolicyDocument=json.dumps(trust_policy)
            )
            
        # 3. Attach read-only managed policies
        managed_policies = [
            "arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess",
            "arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess",
            "arn:aws:iam::aws:policy/AWSCloudTrail_ReadOnlyAccess"
        ]
        for policy_arn in managed_policies:
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            
        # 4. Attach remediation custom policy
        remediation_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:StopInstances",
                        "ec2:DeleteVolume",
                        "ec2:CreateImage",
                        "ec2:CreateSnapshot"
                    ],
                    "Resource": "*"
                }
            ]
        }
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="SentinelFinOpsRemediationPolicy",
            PolicyDocument=json.dumps(remediation_policy)
        )
        print(f"Remediation policy attached to role '{role_name}' in member account.")
        print(f"Bootstrapping completed successfully for account: {account_id}")
        return True
    except Exception as e:
        print(f"FAILED: Error configuring IAM role in account {account_id}. Error: {e}")
        return False

def bootstrap_all_accounts():
    """
    Query AWS Organizations to discover member accounts and trigger bootstrap configuration on each.
    """
    from scanner.account_discovery import discover_accounts
    accounts = discover_accounts()
    
    if not accounts:
        print("No active organization accounts discovered to bootstrap.")
        return
        
    print(f"Discovered {len(accounts)} accounts. Commencing bootstrap automation...")
    success = 0
    failed = 0
    
    for acc in accounts:
        acc_id = acc["account_id"]
        # Skip bootstrapping the management account itself
        config = load_config()
        if acc_id == config["aws"]["management_account_id"]:
            print(f"Skipping management account: {acc_id}")
            continue
            
        if bootstrap_member_account(acc_id):
            success += 1
        else:
            failed += 1
            
    print("=" * 65)
    print(f"Bootstrap Run Complete: {success} Succeeded, {failed} Failed.")
    print("=" * 65)
