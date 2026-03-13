"""Quick test script to check what the API is returning."""

import requests
import json

# Test the openSections API
url = "https://sis.rutgers.edu/soc/api/openSections.json?year=2026&term=1&campus=NB"

print("Fetching open sections from API...")
print(f"URL: {url}\n")

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    print(f"Response type: {type(data)}")
    print(f"Response length: {len(data) if isinstance(data, (list, dict)) else 'N/A'}\n")
    
    # Check if it's a list or dict
    if isinstance(data, list):
        print(f"Response is a list with {len(data)} items")
        if len(data) > 0:
            print(f"\nFirst item example:")
            print(json.dumps(data[0], indent=2))
            print(f"\nFirst 10 index numbers:")
            for i, item in enumerate(data[:10]):
                if isinstance(item, dict):
                    idx = item.get('indexNumber', 'N/A')
                    print(f"  {i+1}. Index: {idx}")
    elif isinstance(data, dict):
        print("Response is a dict")
        print(f"Keys: {list(data.keys())}")
        if 'openSections' in data:
            sections = data['openSections']
            print(f"\nopenSections has {len(sections)} items")
            if len(sections) > 0:
                print(f"\nFirst item example:")
                print(json.dumps(sections[0], indent=2))
    else:
        print(f"Unexpected response type: {type(data)}")
        print(f"Response: {str(data)[:200]}")
    
    # Check for specific indexes
    print("\n" + "="*60)
    print("Checking for your watched indexes:")
    print("="*60)
    
    watched_indexes = [11671, 12345]
    
    # Flatten the data structure
    if isinstance(data, list):
        all_sections = data
    elif isinstance(data, dict) and 'openSections' in data:
        all_sections = data['openSections']
    else:
        all_sections = []
    
    open_indexes = set()
    for item in all_sections:
        if isinstance(item, dict):
            idx = item.get('indexNumber')
            if idx:
                open_indexes.add(idx)
    
    for idx in watched_indexes:
        status = "OPEN" if idx in open_indexes else "CLOSED"
        print(f"  Index {idx}: {status}")
    
    print(f"\nTotal open sections found: {len(open_indexes)}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

