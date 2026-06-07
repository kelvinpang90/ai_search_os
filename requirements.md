# CRM & ERP AI 智能助手系统 — 开发文档 v1.3

> 含完整 Schema · Session 分步执行计划 · 常用查询 · 语音输入  
> 基于 Claude API Tool Use · Python FastAPI · MySQL · 网页聊天界面

---

## 1. 项目概述

### 1.1 目标
为现有 CRM 和 ERP 系统构建一个独立的网页 AI 助手 Demo，允许用户通过自然语言提问，直接获取销售、订单、库存等业务数据，向潜在客户展示产品的 AI 能力。

### 1.2 核心能力
- 自然语言输入，无需学习 SQL 或操作界面
- 跨 CRM（crm_os）和 ERP（erp_os）联合查询
- 实时查询 MySQL 数据库，返回真实业务数据
- 支持销售额统计、客户分析、商机追踪、库存查询等场景


### 1.3 技术栈
| 层级 | 技术选型 | 说明 |
| --- | --- | --- |
| 前端 | HTML / CSS / JavaScript | 独立网页聊天界面，单文件 |
| 后端 | Python + FastAPI | API 服务，对接 Claude 和数据库 |
| AI 模型 | Claude API (claude-sonnet-4-6) | Tool Use 模式，决策查询策略 |
| 数据库 | MySQL (crm_os + erp_os) | 两个独立数据库，只读访问 |
| 驱动 | PyMySQL | Python 连接 MySQL |

## 2. 系统架构

### 2.1 整体流程
| 用户输入自然语言问题 ↓  HTTP POST /chat Python 后端 (FastAPI) ↓  问题 + 工具定义 → Claude API Claude API (Tool Use 决策) ↓  返回 tool_use 指令 Python 后端执行工具 → 查询 MySQL ↓  查询结果还给 Claude Claude 生成自然语言回答 ↓  返回前端展示 用户看到清晰的中文回答 |
| --- |

### 2.2 Tool Use 步骤
- 前端发送用户消息到 POST /chat
- 后端将消息 + 工具定义发给 Claude API
- Claude 决定调用哪个工具及参数，返回 tool_use
- 后端执行工具，查询 MySQL，返回结果
- Claude 生成自然语言回答（如需多步则重复 3-4）
- 后端返回最终文本给前端


## 3. 关键开发约定
以下约定是开发中的硬性规则，Claude Code 必须严格遵守。


### 3.1 organization_id
| ⚠  所有 ERP 查询必须加 organization_id 过滤 ERP 是多租户设计，所有主表（sales_orders、customers、stocks、skus 等）都有 organization_id 字段。 本系统只有一个组织，固定使用 organization_id = 1。 所有 ERP SQL 查询必须在 WHERE 条件中包含： 此规则同样适用于 execute_readonly_sql 兜底工具。 |
| --- |

### 3.2 金额字段
| 统一使用 base_currency_amount（本位币金额） ERP 销售订单支持多币种（MYR、USD 等）。展示和统计金额时，统一使用 base_currency_amount，不使用 total_incl_tax。 如需显示原币种金额，同时返回 currency 和 total_incl_tax 字段。 |
| --- |

### 3.3 软删除与有效性过滤
| ⚠  所有查询必须过滤软删除和无效记录 两个数据库均使用软删除（deleted_at）和有效标记（is_active）。每条查询都必须包含以下过滤条件： sales_orders 额外过滤已取消的订单： |
| --- |

### 3.4 两个数据库是独立实例
| crm_os 和 erp_os 是两个独立的 MySQL 数据库，不能在同一条 SQL 里跨库 JOIN。 跨系统联合查询的正确做法： 先查 ERP 获取 customer_id 列表 再查 CRM 用 company 名称匹配 在 Python 代码层合并结果 Claude 在 System Prompt 里已被告知这一限制，会自动拆分为多次工具调用。 |
| --- |

### 3.5 对话历史长度控制
| 前端发送的 history 数组会随对话增长，超过一定长度会撑爆 Claude 的 context window。 后端需要对 history 做截断处理： |
| --- |

### 3.6 敏感字段禁止查询
| 以下字段和表禁止出现在任何工具返回结果中： crm_os.users.password_hash erp_os.audit_logs（整张表） erp_os.ai_call_logs（整张表） erp_os.login_attempts（整张表） 在 System Prompt 中明确告知 Claude，execute_readonly_sql 工具的黑名单检查中也要拦截对这些表的查询。 |
| --- |

### 3.7 CRM 与 ERP 用户系统不同
| CRM users.id 是 varchar(36) UUID，ERP users.id 是 int 自增。两套用户系统相互独立，不能直接关联。 Demo 场景中不需要跨系统用户关联，保持两套独立即可。 |
| --- |

