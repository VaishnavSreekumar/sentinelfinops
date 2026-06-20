IDLE_THRESHOLD = 5.0

def is_idle(cpu_usage):

    return cpu_usage < IDLE_THRESHOLD