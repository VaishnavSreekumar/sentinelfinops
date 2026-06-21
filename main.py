import sys
from scanner.run_scan import run_scan
from reporting.savings_report import generate_savings_report, generate_trend_report, generate_monthly_report

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "report":
            generate_savings_report()
        elif arg == "trends":
            generate_trend_report()
        elif arg == "monthly":
            generate_monthly_report()
        else:
            run_scan()
    else:
        run_scan()
