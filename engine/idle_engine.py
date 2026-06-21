from scanner.config import CPU_THRESHOLD

def is_idle(cpu_usage):
    return cpu_usage < CPU_THRESHOLD