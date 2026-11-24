# 第十九阶段：启动验收门槛
在第十八阶段 CI 的数据库测试及 Docker build 后，新增真实容器启动和 HTTP 冒烟测试。使用 CI 临时数据库、虚构密钥，不访问模型或生产环境。为测试角色授予临时数据库 public schema 的 CREATE/USAGE 权限（PostgreSQL 16 默认不向普通角色开放 CREATE）。
验证根路径启动状态、数据库和记忆开关、无密钥及无效人物密钥拒绝、MCP 无效密钥拒绝。失败时收集容器日志并清理容器。此测试不证明实际聊天、MCP 握手或跨客户端记忆连续性。
上传到 multi-character 分支后，在 Actions 查看 Multi integration gate；必须通过所有步骤再建立独立 Render/Neon 测试环境。当前没有运行 Docker 或真实数据库的条件，不能确认 CI 通过。依赖锁仍沿用原项目，安装兼容性待 CI 验证。
