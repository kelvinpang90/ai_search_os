"""Session 2：7 个工具的 JSON Schema 定义（供 Claude Tool Use 使用）。"""

TOOLS = [
    {
        "name": "query_sales_summary",
        "description": "统计销售额。日期字段用 business_date，金额用 base_currency_amount。"
                       "自动过滤 DRAFT/CANCELLED 订单。",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
                "customer_name": {"type": "string", "description": "客户 name 模糊匹配，可选"},
                "group_by": {"type": "string", "enum": ["customer", "month", "warehouse"],
                             "description": "分组维度，默认 month"}
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "query_sales_orders",
        "description": "查询销售订单列表，支持按客户名称、订单状态、日期范围筛选。"
                       "自动过滤 organization_id=1、is_active=1、deleted_at IS NULL。",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "客户名称模糊匹配，可选"},
                "status": {"type": "string",
                           "enum": ["DRAFT", "CONFIRMED", "PARTIAL_SHIPPED", "FULLY_SHIPPED",
                                    "INVOICED", "PAID", "CANCELLED"],
                           "description": "订单状态，可选"},
                "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD，可选"},
                "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD，可选"},
                "limit": {"type": "integer", "description": "返回条数，默认 20"}
            }
        }
    },
    {
        "name": "query_customer_info",
        "description": "查询客户档案信息，并附带其采购历史汇总（订单数与累计金额，"
                       "金额按 base_currency_amount 统计）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "客户名称模糊匹配，可选"},
                "customer_code": {"type": "string", "description": "客户编号精确匹配，可选"}
            }
        }
    },
    {
        "name": "query_crm_deals",
        "description": "查询 CRM 商机。status 枚举：lead/following/negotiating/won/lost。",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string",
                           "enum": ["lead", "following", "negotiating", "won", "lost"]},
                "assigned_to_name": {"type": "string", "description": "负责销售员姓名模糊匹配"},
                "min_amount": {"type": "number", "description": "最低金额筛选"},
                "limit": {"type": "integer", "description": "返回条数，默认 20"}
            }
        }
    },
    {
        "name": "query_sales_targets",
        "description": "查询销售员的销售目标，并与同期商机实际成交金额（status=won，"
                       "按 won_at 所属年月统计）对比，用于评估达成情况。",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_name": {"type": "string", "description": "销售员姓名模糊匹配，可选"},
                "year": {"type": "integer", "description": "年份，可选"},
                "month": {"type": "integer", "description": "月份 1-12，可选"}
            }
        }
    },
    {
        "name": "query_stock_levels",
        "description": "查询库存。available 是虚拟列(on_hand-reserved-quality_hold)。"
                       "low_stock_only=true 返回 available <= reorder_point 的商品。",
        "input_schema": {
            "type": "object",
            "properties": {
                "sku_name": {"type": "string", "description": "商品名称模糊匹配"},
                "sku_code": {"type": "string", "description": "SKU 编号精确匹配"},
                "warehouse_name": {"type": "string", "description": "仓库名称"},
                "low_stock_only": {"type": "boolean", "description": "仅返回低库存商品"}
            }
        }
    },
    {
        "name": "execute_readonly_sql",
        "description": "执行只读 SQL。仅 SELECT。crm_os 和 erp_os 是独立数据库，"
                       "不能跨库 JOIN。ERP 查询必须包含 organization_id = 1。",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SELECT 语句"},
                "database": {"type": "string", "enum": ["crm_os", "erp_os"]}
            },
            "required": ["sql", "database"]
        }
    }
]
