"""Session 2 验收测试：每个工具各调用一次，确认返回非空数据且无 SQL 错误。"""
from tools.executors import execute_tool

CASES = [
    ('query_sales_summary', {'start_date': '2025-12-01', 'end_date': '2026-06-08', 'group_by': 'month'}),
    ('query_sales_orders', {'start_date': '2025-12-01', 'end_date': '2026-06-08', 'limit': 5}),
    ('query_customer_info', {'customer_name': 'Kopitiam'}),
    ('query_crm_deals', {'status': 'won', 'limit': 5}),
    ('query_sales_targets', {'user_name': 'Marcus Johnson'}),
    ('query_stock_levels', {'warehouse_name': 'Kuala Lumpur'}),
    ('execute_readonly_sql', {'sql': "SELECT id, name FROM customers WHERE organization_id = 1 LIMIT 3", 'database': 'erp_os'}),
]

for name, params in CASES:
    print(f'=== {name}({params}) ===')
    result = execute_tool(name, params)
    assert 'error' not in result, f'{name} 返回错误: {result.get("error")}'
    rows = result.get('data') or result.get('rows')
    assert rows, f'{name} 返回空结果'
    print(f'返回 {len(rows)} 条，示例: {rows[0]}')

print('\n全部 7 个工具均返回非空数据，无 SQL 错误。')
