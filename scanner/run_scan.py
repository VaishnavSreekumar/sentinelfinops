import uuid
import boto3
from scanner.ec2_scanner import get_instances
from scanner.cloudwatch_scanner import get_average_cpu
from engine.idle_engine import is_idle
from engine.cost_engine import monthly_cost
from notifications.notifier import send_alert
from scanner.owner_detector import get_instance_owner
from storage.snooze_manager import is_snoozed
from scanner.config import AWS_REGION

# Import AI pipeline composition root and contracts
from ai.runtime import create_ai_runtime
from ai.contracts.scan_context import ScanContext
from ai.contracts.enums import ResourceType
from ai.contracts.metrics_summary import MetricsSummary
from ai.contracts.cost_summary import CostSummary
from ai.contracts.owner_info import OwnerInfo
from ai.contracts.history_summary import HistorySummary

def run_scan():
    print("\n=== SentinelFinOps ===\n")

    # 1. Resolve local AWS account credentials dynamically
    try:
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]
    except Exception:
        account_id = "123456789012"
    account_name = "Local Account"
    region = AWS_REGION

    # 2. Instantiate composition root for AI Runtime
    try:
        ai_runtime = create_ai_runtime()
    except Exception as e:
        print(f"Failed to initialize AI Runtime: {e}")
        ai_runtime = None

    instances = get_instances()

    print(f"AWS Region: {AWS_REGION}")
    print(f"Instances Found: {len(instances)}")

    for instance in instances:

        instance_id = instance["instance_id"]
        instance_type = instance["instance_type"]
        instance_name = instance.get("instance_name", "Unknown")

        cpu = get_average_cpu(instance_id)

        cost = monthly_cost(instance_type)

        print(f"Instance Name: {instance_name}")
        print(f"Instance ID: {instance_id}")
        print()
        print(f"CPU: {cpu:.2f}%")
        print(f"Cost: ${cost:.2f}")
        print()

        if is_idle(cpu):

            print("IDLE CHECK PASSED")
            print()

            if is_snoozed(instance_id):
                print("Alert suppressed (snoozed)")
                continue

            from storage.alert_state_manager import get_alert_state, set_alert_state

            state = get_alert_state(instance_id)

            if state == "NEW":
                print("State: NEW")
                print("Sending alert")

                owner = get_instance_owner(instance_id)
                print(f"Owner: {owner}")
                print()

                # Execute the AI validation/enrichment pipeline if active
                recommendation = None
                policy_result = None

                if ai_runtime is not None:
                    execution_id = uuid.uuid4()
                    scan_ctx = ScanContext(
                        execution_id=execution_id,
                        resource_id=instance_id,
                        resource_type=ResourceType.EC2,
                        raw_resource=instance,
                        metrics=MetricsSummary(
                            cpu_mean_7_days=cpu,
                            cpu_max_7_days=cpu
                        ),
                        cost_summary=CostSummary(
                            current_cost=cost,
                            estimated_monthly_cost=cost,
                            projected_savings=cost,
                            pricing_source="PricingAPI"
                        ),
                        owner_info=OwnerInfo(owner_arn=owner),
                        history_summary=HistorySummary(alert_state=state),
                        account_id=account_id,
                        account_name=account_name,
                        region=region
                    )
                    recommendation, policy_result = ai_runtime.process(scan_ctx)

                print("Sending Slack alert...")
                send_alert(
                    instance_name,
                    instance_id,
                    owner,
                    cpu,
                    cost,
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    recommendation=recommendation,
                    policy_result=policy_result
                )
                print("Slack alert completed")

                set_alert_state(instance_id, "ALERTED")
                print("State changed: ALERTED")

            elif state == "ALERTED":
                print("State: ALERTED")
                print("Alert already active")

            elif state == "ACKNOWLEDGED":
                print("State: ACKNOWLEDGED")
                print("Alert acknowledged")

            elif state == "REMEDIATED":
                print("State: REMEDIATED")
                print("Alert remediated")


        else:

            from storage.alert_state_manager import clear_alert_state
            print("ACTIVE")
            clear_alert_state(instance_id)
            print("Alert state cleared")

        print("-" * 50)

    from scanner.ebs_scanner import get_unattached_volumes, estimate_ebs_monthly_cost
    ebs_volumes = get_unattached_volumes()
    for vol in ebs_volumes:
        vol_id = vol["volume_id"]
        size = vol["size_gb"]
        vol_type = vol["volume_type"]
        savings = estimate_ebs_monthly_cost(vol)
        
        print("EBS Volume Found")
        print(f"Volume ID: {vol_id}")
        print(f"Size: {size} GB")
        print(f"Type: {vol_type}")
        print(f"Estimated Savings: ${savings:.2f}")
        print()
        
        from storage.alert_state_manager import get_alert_state, set_alert_state
        state = get_alert_state(vol_id)
        
        if state == "NEW":
            print("State: NEW")
            print("Sending alert")

            # Execute the AI validation/enrichment pipeline if active
            recommendation = None
            policy_result = None

            if ai_runtime is not None:
                execution_id = uuid.uuid4()
                scan_ctx = ScanContext(
                    execution_id=execution_id,
                    resource_id=vol_id,
                    resource_type=ResourceType.EBS,
                    raw_resource=vol,
                    metrics=MetricsSummary(),
                    cost_summary=CostSummary(
                        current_cost=savings,
                        estimated_monthly_cost=savings,
                        projected_savings=savings,
                        pricing_source="PricingAPI"
                    ),
                    owner_info=OwnerInfo(),
                    history_summary=HistorySummary(alert_state=state),
                    account_id=account_id,
                    account_name=account_name,
                    region=region
                )
                recommendation, policy_result = ai_runtime.process(scan_ctx)

            from notifications.notifier import send_ebs_alert
            send_ebs_alert(
                vol_id,
                size,
                savings,
                account_id=account_id,
                account_name=account_name,
                region=region,
                recommendation=recommendation,
                policy_result=policy_result
            )
            set_alert_state(vol_id, "ALERTED")
            print("State changed: ALERTED")
        elif state == "ALERTED":
            print("State: ALERTED")
            print("Alert already active")
        elif state == "ACKNOWLEDGED":
            print("State: ACKNOWLEDGED")
            print("Alert acknowledged")
        elif state == "REMEDIATED":
            print("State: REMEDIATED")
            print("Volume remediated")
            
        print("-" * 50)
