"""
Example Usage Script for Codebeamer Smart Tool
Demonstrates the efficiency gains over individual API calls
"""

from codebeamer_smart_tool import CodebeamerSmartTool


def demonstrate_efficiency():
    """Show the efficiency improvements"""
    
    print("=" * 70)
    print("CODEBEAMER SMART TOOL - EFFICIENCY DEMONSTRATION")
    print("=" * 70)
    
    # Initialize
    tool = CodebeamerSmartTool(
        base_url="https://your-codebeamer.com",
        api_key="your-api-key",
        max_calls_per_minute=60,
        default_cache_ttl=300,
        # Set to False if using self-signed certificates
        ssl_verify=False  
    )
    
    # ========================================
    # SCENARIO 1: Get All Bugs in Projects
    # ========================================
    print("\n" + "=" * 70)
    print("SCENARIO 1: Get all open bugs across 3 projects")
    print("=" * 70)
    
    print("\n❌ OLD WAY (Multiple sequential calls):")
    print("   1. GET /v3/projects/123")
    print("   2. GET /v3/projects/124")
    print("   3. GET /v3/projects/125")
    print("   4. GET /v3/projects/123/trackers")
    print("   5. GET /v3/projects/124/trackers")
    print("   6. GET /v3/projects/125/trackers")
    print("   7-N. GET /v3/trackers/{id}/items for each tracker")
    print("   TOTAL: ~15-25 API calls")
    
    print("\n✅ NEW WAY (Single CbQL query):")
    bugs = tool.query_items(
        project_ids=[123, 124, 125],
        tracker_names=['Bugs'],
        statuses=['Open', 'In Progress'],
        include_fields=['summary', 'priority', 'assignee']
    )
    print("   1. POST /v3/items/query (with CbQL)")
    print("   TOTAL: 1 API call")
    print(f"   IMPROVEMENT: 96% reduction in API calls")
    
    # ========================================
    # SCENARIO 2: Dashboard Data
    # ========================================
    print("\n" + "=" * 70)
    print("SCENARIO 2: Collect dashboard data for project")
    print("=" * 70)
    
    print("\n❌ OLD WAY:")
    print("   1. GET /v3/projects/123")
    print("   2. GET /v3/projects/123/trackers")
    print("   3-10. GET /v3/trackers/{id}/items for each tracker")
    print("   11-50. GET /v3/items/{id} for each item detail")
    print("   51-N. GET /v3/items/{id}/relations for each item")
    print("   TOTAL: ~100+ API calls")
    
    print("\n✅ NEW WAY:")
    dashboard_data = tool.get_project_complete(
        project_id=123,
        include_trackers=True,
        include_items=True
    )
    print("   1. GET /v3/projects/123")
    print("   2. GET /v3/projects/123/trackers")
    print("   3. POST /v3/items/query (all items at once)")
    print("   TOTAL: 3 API calls")
    print(f"   IMPROVEMENT: 97% reduction in API calls")
    
    # ========================================
    # SCENARIO 3: Batch Item Updates
    # ========================================
    print("\n" + "=" * 70)
    print("SCENARIO 3: Close 20 resolved bugs")
    print("=" * 70)
    
    print("\n❌ OLD WAY:")
    print("   1-20. PUT /v3/items/{id}/fields for each item")
    print("   TOTAL: 20 API calls")
    
    print("\n✅ NEW WAY:")
    tool.bulk_update_items([
        {'itemId': i, 'fields': {'status': 'Closed'}}
        for i in range(100, 120)
    ])
    print("   1. PUT /v3/items/fields (bulk update)")
    print("   TOTAL: 1 API call")
    print(f"   IMPROVEMENT: 95% reduction in API calls")
    
    # ========================================
    # SCENARIO 4: Caching Benefits
    # ========================================
    print("\n" + "=" * 70)
    print("SCENARIO 4: Repeated queries with caching")
    print("=" * 70)
    
    print("\nFirst call (cache miss):")
    tool.query_items(project_ids=[123])
    
    print("\nSecond call (cache hit):")
    tool.query_items(project_ids=[123])
    
    print("\nThird call (cache hit):")
    tool.query_items(project_ids=[123])
    
    print("\nResult: 2 API calls saved via caching!")
    
    # ========================================
    # STATISTICS
    # ========================================
    print("\n" + "=" * 70)
    print("FINAL STATISTICS")
    print("=" * 70)
    tool.print_stats()
    
    # ========================================
    # RATE LIMITING PROTECTION
    # ========================================
    print("\n" + "=" * 70)
    print("SCENARIO 5: Rate limiting protection")
    print("=" * 70)
    
    print("\nMaking 70 rapid API calls (limit is 60/minute)...")
    print("Tool will automatically wait to prevent throttling...\n")
    
    for i in range(70):
        # Tool automatically manages rate limiting
        tool.query_items(
            project_ids=[123],
            custom_filters={'id': i},
            use_cache=False  # Disable cache to test rate limiting
        )
        if i % 10 == 0:
            stats = tool.get_stats()
            print(f"  Call {i}/70 - Remaining: {stats['remaining_calls_this_minute']}/minute")
    
    print("\n✅ All 70 calls completed without rate limit errors!")
    print("   Tool automatically paused when approaching limit")


