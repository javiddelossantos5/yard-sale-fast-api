#!/usr/bin/env python3
"""
Script to populate the database with realistic message test data between users
"""

import requests
import json
import time as time_module
from datetime import datetime

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

def send_message(token, yard_sale_id, recipient_id, content):
    """Send a message"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    message_data = {
        "content": content,
        "recipient_id": recipient_id
    }
    
    response = requests.post(f"{BASE_URL}/yard-sales/{yard_sale_id}/messages", json=message_data, headers=headers)
    if response.status_code == 200:
        print(f"✅ Sent message: {content[:50]}...")
        return response.json()
    else:
        print(f"❌ Failed to send message: {response.text}")
        return None

def get_yard_sales():
    """Get all yard sales to find owners and IDs"""
    response = requests.get(f"{BASE_URL}/yard-sales")
    if response.status_code == 200:
        return response.json()
    return []

def get_users():
    """Get all users (we'll use the ones we know exist)"""
    return [
        {"id": 1, "username": "javiddelossantos"},
        {"id": 2, "username": "sierradelossantos"},
        {"id": 3, "username": "mikechen"},
        {"id": 4, "username": "sarahjohnson"},
        {"id": 5, "username": "alexrodriguez"},
        {"id": 6, "username": "margarethompson"},
        {"id": 7, "username": "tomwilson"},
        {"id": 8, "username": "jenniferdavis"},
        {"id": 9, "username": "davidlee"},
        {"id": 10, "username": "lisagarcia"},
        {"id": 11, "username": "robertmartinez"}
    ]

def main():
    print("💬 Populating database with realistic message test data...")
    
    # Get yard sales
    yard_sales = get_yard_sales()
    if not yard_sales:
        print("❌ No yard sales found")
        return
    
    print(f"✅ Found {len(yard_sales)} yard sales")
    
    # Get user tokens
    users = get_users()
    user_tokens = {}
    
    for user in users:
        token = get_auth_token(user["username"], "Password")
        if token:
            user_tokens[user["id"]] = {
                "username": user["username"],
                "token": token
            }
        time_module.sleep(0.2)
    
    print(f"✅ Got tokens for {len(user_tokens)} users")
    
    # Realistic message conversations
    message_conversations = [
        # Conversation 1: Furniture inquiry
        {
            "yard_sale_id": 2,
            "owner_id": 2,
            "customer_id": 1,
            "messages": [
                "Hi! I am interested in the furniture you have for sale. Do you have any dining room tables available?",
                "Yes! I have a beautiful oak dining table with 6 chairs. It's in excellent condition. Would you like to see it?",
                "That sounds perfect! What are you asking for it?",
                "I'm asking $200 for the set. It's solid oak and barely used. When would you like to come by?",
                "That's a great price! I can come by tomorrow morning around 10 AM. Is that okay?",
                "Perfect! I'll be here. The address is 456 Oak Street in Vernal. See you tomorrow!"
            ]
        },
        
        # Conversation 2: Electronics inquiry
        {
            "yard_sale_id": 3,
            "owner_id": 5,
            "customer_id": 3,
            "messages": [
                "Hi! I saw your electronics sale. Do you have any gaming consoles?",
                "Yes! I have a PlayStation 4 with 2 controllers and several games. Are you interested?",
                "Definitely! What games do you have and how much are you asking?",
                "I have FIFA 22, Call of Duty, and Spider-Man. Asking $150 for everything.",
                "That's a good deal! Is the console in good working condition?",
                "Yes, it works perfectly. I just upgraded to PS5 so I'm selling this one."
            ]
        },
        
        # Conversation 3: Kids clothes inquiry
        {
            "yard_sale_id": 4,
            "owner_id": 3,
            "customer_id": 4,
            "messages": [
                "Hello! I'm looking for kids clothes. What sizes do you have?",
                "I have clothes from 2T to 12. Mostly girls clothes but some boys too. What size are you looking for?",
                "I need size 6-7 girls clothes. Do you have any dresses or pants?",
                "Yes! I have several cute dresses and lots of pants. All in good condition. $2-5 each.",
                "Great! Can I come by this afternoon to look through them?",
                "Absolutely! I'll be here until 3 PM. The address is 789 Pine Avenue."
            ]
        },
        
        # Conversation 4: Antiques inquiry
        {
            "yard_sale_id": 5,
            "owner_id": 6,
            "customer_id": 7,
            "messages": [
                "Hi! I collect antiques. What kind of vintage items do you have?",
                "I have some beautiful antique furniture, vintage jewelry, and old books. Are you looking for anything specific?",
                "I'm interested in vintage jewelry and old books. What do you have?",
                "I have a vintage pearl necklace, some old silver rings, and a collection of 1950s books. Would you like to see them?",
                "Yes, that sounds wonderful! What are your prices like?",
                "The jewelry ranges from $25-75 and the books are $5-15 each. Very reasonable prices."
            ]
        },
        
        # Conversation 5: Outdoor equipment inquiry
        {
            "yard_sale_id": 6,
            "owner_id": 7,
            "customer_id": 8,
            "messages": [
                "Hi! I'm interested in your camping gear. What do you have available?",
                "I have a 4-person tent, sleeping bags, camping chairs, and a portable stove. All in great condition!",
                "Perfect! I'm planning a camping trip next month. How much for the tent and sleeping bags?",
                "The tent is $50 and I have 2 sleeping bags for $25 each. The whole camping set would be $100.",
                "That's a great deal! Do you have any fishing equipment too?",
                "Yes! I have fishing rods, tackle boxes, and some lures. Add another $30 for the fishing gear."
            ]
        },
        
        # Conversation 6: Multi-family sale inquiry
        {
            "yard_sale_id": 7,
            "owner_id": 8,
            "customer_id": 9,
            "messages": [
                "Hello! I saw your multi-family sale. What kitchen items do you have?",
                "We have lots of kitchen items! Pots, pans, dishes, small appliances. What are you looking for?",
                "I need a good set of pots and pans. Do you have any non-stick cookware?",
                "Yes! I have a complete non-stick set with 8 pieces. Barely used, asking $40 for the set.",
                "That sounds perfect! Do you have any small appliances like a blender or toaster?",
                "Yes! I have a blender for $15 and a toaster for $10. All working perfectly."
            ]
        },
        
        # Conversation 7: Student moving sale
        {
            "yard_sale_id": 8,
            "owner_id": 10,
            "customer_id": 11,
            "messages": [
                "Hi! I'm a student looking for dorm furniture. What do you have?",
                "Perfect! I have a desk, chair, mini fridge, and some storage bins. All great for dorm life!",
                "Great! How much for the desk and chair?",
                "The desk is $30 and the chair is $15. Both in good condition, perfect for studying.",
                "That's exactly what I need! Do you have any textbooks for sale too?",
                "Yes! I have textbooks for various subjects. Most are $10-20 each. What subjects are you looking for?"
            ]
        },
        
        # Conversation 8: Tech worker sale
        {
            "yard_sale_id": 11,
            "owner_id": 1,
            "customer_id": 5,
            "messages": [
                "Hi! I'm interested in your tech setup. What monitors do you have?",
                "I have two 24-inch monitors, both 1080p. Perfect for a dual monitor setup. Asking $100 each.",
                "That's a good price! Are they in good condition? Any dead pixels?",
                "No dead pixels, both work perfectly. I'm just upgrading to 4K monitors. They're about 2 years old.",
                "Perfect! I'll take both monitors. Can I pick them up this weekend?",
                "Absolutely! I'm available Saturday or Sunday. Let me know what time works for you."
            ]
        }
    ]
    
    # Send messages for each conversation
    print("\n💬 Creating realistic message conversations...")
    total_messages = 0
    
    for conversation in message_conversations:
        yard_sale_id = conversation["yard_sale_id"]
        owner_id = conversation["owner_id"]
        customer_id = conversation["customer_id"]
        messages = conversation["messages"]
        
        print(f"\n📧 Creating conversation for yard sale {yard_sale_id}...")
        
        # Alternate between owner and customer sending messages
        for i, message_content in enumerate(messages):
            if i % 2 == 0:  # Customer sends first message
                sender_id = customer_id
                recipient_id = owner_id
            else:  # Owner responds
                sender_id = owner_id
                recipient_id = customer_id
            
            if sender_id in user_tokens:
                result = send_message(
                    user_tokens[sender_id]["token"],
                    yard_sale_id,
                    recipient_id,
                    message_content
                )
                if result:
                    total_messages += 1
                time_module.sleep(0.5)  # Small delay between messages
    
    print(f"\n🎉 Message test data population complete!")
    print(f"📊 Created {total_messages} messages across {len(message_conversations)} conversations")
    
    # Show summary
    print(f"\n📋 Conversation Summary:")
    for i, conversation in enumerate(message_conversations, 1):
        yard_sale = next((ys for ys in yard_sales if ys["id"] == conversation["yard_sale_id"]), None)
        if yard_sale:
            print(f"  {i}. {yard_sale['title']} - {len(conversation['messages'])} messages")

if __name__ == "__main__":
    main()