## 4. 数据库 Schema

### 4.1 CRM 数据库 (crm_os)
**4.1.1 deals（商机）**
| 字段名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| id | varchar(36) | 否 | 主键 UUID |
| contact_id | varchar(36) | 否 | 关联 contacts.id |
| title | varchar(200) | 是 | 商机标题 |
| status | enum | 否 | lead / following / negotiating / won / lost |
| priority | enum | 否 | high / mid / low |
| amount | decimal(15,2) | 否 | 商机预估金额 |
| assigned_to | varchar(36) | 是 | 负责销售员 → users.id |
| won_at | datetime | 是 | 成交时间（status=won 时有值） |
| deleted_at | datetime | 是 | 软删除，IS NULL 表示有效 |
| created_at | datetime | 否 | 创建时间 |
| updated_at | datetime | 否 | 更新时间 |


**4.1.2 contacts（联系人）**
| 字段名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| id | varchar(36) | 否 | 主键 UUID |
| name | varchar(100) | 否 | 联系人姓名 |
| company | varchar(200) | 是 | 公司名 |
| industry | varchar(50) | 是 | 行业 |
| email | varchar(200) | 是 | 邮箱 |
| phone | varchar(30) | 是 | 电话 |
| assigned_to | varchar(36) | 是 | 负责销售员 → users.id |
| last_contact | date | 是 | 最近联系日期 |
| tags | json | 是 | 标签数组 |
| is_archived | smallint | 否 | 0=正常，1=已归档，查询过滤 is_archived=0 |
| deleted_at | datetime | 是 | 软删除 |
| created_at | datetime | 否 | 创建时间 |


**4.1.3 sales_targets（销售目标）**
| 字段名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| id | varchar(36) | 否 | 主键 UUID |
| user_id | varchar(36) | 否 | 销售员 → users.id |
| year | smallint | 否 | 年份 |
| month | smallint | 否 | 月份（1-12） |
| target_amount | decimal(15,2) | 否 | 目标金额 |
| target_count | int | 否 | 目标订单数 |


**4.1.4 activities（跟进记录）**
| 字段名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| id | varchar(36) | 否 | 主键 UUID |
| contact_id | varchar(36) | 否 | 关联联系人 |
| deal_id | varchar(36) | 否 | 关联商机 |
| user_id | varchar(36) | 否 | 操作销售员 |
| type | enum | 否 | phone / email / meeting / WhatsApp / other / status change |
| content | text | 是 | 跟进内容 |
| follow_date | datetime | 否 | 跟进时间 |


**4.1.5 users（CRM 销售员）**
| 字段名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| id | varchar(36) | 否 | 主键 UUID（注意是字符串，非整数） |
| name | varchar(100) | 否 | 姓名 |
| email | varchar(200) | 否 | 邮箱 |
| password_hash | varchar(255) | 否 | 禁止查询此字段 |
| role | enum | 否 | admin / manager / sales |
| manager_id | varchar(36) | 是 | 上级 → users.id |
| is_active | tinyint(1) | 否 | 是否在职 |

### 4.2 ERP 数据库 (erp_os)
| ⚠  所有 ERP 表查询必须加 organization_id = 1 |
| --- |


**4.2.1 sales_orders（销售订单）**
| 字段名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| id | int | 否 | 主键，自增 |
| organization_id | int | 否 | 组织 ID，固定 = 1 |
| document_no | varchar(32) | 否 | 单号 |
| status | enum | 否 | DRAFT / CONFIRMED / PARTIAL_SHIPPED / FULLY_SHIPPED / INVOICED / PAID / CANCELLED |
| customer_id | int | 否 | 客户 → customers.id |
| warehouse_id | int | 否 | 仓库 → warehouses.id |
| business_date | date | 否 | 下单日期（注意不是 order_date） |
| currency | varchar(3) | 否 | 交易货币代码 |
| total_incl_tax | decimal(18,4) | 否 | 含税总额（原币种） |
| base_currency_amount | decimal(18,4) | 否 | 本位币金额（统计用此字段） |
| is_active | tinyint(1) | 否 | 过滤条件：= 1 |
| deleted_at | datetime | 是 | 过滤条件：IS NULL |
| created_at | datetime | 否 | 创建时间 |


**4.2.2 sales_order_lines（销售订单明细）**
| 字段名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| id | int | 否 | 主键 |
| sales_order_id | int | 否 | 关联订单 |
| sku_id | int | 否 | 商品 → skus.id |
| qty_ordered | decimal(18,4) | 否 | 订购数量 |
| qty_shipped | decimal(18,4) | 否 | 已发货数量 |
| unit_price_excl_tax | decimal(18,4) | 否 | 不含税单价 |
| line_total_incl_tax | decimal(18,4) | 否 | 行含税金额 |


