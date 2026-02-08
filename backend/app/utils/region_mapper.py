"""
Region-based demographic mapping for Pexels search queries.
Adds regional context to search terms to fetch culturally appropriate media.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Region to demographic search modifier mapping
REGION_DEMOGRAPHICS = {
    "india": ["Indian", "South Asian", "from India"],
    "africa": ["African", "Black", "from Africa"],
    "europe": ["European", "Caucasian", "from Europe"],
    "east_asia": ["East Asian", "Asian", "from East Asia"],
    "middle_east": ["Middle Eastern", "from Middle East"],
    "latin_america": ["Latin American", "Hispanic", "from Latin America"],
    "north_america": ["American", "North American", "from North America"],
    "southeast_asia": ["Southeast Asian", "from Southeast Asia"],
    "global": [],  # No demographic filter - global/diverse
}


def get_region_modifier(region: Optional[str]) -> str:
    """
    Get the demographic modifier for a region.
    Returns the first modifier from the list, or empty string if region is None or not found.
    
    Args:
        region: Region code (e.g., "india", "africa", "europe")
    
    Returns:
        Demographic modifier string (e.g., "Indian", "African") or empty string
    """
    if not region:
        return ""
    
    region_key = region.lower().strip()
    
    # Check if region exists in our mapping
    if region_key not in REGION_DEMOGRAPHICS:
        logger.warning(f"Unknown region '{region}', using no demographic filter")
        return ""
    
    modifiers = REGION_DEMOGRAPHICS[region_key]
    
    # Return first modifier, or empty string if list is empty (e.g., "global")
    return modifiers[0] if modifiers else ""


def apply_region_to_search_term(search_term: str, region: Optional[str]) -> str:
    """
    Apply regional demographic context to a Pexels search term.
    
    Examples:
        - "doctor explaining to patient" + "india" -> "Indian doctor explaining to patient"
        - "person applying cream" + "africa" -> "African person applying cream"
        - "family having dinner" + region=None -> "family having dinner" (unchanged)
    
    Args:
        search_term: Original Pexels search term
        region: Region code (e.g., "india", "africa")
    
    Returns:
        Modified search term with regional context
    """
    if not region or region.lower() == "global":
        return search_term
    
    modifier = get_region_modifier(region)
    if not modifier:
        return search_term
    
    # Add modifier at the start for person-centric searches
    # This works well with Pexels search algorithm
    enhanced_term = f"{modifier} {search_term}"
    
    logger.info(f"Enhanced search term: '{search_term}' -> '{enhanced_term}' (region: {region})")
    return enhanced_term


def apply_region_to_search_terms(search_terms: list[str], region: Optional[str]) -> list[str]:
    """
    Apply regional demographic context to a list of Pexels search terms.
    
    Args:
        search_terms: List of original Pexels search terms
        region: Region code (e.g., "india", "africa")
    
    Returns:
        List of modified search terms with regional context
    """
    if not region or region.lower() == "global":
        return search_terms
    
    return [apply_region_to_search_term(term, region) for term in search_terms]


def get_supported_regions() -> list[str]:
    """Get list of supported region codes."""
    return list(REGION_DEMOGRAPHICS.keys())
