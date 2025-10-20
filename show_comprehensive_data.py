#!/usr/bin/env python3
"""
Script to display comprehensive test data including all users, yard sales, and comments
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def get_all_yard_sales():
    """Get all yard sales"""
    response = requests.get(f"{BASE_URL}/yard-sales")
    if response.status_code == 200:
        return response.json()
    return []

def get_comments_for_yard_sale(yard_sale_id):
    """Get comments for a specific yard sale"""
    response = requests.get(f"{BASE_URL}/yard-sales/{yard_sale_id}/comments")
    if response.status_code == 200:
        return response.json()
    return []

def main():
    print("🏠 YARD SALE FINDER - COMPREHENSIVE TEST DATA")
    print("=" * 70)
    
    yard_sales = get_all_yard_sales()
    
    if not yard_sales:
        print("❌ No yard sales found in database")
        return
    
    print(f"📊 Total Yard Sales: {len(yard_sales)}")
    print()
    
    # Group by location
    locations = {}
    for sale in yard_sales:
        location = f"{sale['city']}, {sale['state']} {sale['zip_code']}"
        if location not in locations:
            locations[location] = []
        locations[location].append(sale)
    
    for location, sales in locations.items():
        print(f"📍 {location}")
        print("-" * 50)
        
        for sale in sales:
            print(f"🏠 {sale['title']}")
            print(f"   📅 {sale['start_date']} - {sale['end_date'] or 'Single Day'}")
            print(f"   ⏰ {sale['start_time']} - {sale['end_time']}")
            print(f"   📍 {sale['address']}")
            print(f"   👤 {sale['contact_name']} ({sale['contact_phone']})")
            print(f"   🏷️  Categories: {', '.join(sale['categories'])}")
            print(f"   💰 Price Range: {sale['price_range']}")
            print(f"   💳 Payment: {', '.join(sale['payment_methods'])}")
            print(f"   💬 Comments: {sale['comment_count']}")
            print(f"   👨‍💼 Owner: {sale['owner_username']}")
            print()
    
    # Show sample comments
    print("💬 SAMPLE COMMENTS BY YARD SALE")
    print("-" * 50)
    
    for sale in yard_sales[:5]:  # Show comments for first 5 sales
        comments = get_comments_for_yard_sale(sale['id'])
        if comments:
            print(f"🏠 {sale['title']} ({sale['city']}, {sale['state']}):")
            for comment in comments[:3]:  # Show first 3 comments
                print(f"   💬 {comment['username']}: {comment['content']}")
            if len(comments) > 3:
                print(f"   ... and {len(comments) - 3} more comments")
            print()
    
    # Statistics
    print("📈 COMPREHENSIVE STATISTICS")
    print("-" * 50)
    
    total_comments = sum(sale['comment_count'] for sale in yard_sales)
    categories = set()
    owners = set()
    states = set()
    cities = set()
    
    for sale in yard_sales:
        categories.update(sale['categories'])
        owners.add(sale['owner_username'])
        states.add(sale['state'])
        cities.add(sale['city'])
    
    print(f"Total Yard Sales: {len(yard_sales)}")
    print(f"Total Comments: {total_comments}")
    print(f"Unique Categories: {len(categories)}")
    print(f"Unique Owners: {len(owners)}")
    print(f"States Covered: {', '.join(sorted(states))}")
    print(f"Cities Covered: {', '.join(sorted(cities))}")
    
    # Location breakdown
    print(f"\n📍 Location Breakdown:")
    for location, sales in locations.items():
        print(f"  {location}: {len(sales)} sales")
    
    # Owner breakdown
    print(f"\n👥 Owner Breakdown:")
    owner_counts = {}
    for sale in yard_sales:
        owner = sale['owner_username']
        owner_counts[owner] = owner_counts.get(owner, 0) + 1
    
    for owner, count in sorted(owner_counts.items()):
        print(f"  {owner}: {count} yard sale(s)")
    
    # Category breakdown
    print(f"\n🏷️  Top Categories:")
    category_counts = {}
    for sale in yard_sales:
        for category in sale['categories']:
            category_counts[category] = category_counts.get(category, 0) + 1
    
    # Sort categories by count
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    for category, count in sorted_categories[:10]:  # Top 10 categories
        print(f"  {category}: {count} sales")

if __name__ == "__main__":
    main()
