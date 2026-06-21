from datetime import datetime, timezone
from decimal import Decimal
import boto3
from scanner.config import AWS_REGION, REMEDIATION_TABLE, SAVINGS_HISTORY_TABLE

def generate_savings_report():
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(REMEDIATION_TABLE)
        
        response = table.scan()
        items = response.get("Items", [])
        
        optimized_resources = set()
        verified_savings = 0.0
        estimated_savings = 0.0
        
        high_confidence = 0.0
        medium_confidence = 0.0
        low_confidence = 0.0
        
        accounts_data = {}
        
        for item in items:
            status = item.get("status")
            if status != "SUCCESS":
                continue
                
            resource_id = item.get("resource_id")
            if not resource_id:
                continue
                
            optimized_resources.add(resource_id)
            
            cost_source = item.get("cost_source", "ESTIMATED")
            actual_cost = item.get("actual_monthly_cost_at_remediation")
            estimated_val = item.get("estimated_monthly_savings", 0.0)
            
            if cost_source in ["COST_EXPLORER", "PRICING_API"] and actual_cost is not None and float(actual_cost) > 0.0:
                savings = float(actual_cost)
                verified_savings += savings
            else:
                savings = float(estimated_val)
                estimated_savings += savings
                
            confidence = item.get("savings_confidence")
            if not confidence:
                if cost_source == "COST_EXPLORER":
                    confidence = "HIGH"
                elif cost_source == "PRICING_API":
                    confidence = "MEDIUM"
                else:
                    confidence = "LOW"
                    
            if confidence == "HIGH":
                high_confidence += savings
            elif confidence == "MEDIUM":
                medium_confidence += savings
            else:
                low_confidence += savings
                
            # Aggregate per account
            account_name = item.get("account_name")
            account_id = item.get("account_id")
            display_name = account_name if account_name else (account_id if account_id else "Unknown")
            accounts_data[display_name] = accounts_data.get(display_name, 0.0) + savings
                
        total_monthly_savings = verified_savings + estimated_savings
        projected_annual_savings = total_monthly_savings * 12
        
        print("SentinelFinOps Savings Report")
        print()
        print(f"Resources Optimized: {len(optimized_resources)}")
        print()
        print("Verified Savings:")
        print(f"${verified_savings:.2f}/month")
        print()
        print("Estimated Savings:")
        print(f"${estimated_savings:.2f}/month")
        print()
        print("Total Savings:")
        print(f"${total_monthly_savings:.2f}/month")
        print()
        print("Projected Annual Savings:")
        print(f"${projected_annual_savings:.2f}/year")
        print()
        print("Savings Confidence Summary:")
        print(f"HIGH (Cost Explorer): ${high_confidence:.2f}/month")
        print(f"MEDIUM (Pricing API): ${medium_confidence:.2f}/month")
        print(f"LOW (Estimated): ${low_confidence:.2f}/month")
        
        print("Savings report generated")
        
        # Format account savings list
        account_savings_list = []
        for name, val in accounts_data.items():
            account_savings_list.append({
                "account_name": name,
                "savings": Decimal(str(round(val, 2)))
            })
        
        # Persist report
        history_table = dynamodb.Table(SAVINGS_HISTORY_TABLE)
        now = datetime.now(timezone.utc)
        report_date = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")
        
        history_table.put_item(
            Item={
                "report_date": report_date,
                "timestamp": timestamp,
                "resources_optimized": Decimal(str(len(optimized_resources))),
                "verified_savings": Decimal(str(round(verified_savings, 2))),
                "estimated_savings": Decimal(str(round(estimated_savings, 2))),
                "total_savings": Decimal(str(round(total_monthly_savings, 2))),
                "annual_projection": Decimal(str(round(projected_annual_savings, 2))),
                "high_confidence_savings": Decimal(str(round(high_confidence, 2))),
                "medium_confidence_savings": Decimal(str(round(medium_confidence, 2))),
                "low_confidence_savings": Decimal(str(round(low_confidence, 2))),
                "account_savings": account_savings_list
            }
        )
        print("Savings report saved")
        
    except Exception as e:
        print(f"Error generating savings report: {e}")

def generate_trend_report():
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(SAVINGS_HISTORY_TABLE)
        
        response = table.scan()
        items = response.get("Items", [])
        
        sorted_items = sorted(items, key=lambda x: (x.get("report_date", ""), x.get("timestamp", "")))
        
        print("SentinelFinOps Savings Trend")
        print()
        for item in sorted_items:
            date = item.get("report_date")
            account_savings = item.get("account_savings", [])
            
            if account_savings:
                for acc in account_savings:
                    name = acc.get("account_name", "Unknown")
                    savings = float(acc.get("savings", 0.0))
                    print(date)
                    print(name)
                    print(f"${savings:.2f}")
                    print()
            else:
                # Fallback for legacy v3.0 items
                total = float(item.get("total_savings", 0.0))
                print(date)
                print("LocalPrimaryAccount")
                print(f"${total:.2f}")
                print()
            
    except Exception as e:
        print(f"Error generating trend report: {e}")

