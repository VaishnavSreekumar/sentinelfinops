import boto3
from scanner.ec2_scanner import get_instances
from scanner.cloudwatch_scanner import get_average_cpu
from engine.idle_engine import is_idle
from engine.cost_engine import monthly_cost
from notifications.notifier import send_alert, send_ebs_alert
from scanner.owner_detector import get_instance_owner
from storage.snooze_manager import is_snoozed
from scanner.config import (
    AWS_REGION, ALLOWED_REGIONS, DENIED_REGIONS,
    MAINTENANCE_WINDOW_START, MAINTENANCE_WINDOW_END
)
from storage.alert_state_manager import get_alert_state, set_alert_state, clear_alert_state
from storage.audit_logger import log_action
from scanner.account_discovery import discover_accounts
from scanner.account_session import assume_member_role
from storage.remediation_manager import get_current_account_id
from reporting.savings_report import generate_savings_report

def is_tag_exempt(tags):
    if not tags:
        return False
    for tag in tags:
        key = tag.get("Key", "").strip().lower()
        val = tag.get("Value", "").strip().lower()
        if key == "sentinelfinops" and val == "ignore":
            return True
    return False

def run_scan():
    print("\n=== SentinelFinOps ===\n")
    
    accounts = discover_accounts()
    curr_account = get_current_account_id()
    
    if not accounts:
        print("No organization accounts discovered or not in organization. Falling back to local account.")
        accounts = [{
            "account_id": curr_account if curr_account else "LocalAccount",
            "account_name": "LocalPrimaryAccount",
            "account_email": "local@sentinelfinops.local",
            "account_status": "ACTIVE"
        }]

    scanned_count = 0
    failed_count = 0

    for acc in accounts:
        account_id = acc["account_id"]
        account_name = acc["account_name"]
        
        print("=" * 60)
        print(f"Account: {account_name}")
        print(f"Account ID: {account_id}")
        
        try:
            if account_id == curr_account:
                session = boto3.Session()
            else:
                session = assume_member_role(account_id)
                if not session:
                    raise Exception("Unable to assume role")
                    
            # Discover active regions
            ec2_client = session.client("ec2", region_name=AWS_REGION)
            regions_resp = ec2_client.describe_regions()
            enabled_regions = [r["RegionName"] for r in regions_resp.get("Regions", [])]
            
            for region in enabled_regions:
                if ALLOWED_REGIONS and region not in ALLOWED_REGIONS:
                    continue
                if DENIED_REGIONS and region in DENIED_REGIONS:
                    continue
                    
                print(f"Scanning Region: {region}")
                
                # --- EC2 Scan ---
                instances = get_instances(session, region)
                for instance in instances:
                    instance_id = instance["instance_id"]
                    instance_type = instance["instance_type"]
                    instance_name = instance.get("instance_name", "Unknown")
                    tags = instance.get("tags", [])
                    
                    if is_tag_exempt(tags):
                        print(f"Exempt tag found. Skipping instance {instance_id}.")
                        log_action(instance_id, "skip", account_id, account_name, region, skip_reason="TAG_EXEMPTION")
                        continue
                        
                    cpu = get_average_cpu(instance_id, session, region)
                    cost = monthly_cost(instance_type)
                    
                    print(f"Instance Name: {instance_name}")
                    print(f"Instance ID: {instance_id}")
                    print(f"CPU: {cpu:.2f}%")
                    print(f"Cost: ${cost:.2f}")
                    print()
                    
                    if is_idle(cpu):
                        print("IDLE CHECK PASSED")
                        if is_snoozed(instance_id):
                            print("Alert suppressed (snoozed)")
                            continue
                            
                        state = get_alert_state(instance_id)
                        if state == "NEW":
                            print("State: NEW. Sending alert...")
                            owner = get_instance_owner(instance_id, session, region)
                            print(f"Owner: {owner}")
                            
                            send_alert(
                                instance_name,
                                instance_id,
                                owner,
                                cpu,
                                cost,
                                account_id=account_id,
                                account_name=account_name,
                                region=region
                            )
                            set_alert_state(instance_id, "ALERTED")
                            print("State changed: ALERTED")
                        elif state == "ALERTED":
                            print("State: ALERTED. Alert already active")
                        elif state == "ACKNOWLEDGED":
                            print("State: ACKNOWLEDGED. Alert acknowledged")
                        elif state == "REMEDIATED":
                            print("State: REMEDIATED. Alert remediated")
                    else:
                        print("ACTIVE")
                        clear_alert_state(instance_id)
                        print("Alert state cleared")
                        
                    print("-" * 50)
                    
                # --- EBS Scan ---
                from scanner.ebs_scanner import get_unattached_volumes, estimate_ebs_monthly_cost
                ebs_volumes = get_unattached_volumes(session, region)
                for vol in ebs_volumes:
                    vol_id = vol["volume_id"]
                    size = vol["size_gb"]
                    vol_type = vol["volume_type"]
                    tags = vol.get("tags", [])
                    
                    if is_tag_exempt(tags):
                        print(f"Exempt tag found. Skipping volume {vol_id}.")
                        log_action(vol_id, "skip", account_id, account_name, region, skip_reason="TAG_EXEMPTION")
                        continue
                        
                    savings = estimate_ebs_monthly_cost(vol)
                    
                    print("EBS Volume Found")
                    print(f"Volume ID: {vol_id}")
                    print(f"Size: {size} GB")
                    print(f"Type: {vol_type}")
                    print(f"Estimated Savings: ${savings:.2f}")
                    print()
                    
                    state = get_alert_state(vol_id)
                    if state == "NEW":
                        print("State: NEW. Sending alert...")
                        send_ebs_alert(
                            vol_id,
                            size,
                            savings,
                            account_id=account_id,
                            account_name=account_name,
                            region=region
                        )
                        set_alert_state(vol_id, "ALERTED")
                        print("State changed: ALERTED")
                    elif state == "ALERTED":
                        print("State: ALERTED. Alert already active")
                    elif state == "ACKNOWLEDGED":
                        print("State: ACKNOWLEDGED. Alert acknowledged")
                    elif state == "REMEDIATED":
                        print("State: REMEDIATED. Volume remediated")
                        
                    print("-" * 50)
                    
            scanned_count += 1
        except Exception as e:
            print(f"Scan failed for account {account_id}: {e}")
            failed_count += 1

    print("=" * 60)
    print(f"Accounts Scanned: {scanned_count}")
    print(f"Accounts Failed: {failed_count}")
    print("=" * 60)
    
    # Daily Savings Snapshot Automation
    print("Running Daily Savings Snapshot...")
    generate_savings_report()
