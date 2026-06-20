INSTANCE_PRICES = {
    "t2.micro": 0.0116,
    "t3.micro": 0.0104,
    "t2.small": 0.023,
    "t3.small": 0.0208
}

def monthly_cost(instance_type):

    hourly_cost = INSTANCE_PRICES.get(
        instance_type,
        0
    )

    return hourly_cost * 24 * 30