def generate_monthly_report():
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(REMEDIATION_TABLE)
        
        response = table.scan()
        items = response.get("Items", [])
        
        now = datetime.now(timezone.utc)
        current_month_prefix = now.strftime("%Y-%m")
        month_name_year = now.strftime("%B %Y")
        
        optimized_resources = set()
        ec2_count = 0
        ebs_count = 0
        compute_savings = 0.0
        storage_savings = 0.0
        
        high_confidence = 0.0
        medium_confidence = 0.0
        low_confidence = 0.0
        
        for item in items:
            status = item.get("status")
            if status != "SUCCESS":
                continue
                
            timestamp = item.get("timestamp", "")
            if not timestamp.startswith(current_month_prefix):
                continue
                
            resource_id = item.get("resource_id")
            if not resource_id:
                continue
                
            optimized_resources.add(resource_id)
            
            res_type = item.get("resource_type", "EC2")
            if res_type == "EC2":
                ec2_count += 1
            elif res_type == "EBS":
                ebs_count += 1
                
            cost_source = item.get("cost_source", "ESTIMATED")
            actual_cost = item.get("actual_monthly_cost_at_remediation")
            estimated_val = item.get("estimated_monthly_savings", 0.0)
            
            if cost_source in ["COST_EXPLORER", "PRICING_API"] and actual_cost is not None and float(actual_cost) > 0.0:
                savings = float(actual_cost)
            else:
                savings = float(estimated_val)
                
            category = item.get("remediation_category")
            if not category:
                if res_type == "EC2":
                    category = "COMPUTE"
                elif res_type == "EBS":
                    category = "STORAGE"
                    
            if category == "COMPUTE":
                compute_savings += savings
            elif category == "STORAGE":
                storage_savings += savings
                
            confidence = item.get("savings_confidence")
            if not confidence:
                if cost_source == "COST_EXPLORER":
                    confidence = "HIGH"
                elif cost_source == "PRICING_API":
                    confidence = "MEDIUM"
                else:
                    confidence = "LOW"
                    
            if confidence == "HIGH":
                high_confidence += savings
            elif confidence == "MEDIUM":
                medium_confidence += savings
            else:
                low_confidence += savings
                
        total_savings = compute_savings + storage_savings
        projected_annual_savings = total_savings * 12
        
        print(f"{month_name_year} Summary")
        print()
        print(f"Resources Optimized: {len(optimized_resources)}")
        print()
        print(f"EC2 Remediations: {ec2_count}")
        print()
        print(f"EBS Remediations: {ebs_count}")
        print()
        print("Compute Savings:")
        print(f"${compute_savings:.2f}")
        print()
        print("Storage Savings:")
        print(f"${storage_savings:.2f}")
        print()
        print("Total Savings:")
        print(f"${total_savings:.2f}")
        print()
        print("Projected Annual Savings:")
        print(f"${projected_annual_savings:.2f}")
        print()
        print("Savings Confidence Summary:")
        print(f"HIGH (Cost Explorer): ${high_confidence:.2f}")
        print(f"MEDIUM (Pricing API): ${medium_confidence:.2f}")
        print(f"LOW (Estimated): ${low_confidence:.2f}")
        
    except Exception as e:
        print(f"Error generating monthly report: {e}")

def generate_account_report():
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(REMEDIATION_TABLE)
        
        response = table.scan()
        items = response.get("Items", [])
        
        accounts_data = {}
        
        for item in items:
            status = item.get("status")
            if status != "SUCCESS":
                continue
                
            account_name = item.get("account_name")
            account_id = item.get("account_id")
            display_name = account_name if account_name else (account_id if account_id else "Unknown")
            
            if display_name not in accounts_data:
                accounts_data[display_name] = {
                    "verified": 0.0,
                    "pricing_api": 0.0,
                    "estimated": 0.0,
                    "total": 0.0
                }
                
            cost_source = item.get("cost_source", "ESTIMATED")
            actual_cost = item.get("actual_monthly_cost_at_remediation")
            estimated_val = item.get("estimated_monthly_savings", 0.0)
            
            if cost_source == "COST_EXPLORER" and actual_cost is not None:
                savings = float(actual_cost)
                accounts_data[display_name]["verified"] += savings
            elif cost_source == "PRICING_API" and actual_cost is not None:
                savings = float(actual_cost)
                accounts_data[display_name]["pricing_api"] += savings
            else:
                savings = float(estimated_val)
                accounts_data[display_name]["estimated"] += savings
                
            accounts_data[display_name]["total"] += savings
            
        print("SentinelFinOps Account Report")
        print()
        
        global_verified = 0.0
        global_pricing = 0.0
        global_estimated = 0.0
        global_total = 0.0
        
        for name, data in accounts_data.items():
            print(name)
            print(f"Verified Savings: ${data['verified']:.2f}")
            print(f"Pricing API Savings: ${data['pricing_api']:.2f}")
            print(f"Estimated Savings: ${data['estimated']:.2f}")
            print(f"Savings: ${data['total']:.2f}")
            print()
            
            global_verified += data['verified']
            global_pricing += data['pricing_api']
            global_estimated += data['estimated']
            global_total += data['total']
            
        print("Total Savings")
        print(f"${global_total:.2f}")
        print()
        print("Global Totals Summary:")
        print(f"Verified Savings: ${global_verified:.2f}")
        print(f"Pricing API Savings: ${global_pricing:.2f}")
        print(f"Estimated Savings: ${global_estimated:.2f}")
        
    except Exception as e:
        print(f"Error generating account report: {e}")