**4.2.3 customers（ERP 客户）**
| 字段名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| id | int | 否 | 主键（注意是整数，与 CRM users.id 不同） |
| organization_id | int | 否 | 固定 = 1 |
| code | varchar(32) | 否 | 客户编号 |
| name | varchar(200) | 否 | 客户名称（英文） |
| name_zh | varchar(200) | 是 | 客户名称（中文） |
| customer_type | enum | 否 | B2B / B2C |
| currency | varchar(3) | 否 | 默认货币 |
| credit_limit | decimal(18,4) | 否 | 信用额度 |
| is_active | tinyint(1) | 否 | 过滤：= 1 |
| deleted_at | datetime | 是 | 过滤：IS NULL |


**4.2.4 stocks（库存）**
| 字段名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| sku_id | int | 否 | 商品（与 warehouse_id 联合唯一） |
| warehouse_id | int | 否 | 仓库 |
| on_hand | decimal(18,4) | 否 | 在库数量 |
| reserved | decimal(18,4) | 否 | 已预留 |
| quality_hold | decimal(18,4) | 否 | 质检扣留 |
| available | decimal(18,4) | 是 | 可用量（虚拟列 = on_hand - reserved - quality_hold） |
| avg_cost | decimal(18,4) | 否 | 加权平均成本 |


**4.2.5 skus（商品）**
| 字段名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| id | int | 否 | 主键 |
| organization_id | int | 否 | 固定 = 1 |
| code | varchar(64) | 否 | SKU 编号 |
| name | varchar(200) | 否 | 商品名称（英文） |
| name_zh | varchar(200) | 是 | 商品名称（中文） |
| unit_price_excl_tax | decimal(18,4) | 否 | 不含税单价 |
| safety_stock | decimal(18,4) | 否 | 安全库存 |
| reorder_point | decimal(18,4) | 否 | 补货触发点 |
| is_active | tinyint(1) | 否 | 过滤：= 1 |
| deleted_at | datetime | 是 | 过滤：IS NULL |


**4.2.6 invoices（发票）**
| 字段名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| id | int | 否 | 主键 |
| organization_id | int | 否 | 固定 = 1 |
| document_no | varchar(32) | 否 | 发票号 |
| status | enum | 否 | DRAFT / SUBMITTED / VALIDATED / FINAL / REJECTED / CANCELLED |
| customer_id | int | 否 | 客户 |
| business_date | date | 否 | 开票日期 |
| due_date | date | 是 | 到期日 |
| total_incl_tax | decimal(18,4) | 否 | 含税总额 |
| paid_amount | decimal(18,4) | 否 | 已收金额 |


**4.2.7 payments（收款）**
| 字段名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| id | int | 否 | 主键 |
| organization_id | int | 否 | 固定 = 1 |
| direction | enum | 否 | INBOUND=收款 / OUTBOUND=付款 |
| customer_id | int | 是 | 客户（收款时） |
| business_date | date | 否 | 收款日期 |
| method | enum | 否 | CASH / BANK_TRANSFER / FPX / DUITNOW / CREDIT_CARD / CHEQUE / OTHER |
| amount | decimal(18,4) | 否 | 收款金额 |
| unallocated_amount | decimal(18,4) | 否 | 未核销金额 |


**4.2.8 warehouses（仓库）**
| 字段名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| id | int | 否 | 主键 |
| organization_id | int | 否 | 固定 = 1 |
| name | varchar(120) | 否 | 仓库名称 |
| type | enum | 否 | MAIN / BRANCH / TRANSIT / QUARANTINE |
| is_active | tinyint(1) | 否 | 过滤：= 1 |
| deleted_at | datetime | 是 | 过滤：IS NULL |

### 4.3 关键外键关系
| 源表.字段 | → | 目标表.字段 |
| --- | --- | --- |
| crm: deals.contact_id | → | crm: contacts.id |
| crm: deals.assigned_to | → | crm: users.id |
| crm: sales_targets.user_id | → | crm: users.id |
| erp: sales_orders.customer_id | → | erp: customers.id |
| erp: sales_orders.warehouse_id | → | erp: warehouses.id |
| erp: sales_order_lines.sales_order_id | → | erp: sales_orders.id |
| erp: sales_order_lines.sku_id | → | erp: skus.id |
| erp: stocks.sku_id | → | erp: skus.id |
| erp: stocks.warehouse_id | → | erp: warehouses.id |

