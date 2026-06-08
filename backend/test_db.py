"""Session 1 验收测试：验证 CRM 和 ERP 数据库均可连接并查询。"""
from db.crm import crm_query
from db.erp import erp_query, ERP_ORG_ID

print('=== CRM (crm_os) ===')
crm_rows = crm_query(
    'SELECT id, name, company FROM contacts WHERE deleted_at IS NULL LIMIT 1'
)
print(crm_rows)
assert crm_rows, 'crm_os 查询返回空结果'

print('=== ERP (erp_os) ===')
erp_rows = erp_query(
    'SELECT id, code, name FROM customers '
    'WHERE organization_id = %s AND is_active = 1 AND deleted_at IS NULL LIMIT 1',
    [ERP_ORG_ID]
)
print(erp_rows)
assert erp_rows, 'erp_os 查询返回空结果'

print('\n两个数据库连接与查询均成功。')
