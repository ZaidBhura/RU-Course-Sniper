"""Test the fix for string index numbers."""

from src.soc_client import SOCClient

client = SOCClient()
sections = client.fetch_open_sections()

print(f'Found {len(sections)} open sections')

# Check first few
if len(sections) > 0:
    print(f'\nFirst 5 sections: {[s.indexNumber for s in sections[:5]]}')

# Check your watched indexes
watched = [11671, 12345]
found = [s.indexNumber for s in sections if s.indexNumber in watched]

if found:
    print(f'\nYour watched indexes that are OPEN: {found}')
else:
    print(f'\nYour watched indexes ({watched}) are not in the open sections list')
    print('This means they are currently CLOSED according to the API')