## 5. 工具定义 (Tools)
| 工具名称 | 数据库 | 功能 |
| --- | --- | --- |
| query_sales_summary | ERP | 按 business_date / 客户 / 仓库统计 base_currency_amount |
| query_sales_orders | ERP | 查询订单列表，多维度筛选 |
| query_customer_info | ERP | 查询客户档案与购买历史 |
| query_crm_deals | CRM | 查询商机，按 status/assigned_to 筛选 |
| query_sales_targets | CRM | 查询销售目标与达成对比 |
| query_stock_levels | ERP | 查询库存 available，支持低库存预警 |
| execute_readonly_sql | ERP/CRM | 通用 SELECT 兜底工具 |

### 5.1 工具 JSON Schema 定义

**5.1.1 query_sales_summary**
| {   "name": "query_sales_summary",   "description": "统计销售额。日期字段用 business_date，金额用     base_currency_amount。自动过滤 DRAFT/CANCELLED 订单。",   "input_schema": {     "type": "object",     "properties": {       "start_date":    {"type":"string","description":"开始日期 YYYY-MM-DD"},       "end_date":      {"type":"string","description":"结束日期 YYYY-MM-DD"},       "customer_name": {"type":"string","description":"客户 name 模糊匹配，可选"},       "group_by":      {"type":"string","enum":["customer","month","warehouse"],                         "description":"分组维度，默认 month"}     },     "required": ["start_date","end_date"]   } } |
| --- |


**5.1.2 query_crm_deals**
| {   "name": "query_crm_deals",   "description": "查询 CRM 商机。status 枚举：lead/following/negotiating/won/lost。",   "input_schema": {     "type": "object",     "properties": {       "status":           {"type":"string",                            "enum":["lead","following","negotiating","won","lost"]},       "assigned_to_name": {"type":"string","description":"负责销售员姓名模糊匹配"},       "min_amount":       {"type":"number","description":"最低金额筛选"},       "limit":            {"type":"integer","description":"返回条数，默认 20"}     }   } } |
| --- |


**5.1.3 query_stock_levels**
| {   "name": "query_stock_levels",   "description": "查询库存。available 是虚拟列(on_hand-reserved-quality_hold)。     low_stock_only=true 返回 available <= reorder_point 的商品。",   "input_schema": {     "type": "object",     "properties": {       "sku_name":      {"type":"string","description":"商品名称模糊匹配"},       "sku_code":      {"type":"string","description":"SKU 编号精确匹配"},       "warehouse_name":{"type":"string","description":"仓库名称"},       "low_stock_only":{"type":"boolean","description":"仅返回低库存商品"}     }   } } |
| --- |


**5.1.4 execute_readonly_sql（兜底）**
| {   "name": "execute_readonly_sql",   "description": "执行只读 SQL。仅 SELECT。crm_os 和 erp_os 是独立数据库，     不能跨库 JOIN。ERP 查询必须包含 organization_id = 1。",   "input_schema": {     "type": "object",     "properties": {       "sql":      {"type":"string","description":"SELECT 语句"},       "database": {"type":"string","enum":["crm_os","erp_os"]}     },     "required": ["sql","database"]   } } |
| --- |

## 6. 后端实现 (Python)

### 6.1 项目结构
| ai_assistant/ ├── main.py              # FastAPI 入口，/chat 接口 ├── claude_client.py     # Claude API Tool Use 循环（含 history 截断） ├── tools/ |   ├── definitions.py   # 所有工具 JSON Schema |   └── executors.py     # 工具执行函数（含准确 SQL） ├── db/ |   ├── crm.py           # CRM 连接（VARCHAR uuid 主键） |   └── erp.py           # ERP 连接（INT 主键，多租户） ├── frontend/ |   └── index.html       # 聊天界面（单文件） ├── test_db.py           # Session 1 验收测试 ├── test_tools.py        # Session 2 验收测试 ├── test_claude.py       # Session 3 验收测试 ├── .env                 # 密钥配置（不提交 Git） └── requirements.txt |
| --- |

### 6.2 requirements.txt
| fastapi==0.115.0 uvicorn==0.30.0 anthropic==0.34.0 pymysql==1.1.1 python-dotenv==1.0.0 pydantic==2.9.0 |
| --- |

### 6.3 .env 配置
| ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx   CRM_DB_HOST=localhost CRM_DB_PORT=3306 CRM_DB_NAME=crm_os CRM_DB_USER=ai_readonly CRM_DB_PASSWORD=your_password   ERP_DB_HOST=localhost ERP_DB_PORT=3306 ERP_DB_NAME=erp_os ERP_DB_USER=ai_readonly ERP_DB_PASSWORD=your_password   ERP_ORG_ID=1 |
| --- |

