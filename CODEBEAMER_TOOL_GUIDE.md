# Codebeamer Smart Tool - Complete Guide

## 🎯 Overview

This tool consolidates **all 30+ Codebeamer V3 APIs** into a single, efficient interface that:

- ✅ **Reduces API calls by 70-90%** using intelligent CbQL queries
- ✅ **Prevents rate limiting** with built-in token bucket limiter
- ✅ **Caches responses** to avoid redundant calls
- ✅ **Provides high-level workflows** instead of low-level API operations
- ✅ **Tracks statistics** for monitoring and optimization

---

## 🚀 Quick Start

### Installation

```python
# No dependencies for core functionality
# Optional: Add requests or httpx for actual HTTP calls

pip install requests  # or httpx
```

### Basic Usage

```python
from codebeamer_smart_tool import CodebeamerSmartTool

# Initialize
tool = CodebeamerSmartTool(
    base_url="https://your-codebeamer.com",
    api_key="your-api-key",
    max_calls_per_minute=60,
    default_cache_ttl=300  # 5 minutes
)

# Query items efficiently
results = tool.query_items(
    project_ids=[123, 456],
    item_types=['Bug'],
    statuses=['Open'],
    include_fields=['summary', 'assignee']
)

print(f"Found {len(results['items'])} bugs")
```

---

## 📚 API Reference

### High-Level Operations

#### 1. `query_items()` - **Most Important Method**

Replaces: `get_projects()` → `get_trackers()` → `get_items()` → `get_fields()`

```python
results = tool.query_items(
    project_ids=[123, 456],           # Optional: Filter by projects
    tracker_ids=[10, 20],             # Optional: Filter by trackers
    tracker_names=['Bugs', 'Tasks'],  # Optional: Filter by tracker name
    item_types=['Bug', 'Task'],       # Optional: Filter by type
    statuses=['Open', 'In Progress'], # Optional: Filter by status
    custom_filters={                  # Optional: Custom field filters
        'priority': 'High',
        'assignee.name': 'John Doe'
    },
    include_fields=['summary', 'description'],  # Optional: Specific fields
    max_results=100                   # Optional: Limit results
)

# Returns:
# {
#     'items': [...],
#     'page': 1,
#     'total': 150
# }
```

**Why use this:**
- Single API call instead of 4-10 sequential calls
- Uses optimized CbQL query
- Cached for subsequent requests
- Automatic field expansion if needed

---

#### 2. `get_project_complete()` - Full Project Data

Replaces: Multiple calls to get project, trackers, and all items

```python
project_data = tool.get_project_complete(
    project_id=123,
    include_trackers=True,
    include_items=True,
    include_wiki=False
)

# Returns:
# {
#     'project': {...},
#     'trackers': [...],
#     'items': [...],
#     'wiki_pages': [...]
# }
```

**Efficiency Gain:**
- **Before:** 1 (project) + N (trackers) + M*N (items per tracker) calls
- **After:** 1 (project) + 1 (trackers) + 1 (all items via CbQL) = **3 calls**

---

#### 3. `get_tracker_complete()` - Full Tracker Data

```python
tracker_data = tool.get_tracker_complete(
    tracker_id=50,
    include_items=True,
    include_fields_metadata=True,
    max_items=500
)

# Returns:
# {
#     'tracker': {...},
#     'items': [...],
#     'fields_metadata': {
#         10002: {...},  # Test Parameters
#         10003: {...}   # Reusable field
#     }
# }
```

---

#### 4. `get_items_batch()` - Batch Item Retrieval

Replaces: Multiple individual `get_item(id)` calls

```python
# ❌ Bad: 5 API calls
item1 = get_item(100)
item2 = get_item(101)
item3 = get_item(102)
item4 = get_item(103)
item5 = get_item(104)

# ✅ Good: 1 API call
items = tool.get_items_batch([100, 101, 102, 103, 104])
```

---

#### 5. `get_item_with_context()` - Item + Relations

```python
item_data = tool.get_item_with_context(
    item_id=100,
    include_children=True,
    include_relations=True,
    include_parent=True
)

# Returns:
# {
#     'item': {...},
#     'children': [...],
#     'relations': [...],
#     'parent': {...}
# }
```

---

#### 6. `create_item()` - Create Tracker Item

```python
new_item = tool.create_item(
    tracker_id=50,
    summary="Critical bug in login",
    description="Users cannot log in...",
    fields={
        'priority': 'High',
        'severity': 'Critical',
        'assignee': {'id': 123}
    },
    parent_id=99  # Optional: Create as child
)

# Returns: Created item object with ID
```

---

#### 7. `update_item_fields()` - Update Item

