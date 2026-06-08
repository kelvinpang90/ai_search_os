-- 之前创建的 ai_readonly@'localhost' 只允许容器内部连接，无法被外部访问。
-- 创建一个 host='%' 的账号，允许从宿主机 / 其他容器连接。
CREATE USER IF NOT EXISTS 'ai_readonly'@'%' IDENTIFIED BY '123456';
GRANT SELECT ON crm_os.* TO 'ai_readonly'@'%';
GRANT SELECT ON erp_os.* TO 'ai_readonly'@'%';
FLUSH PRIVILEGES;

-- 旧账号不再需要，可以删除（如不放心可先保留，确认新账号可用后再删）
DROP USER IF EXISTS 'ai_readonly'@'localhost';
