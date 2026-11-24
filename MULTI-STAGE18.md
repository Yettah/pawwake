# 第十八阶段：独立测试部署准备（非正式发布）
1. 在 GitHub 创建 multi-character 分支，仅向该分支上传本包解压后的文件（包括隐藏的 .github 目录）。不要覆盖 main。
2. 在 Actions 中查看 Multi integration gate。该工作流使用临时 PostgreSQL 16 和非超级用户角色，不使用 Neon 或任何真实密钥。必须通过真实 RLS 测试和 Docker build 才进入下一步。
3. 如失败，保留错误日志并修复；不要跳过测试或关闭 RLS。
4. 通过后才创建独立 Neon 测试项目和独立 Render Docker Web Service，选择 multi-character 分支。render.multi-test.yaml 仅供手动配置参考，不替换原 render.yaml。检查免费额度及费用后再创建。
5. Neon 测试连接角色须能创建表、安装所需扩展且无 SUPERUSER/BYPASSRLS 权限；不能使用生产连接串。检查 SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user;。若无法满足权限条件，停止部署并排查。
6. 使用新的 GATEWAY_SECRET、DASHBOARD_PASSWORD、SESSION_SECRET；仅在 Render 环境变量填写。不要提交密钥。使用虚构人物 A/B，先关闭真实模型调用，验证后台权限和数据隔离，再配置测试模型及提取模型。
7. 验收：A/B 密钥隔离、跨客户端同人物召回、SSE、MCP、重启任务恢复、导出范围、错误密钥拒绝。任何串记忆或任务丢失均阻止发布。
8. 回滚：停止测试服务；原 main、原 Render、原 Neon 不受修改。测试数据库仅在确认无所需资料后删除。
限制：本阶段仅添加 CI 和部署参考，没有执行 GitHub Actions、真实数据库或 Render 部署；已有功能缺陷仍待验证修复。
