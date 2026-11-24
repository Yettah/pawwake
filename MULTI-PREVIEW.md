# Pawwake Multi — 第一阶段兼容性预览
基于 489b345，保留 AGPL-3.0 与原项目贡献者声明。

本版本只实现 OpenAI Bearer 鉴权兼容，并不实现单服务多人物隔离。不要把多个伴侣接到同一个实例。

临时隔离方案：每位伴侣使用独立 Render Web Service、独立 PostgreSQL 数据库（可在同一 Neon 项目下创建，建议独立数据库角色），独立 GATEWAY_SECRET、DASHBOARD_PASSWORD、SESSION_SECRET。禁止复用 DATABASE_URL。每个实例使用原 Dashboard 设置各自人设和模型。相同人物的多个客户端使用该实例的 URL/v1 和 GATEWAY_SECRET。若客户端要求完整接口，则使用 URL/v1/chat/completions。上游 API Key 仅填写在 Dashboard。浏览器跨域支持未验证。

本补丁新增 Bearer 仅用于 /v1/models 与 /v1/chat/completions；原 X-Gateway-Key 权限保持不变。不要把密钥提交到 Git。Render 免费服务资源、休眠和数据库额度需自行确认。未验证真实数据库、Docker 构建或上游模型调用。不要导入真实记录，先用虚构数据测试。

测试：python tests/test_bearer.py；python -m compileall -q .

下一阶段：单服务人物身份路由、数据库隔离、后台任务和缓存隔离、人物管理界面、备份隔离及集成测试。
