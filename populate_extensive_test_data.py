#!/usr/bin/env python3
"""
Script to populate the database with extensive test data including multiple users,
yard sales, and realistic comments between users
"""

import requests
import json
from datetime import date, time, timedelta
import random
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

def register_user(user_data):
    """Register a new user"""
    response = requests.post(f"{BASE_URL}/register", json=user_data)
    if response.status_code == 201:
        print(f"✅ Registered user: {user_data['username']}")
        return True
    else:
        print(f"❌ Failed to register {user_data['username']}: {response.text}")
        return False

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
        return True
    else:
        print(f"❌ Failed to add comment: {response.text}")
        return False

def main():
    print("🚀 Populating database with extensive test data...")
    
    # First, get token for existing user
    existing_token = get_auth_token("javiddelossantos", "Password")
    if not existing_token:
        print("❌ Could not authenticate with existing user")
        return
    
    print("✅ Authenticated with existing user")
    
    # Register new users
    new_users = [
        {
            "username": "sierradelossantos",
            "email": "sierradelossantos@gmail.com",
            "password": "Password"
        },
        {
            "username": "mikechen",
            "email": "mike.chen@email.com",
            "password": "Password"
        },
        {
            "username": "sarahjohnson",
            "email": "sarah.johnson@email.com",
            "password": "Password"
        },
        {
            "username": "alexrodriguez",
            "email": "alex.rodriguez@email.com",
            "password": "Password"
        },
        {
            "username": "margarethompson",
            "email": "margaret.thompson@email.com",
            "password": "Password"
        },
        {
            "username": "tomwilson",
            "email": "tom.wilson@email.com",
            "password": "Password"
        },
        {
            "username": "jenniferdavis",
            "email": "jennifer.davis@email.com",
            "password": "Password"
        },
        {
            "username": "davidlee",
            "email": "david.lee@email.com",
            "password": "Password"
        },
        {
            "username": "lisagarcia",
            "email": "lisa.garcia@email.com",
            "password": "Password"
        },
        {
            "username": "robertmartinez",
            "email": "robert.martinez@email.com",
            "password": "Password"
        }
    ]
    
    print("\n👥 Registering new users...")
    registered_users = ["javiddelossantos"]  # Existing user
    
    for user_data in new_users:
        if register_user(user_data):
            registered_users.append(user_data["username"])
        time_module.sleep(0.5)  # Small delay between registrations
    
    print(f"✅ Registered {len(registered_users)} users total")
    
    # Get tokens for all users
    user_tokens = {}
    for username in registered_users:
        token = get_auth_token(username, "Password")
        if token:
            user_tokens[username] = token
        time_module.sleep(0.2)
    
    print(f"✅ Got tokens for {len(user_tokens)} users")
    
    # Extensive yard sales data
    yard_sales_data = [
        # Vernal, UT sales (continuing the theme)
        {
            "title": "Vernal Family Moving Sale",
            "description": "Moving out of state! Everything must go! Furniture, appliances, tools, and household items. Great deals on quality items.",
            "start_date": "2024-10-26",
            "end_date": "2024-10-27",
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
            "payment_methods": ["Cash", "Venmo", "PayPal", "Apple Pay", "Google Pay"],
            "owner": "sarahjohnson"
        },
        {
            "title": "Kids' Clothes & Toys Yard Sale",
            "description": "Kids have outgrown everything! Tons of clothes sizes 2T-12, toys, books, and baby gear. All items in excellent condition.",
            "start_date": "2024-10-28",
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
            "payment_methods": ["Cash", "Venmo", "Apple Pay", "Samsung Pay"],
            "owner": "mikechen"
        },
        {
            "title": "Electronics & Gaming Sale",
            "description": "Upgrading my setup! Selling gaming consoles, computers, monitors, and electronics. Some items still under warranty.",
            "start_date": "2024-10-29",
            "end_date": "2024-10-30",
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
            "payment_methods": ["Cash", "Venmo", "Zelle", "PayPal", "Apple Pay", "Google Pay", "Credit Card"],
            "owner": "alexrodriguez"
        },
        {
            "title": "Antique & Vintage Collection",
            "description": "Estate sale featuring antique furniture, vintage collectibles, and unique finds. Perfect for collectors and decorators.",
            "start_date": "2024-11-01",
            "end_date": "2024-11-02",
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
            "payment_methods": ["Cash", "Check", "Credit Card", "Money Order"],
            "owner": "margarethompson"
        },
        {
            "title": "Outdoor & Sports Equipment",
            "description": "Camping gear, fishing equipment, bikes, and outdoor sports items. Perfect for outdoor enthusiasts!",
            "start_date": "2024-11-03",
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
            "payment_methods": ["Cash", "Venmo", "Apple Pay", "Cash App"],
            "owner": "tomwilson"
        },
        {
            "title": "Multi-Family Neighborhood Sale",
            "description": "Three families selling together! Furniture, clothes, kitchen items, and more. Something for everyone!",
            "start_date": "2024-11-04",
            "end_date": "2024-11-05",
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
            "payment_methods": ["Cash", "Venmo", "Zelle", "Google Pay", "Samsung Pay"],
            "owner": "jenniferdavis"
        },
        
        # Salt Lake City, UT sales
        {
            "title": "Downtown SLC Apartment Sale",
            "description": "Moving to a smaller place! Selling furniture, electronics, and home decor. Everything in great condition.",
            "start_date": "2024-11-06",
            "end_date": None,
            "start_time": "09:00:00",
            "end_time": "16:00:00",
            "address": "123 Main Street",
            "city": "Salt Lake City",
            "state": "UT",
            "zip_code": "84101",
            "contact_name": "David Lee",
            "contact_phone": "(801) 555-1234",
            "contact_email": "david.lee@email.com",
            "allow_messages": True,
            "categories": ["Furniture", "Electronics", "Home Decor"],
            "price_range": "$20-$300",
            "payment_methods": ["Cash", "Venmo", "Zelle", "Apple Pay", "Credit Card"],
            "owner": "davidlee"
        },
        {
            "title": "University Student Moving Sale",
            "description": "Graduating and moving! Selling dorm furniture, textbooks, and college essentials. Great prices for students!",
            "start_date": "2024-11-07",
            "end_date": "2024-11-08",
            "start_time": "10:00:00",
            "end_time": "18:00:00",
            "address": "456 University Ave",
            "city": "Salt Lake City",
            "state": "UT",
            "zip_code": "84112",
            "contact_name": "Lisa Garcia",
            "contact_phone": "(801) 555-5678",
            "contact_email": "lisa.garcia@email.com",
            "allow_messages": True,
            "categories": ["Furniture", "Books", "Electronics", "Miscellaneous"],
            "price_range": "Under $50",
            "payment_methods": ["Cash", "Venmo"],
            "owner": "lisagarcia"
        },
        
        # Provo, UT sales
        {
            "title": "BYU Student Housing Sale",
            "description": "End of semester sale! Furniture, kitchen items, and study materials. Perfect for incoming students.",
            "start_date": "2024-11-09",
            "end_date": None,
            "start_time": "08:00:00",
            "end_time": "15:00:00",
            "address": "789 College Street",
            "city": "Provo",
            "state": "UT",
            "zip_code": "84601",
            "contact_name": "Robert Martinez",
            "contact_phone": "(801) 555-9012",
            "contact_email": "robert.martinez@email.com",
            "allow_messages": True,
            "categories": ["Furniture", "Kitchen", "Books", "Electronics"],
            "price_range": "$10-$150",
            "payment_methods": ["Cash", "Venmo", "PayPal"],
            "owner": "robertmartinez"
        },
        
        # Denver, CO sales
        {
            "title": "Denver Suburb Family Sale",
            "description": "Family downsizing! Selling furniture, toys, and household items. Everything must go!",
            "start_date": "2024-11-10",
            "end_date": "2024-11-11",
            "start_time": "07:00:00",
            "end_time": "17:00:00",
            "address": "321 Mountain View Drive",
            "city": "Denver",
            "state": "CO",
            "zip_code": "80202",
            "contact_name": "Sierra Delossantos",
            "contact_phone": "(303) 555-3456",
            "contact_email": "sierradelossantos@gmail.com",
            "allow_messages": True,
            "categories": ["Furniture", "Toys", "Household", "Clothing"],
            "price_range": "$5-$200",
            "payment_methods": ["Cash", "Venmo", "Zelle"],
            "owner": "sierradelossantos"
        },
        {
            "title": "Denver Tech Worker Sale",
            "description": "Remote work setup sale! Selling office furniture, monitors, and tech accessories. High-quality items!",
            "start_date": "2024-11-12",
            "end_date": None,
            "start_time": "09:00:00",
            "end_time": "16:00:00",
            "address": "654 Tech Boulevard",
            "city": "Denver",
            "state": "CO",
            "zip_code": "80205",
            "contact_name": "Javier Delossantos",
            "contact_phone": "(303) 555-7890",
            "contact_email": "javiddelossantos5@gmail.com",
            "allow_messages": True,
            "categories": ["Electronics", "Furniture", "Office Supplies"],
            "price_range": "$50-$400",
            "payment_methods": ["Cash", "Venmo", "PayPal", "Zelle"],
            "owner": "javiddelossantos"
        },
        
        # Phoenix, AZ sales
        {
            "title": "Phoenix Retirement Community Sale",
            "description": "Retirement community sale! Selling furniture, collectibles, and household items. Moving to assisted living.",
            "start_date": "2024-11-13",
            "end_date": "2024-11-14",
            "start_time": "08:00:00",
            "end_time": "16:00:00",
            "address": "987 Desert Rose Lane",
            "city": "Phoenix",
            "state": "AZ",
            "zip_code": "85001",
            "contact_name": "Margaret Thompson",
            "contact_phone": "(602) 555-2468",
            "contact_email": "margaret.thompson@email.com",
            "allow_messages": False,
            "categories": ["Furniture", "Collectibles", "Antiques", "Household"],
            "price_range": "$15-$250",
            "payment_methods": ["Cash", "Check"],
            "owner": "margarethompson"
        },
        {
            "title": "Phoenix College Student Sale",
            "description": "End of semester! Selling textbooks, dorm furniture, and college supplies. Great deals for students!",
            "start_date": "2024-11-15",
            "end_date": None,
            "start_time": "10:00:00",
            "end_time": "17:00:00",
            "address": "147 Campus Drive",
            "city": "Phoenix",
            "state": "AZ",
            "zip_code": "85004",
            "contact_name": "Alex Rodriguez",
            "contact_phone": "(602) 555-1357",
            "contact_email": "alex.rodriguez@email.com",
            "allow_messages": True,
            "categories": ["Books", "Furniture", "Electronics", "Miscellaneous"],
            "price_range": "Under $75",
            "payment_methods": ["Cash", "Venmo"],
            "owner": "alexrodriguez"
        }
    ]
    
    # Create yard sales
    print("\n🏠 Creating yard sales...")
    created_yard_sales = []
    
    for yard_sale_data in yard_sales_data:
        owner = yard_sale_data.pop("owner")
        if owner in user_tokens:
            result = create_yard_sale(user_tokens[owner], yard_sale_data)
            if result:
                created_yard_sales.append(result)
        time_module.sleep(0.3)  # Small delay between creations
    
    print(f"✅ Created {len(created_yard_sales)} yard sales")
    
    # Realistic comments between users
    comments_data = [
        # Comments for different yard sales
        {"yard_sale_id": 1, "username": "sierradelossantos", "content": "Great! What time do you start on Saturday?"},
        {"yard_sale_id": 1, "username": "mikechen", "content": "Do you have any dining room tables?"},
        {"yard_sale_id": 1, "username": "davidlee", "content": "Are the electronics still working?"},
        {"yard_sale_id": 1, "username": "lisagarcia", "content": "Can I get a preview of the furniture?"},
        
        {"yard_sale_id": 2, "username": "sarahjohnson", "content": "What sizes are the kids' clothes?"},
        {"yard_sale_id": 2, "username": "alexrodriguez", "content": "Do you have any camping tents?"},
        {"yard_sale_id": 2, "username": "margarethompson", "content": "Are the bikes in good condition?"},
        {"yard_sale_id": 2, "username": "tomwilson", "content": "What vintage items do you have?"},
        
        {"yard_sale_id": 3, "username": "jenniferdavis", "content": "Can you hold the gaming console until Sunday?"},
        {"yard_sale_id": 3, "username": "robertmartinez", "content": "Do you accept trades?"},
        {"yard_sale_id": 3, "username": "sierradelossantos", "content": "What's the best time to come by?"},
        {"yard_sale_id": 3, "username": "mikechen", "content": "Are there any early bird specials?"},
        
        {"yard_sale_id": 4, "username": "sarahjohnson", "content": "What types of antiques do you have?"},
        {"yard_sale_id": 4, "username": "davidlee", "content": "Are the prices negotiable?"},
        {"yard_sale_id": 4, "username": "lisagarcia", "content": "Do you have any vintage jewelry?"},
        
        {"yard_sale_id": 5, "username": "alexrodriguez", "content": "What camping gear do you have?"},
        {"yard_sale_id": 5, "username": "jenniferdavis", "content": "Are the fishing rods included?"},
        {"yard_sale_id": 5, "username": "robertmartinez", "content": "What condition are the bikes in?"},
        
        {"yard_sale_id": 6, "username": "margarethompson", "content": "What kitchen items are available?"},
        {"yard_sale_id": 6, "username": "tomwilson", "content": "Do you have any appliances?"},
        {"yard_sale_id": 6, "username": "sierradelossantos", "content": "What time do you start on Friday?"},
        
        # Comments for new yard sales
        {"yard_sale_id": 7, "username": "mikechen", "content": "Is the furniture in good condition?"},
        {"yard_sale_id": 7, "username": "sarahjohnson", "content": "What electronics are you selling?"},
        {"yard_sale_id": 7, "username": "alexrodriguez", "content": "Do you have any gaming equipment?"},
        
        {"yard_sale_id": 8, "username": "davidlee", "content": "What textbooks do you have?"},
        {"yard_sale_id": 8, "username": "lisagarcia", "content": "Are the prices student-friendly?"},
        {"yard_sale_id": 8, "username": "robertmartinez", "content": "What dorm furniture is available?"},
        
        {"yard_sale_id": 9, "username": "margarethompson", "content": "Perfect for incoming students!"},
        {"yard_sale_id": 9, "username": "tomwilson", "content": "What study materials do you have?"},
        {"yard_sale_id": 9, "username": "jenniferdavis", "content": "Are the prices negotiable for students?"},
        
        {"yard_sale_id": 10, "username": "sierradelossantos", "content": "Great location! What time do you start?"},
        {"yard_sale_id": 10, "username": "mikechen", "content": "What toys are available?"},
        {"yard_sale_id": 10, "username": "sarahjohnson", "content": "Do you have any baby items?"},
        
        {"yard_sale_id": 11, "username": "alexrodriguez", "content": "What monitors are you selling?"},
        {"yard_sale_id": 11, "username": "davidlee", "content": "Perfect for remote work setup!"},
        {"yard_sale_id": 11, "username": "lisagarcia", "content": "Are the prices negotiable?"},
        
        {"yard_sale_id": 12, "username": "robertmartinez", "content": "What collectibles do you have?"},
        {"yard_sale_id": 12, "username": "margarethompson", "content": "Are the antiques authentic?"},
        {"yard_sale_id": 12, "username": "tomwilson", "content": "What's the best time to visit?"},
        
        {"yard_sale_id": 13, "username": "jenniferdavis", "content": "What textbooks are available?"},
        {"yard_sale_id": 13, "username": "sierradelossantos", "content": "Perfect for college students!"},
        {"yard_sale_id": 13, "username": "mikechen", "content": "Are the prices student-friendly?"}
    ]
    
    # Add comments
    print("\n💬 Adding realistic comments...")
    comment_count = 0
    
    for comment_data in comments_data:
        yard_sale_id = comment_data["yard_sale_id"]
        username = comment_data["username"]
        content = comment_data["content"]
        
        if username in user_tokens and yard_sale_id <= len(created_yard_sales):
            if add_comment(user_tokens[username], yard_sale_id, content):
                comment_count += 1
        time_module.sleep(0.2)  # Small delay between comments
    
    print(f"✅ Added {comment_count} comments")
    
    # Summary
    print(f"\n🎉 Extensive test data population complete!")
    print(f"📊 Created {len(created_yard_sales)} yard sales")
    print(f"👥 Total users: {len(registered_users)}")
    print(f"💬 Total comments: {comment_count}")
    
    # Show summary by location
    locations = {}
    for sale in created_yard_sales:
        location = f"{sale['city']}, {sale['state']} {sale['zip_code']}"
        if location not in locations:
            locations[location] = 0
        locations[location] += 1
    
    print(f"\n📍 Yard sales by location:")
    for location, count in locations.items():
        print(f"  {location}: {count} sales")

if __name__ == "__main__":
    main()
