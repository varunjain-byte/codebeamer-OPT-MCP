"""
Codebeamer Smart Tool - Efficient API Wrapper
Consolidates all Codebeamer V3 APIs into an intelligent, cache-aware composite tool
that minimizes API calls and handles rate limiting.
"""

import time
import hashlib
import json
import requests
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum


class OperationType(Enum):
    """Supported operation types"""
    QUERY = "query"
    GET_PROJECT = "get_project"
    GET_TRACKER = "get_tracker"
    GET_ITEM = "get_item"
    CREATE_ITEM = "create_item"
    UPDATE_ITEM = "update_item"
    DELETE_ITEM = "delete_item"
    MANAGE_ASSOCIATIONS = "manage_associations"
    GET_HIERARCHY = "get_hierarchy"


@dataclass
class CacheEntry:
    """Cache entry with TTL support"""
    data: Any
    timestamp: float
    ttl: int  # seconds
    
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


class RateLimiter:
    """Token bucket rate limiter to prevent API throttling"""
    
    def __init__(self, max_calls_per_minute: int = 60):
        self.max_calls = max_calls_per_minute
        self.call_timestamps: List[float] = []
        self.window = 60  # 1 minute window
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        
        # Remove timestamps older than the window
        self.call_timestamps = [
            ts for ts in self.call_timestamps 
            if now - ts < self.window
        ]
        
        if len(self.call_timestamps) >= self.max_calls:
            # Calculate wait time
            oldest = self.call_timestamps[0]
            wait_time = self.window - (now - oldest) + 0.1
            if wait_time > 0:
                print(f"Rate limit approaching, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                # Clear old timestamps after waiting
                self.call_timestamps = []
        
        self.call_timestamps.append(now)
    
    def get_remaining_calls(self) -> int:
        """Get number of remaining calls in current window"""
        now = time.time()
        self.call_timestamps = [
            ts for ts in self.call_timestamps 
            if now - ts < self.window
        ]
        return self.max_calls - len(self.call_timestamps)


class CodebeamerSmartTool:
    """
    Smart wrapper for Codebeamer V3 APIs with:
    - Intelligent query optimization (prefers CbQL over sequential calls)
    - Response caching with configurable TTL
    - Rate limiting protection
    - Automatic data aggregation
    """
    
    def __init__(
        self, 
        base_url: str,
        api_key: str,
        max_calls_per_minute: int = 60,
        default_cache_ttl: int = 300,
        ssl_verify: Any = True
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.cache: Dict[str, CacheEntry] = {}
        self.rate_limiter = RateLimiter(max_calls_per_minute)
        self.default_cache_ttl = default_cache_ttl
        self.ssl_verify = ssl_verify
        self.stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def _generate_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate a unique cache key for the request"""
        key_str = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Retrieve from cache if available and not expired"""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if not entry.is_expired():
                self.stats['cache_hits'] += 1
                print(f"Cache hit: {cache_key[:8]}...")
                return entry.data
            else:
                del self.cache[cache_key]
        
        self.stats['cache_misses'] += 1
        return None
    
    def _set_cache(self, cache_key: str, data: Any, ttl: Optional[int] = None):
        """Store data in cache"""
        ttl = ttl or self.default_cache_ttl
        self.cache[cache_key] = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl=ttl
        )
    
    def _make_api_call(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        body: Optional[Dict] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> Any:
        """
        Make an API call with rate limiting and caching
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = f'/{endpoint}'
            
        cache_key = self._generate_cache_key(endpoint, params or {})
        
        # Check cache for GET requests
        if method == 'GET' and use_cache:
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data
        
        # Rate limiting
        self.rate_limiter.wait_if_needed()
        
        # Make actual API call
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        print(f"API Call: {method} {endpoint}")
        self.stats['api_calls'] += 1
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=body,
                timeout=30,  # 30 seconds timeout
                verify=self.ssl_verify
            )
            
            # Handle successful response
            if response.status_code in (200, 201):
                # Try to parse JSON, handle empty responses
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    data = {} if response.content else None
                
                # Cache GET responses
                if method == 'GET' and use_cache:
                    self._set_cache(cache_key, data, cache_ttl)
                
                return data
                
            # Handle errors
            else:
                print(f"API Error {response.status_code}: {response.text}")
                # Create detailed error structure
                error_data = {
                    "error": True,
                    "status_code": response.status_code,
                    "message": f"API request failed with status {response.status_code}",
                    "details": response.text
                }
                # Try to parse detailed error from response
                try:
                    error_json = response.json()
                    error_data.update(error_json)
                except:
                    pass
                    
                return error_data
                
                return error_data
                
        except requests.exceptions.SSLError as e:
            print(f"SSL Verification Error: {str(e)}")
            return {
                "error": True,
                "message": f"SSL verification failed. Try setting CODEBEAMER_SSL_VERIFY=False if using self-signed certs.",
                "details": str(e)
            }
        except requests.exceptions.RequestException as e:
            print(f"Connection Error: {str(e)}")
            return {
                "error": True,
                "message": f"Network error: {str(e)}"
            }
    
    def _build_cbql_query(
        self,
        project_ids: Optional[List[int]] = None,
        tracker_ids: Optional[List[int]] = None,
        tracker_names: Optional[List[str]] = None,
        item_types: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        custom_filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build a CbQL query from filters"""
        conditions = []
        
        if project_ids:
            conditions.append(f"project.id IN ({', '.join(map(str, project_ids))})")
        
        if tracker_ids:
            conditions.append(f"tracker.id IN ({', '.join(map(str, tracker_ids))})")
        
        if tracker_names:
            names = ', '.join(f"'{name}'" for name in tracker_names)
            conditions.append(f"tracker.name IN ({names})")
        
        if item_types:
            types = ', '.join(f"'{t}'" for t in item_types)
            conditions.append(f"type IN ({types})")
        
        if statuses:
            status_list = ', '.join(f"'{s}'" for s in statuses)
            conditions.append(f"status IN ({status_list})")
        
        if custom_filters:
            for field, value in custom_filters.items():
                if isinstance(value, list):
                    vals = ', '.join(f"'{v}'" for v in value)
                    conditions.append(f"{field} IN ({vals})")
                else:
                    conditions.append(f"{field} = '{value}'")
        
        return " AND ".join(conditions) if conditions else "project.id > 0"
    
    # ===========================
    # HIGH-LEVEL OPERATIONS
    # ===========================
    
    def list_projects(
        self,
        page: int = 1,
        page_size: int = 100,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        List all available projects in Codebeamer.
        
        This is the recommended FIRST CALL when starting to explore Codebeamer.
        Returns project IDs needed for subsequent queries.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of projects per page (1-500, default 100)
            use_cache: Whether to use cached results (default True)
            
        Returns:
            Dict with 'projects' list and pagination info
        """
        # Codebeamer V3 API uses page/pageSize for pagination
        params = {
            'page': page,
            'pageSize': min(page_size, 500)  # API max is 500
        }
        
        result = self._make_api_call(
            method='GET',
            endpoint='/v3/projects',
            params=params,
            use_cache=use_cache,
            cache_ttl=600  # 10 minutes - projects rarely change
        )
        
        return result
    
    def query_items(

        self,
        project_ids: Optional[List[int]] = None,
        tracker_ids: Optional[List[int]] = None,
        tracker_names: Optional[List[str]] = None,
        item_types: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        custom_filters: Optional[Dict[str, Any]] = None,
        include_fields: Optional[List[str]] = None,
        max_results: int = 100,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Efficient query using CbQL - replaces multiple get_projects -> get_trackers -> get_items calls
        
        Example:
            tool.query_items(
                project_ids=[123, 456],
                statuses=['Open', 'In Progress'],
                item_types=['Bug'],
                include_fields=['summary', 'assignee', 'priority']
            )
        """
        cbql = self._build_cbql_query(
            project_ids=project_ids,
            tracker_ids=tracker_ids,
            tracker_names=tracker_names,
            item_types=item_types,
            statuses=statuses,
            custom_filters=custom_filters
        )
        
        body = {
            'queryString': cbql,
            'page': 1,
            'pageSize': max_results
        }
        
        print(f"Executing CbQL query: {cbql}")
        
        result = self._make_api_call(
            method='POST',
            endpoint='/v3/items/query',
            body=body,
            use_cache=use_cache,
            cache_ttl=180  # 3 minutes for query results
        )
        
        # If specific fields requested, fetch detailed items
        if include_fields and result.get('items'):
            item_ids = [item['id'] for item in result['items']]
            detailed_items = self.get_items_batch(item_ids, fields=include_fields)
            result['items'] = detailed_items
        
        return result
    
    def get_project_complete(
        self,
        project_id: int,
        include_trackers: bool = True,
        include_items: bool = False,
        include_wiki: bool = False
    ) -> Dict[str, Any]:
        """
        Get complete project data in optimized calls
        
        Instead of: get_project() -> get_trackers() -> get_items() for each tracker
        This does: get_project() + get_trackers() + single CbQL query for all items
        """
        result = {
            'project': None,
            'trackers': [],
            'items': [],
            'wiki_pages': []
        }
        
        # Get project details
        result['project'] = self._make_api_call(
            method='GET',
            endpoint=f'/v3/projects/{project_id}'
        )
        
        if include_trackers:
            # Get all trackers in one call
            result['trackers'] = self._make_api_call(
                method='GET',
                endpoint=f'/v3/projects/{project_id}/trackers'
            )
            
            if include_items and result['trackers'] and isinstance(result['trackers'], list):
                # Get all items across all trackers in ONE CbQL query
                tracker_ids = [t.get('id') for t in result['trackers'] if isinstance(t, dict)]
                if tracker_ids:
                    items_result = self.query_items(
                        project_ids=[project_id],
                        tracker_ids=tracker_ids,
                        max_results=1000
                    )
                    result['items'] = items_result.get('items', [])
        
        if include_wiki:
            # Note: Would need project's wiki page IDs
            # This is a placeholder
            result['wiki_pages'] = []
        
        return result
    
    def get_tracker_complete(
        self,
        tracker_id: int,
        include_items: bool = True,
        include_fields_metadata: bool = False,
        max_items: int = 500
    ) -> Dict[str, Any]:
        """
        Get complete tracker data efficiently
        
        Replaces: get_tracker() -> get_items() -> get_field_metadata() for each field
        With: get_tracker() + single query for all items + cached field metadata
        """
        result = {
            'tracker': None,
            'items': [],
            'fields_metadata': {}
        }
        
        # Get tracker details
        result['tracker'] = self._make_api_call(
            method='GET',
            endpoint=f'/v3/trackers/{tracker_id}'
        )
        
        if include_items:
            # Get all items via CbQL query
            items_result = self.query_items(
                tracker_ids=[tracker_id],
                max_results=max_items
            )
            result['items'] = items_result.get('items', [])
        
        if include_fields_metadata:
            # Get field metadata for important fields
            # These are often needed for test cases
            special_fields = [10002, 10003]  # Test Parameters, Reusable
            for field_id in special_fields:
                try:
                    field_meta = self._make_api_call(
                        method='GET',
                        endpoint=f'/v3/trackers/{tracker_id}/fields/{field_id}',
                        use_cache=True,
                        cache_ttl=3600  # 1 hour - field metadata rarely changes
                    )
                    result['fields_metadata'][field_id] = field_meta
                except Exception as e:
                    print(f"Could not fetch field {field_id}: {e}")
        
        return result
    
    def get_items_batch(
        self,
        item_ids: List[int],
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get multiple items efficiently using CbQL
        
        Instead of: get_item(1), get_item(2), get_item(3)...
        Use: Single CbQL query with item IDs
        """
        if not item_ids:
            return []
        
        # Build CbQL for specific items
        ids_str = ', '.join(map(str, item_ids))
        cbql = f"item.id IN ({ids_str})"
        
        body = {
            'queryString': cbql,
            'page': 1,
            'pageSize': len(item_ids)
        }
        
        result = self._make_api_call(
            method='POST',
            endpoint='/v3/items/query',
            body=body,
            use_cache=True
        )
        
        return result.get('items', [])
    
    def get_item_with_context(
        self,
        item_id: int,
        include_children: bool = False,
        include_relations: bool = False,
        include_parent: bool = False
    ) -> Dict[str, Any]:
        """
        Get item with all context in optimized calls
        
        Replaces: get_item() -> get_children() -> get_relations() -> get_parent()
        With: Parallel calls or smart aggregation
        """
        result = {
            'item': None,
            'children': [],
            'relations': [],
            'parent': None
        }
        
        # Get main item
        result['item'] = self._make_api_call(
            method='GET',
            endpoint=f'/v3/items/{item_id}'
        )
        
        if include_children:
            result['children'] = self._make_api_call(
                method='GET',
                endpoint=f'/v3/items/{item_id}/children'
            )
        
        if include_relations:
            result['relations'] = self._make_api_call(
                method='GET',
                endpoint=f'/v3/items/{item_id}/relations'
            )
        
        if include_parent and result['item'].get('parent'):
            parent_id = result['item']['parent']['id']
            result['parent'] = self._make_api_call(
                method='GET',
                endpoint=f'/v3/items/{parent_id}'
            )
        
        return result
    
    def create_item(
        self,
        tracker_id: int,
        summary: str,
        description: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
        parent_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new tracker item"""
        body = {
            'tracker': {'id': tracker_id},
            'summary': summary
        }
        
        if description:
            body['description'] = description
        
        if fields:
            body.update(fields)
        
        if parent_id:
            body['parent'] = {'id': parent_id}
        
        return self._make_api_call(
            method='POST',
            endpoint=f'/v3/trackers/{tracker_id}/items',
            body=body,
            use_cache=False
        )
    
    def update_item_fields(
        self,
        item_id: int,
        fields: Dict[str, Any],
        clear_cache: bool = True
    ) -> Dict[str, Any]:
        """Update specific fields of an item"""
        result = self._make_api_call(
            method='PUT',
            endpoint=f'/v3/items/{item_id}/fields',
            body=fields,
            use_cache=False
        )
        
        # Clear relevant cache entries
        if clear_cache:
            self._clear_item_cache(item_id)
        
        return result
    
    def bulk_update_items(
        self,
        updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Bulk update multiple items efficiently
        
        updates: [
            {'itemId': 123, 'fields': {'status': 'Done'}},
            {'itemId': 124, 'fields': {'status': 'Done'}}
        ]
        """
        return self._make_api_call(
            method='PUT',
            endpoint='/v3/items/fields',
            body={'updates': updates},
            use_cache=False
        )
    
    def manage_associations(
        self,
        action: Literal['create', 'get', 'delete'],
        from_item_id: Optional[int] = None,
        to_item_id: Optional[int] = None,
        association_id: Optional[int] = None,
        association_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Manage associations between items"""
        
        if action == 'create':
            body = {
                'from': {'id': from_item_id},
                'to': {'id': to_item_id},
                'type': association_type or 'related'
            }
            return self._make_api_call(
                method='POST',
                endpoint='/v3/associations',
                body=body,
                use_cache=False
            )
        
        elif action == 'get':
            return self._make_api_call(
                method='GET',
                endpoint=f'/v3/items/{from_item_id}/relations'
            )
        
        elif action == 'delete':
            return self._make_api_call(
                method='DELETE',
                endpoint=f'/v3/associations/{association_id}',
                use_cache=False
            )
    
    def get_hierarchy_tree(
        self,
        tracker_id: int,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Get tracker hierarchy tree efficiently
        
        Uses /v3/trackers/{trackerId}/children and recursively builds tree
        """
        def build_tree(parent_endpoint: str, depth: int = 0):
            if depth >= max_depth:
                return []
            
            children = self._make_api_call(
                method='GET',
                endpoint=parent_endpoint,
                use_cache=True,
                cache_ttl=600  # 10 minutes
            )
            
            if isinstance(children, list):
                for child in children:
                    if isinstance(child, dict):
                        child['children'] = build_tree(
                            f"/v3/items/{child.get('id')}/children",
                            depth + 1
                        )
            else:
                # Handle error or empty response
                return []
            
            return children
        
        return {
            'tracker_id': tracker_id,
            'tree': build_tree(f'/v3/trackers/{tracker_id}/children')
        }
    
    def convert_wiki_to_html(
        self,
        project_id: int,
        wiki_content: str
    ) -> str:
        """Convert wiki markup to HTML"""
        result = self._make_api_call(
            method='POST',
            endpoint=f'/v3/projects/{project_id}/wiki2html',
            body={'content': wiki_content},
            use_cache=False
        )
        return result.get('html', '')
    
    # ===========================
    # UTILITY METHODS
    # ===========================
    
    def _clear_item_cache(self, item_id: int):
        """Clear cache entries related to an item"""
        keys_to_delete = [
            key for key in self.cache.keys()
            if f'/items/{item_id}' in key
        ]
        for key in keys_to_delete:
            del self.cache[key]
    
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cache, optionally by pattern"""
        if pattern:
            keys_to_delete = [
                key for key in self.cache.keys()
                if pattern in key
            ]
            for key in keys_to_delete:
                del self.cache[key]
        else:
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        cache_hit_rate = (
            self.stats['cache_hits'] / 
            (self.stats['cache_hits'] + self.stats['cache_misses'])
            if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0
            else 0
        )
        
        return {
            **self.stats,
            'cache_hit_rate': f"{cache_hit_rate:.2%}",
            'cache_size': len(self.cache),
            'remaining_calls_this_minute': self.rate_limiter.get_remaining_calls()
        }
    
    def print_stats(self):
        """Print usage statistics"""
        stats = self.get_stats()
        print("\nCodebeamer Smart Tool Statistics:")
        print(f"   API Calls Made: {stats['api_calls']}")
        print(f"   Cache Hits: {stats['cache_hits']}")
        print(f"   Cache Misses: {stats['cache_misses']}")
        print(f"   Cache Hit Rate: {stats['cache_hit_rate']}")
        print(f"   Cache Size: {stats['cache_size']} entries")
        print(f"   Remaining Calls: {stats['remaining_calls_this_minute']}/minute")


# ===========================
# USAGE EXAMPLES
# ===========================

def example_usage():
    """Example usage of the CodebeamerSmartTool"""
    
    # Initialize the tool
    tool = CodebeamerSmartTool(
        base_url="https://your-codebeamer-instance.com",
        api_key="your-api-key",
        max_calls_per_minute=60,
        default_cache_ttl=300
    )
    
    # Example 1: Query items efficiently (replaces multiple API calls)
    print("\n=== Example 1: Efficient Query ===")
    bugs = tool.query_items(
        project_ids=[123, 456],
        item_types=['Bug'],
        statuses=['Open', 'In Progress'],
        include_fields=['summary', 'assignee', 'priority']
    )
    print(f"Found {len(bugs.get('items', []))} bugs")
    
    # Example 2: Get complete project data
    print("\n=== Example 2: Complete Project Data ===")
    project_data = tool.get_project_complete(
        project_id=123,
        include_trackers=True,
        include_items=True
    )
    print(f"Project: {project_data['project'].get('name')}")
    print(f"Trackers: {len(project_data['trackers'])}")
    print(f"Total Items: {len(project_data['items'])}")
    
    # Example 3: Batch get items (instead of individual calls)
    print("\n=== Example 3: Batch Get Items ===")
    item_ids = [100, 101, 102, 103, 104]
    items = tool.get_items_batch(item_ids)
    print(f"Retrieved {len(items)} items in one call")
    
    # Example 4: Get item with full context
    print("\n=== Example 4: Item with Context ===")
    item_context = tool.get_item_with_context(
        item_id=100,
        include_children=True,
        include_relations=True
    )
    print(f"Item: {item_context['item'].get('summary')}")
    print(f"Children: {len(item_context['children'])}")
    print(f"Relations: {len(item_context['relations'])}")
    
    # Example 5: Create and update items
    print("\n=== Example 5: Create Item ===")
    new_item = tool.create_item(
        tracker_id=50,
        summary="New bug found",
        description="Description here",
        fields={'priority': 'High', 'severity': 'Critical'}
    )
    print(f"Created item: {new_item.get('id')}")
    
    # Example 6: Bulk update
    print("\n=== Example 6: Bulk Update ===")
    tool.bulk_update_items([
        {'itemId': 100, 'fields': {'status': 'Done'}},
        {'itemId': 101, 'fields': {'status': 'Done'}},
        {'itemId': 102, 'fields': {'status': 'Done'}}
    ])
    print("Bulk update completed")
    
    # Print statistics
    tool.print_stats()


if __name__ == "__main__":
    example_usage()
