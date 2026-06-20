from scanner.ec2_scanner import get_instances
from scanner.cloudwatch_scanner import get_average_cpu

from engine.idle_engine import is_idle
from engine.cost_engine import monthly_cost

from notifications.notifier import send_alert
from scanner.owner_detector import get_instance_owner
from storage.snooze_manager import is_snoozed

print("\n=== SentinelFinOps ===\n")

instances = get_instances()

for instance in instances:

    instance_id = instance["instance_id"]
    instance_type = instance["instance_type"]
    instance_name = instance.get("instance_name", "Unknown")

    cpu = get_average_cpu(instance_id)

    cost = monthly_cost(instance_type)

    print(f"Instance Name: {instance_name}")
    print(f"Instance ID: {instance_id}")
    print(f"CPU: {cpu:.2f}%")
    print(f"Cost: ${cost:.2f}")

    if is_idle(cpu):

        print("⚠️ IDLE")

        if is_snoozed(instance_id):
            print("⏰ Alert suppressed (snoozed)")
            continue

        owner = get_instance_owner(instance_id)
        send_alert(
            instance_name,
            instance_id,
            owner,
            cpu,
            cost
        )

    else:

        print("✅ ACTIVE")

    print("-" * 50)