from scanner.ec2_scanner import get_instances
from scanner.cloudwatch_scanner import get_average_cpu

from engine.idle_engine import is_idle
from engine.cost_engine import monthly_cost

from notifications.notifier import send_alert

print("\n=== SentinelFinOps ===\n")

instances = get_instances()

for instance in instances:

    instance_id = instance["instance_id"]
    instance_type = instance["instance_type"]

    cpu = get_average_cpu(instance_id)

    cost = monthly_cost(instance_type)

    print(f"Instance: {instance_id}")
    print(f"CPU: {cpu:.2f}%")
    print(f"Cost: ${cost:.2f}")

    if is_idle(cpu):

        print("⚠️ IDLE")

        send_alert(
            instance_id,
            cpu,
            cost
        )

    else:

        print("✅ ACTIVE")

    print("-" * 50)