### 6.4 数据库连接层
| # db/erp.py import pymysql, os from dotenv import load_dotenv load_dotenv()   ERP_ORG_ID = int(os.getenv('ERP_ORG_ID', 1))   def erp_query(sql: str, params=None) -> list:     conn = pymysql.connect(         host=os.getenv('ERP_DB_HOST'),         port=int(os.getenv('ERP_DB_PORT', 3306)),         db=os.getenv('ERP_DB_NAME'),         user=os.getenv('ERP_DB_USER'),         password=os.getenv('ERP_DB_PASSWORD'),         charset='utf8mb4',         cursorclass=pymysql.cursors.DictCursor     )     try:         with conn.cursor() as cur:             cur.execute(sql, params or ())             return cur.fetchall()     finally:         conn.close()   # db/crm.py 结构相同，替换 ERP_ 前缀为 CRM_ |
| --- |

### 6.5 Claude API 核心（含 history 截断）
| import anthropic, json from tools.definitions import TOOLS from tools.executors import execute_tool   client = anthropic.Anthropic()   SYSTEM_PROMPT = ''' 你是一个专业的业务数据助手，可以查询 CRM (crm_os) 和 ERP (erp_os) 数据。 重要规则： 1. ERP 所有查询必须加 organization_id = 1 2. 金额统计使用 base_currency_amount（本位币） 3. 必须过滤：is_active=1, deleted_at IS NULL 4. sales_orders 过滤：status NOT IN ('DRAFT','CANCELLED') 5. 两个数据库独立，不能跨库 JOIN，需分步查询 6. 禁止查询 password_hash、audit_logs、ai_call_logs 用清晰简洁的中文回答，数据多时用表格呈现。 '''   def trim_history(history: list, max_turns: int = 10) -> list:     if len(history) <= max_turns * 2:         return history     return history[-(max_turns * 2):]   def chat(messages: list) -> str:     messages = trim_history(messages)     while True:         response = client.messages.create(             model='claude-sonnet-4-6',             max_tokens=4096,             system=SYSTEM_PROMPT,             tools=TOOLS,             messages=messages         )         messages.append({'role':'assistant','content':response.content})         if response.stop_reason == 'end_turn':             for block in response.content:                 if hasattr(block,'text'): return block.text         if response.stop_reason == 'tool_use':             results = []             for block in response.content:                 if block.type == 'tool_use':                     result = execute_tool(block.name, block.input)                     results.append({                         'type':'tool_result',                         'tool_use_id':block.id,                         'content':json.dumps(result,ensure_ascii=False,default=str)                     })             messages.append({'role':'user','content':results}) |
| --- |

### 6.6 工具执行 SQL（含所有过滤条件）
| from db.erp import erp_query, ERP_ORG_ID from db.crm import crm_query   FORBIDDEN_TABLES = ['audit_logs','ai_call_logs','login_attempts','alembic_version'] FORBIDDEN_COLS   = ['password_hash']   def execute_tool(name, params):     handlers = {         'query_sales_summary':  query_sales_summary,         'query_sales_orders':   query_sales_orders,         'query_customer_info':  query_customer_info,         'query_crm_deals':      query_crm_deals,         'query_sales_targets':  query_sales_targets,         'query_stock_levels':   query_stock_levels,         'execute_readonly_sql': execute_readonly_sql,     }     fn = handlers.get(name)     if not fn: return {'error': f'未知工具: {name}'}     try: return fn(**params)     except Exception as e: return {'error': str(e)}   def execute_readonly_sql(sql: str, database: str):     sql_up = sql.strip().upper()     if not sql_up.startswith('SELECT'):         return {'error': '只允许 SELECT'}     for t in FORBIDDEN_TABLES:         if t.upper() in sql_up: return {'error': f'禁止查询 {t}'}     for c in FORBIDDEN_COLS:         if c.upper() in sql_up: return {'error': f'禁止查询 {c}'}     if 'LIMIT' not in sql_up: sql = sql.rstrip(';') + ' LIMIT 200'     fn = crm_query if database == 'crm_os' else erp_query     rows = fn(sql)     return {'rows': rows, 'count': len(rows)}   def query_sales_summary(start_date, end_date, customer_name=None, group_by='month'):     gmap = {'month':'DATE_FORMAT(so.business_date,"%Y-%m")',             'customer':'c.name','warehouse':'w.name'}     gexpr = gmap.get(group_by,gmap['month'])     where = '''WHERE so.organization_id = %s               AND so.business_date BETWEEN %s AND %s               AND so.is_active = 1 AND so.deleted_at IS NULL               AND so.status NOT IN ('DRAFT','CANCELLED')'''     params = [ERP_ORG_ID, start_date, end_date]     if customer_name:         where += ' AND c.name LIKE %s'; params.append(f'%{customer_name}%')     sql = f'''SELECT {gexpr} AS dimension,                COUNT(so.id) AS order_count,                SUM(so.base_currency_amount) AS total_sales         FROM sales_orders so         JOIN customers c ON so.customer_id=c.id         JOIN warehouses w ON so.warehouse_id=w.id         {where} GROUP BY {gexpr} ORDER BY total_sales DESC LIMIT 50'''     return {'data': erp_query(sql, params)}   def query_crm_deals(status=None, assigned_to_name=None, min_amount=None, limit=20):     where = 'WHERE d.deleted_at IS NULL'     params = []     if status: where += ' AND d.status=%s'; params.append(status)     if assigned_to_name:         where += ' AND u.name LIKE %s'; params.append(f'%{assigned_to_name}%')     if min_amount: where += ' AND d.amount>=%s'; params.append(min_amount)     sql = f'''SELECT d.title,d.status,d.priority,d.amount,                c.name AS contact,c.company,u.name AS owner,                d.created_at,d.won_at         FROM deals d         JOIN contacts c ON d.contact_id=c.id         LEFT JOIN users u ON d.assigned_to=u.id         {where} ORDER BY d.amount DESC LIMIT %s'''     params.append(limit)     return {'data': crm_query(sql, params)}   def query_stock_levels(sku_name=None,sku_code=None,warehouse_name=None,low_stock_only=False):     where = 'WHERE sk.organization_id=%s AND sk.is_active=1 AND sk.deleted_at IS NULL'     params = [ERP_ORG_ID]     if sku_name:   where+=" AND sk.name LIKE %s"; params.append(f'%{sku_name}%')     if sku_code:   where+=" AND sk.code=%s"; params.append(sku_code)     if warehouse_name: where+=" AND wh.name LIKE %s"; params.append(f'%{warehouse_name}%')     if low_stock_only: where+=" AND st.available <= sk.reorder_point"     sql = f'''SELECT sk.code,sk.name,wh.name AS warehouse,                st.on_hand,st.reserved,st.available,                sk.reorder_point,sk.safety_stock         FROM stocks st         JOIN skus sk ON st.sku_id=sk.id         JOIN warehouses wh ON st.warehouse_id=wh.id         {where} ORDER BY st.available ASC LIMIT 100'''     return {'data': erp_query(sql, params)} |
| --- |

