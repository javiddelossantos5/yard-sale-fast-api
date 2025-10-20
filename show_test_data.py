#!/usr/bin/env python3
"""
Script to display all test data in the database
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
    print("🏠 YARD SALE FINDER - TEST DATA SUMMARY")
    print("=" * 60)
    
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
        print("-" * 40)
        
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
            print()
    
    # Show comments for a few yard sales
    print("💬 SAMPLE COMMENTS")
    print("-" * 40)
    
    for sale in yard_sales[:3]:  # Show comments for first 3 sales
        comments = get_comments_for_yard_sale(sale['id'])
        if comments:
            print(f"🏠 {sale['title']}:")
            for comment in comments[:2]:  # Show first 2 comments
                print(f"   💬 {comment['username']}: {comment['content']}")
            print()
    
    # Statistics
    print("📈 STATISTICS")
    print("-" * 40)
    
    total_comments = sum(sale['comment_count'] for sale in yard_sales)
    categories = set()
    for sale in yard_sales:
        categories.update(sale['categories'])
    
    print(f"Total Yard Sales: {len(yard_sales)}")
    print(f"Total Comments: {total_comments}")
    print(f"Unique Categories: {len(categories)}")
    print(f"Categories: {', '.join(sorted(categories))}")
    
    # Location breakdown
    print(f"\nLocations:")
    for location, sales in locations.items():
        print(f"  {location}: {len(sales)} sales")

if __name__ == "__main__":
    main()
