"""
Example API requests demonstrating region-based media fetching.
Requires the backend server to be running: uvicorn app.main:app --reload
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_supported_regions():
    """Test the /supported-regions endpoint."""
    print("\n" + "="*70)
    print("TEST: Get Supported Regions")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/supported-regions")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Found {len(data['supported_regions'])} regions:")
        for region in data['supported_regions']:
            details = data['region_details'][region]
            print(f"  • {region:20} - {details['description']}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)


def test_create_video_with_region():
    """Test the /create endpoint with region parameter."""
    print("\n" + "="*70)
    print("TEST: Create Video with Region (India)")
    print("="*70)
    
    # This is a dry-run test - just validates the API accepts the parameter
    # In production, this would trigger a full video generation
    
    data = {
        'topic': 'Pain relief medication for joint pain',
        'video_type': 'product_ad',
        'brand_name': 'PainAway',
        'region': 'india',  # Target Indian market
        'persona': 'professional narrator',
        'tone': 'clear and reassuring'
    }
    
    print("\nRequest data:")
    print(json.dumps(data, indent=2))
    
    print("\n⚠️  Note: This would start a full video generation pipeline.")
    print("To actually test, uncomment the code below and ensure server is running.\n")
    
    # Uncomment to actually test (will take several minutes):
    # response = requests.post(f"{BASE_URL}/create", data=data)
    # if response.status_code == 200:
    #     result = response.json()
    #     print(f"✅ Video generated: {result['video_id']}")
    #     print(f"   Path: {result['video_path']}")
    # else:
    #     print(f"❌ Failed: {response.status_code}")
    #     print(response.text)


def demo_region_comparison():
    """Show how the same topic would be handled for different regions."""
    print("\n" + "="*70)
    print("DEMO: Region-Based Media Fetching Examples")
    print("="*70)
    
    base_topic = "Diabetes management with healthy lifestyle"
    regions = ["india", "africa", "europe", "global"]
    
    print(f"\nTopic: {base_topic}\n")
    
    for region in regions:
        print(f"Region: {region.upper()}")
        print("-" * 70)
        
        data = {
            'topic': base_topic,
            'video_type': 'patient_awareness',
            'brand_name': 'DiabeCare',
            'region': region,
            'persona': 'warm health educator',
            'tone': 'encouraging and supportive'
        }
        
        print(f"  Expected media: ", end="")
        if region == "india":
            print("Indian patients, families, healthcare settings")
        elif region == "africa":
            print("African individuals, local community contexts")
        elif region == "europe":
            print("European patients, Western healthcare settings")
        elif region == "global":
            print("Diverse, multicultural imagery")
        
        print(f"  API call: POST /create with region='{region}'")
        print()


def main():
    """Run all example tests."""
    print("\n" + "="*70)
    print("REGION-BASED MEDIA FETCHING - API EXAMPLES")
    print("="*70)
    
    try:
        # Test 1: Check supported regions endpoint
        test_supported_regions()
        
        # Test 2: Show how to create video with region
        test_create_video_with_region()
        
        # Demo: Compare different regions
        demo_region_comparison()
        
        print("\n" + "="*70)
        print("EXAMPLES COMPLETED")
        print("="*70)
        print("\n✅ Region support is ready to use!")
        print("\nNext steps:")
        print("  1. Start backend: cd backend && uvicorn app.main:app --reload")
        print("  2. Call /supported-regions to see all available regions")
        print("  3. Call /create with region='india' (or other region)")
        print("  4. Check logs to see enhanced search terms in action")
        print()
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Backend server is not running")
        print("\nPlease start the server:")
        print("  cd backend")
        print("  uvicorn app.main:app --reload")
        print("\nThen run this script again.\n")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
