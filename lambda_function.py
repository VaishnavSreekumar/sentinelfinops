from scanner.run_scan import run_scan

def lambda_handler(event, context):
    run_scan()
    return {
        "statusCode": 200,
        "body": "Scan completed"
    }
