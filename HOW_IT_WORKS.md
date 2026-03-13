# How the Dynamic Course Name System Works

## Overview
The system is **100% dynamic** - no hardcoded course names. Everything is fetched from the Rutgers API in real-time.

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Application Startup                                       │
│    - Loads indexes from config.yaml                         │
│    - Starts CourseEnricher in background thread             │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CourseEnricher (Background Thread)                       │
│    - Fetches ALL courses from Rutgers API                   │
│    - URL: courses.json?year=2026&term=1&campus=NB          │
│    - Builds index → course mapping                           │
│    - Stores in memory cache: index_to_detail[11671] = ...  │
│    - Refreshes every 10 minutes automatically              │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. When ANY Index is Mentioned                              │
│    - Code calls: enricher.get_detail(index_number)          │
│    - Looks up in cache: index_to_detail.get(11671)         │
│    - Returns CourseDetail object OR None                    │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Display Logic (Same Everywhere)                           │
│    if course_detail:                                         │
│        show: "Index 11671 - CS 112: Data Structures"       │
│    else:                                                      │
│        show: "Index 11671 (course details loading...)"      │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. CourseEnricher (`src/enricher.py`)
- **Fetches** all course data from Rutgers API
- **Caches** it in memory as a dictionary: `{index_number: CourseDetail}`
- **Refreshes** automatically every 10 minutes
- **Thread-safe** using locks

### 2. Dynamic Lookup
Every time an index is displayed, the code:
```python
course_detail = self.enricher.get_detail(index_num)
if course_detail:
    course_name = f"{course_detail.subject} {course_detail.courseNumber}: {course_detail.title}"
    # Display with course name
else:
    # Display without course name (not loaded yet)
```

### 3. Where It's Used (All Dynamic)
- ✅ `add` command confirmation
- ✅ `remove` command confirmation  
- ✅ `list` command
- ✅ Startup display
- ✅ Alert messages
- ✅ Poll status
- ✅ Discord notifications
- ✅ Closed notifications

## Example: Adding Index 99999

1. **User types:** `add 99999`
2. **Code executes:**
   ```python
   course_detail = enricher.get_detail(99999)  # Lookup in cache
   ```
3. **If found in cache:**
   - Returns: `CourseDetail(subject="MATH", courseNumber="151", title="Calculus I", ...)`
   - Displays: `"Added index 99999 - MATH 151: Calculus I"`
4. **If NOT in cache yet:**
   - Returns: `None`
   - Displays: `"Added index 99999 (course details loading...)"`
   - Will show course name after next cache refresh (within 10 min)

## Why It's Dynamic

1. **No hardcoding:** Course names come from the API, not code
2. **Works for ANY index:** Add any 5-digit index, it will look it up
3. **Auto-updates:** Cache refreshes every 10 minutes
4. **Same logic everywhere:** All display code uses the same `get_detail()` lookup

## API Data Structure

The system fetches from:
```
https://sis.rutgers.edu/soc/api/courses.json?year=2026&term=1&campus=NB
```

Returns JSON with structure:
```json
[
  {
    "subject": "CS",
    "courseNumber": "112",
    "title": "Data Structures",
    "sections": [
      {
        "indexNumber": 11671,
        "number": "01",
        "instructors": ["John Doe"],
        "meetingTimes": ["Mon/Wed 10:20 AM - 11:40 AM"]
      }
    ]
  }
]
```

The system extracts and maps:
- `indexNumber` → Full course details
- Stores in: `{11671: CourseDetail(...)}`

## Thread Safety

- **Background thread** fetches course data
- **Main thread** reads from cache
- **Locks** prevent race conditions
- **Safe** for concurrent access

## Summary

✅ **Fully dynamic** - no hardcoded values  
✅ **Works for any index** - automatically looks up course names  
✅ **Auto-refreshes** - updates every 10 minutes  
✅ **Consistent** - same lookup logic everywhere  
✅ **Thread-safe** - handles concurrent access properly  

The system will work for **any index number** you add, as long as it exists in the Rutgers course catalog for that semester.

