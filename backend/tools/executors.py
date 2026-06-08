"""Session 2：7 个工具的执行函数 + execute_readonly_sql 安全校验。"""
from db.crm import crm_query
from db.erp import erp_query, ERP_ORG_ID

FORBIDDEN_TABLES = ['audit_logs', 'ai_call_logs', 'login_attempts', 'alembic_version']
FORBIDDEN_COLS = ['password_hash']


def execute_tool(name, params):
    handlers = {
        'query_sales_summary': query_sales_summary,
        'query_sales_orders': query_sales_orders,
        'query_customer_info': query_customer_info,
        'query_crm_deals': query_crm_deals,
        'query_sales_targets': query_sales_targets,
        'query_stock_levels': query_stock_levels,
        'execute_readonly_sql': execute_readonly_sql,
    }
    fn = handlers.get(name)
    if not fn:
        return {'error': f'未知工具: {name}'}
    try:
        return fn(**params)
    except Exception as e:
        return {'error': str(e)}


def execute_readonly_sql(sql: str, database: str):
    sql_up = sql.strip().upper()
    if not sql_up.startswith('SELECT'):
        return {'error': '只允许 SELECT'}
    for t in FORBIDDEN_TABLES:
        if t.upper() in sql_up:
            return {'error': f'禁止查询 {t}'}
    for c in FORBIDDEN_COLS:
        if c.upper() in sql_up:
            return {'error': f'禁止查询 {c}'}
    if 'LIMIT' not in sql_up:
        sql = sql.rstrip(';') + ' LIMIT 200'
    fn = crm_query if database == 'crm_os' else erp_query
    rows = fn(sql)
    return {'rows': rows, 'count': len(rows)}


def query_sales_summary(start_date, end_date, customer_name=None, group_by='month'):
    gmap = {'month': 'DATE_FORMAT(so.business_date,"%%Y-%%m")',
            'customer': 'c.name', 'warehouse': 'w.name'}
    gexpr = gmap.get(group_by, gmap['month'])
    where = '''WHERE so.organization_id = %s
               AND so.business_date BETWEEN %s AND %s
               AND so.is_active = 1 AND so.deleted_at IS NULL
               AND so.status NOT IN ('DRAFT','CANCELLED')'''
    params = [ERP_ORG_ID, start_date, end_date]
    if customer_name:
        where += ' AND c.name LIKE %s'
        params.append(f'%{customer_name}%')
    sql = f'''SELECT {gexpr} AS dimension,
               COUNT(so.id) AS order_count,
               SUM(so.base_currency_amount) AS total_sales
        FROM sales_orders so
        JOIN customers c ON so.customer_id = c.id
        JOIN warehouses w ON so.warehouse_id = w.id
        {where} GROUP BY {gexpr} ORDER BY total_sales DESC LIMIT 50'''
    return {'data': erp_query(sql, params)}


def query_sales_orders(customer_name=None, status=None, start_date=None, end_date=None, limit=20):
    where = '''WHERE so.organization_id = %s
               AND so.is_active = 1 AND so.deleted_at IS NULL'''
    params = [ERP_ORG_ID]
    if customer_name:
        where += ' AND c.name LIKE %s'
        params.append(f'%{customer_name}%')
    if status:
        where += ' AND so.status = %s'
        params.append(status)
    if start_date:
        where += ' AND so.business_date >= %s'
        params.append(start_date)
    if end_date:
        where += ' AND so.business_date <= %s'
        params.append(end_date)
    sql = f'''SELECT so.document_no, so.status, c.name AS customer, w.name AS warehouse,
               so.business_date, so.currency, so.total_incl_tax, so.base_currency_amount
        FROM sales_orders so
        JOIN customers c ON so.customer_id = c.id
        JOIN warehouses w ON so.warehouse_id = w.id
        {where} ORDER BY so.business_date DESC LIMIT %s'''
    params.append(limit)
    return {'data': erp_query(sql, params)}


