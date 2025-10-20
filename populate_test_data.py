#!/usr/bin/env python3
"""
Script to populate the database with test data for yard sales
"""

import requests
import json
from datetime import date, time, timedelta
import random

# API base URL
BASE_URL = "http://localhost:8000"

def get_auth_token():
    """Get authentication token"""
    login_data = {
        "username": "javiddelossantos",
        "password": "Password"
    }
    
    response = requests.post(f"{BASE_URL}/login", json=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.text}")
        return None

def create_yard_sale(token, yard_sale_data):
    """Create a yard sale"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.post(f"{BASE_URL}/yard-sales", json=yard_sale_data, headers=headers)
    if response.status_code == 201:
        print(f"✅ Created yard sale: {yard_sale_data['title']}")
        return response.json()
    else:
        print(f"❌ Failed to create yard sale: {response.text}")
        return None

def add_comment(token, yard_sale_id, comment_content):
    """Add a comment to a yard sale"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    comment_data = {"content": comment_content}
    response = requests.post(f"{BASE_URL}/yard-sales/{yard_sale_id}/comments", json=comment_data, headers=headers)
    if response.status_code == 201:
        print(f"✅ Added comment to yard sale {yard_sale_id}")
    else:
        print(f"❌ Failed to add comment: {response.text}")