### 6.7 FastAPI 接口 (main.py)
| from fastapi import FastAPI from fastapi.staticfiles import StaticFiles from fastapi.middleware.cors import CORSMiddleware from pydantic import BaseModel from claude_client import chat   app = FastAPI() app.add_middleware(CORSMiddleware,allow_origins=['*'],                    allow_methods=['*'],allow_headers=['*'])   class ChatRequest(BaseModel):     message: str     history: list = []   @app.post('/chat') async def chat_endpoint(req: ChatRequest):     messages = req.history + [{'role':'user','content':req.message}]     reply = chat(messages)     return {'reply': reply}   app.mount('/',StaticFiles(directory='frontend',html=True),name='static') # 启动：uvicorn main:app --reload --host 0.0.0.0 --port 8000 |
| --- |

## 7. 前端实现 (frontend/index.html)
- 聊天气泡界面，区分用户和 AI 消息
- 引入 marked.js 渲染 Markdown（表格、加粗、列表）
- 发送时显示「思考中...」加载动画
- Enter 发送，Shift+Enter 换行
- 前端维护 history 数组（最多发 20 轮，超出自动截断）
- 单个 HTML 文件，无需构建工具


### 7.1 核心 JS 逻辑
| let history = []; const MAX_HISTORY = 20;  // 前端也限制，双重保险   async function sendMessage() {     const msg = document.getElementById('input').value.trim();     if (!msg) return;     appendMessage('user', msg);     document.getElementById('input').value = '';     showThinking();     try {         const res = await fetch('/chat', {             method:'POST',             headers:{'Content-Type':'application/json'},             body:JSON.stringify({message:msg, history})         });         const data = await res.json();         history.push({role:'user',content:msg});         history.push({role:'assistant',content:data.reply});         if (history.length > MAX_HISTORY*2)             history = history.slice(-MAX_HISTORY*2);         hideThinking();         appendMessage('assistant', marked.parse(data.reply));     } catch(e) {         hideThinking();         appendMessage('assistant','查询失败，请稍后重试。');     } } |
| --- |

## 8. Claude Code 分步执行计划
以下计划适用于 Claude Pro plan。每个 Session 功能独立、可单独验收，避免单次 context 超限。
使用方式：每个 Session 开始时，把本文档 + 项目目录一起给 Claude Code，然后粘贴对应的「Claude Code 指令」。

| Session 1  —  项目骨架 + 数据库连接层 |
| --- |
| 目标：建立项目结构，确保能连上两个数据库  产出文件： requirements.txt .env.example db/crm.py、db/erp.py（连接 + 查询函数） test_db.py（验收测试）  验收标准： python test_db.py 输出两个数据库各一条查询结果，无报错  Claude Code 指令： |