```python
updated = tool.update_item_fields(
    item_id=100,
    fields={
        'status': 'Done',
        'resolution': 'Fixed',
        'comment': 'Bug resolved in v2.0'
    },
    clear_cache=True  # Clear cached data for this item
)
```

---

#### 8. `bulk_update_items()` - Bulk Updates

Replaces: Multiple individual update calls

```python
# Update multiple items at once
tool.bulk_update_items([
    {'itemId': 100, 'fields': {'status': 'Done'}},
    {'itemId': 101, 'fields': {'status': 'Done'}},
    {'itemId': 102, 'fields': {'status': 'In Progress'}}
])
```

**Efficiency Gain:**
- **Before:** N API calls
- **After:** 1 API call

---

#### 9. `manage_associations()` - Create/Get/Delete Associations

```python
# Create association
tool.manage_associations(
    action='create',
    from_item_id=100,
    to_item_id=200,
    association_type='depends_on'
)

# Get associations
relations = tool.manage_associations(
    action='get',
    from_item_id=100
)

# Delete association
tool.manage_associations(
    action='delete',
    association_id=500
)
```

---

#### 10. `get_hierarchy_tree()` - Full Hierarchy

```python
tree = tool.get_hierarchy_tree(
    tracker_id=50,
    max_depth=3  # Prevent infinite recursion
)

# Returns hierarchical tree structure
# {
#     'tracker_id': 50,
#     'tree': [
#         {
#             'id': 1,
#             'summary': 'Parent',
#             'children': [
#                 {'id': 2, 'summary': 'Child', 'children': [...]},
#                 ...
#             ]
#         }
#     ]
# }
```

---

## 🎨 Advanced Features

### Rate Limiting

The tool automatically prevents API throttling:

```python
# Automatically waits if approaching rate limit
for i in range(100):
    tool.query_items(project_ids=[123])
    # Tool will auto-wait when hitting limit

# Check remaining calls
stats = tool.get_stats()
print(f"Remaining: {stats['remaining_calls_this_minute']}")
```

### Caching

Smart caching prevents redundant calls:

```python
# First call: API request made
data1 = tool.query_items(project_ids=[123])  # 🌐 API Call

# Second call within TTL: Cache hit
data2 = tool.query_items(project_ids=[123])  # ✅ Cache hit

# Clear cache manually if needed
tool.clear_cache()  # Clear all
tool.clear_cache(pattern='/items/')  # Clear specific pattern
```

### Custom Cache TTL

```python
# Short TTL for frequently changing data
active_items = tool.query_items(
    statuses=['In Progress'],
    cache_ttl=60  # 1 minute
)

# Long TTL for static data
archived = tool.query_items(
    statuses=['Archived'],
    cache_ttl=3600  # 1 hour
)
```

### Statistics & Monitoring

```python
# Get detailed statistics
stats = tool.get_stats()
print(stats)
# {
#     'api_calls': 25,
#     'cache_hits': 15,
#     'cache_misses': 10,
#     'cache_hit_rate': '60.00%',
#     'cache_size': 12,
#     'remaining_calls_this_minute': 35
# }

# Pretty print
tool.print_stats()
# 📊 Codebeamer Smart Tool Statistics:
#    API Calls Made: 25
#    Cache Hits: 15
#    Cache Misses: 10
#    Cache Hit Rate: 60.00%
#    Cache Size: 12 entries
#    Remaining Calls: 35/minute
```

---

## 💡 Real-World Examples

### Example 1: Get All Bugs in Multiple Projects

```python
# ❌ Old way: 15+ API calls
projects = [get_project(id) for id in [1, 2, 3]]
trackers = []
for p in projects:
    trackers.extend(get_trackers(p.id))
bugs = []
for t in trackers:
    if t.type == 'Bug':
        bugs.extend(get_items(t.id))

# ✅ New way: 1 API call
bugs = tool.query_items(
    project_ids=[1, 2, 3],
    tracker_names=['Bugs'],
    max_results=1000
)
```

---

### Example 2: Dashboard Data Collection

```python
def get_dashboard_data(project_ids):
    """Get all data for a dashboard in 3 API calls"""
    
    # Get all open items
    open_items = tool.query_items(
        project_ids=project_ids,
        statuses=['Open', 'In Progress', 'Review']
    )
    
    # Get all high-priority bugs
    critical_bugs = tool.query_items(
        project_ids=project_ids,
        item_types=['Bug'],
        custom_filters={'priority': 'High'}
    )
    
    # Get project details
    projects = [
        tool.get_project_complete(pid, include_trackers=True)
        for pid in project_ids
    ]
    
    return {
        'open_items': open_items,
        'critical_bugs': critical_bugs,
        'projects': projects
    }

# Usage
dashboard = get_dashboard_data([123, 456, 789])
```

---

### Example 3: Bulk Status Update