def query_customer_info(customer_name=None, customer_code=None):
    where = 'WHERE c.organization_id = %s AND c.is_active = 1 AND c.deleted_at IS NULL'
    params = [ERP_ORG_ID]
    if customer_code:
        where += ' AND c.code = %s'
        params.append(customer_code)
    elif customer_name:
        where += ' AND c.name LIKE %s'
        params.append(f'%{customer_name}%')
    sql = f'''SELECT c.id, c.code, c.name, c.name_zh, c.customer_type, c.currency, c.credit_limit
        FROM customers c {where} LIMIT 5'''
    customers = erp_query(sql, params)
    for cust in customers:
        history_sql = '''SELECT COUNT(*) AS order_count, SUM(base_currency_amount) AS total_amount
            FROM sales_orders
            WHERE organization_id = %s AND customer_id = %s
              AND is_active = 1 AND deleted_at IS NULL
              AND status NOT IN ('DRAFT','CANCELLED')'''
        history = erp_query(history_sql, [ERP_ORG_ID, cust['id']])
        cust['purchase_summary'] = history[0] if history else None
    return {'data': customers}


def query_crm_deals(status=None, assigned_to_name=None, min_amount=None, limit=20):
    where = 'WHERE d.deleted_at IS NULL'
    params = []
    if status:
        where += ' AND d.status=%s'
        params.append(status)
    if assigned_to_name:
        where += ' AND u.name LIKE %s'
        params.append(f'%{assigned_to_name}%')
    if min_amount:
        where += ' AND d.amount>=%s'
        params.append(min_amount)
    sql = f'''SELECT d.title,d.status,d.priority,d.amount,
               c.name AS contact,c.company,u.name AS owner,
               d.created_at,d.won_at
        FROM deals d
        JOIN contacts c ON d.contact_id=c.id
        LEFT JOIN users u ON d.assigned_to=u.id
        {where} ORDER BY d.amount DESC LIMIT %s'''
    params.append(limit)
    return {'data': crm_query(sql, params)}


def query_sales_targets(user_name=None, year=None, month=None):
    where = 'WHERE u.is_active = 1'
    params = []
    if user_name:
        where += ' AND u.name LIKE %s'
        params.append(f'%{user_name}%')
    if year:
        where += ' AND st.year = %s'
        params.append(year)
    if month:
        where += ' AND st.month = %s'
        params.append(month)
    sql = f'''SELECT st.year, st.month, u.name AS sales_rep, st.target_amount, st.target_count
        FROM sales_targets st
        JOIN users u ON st.user_id = u.id
        {where} ORDER BY st.year DESC, st.month DESC LIMIT 50'''
    targets = crm_query(sql, params)
    for t in targets:
        actual_sql = '''SELECT COUNT(*) AS won_count, SUM(d.amount) AS won_amount
            FROM deals d
            JOIN users u ON d.assigned_to = u.id
            WHERE u.name = %s AND d.status = 'won' AND d.deleted_at IS NULL
              AND YEAR(d.won_at) = %s AND MONTH(d.won_at) = %s'''
        actual = crm_query(actual_sql, [t['sales_rep'], t['year'], t['month']])
        t['actual'] = actual[0] if actual else None
    return {'data': targets}


def query_stock_levels(sku_name=None, sku_code=None, warehouse_name=None, low_stock_only=False):
    where = 'WHERE sk.organization_id=%s AND sk.is_active=1 AND sk.deleted_at IS NULL'
    params = [ERP_ORG_ID]
    if sku_name:
        where += " AND (sk.name LIKE %s OR sk.name_zh LIKE %s)"
        params.append(f'%{sku_name}%')
        params.append(f'%{sku_name}%')
    if sku_code:
        where += " AND sk.code=%s"
        params.append(sku_code)
    if warehouse_name:
        where += " AND wh.name LIKE %s"
        params.append(f'%{warehouse_name}%')
    if low_stock_only:
        where += " AND st.available <= sk.reorder_point"
    sql = f'''SELECT sk.code,sk.name,wh.name AS warehouse,
               st.on_hand,st.reserved,st.available,
               sk.reorder_point,sk.safety_stock
        FROM stocks st
        JOIN skus sk ON st.sku_id=sk.id
        JOIN warehouses wh ON st.warehouse_id=wh.id
        {where} ORDER BY st.available ASC LIMIT 100'''
    return {'data': erp_query(sql, params)}
