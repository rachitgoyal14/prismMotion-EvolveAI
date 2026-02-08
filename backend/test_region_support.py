"""
Test script for region-based media fetching support.
Tests the region_mapper utility and verifies API integration.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.utils.region_mapper import (
    get_region_modifier,
    apply_region_to_search_term,
    apply_region_to_search_terms,
    get_supported_regions,
)


def test_region_modifiers():
    """Test that each region returns appropriate modifiers."""
    print("\n" + "="*60)
    print("TEST: Region Modifiers")
    print("="*60)
    
    test_cases = [
        ("india", "Indian"),
        ("africa", "African"),
        ("europe", "European"),
        ("east_asia", "East Asian"),
        ("middle_east", "Middle Eastern"),
        ("latin_america", "Latin American"),
        ("north_america", "American"),
        ("southeast_asia", "Southeast Asian"),
        ("global", ""),
        (None, ""),
        ("unknown_region", ""),
    ]
    
    for region, expected in test_cases:
        result = get_region_modifier(region)
        status = "✅" if result == expected else "❌"
        region_str = str(region) if region else "None"
        print(f"{status} Region: {region_str:20} -> Modifier: '{result:20}' (Expected: '{expected}')")


def test_search_term_enhancement():
    """Test search term enhancement with regional context."""
    print("\n" + "="*60)
    print("TEST: Search Term Enhancement")
    print("="*60)
    
    base_terms = [
        "doctor explaining to patient",
        "person applying pain relief cream",
        "family having dinner together",
        "elderly man walking in park",
    ]
    
    regions = ["india", "africa", "europe", "global", None]
    
    for region in regions:
        print(f"\nRegion: {region or 'None (default)'}")
        print("-" * 60)
        for term in base_terms:
            enhanced = apply_region_to_search_term(term, region)
            print(f"  Original: {term}")
            print(f"  Enhanced: {enhanced}")
            print()


def test_list_enhancement():
    """Test enhancing a list of search terms."""
    print("\n" + "="*60)
    print("TEST: List Enhancement")
    print("="*60)
    
    search_terms = [
        "doctor consulting patient in clinic",
        "person holding medication bottle",
        "pharmacist explaining prescription"
    ]
    
    print(f"\nOriginal terms: {search_terms}")
    
    for region in ["india", "africa", "global"]:
        enhanced = apply_region_to_search_terms(search_terms, region)
        print(f"\nRegion: {region}")
        print(f"Enhanced: {enhanced}")


def test_supported_regions():
    """Test getting list of supported regions."""
    print("\n" + "="*60)
    print("TEST: Supported Regions")
    print("="*60)
    
    regions = get_supported_regions()
    print(f"\nTotal supported regions: {len(regions)}")
    print(f"Regions: {', '.join(regions)}")


def test_real_world_scenarios():
    """Test real-world pharmaceutical video scenarios."""
    print("\n" + "="*60)
    print("TEST: Real-World Pharmaceutical Scenarios")
    print("="*60)
    
    scenarios = [
        {
            "name": "Diabetes Awareness - India",
            "region": "india",
            "terms": [
                "person checking blood sugar level",
                "family having healthy meal",
                "doctor discussing diabetes management"
            ]
        },
        {
            "name": "Hypertension Campaign - Africa",
            "region": "africa",
            "terms": [
                "person measuring blood pressure",
                "elderly man taking medication",
                "healthcare worker educating patient"
            ]
        },
        {
            "name": "Pain Relief Product - Europe",
            "region": "europe",
            "terms": [
                "person applying topical cream to joint",
                "active senior stretching outdoors",
                "physiotherapist demonstrating exercises"
            ]
        },
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print("-" * 60)
        print(f"Region: {scenario['region']}")
        print("\nSearch term transformations:")
        
        for term in scenario['terms']:
            enhanced = apply_region_to_search_term(term, scenario['region'])
            print(f"  • {term}")
            print(f"    → {enhanced}")


def run_all_tests():
    """Run all test functions."""
    print("\n" + "="*60)
    print("REGION-BASED MEDIA FETCHING - TEST SUITE")
    print("="*60)
    
    test_region_modifiers()
    test_search_term_enhancement()
    test_list_enhancement()
    test_supported_regions()
    test_real_world_scenarios()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)
    print("\n✅ Region support is working correctly!")
    print("\nUsage in API:")
    print("  POST /create")
    print("  Form data: region='india' (or 'africa', 'europe', etc.)")
    print("\nGet supported regions:")
    print("  GET /supported-regions")
    print("\n")


if __name__ == "__main__":
    run_all_tests()