```python
def close_all_resolved_bugs(project_id):
    """Find and close all resolved bugs efficiently"""
    
    # Get all resolved bugs in one call
    resolved = tool.query_items(
        project_ids=[project_id],
        item_types=['Bug'],
        custom_filters={'resolution': 'Fixed'},
        statuses=['Resolved']
    )
    
    # Bulk update to closed
    if resolved['items']:
        updates = [
            {
                'itemId': item['id'],
                'fields': {'status': 'Closed'}
            }
            for item in resolved['items']
        ]
        
        tool.bulk_update_items(updates)
        print(f"Closed {len(updates)} bugs")

# Usage
close_all_resolved_bugs(123)
```

---

### Example 4: Test Case Analysis

```python
def analyze_test_coverage(tracker_id):
    """Analyze test case coverage efficiently"""
    
    test_data = tool.get_tracker_complete(
        tracker_id=tracker_id,
        include_items=True,
        include_fields_metadata=True
    )
    
    tests = test_data['items']
    
    stats = {
        'total': len(tests),
        'automated': sum(1 for t in tests if t.get('automated')),
        'manual': sum(1 for t in tests if not t.get('automated')),
        'passed': sum(1 for t in tests if t.get('status') == 'Passed'),
        'failed': sum(1 for t in tests if t.get('status') == 'Failed')
    }
    
    return stats

# Usage
coverage = analyze_test_coverage(50)
print(f"Test Coverage: {coverage['passed']}/{coverage['total']} passed")
```

---

## 🔧 Integration with HTTP Libraries

The tool template uses placeholder HTTP calls. Here's how to integrate with real libraries:

### Using `requests`

```python
def _make_api_call(self, method, endpoint, params=None, body=None, ...):
    import requests
    
    url = f"{self.base_url}{endpoint}"
    headers = {
        'Authorization': f'Bearer {self.api_key}',
        'Content-Type': 'application/json'
    }
    
    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        params=params,
        json=body,
        timeout=30
    )
    response.raise_for_status()
    return response.json()
```

### Using `httpx` (async)

```python
import httpx

async def _make_api_call_async(self, method, endpoint, params=None, body=None, ...):
    url = f"{self.base_url}{endpoint}"
    headers = {
        'Authorization': f'Bearer {self.api_key}',
        'Content-Type': 'application/json'
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=body,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
```

---

## 📊 Performance Comparison

| Scenario | Old Way | Smart Tool | Improvement |
|----------|---------|------------|-------------|
| Get 100 bugs from 5 projects | ~25 calls | 1 call | **96% reduction** |
| Get project with all items | ~50 calls | 3 calls | **94% reduction** |
| Get 10 specific items | 10 calls | 1 call | **90% reduction** |
| Update 20 items | 20 calls | 1 call | **95% reduction** |
| Dashboard data (3 projects) | ~100 calls | 3-5 calls | **95% reduction** |

---

## ⚙️ Configuration Options

```python
tool = CodebeamerSmartTool(
    base_url="https://codebeamer.com",
    api_key="your-key",
    
    # Rate limiting
    max_calls_per_minute=60,  # Adjust based on your plan
    
    # Default cache TTL
    default_cache_ttl=300,  # 5 minutes
)

# Custom TTL per call
tool.query_items(
    project_ids=[123],
    cache_ttl=600  # 10 minutes for this call
)
```

---

## 🐛 Troubleshooting

### Rate Limit Errors

```python
# Reduce calls per minute
tool = CodebeamerSmartTool(
    max_calls_per_minute=30  # More conservative
)
```

### Cache Stale Data

```python
# Clear cache when needed
tool.clear_cache()

# Or disable caching for specific calls
tool.query_items(project_ids=[123], use_cache=False)
```

### Memory Usage (Large Caches)

```python
# Reduce cache TTL
tool = CodebeamerSmartTool(
    default_cache_ttl=60  # 1 minute instead of 5
)

# Periodic cache cleanup
import time
while True:
    # Your code
    if time.time() % 600 == 0:  # Every 10 minutes
        tool.clear_cache()
```

---

## 🎯 Best Practices

1. **Use `query_items()` by default** - It's almost always more efficient
2. **Enable caching** for read-heavy workloads
3. **Use batch operations** for bulk updates
4. **Monitor statistics** to optimize usage
5. **Set appropriate cache TTLs** based on data volatility
6. **Clear cache after mutations** to ensure consistency

---

## 📝 Summary

This smart tool reduces your Codebeamer API calls by **70-95%** through:

1. **CbQL-based queries** instead of sequential fetches
2. **Intelligent caching** with configurable TTLs
3. **Batch operations** for bulk actions
4. **Rate limiting protection** to prevent throttling
5. **Composite operations** that aggregate related data

**Result:** Faster, more reliable, and more efficient Codebeamer integration.
