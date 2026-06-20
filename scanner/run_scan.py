from scanner.ec2_scanner import get_instances
from scanner.cloudwatch_scanner import get_average_cpu
from engine.idle_engine import is_idle
from engine.cost_engine import monthly_cost
from notifications.notifier import send_alert
from scanner.owner_detector import get_instance_owner
from storage.snooze_manager import is_snoozed
from scanner.config import AWS_REGION

def run_scan():
    print("\n=== SentinelFinOps ===\n")

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

                print("Sending Slack alert...")
                send_alert(
                    instance_name,
                    instance_id,
                    owner,
                    cpu,
                    cost
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

        else:

            from storage.alert_state_manager import clear_alert_state
            print("ACTIVE")
            clear_alert_state(instance_id)
            print("Alert state cleared")

        print("-" * 50)