def main():
    print("🚀 Populating database with test yard sale data...")
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("❌ Could not authenticate. Make sure the server is running and you're logged in.")
        return
    
    print("✅ Authentication successful")
    
    # Test data for yard sales
    yard_sales_data = [
        {
            "title": "Vernal Family Moving Sale",
            "description": "Moving out of state! Everything must go! Furniture, appliances, tools, and household items. Great deals on quality items.",
            "start_date": "2025-10-26",
            "end_date": "2025-10-27",
            "start_time": "07:00:00",
            "end_time": "17:00:00",
            "address": "456 Oak Street",
            "city": "Vernal",
            "state": "UT",
            "zip_code": "84078",
            "contact_name": "Sarah Johnson",
            "contact_phone": "(435) 789-1234",
            "contact_email": "sarah.johnson@email.com",
            "allow_messages": True,
            "categories": ["Furniture", "Appliances", "Tools", "Household"],
            "price_range": "$10-$200",
            "payment_methods": ["Cash", "Venmo", "PayPal"]
        },
        {
            "title": "Kids' Clothes & Toys Yard Sale",
            "description": "Kids have outgrown everything! Tons of clothes sizes 2T-12, toys, books, and baby gear. All items in excellent condition.",
            "start_date": "2025-10-28",
            "end_date": None,
            "start_time": "09:00:00",
            "end_time": "15:00:00",
            "address": "789 Pine Avenue",
            "city": "Vernal",
            "state": "UT",
            "zip_code": "84078",
            "contact_name": "Mike and Lisa Chen",
            "contact_phone": "(435) 555-9876",
            "contact_email": "chenfamily@email.com",
            "allow_messages": True,
            "categories": ["Clothing", "Toys", "Books", "Baby Gear"],
            "price_range": "Under $25",
            "payment_methods": ["Cash", "Venmo"]
        },
        {
            "title": "Electronics & Gaming Sale",
            "description": "Upgrading my setup! Selling gaming consoles, computers, monitors, and electronics. Some items still under warranty.",
            "start_date": "2025-10-29",
            "end_date": "2025-10-30",
            "start_time": "10:00:00",
            "end_time": "18:00:00",
            "address": "321 Elm Drive",
            "city": "Vernal",
            "state": "UT",
            "zip_code": "84078",
            "contact_name": "Alex Rodriguez",
            "contact_phone": "(435) 456-7890",
            "contact_email": "alex.rodriguez@email.com",
            "allow_messages": True,
            "categories": ["Electronics", "Gaming", "Computers"],
            "price_range": "$50-$500",
            "payment_methods": ["Cash", "Venmo", "Zelle", "PayPal"]
        },
        {
            "title": "Antique & Vintage Collection",
            "description": "Estate sale featuring antique furniture, vintage collectibles, and unique finds. Perfect for collectors and decorators.",
            "start_date": "2025-11-01",
            "end_date": "2025-11-02",
            "start_time": "08:00:00",
            "end_time": "16:00:00",
            "address": "654 Maple Lane",
            "city": "Vernal",
            "state": "UT",
            "zip_code": "84078",
            "contact_name": "Margaret Thompson",
            "contact_phone": "(435) 321-6543",
            "contact_email": "margaret.t@email.com",
            "allow_messages": False,
            "categories": ["Antiques", "Vintage", "Collectibles", "Furniture"],
            "price_range": "$25-$300",
            "payment_methods": ["Cash", "Check"]
        },
        {
            "title": "Outdoor & Sports Equipment",
            "description": "Camping gear, fishing equipment, bikes, and outdoor sports items. Perfect for outdoor enthusiasts!",
            "start_date": "2025-11-03",
            "end_date": None,
            "start_time": "07:30:00",
            "end_time": "14:00:00",
            "address": "987 Cedar Street",
            "city": "Vernal",
            "state": "UT",
            "zip_code": "84078",
            "contact_name": "Tom Wilson",
            "contact_phone": "(435) 654-3210",
            "contact_email": "tom.wilson@email.com",
            "allow_messages": True,
            "categories": ["Outdoor", "Sports", "Camping", "Fishing"],
            "price_range": "$15-$150",
            "payment_methods": ["Cash", "Venmo"]
        },
        {
            "title": "Multi-Family Neighborhood Sale",
            "description": "Three families selling together! Furniture, clothes, kitchen items, and more. Something for everyone!",
            "start_date": "2025-11-04",
            "end_date": "2025-11-05",
            "start_time": "08:00:00",
            "end_time": "17:00:00",
            "address": "147 Birch Road",
            "city": "Vernal",
            "state": "UT",
            "zip_code": "84078",
            "contact_name": "Jennifer Davis",
            "contact_phone": "(435) 987-6543",
            "contact_email": "jennifer.davis@email.com",
            "allow_messages": True,
            "categories": ["Furniture", "Clothing", "Kitchen", "Miscellaneous"],
            "price_range": "$5-$100",
            "payment_methods": ["Cash", "Venmo", "Zelle"]
        }
    ]
    
    # Create yard sales
    created_yard_sales = []
    for yard_sale_data in yard_sales_data:
        result = create_yard_sale(token, yard_sale_data)
        if result:
            created_yard_sales.append(result)
    
    print(f"\n✅ Created {len(created_yard_sales)} yard sales")
    
    # Add some comments to make it more realistic
    comments = [
        "Great! What time do you start on Saturday?",
        "Do you have any dining room tables?",
        "Are the electronics still working?",
        "Can I get a preview of the furniture?",
        "What sizes are the kids' clothes?",
        "Do you have any camping tents?",
        "Are the bikes in good condition?",
        "What vintage items do you have?",
        "Can you hold the gaming console until Sunday?",
        "Do you accept trades?",
        "What's the best time to come by?",
        "Are there any early bird specials?"
    ]
    
    print("\n💬 Adding comments to yard sales...")
    for i, yard_sale in enumerate(created_yard_sales):
        # Add 1-3 random comments to each yard sale
        num_comments = random.randint(1, 3)
        for j in range(num_comments):
            comment = random.choice(comments)
            add_comment(token, yard_sale["id"], comment)
    
    print(f"\n🎉 Test data population complete!")
    print(f"📊 Created {len(created_yard_sales)} yard sales in Vernal, UT (84078)")
    print(f"💬 Added comments to make the data more realistic")
    
    # Show summary
    print(f"\n📋 Summary of created yard sales:")
    for yard_sale in created_yard_sales:
        print(f"  • {yard_sale['title']} - {yard_sale['start_date']} at {yard_sale['address']}")

if __name__ == "__main__":
    main()
