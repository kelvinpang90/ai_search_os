-- 创建 AI 助手只读账号（按 requirements.md §11.1）
-- 执行方式：docker exec -i erp_mysql mysql -uroot -p < setup_readonly_user.sql

CREATE USER IF NOT EXISTS 'ai_readonly'@'%' IDENTIFIED BY '123456';
GRANT SELECT ON crm_os.* TO 'ai_readonly'@'%';
GRANT SELECT ON erp_os.* TO 'ai_readonly'@'%';
FLUSH PRIVILEGES;
