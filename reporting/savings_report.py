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
                "low_confidence_savings": Decimal(str(round(low_confidence, 2)))
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
        
        # Sort by report_date, then timestamp
        sorted_items = sorted(items, key=lambda x: (x.get("report_date", ""), x.get("timestamp", "")))
        
        print("SentinelFinOps Savings Trend")
        print()
        for item in sorted_items:
            date = item.get("report_date")
            total = float(item.get("total_savings", 0.0))
            print(f"{date} : ${total:.2f}")
            
    except Exception as e:
        print(f"Error generating trend report: {e}")

def generate_monthly_report():
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(REMEDIATION_TABLE)
        
        response = table.scan()
        items = response.get("Items", [])
        
        now = datetime.now(timezone.utc)
        current_month_prefix = now.strftime("%Y-%m")  # e.g., "2026-06"
        month_name_year = now.strftime("%B %Y")       # e.g., "June 2026"
        
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
                # fallback heuristics
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