| Session 2  —  工具定义 + SQL 执行层 |
| --- |
| 前置条件：Session 1 完成，test_db.py 通过 目标：实现所有工具的查询逻辑，每个工具都能返回真实数据  产出文件： tools/definitions.py（7 个工具 JSON Schema） tools/executors.py（7 个执行函数 + 安全校验） test_tools.py（每个工具各调用一次）  验收标准： python test_tools.py 每个工具输出非空数据，无 SQL 错误  Claude Code 指令： |


| Session 3  —  Claude API 集成（Tool Use 循环） |
| --- |
| 前置条件：Session 2 完成，test_tools.py 通过 目标：Claude 能理解自然语言并正确调用工具返回回答  产出文件： claude_client.py（含 System Prompt + Tool Use 循环 + history 截断） test_claude.py（端到端测试 5 个示例问题）  验收标准： python test_claude.py 每个问题都得到中文回答，数据与数据库一致  Claude Code 指令： |


| Session 4  —  FastAPI 后端接口 |
| --- |
| 前置条件：Session 3 完成，test_claude.py 通过 目标：HTTP 接口可用，支持多轮对话  产出文件： main.py（FastAPI + CORS + 静态文件挂载）  验收标准： uvicorn main:app --reload 正常启动 curl 发两轮对话，第二轮能引用第一轮内容  Claude Code 指令： |


| Session 5  —  前端聊天界面 |
| --- |
| 前置条件：Session 4 完成，/chat 接口可用 目标：完整 Demo 可在浏览器运行  产出文件： frontend/index.html（单文件，含 HTML + CSS + JS）  验收标准： 浏览器打开 http://localhost:8000 输入销售问题，AI 回答包含格式化表格 连续问 3 个问题，对话历史正确保留 点击麦克风按钮，说话后文字出现在输入框 右上角切换中/英语言，语音识别切换成功 快捷查询按钮点击后自动填入输入框  Claude Code 指令： |

## 9. 常用查询指令
以下查询指令用于两处：① Demo 展示时向潜在客户演示，② 前端快捷按钮的文字内容。
Claude Code 在 Session 5 实现前端时，将这些查询按类别做成点击按钮。


### 9.1 销售统计
| 中文指令 | English |
| --- | --- |
| 上个月的总销售额是多少？ | What was the total sales last month? |
| 销售额最高的前 5 个客户是谁？ | Who are the top 5 customers by sales? |
| 今年每个月的销售额趋势？ | Show me the monthly sales trend this year. |
| 本月和上月的销售额对比 | Compare this month's sales vs last month. |
| 哪个仓库的销售额最高？ | Which warehouse has the highest sales? |
| 今年到目前的累计销售额是多少？ | What is the YTD total sales so far? |
| 最近 7 天有哪些新订单？ | What are the new orders in the last 7 days? |
| 哪些订单还未完成发货？ | Which orders have not been fully shipped yet? |

### 9.2 客户分析
| 中文指令 | English |
| --- | --- |
| 客户 XX 最近 3 个月下了多少单？ | How many orders did customer XX place in the last 3 months? |
| 超过 90 天没有再次购买的客户有哪些？ | Which customers haven't ordered in the last 90 days? |
| 信用额度最高的前 10 个客户 | List the top 10 customers by credit limit. |
| B2B 和 B2C 客户各有多少？ | How many B2B vs B2C customers do we have? |
| 哪些客户有未收款的发票？ | Which customers have outstanding unpaid invoices? |
| 逾期未付款的客户列表 | List customers with overdue invoices. |

### 9.3 CRM 商机管理
| 中文指令 | English |
| --- | --- |
| 目前谈判阶段的商机有哪些？总金额是多少？ | What deals are in negotiating stage? What's the total value? |
| 本月新增的商机有哪些？ | What new deals were created this month? |
| 本月成交（won）的商机统计 | Summarize the won deals this month. |
| 每个销售员各有多少个进行中的商机？ | How many active deals does each salesperson have? |
| 金额最高的 10 个商机 | List the top 10 deals by amount. |
| 哪些高优先级商机还没有跟进记录？ | Which high-priority deals have no activity logged? |
| 各销售员的商机总金额对比 | Compare total deal amounts by salesperson. |

### 9.4 库存管理
| 中文指令 | English |
| --- | --- |
| 哪些商品库存低于补货触发点？ | Which products are below the reorder point? |
| 哪些商品库存低于安全库存？ | Which products are below the safety stock level? |
| 各仓库的库存总量 | Show total stock quantity by warehouse. |
| 商品 XX 在各仓库的可用库存是多少？ | What is the available stock of product XX across all warehouses? |
| 库存可用量为零的商品列表 | List products with zero available stock. |
| 库存总价值最高的前 10 个商品 | Top 10 products by total inventory value (qty × avg cost). |

