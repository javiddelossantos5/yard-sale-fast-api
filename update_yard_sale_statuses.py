#!/usr/bin/env python3
"""
Script to update existing yard sales with different statuses for testing
"""

import requests
import json
import time as time_module

# API base URL
BASE_URL = "http://localhost:8000"

def get_auth_token(username, password):
    """Get authentication token for a user"""
    login_data = {
        "username": username,
        "password": password
    }
    
    response = requests.post(f"{BASE_URL}/login", json=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed for {username}: {response.text}")
        return None

def update_yard_sale_status(token, yard_sale_id, status):
    """Update yard sale status"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    update_data = {"status": status}
    response = requests.put(f"{BASE_URL}/yard-sales/{yard_sale_id}", json=update_data, headers=headers)
    if response.status_code == 200:
        print(f"✅ Updated yard sale {yard_sale_id} to status: {status}")
        return True
    else:
        print(f"❌ Failed to update yard sale {yard_sale_id}: {response.text}")
        return False

def get_yard_sales():
    """Get all yard sales"""
    response = requests.get(f"{BASE_URL}/yard-sales")
    if response.status_code == 200:
        return response.json()
    return []

def main():
    print("🔄 Updating yard sale statuses for testing...")
    
    # Get authentication token
    token = get_auth_token("javiddelossantos", "Password")
    if not token:
        print("❌ Could not authenticate")
        return
    
    print("✅ Authenticated successfully")
    
    # Get all yard sales
    yard_sales = get_yard_sales()
    if not yard_sales:
        print("❌ No yard sales found")
        return
    
    print(f"✅ Found {len(yard_sales)} yard sales")
    
    # Update some yard sales with different statuses
    status_updates = [
        # Set some yard sales to "on_break"
        {"yard_sale_id": 2, "status": "on_break", "reason": "Taking a lunch break"},
        {"yard_sale_id": 5, "status": "on_break", "reason": "Restocking items"},
        {"yard_sale_id": 8, "status": "on_break", "reason": "Weather break"},
        
        # Set some yard sales to "closed"
        {"yard_sale_id": 3, "status": "closed", "reason": "Sale ended early"},
        {"yard_sale_id": 7, "status": "closed", "reason": "All items sold"},
        {"yard_sale_id": 12, "status": "closed", "reason": "Moving completed"},
        
        # Keep some as "active"
        {"yard_sale_id": 1, "status": "active", "reason": "Currently running"},
        {"yard_sale_id": 4, "status": "active", "reason": "Still selling"},
        {"yard_sale_id": 6, "status": "active", "reason": "Open for business"},
    ]
    
    print("\n🔄 Updating yard sale statuses...")
    updated_count = 0
    
    for update in status_updates:
        yard_sale_id = update["yard_sale_id"]
        status = update["status"]
        reason = update["reason"]
        
        # Check if yard sale exists
        yard_sale = next((ys for ys in yard_sales if ys["id"] == yard_sale_id), None)
        if yard_sale:
            if update_yard_sale_status(token, yard_sale_id, status):
                print(f"   📝 Reason: {reason}")
                updated_count += 1
            time_module.sleep(0.3)  # Small delay between updates
        else:
            print(f"⚠️  Yard sale {yard_sale_id} not found")
    
    print(f"\n🎉 Status update complete!")
    print(f"📊 Updated {updated_count} yard sales with different statuses")
    
    # Show summary by status
    print(f"\n📋 Status Summary:")
    status_counts = {"active": 0, "on_break": 0, "closed": 0}
    
    for yard_sale in yard_sales:
        if yard_sale["id"] in [u["yard_sale_id"] for u in status_updates]:
            status = next((u["status"] for u in status_updates if u["yard_sale_id"] == yard_sale["id"]), "active")
        else:
            status = "active"  # Default status
        
        if status in status_counts:
            status_counts[status] += 1
    
    for status, count in status_counts.items():
        print(f"  {status}: {count} yard sales")

if __name__ == "__main__":
    main()