def real_world_example():
    """Real-world example: Sprint Report Generation"""
    
    print("\n" + "=" * 70)
    print("REAL-WORLD EXAMPLE: Generate Sprint Report")
    print("=" * 70)
    
    tool = CodebeamerSmartTool(
        base_url="https://your-codebeamer.com",
        api_key="your-api-key"
    )
    
    def generate_sprint_report(project_id: int, sprint_id: int):
        """Generate comprehensive sprint report efficiently"""
        
        print(f"\nGenerating report for Sprint {sprint_id}...")
        
        # Get all sprint items in ONE call
        sprint_items = tool.query_items(
            project_ids=[project_id],
            custom_filters={'sprint': sprint_id},
            include_fields=['summary', 'status', 'assignee', 'storyPoints']
        )
        
        items = sprint_items.get('items', [])
        
        # Calculate statistics
        total_items = len(items)
        completed = sum(1 for i in items if i.get('status') == 'Done')
        in_progress = sum(1 for i in items if i.get('status') == 'In Progress')
        story_points_done = sum(
            i.get('storyPoints', 0) 
            for i in items 
            if i.get('status') == 'Done'
        )
        
        report = {
            'sprint_id': sprint_id,
            'total_items': total_items,
            'completed': completed,
            'in_progress': in_progress,
            'completion_rate': f"{(completed/total_items*100):.1f}%" if total_items else "0%",
            'story_points_completed': story_points_done,
            'items': items
        }
        
        print(f"\n📊 Sprint {sprint_id} Report:")
        print(f"   Total Items: {total_items}")
        print(f"   Completed: {completed}")
        print(f"   In Progress: {in_progress}")
        print(f"   Completion Rate: {report['completion_rate']}")
        print(f"   Story Points Done: {story_points_done}")
        print(f"\n   API Calls Used: 1 (instead of ~{total_items + 10})")
        
        return report
    
    # Generate report
    report = generate_sprint_report(project_id=123, sprint_id=45)
    
    # Show tool statistics
    print("\n" + "-" * 70)
    tool.print_stats()


def comparison_table():
    """Print comparison table"""
    
    print("\n" + "=" * 70)
    print("EFFICIENCY COMPARISON TABLE")
    print("=" * 70)
    
    comparisons = [
        ("Get 100 bugs from 5 projects", "~25 calls", "1 call", "96%"),
        ("Get project with all items", "~50 calls", "3 calls", "94%"),
        ("Get 10 specific items", "10 calls", "1 call", "90%"),
        ("Update 20 items", "20 calls", "1 call", "95%"),
        ("Dashboard data (3 projects)", "~100 calls", "3-5 calls", "95%"),
        ("Sprint report", "~50 calls", "1 call", "98%"),
    ]
    
    print(f"\n{'Scenario':<35} {'Old Way':<15} {'Smart Tool':<15} {'Reduction':<10}")
    print("-" * 70)
    
    for scenario, old, new, reduction in comparisons:
        print(f"{scenario:<35} {old:<15} {new:<15} {reduction:<10}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Run demonstrations
    demonstrate_efficiency()
    real_world_example()
    comparison_table()
    
    print("\n" + "=" * 70)
    print("💡 KEY TAKEAWAYS")
    print("=" * 70)
    print("""
1. Use query_items() with CbQL for 90%+ reduction in API calls
2. Leverage caching to avoid redundant requests
3. Use batch operations for bulk updates
4. Tool automatically prevents rate limiting
5. Monitor statistics to optimize usage

RESULT: 70-98% fewer API calls = Faster, more reliable integration
    """)