### 9.5 应收款 / 收款
| 中文指令 | English |
| --- | --- |
| 本月收到了多少款项？ | How much payment was received this month? |
| 目前未收款的发票总金额是多少？ | What is the total amount of unpaid invoices? |
| 30 天以上未收款的发票有哪些？ | List invoices unpaid for more than 30 days. |
| 各付款方式的收款金额占比 | Break down payment received by payment method. |

### 9.6 销售目标达成（CRM）
| 中文指令 | English |
| --- | --- |
| 本月各销售员的目标金额是多少？ | What are the sales targets for each rep this month? |
| 各销售员目标达成情况 | How is each salesperson tracking against their target? |

### 9.7 跨系统联合查询（最佳卖点）
| 这类问题最能打动潜在客户，展示 AI 跨系统整合能力 "销售额最高的 3 个客户，他们在 CRM 里有没有进行中的商机？" "Which top customers have active CRM deals we should prioritize?" "哪些客户有逾期未付款发票，且在 CRM 里还有跟进中的商机？" "Which customers have overdue invoices but still have ongoing deals in CRM?" |
| --- |

## 10. 语音输入功能
语音输入使用浏览器内置的 Web Speech API，无需后端改动、无需第三方服务、零额外费用。


### 10.1 工作量评估
| 项目 | 说明 |
| --- | --- |
| 代码量 | 约 40 行 JS，全部在 frontend/index.html 内 |
| 后端改动 | 无，完全是前端功能 |
| 额外 Session | 无，合并进 Session 5 |
| 外部服务/费用 | 无，使用浏览器内置 API |
| 浏览器兼容 | Chrome/Edge：完整支持；Safari：部分支持；Firefox：不支持 |
| Demo 建议 | 使用 Chrome 演示，效果最佳 |

### 10.2 实现逻辑
| // 1. 检测浏览器支持 const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition; const voiceBtn = document.getElementById('voice-btn'); if (!SpeechRecognition) {     voiceBtn.style.display = 'none';  // 不支持则隐藏按钮 }   // 2. 初始化 let currentLang = 'zh-CN';  // 默认中文 const recognition = new SpeechRecognition(); recognition.continuous = false; recognition.interimResults = true;  // 实时显示识别中的文字 recognition.lang = currentLang;   // 3. 语言切换（右上角按钮） function toggleLang() {     currentLang = currentLang === 'zh-CN' ? 'en-US' : 'zh-CN';     recognition.lang = currentLang;     document.getElementById('lang-btn').textContent =         currentLang === 'zh-CN' ? '中文' : 'EN'; }   // 4. 开始录音 let isRecording = false; function toggleVoice() {     if (isRecording) {         recognition.stop();     } else {         recognition.lang = currentLang;         recognition.start();         isRecording = true;         voiceBtn.classList.add('recording');  // 变红表示录音中     } }   // 5. 实时结果 → 填入输入框 recognition.onresult = (event) => {     const transcript = Array.from(event.results)         .map(r => r[0].transcript).join('');     document.getElementById('input').value = transcript;     // 用户可以在识别完成后再编辑，然后按 Enter 发送 };   recognition.onend = () => {     isRecording = false;     voiceBtn.classList.remove('recording'); };   recognition.onerror = (e) => {     isRecording = false;     voiceBtn.classList.remove('recording');     if (e.error === 'not-allowed')         alert('请在浏览器设置中允许麦克风权限'); }; |
| --- |

### 10.3 UI 元素
- 右上角语言切换按钮：显示「中文」或「EN」，点击切换
- 输入框右侧麦克风图标按钮：点击开始录音，录音中变红色
- 实时识别文字自动填入输入框，用户可以确认或编辑后发送
- 浏览器不支持时自动隐藏麦克风按钮，不影响文字输入


## 11. 安全与部署

### 11.1 只读账号
| CREATE USER 'ai_readonly'@'%' IDENTIFIED BY 'strong_password'; GRANT SELECT ON crm_os.* TO 'ai_readonly'@'%'; GRANT SELECT ON erp_os.* TO 'ai_readonly'@'%'; FLUSH PRIVILEGES; |
| --- |

### 11.2 启动
| pip install -r requirements.txt cp .env.example .env   # 填入真实配置 uvicorn main:app --reload --host 0.0.0.0 --port 8000 # 浏览器访问 http://localhost:8000 |
| --- |

### 11.3 注意事项
- 两个数据库（crm_os / erp_os）需各自配置连接信息，不要混用
- ANTHROPIC_API_KEY 存 .env，不提交 Git（.gitignore 加上 .env）
- Demo 时使用的是真实数据库，请确认数据符合展示需求


— 文档结束  v1.3 —