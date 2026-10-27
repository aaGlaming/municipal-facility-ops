# Step 35：整理项目文档与交付材料

## 完成内容

- 更新根目录 README：当前交付状态、启动、验证、数据、评测和备份恢复命令。
- 新增 `docs/DELIVERY.md`：新成员操作路径、API/配置边界、失败归因、已知限制和 Step 33/34 阻断说明。
- 更新 `docs/Preparation/api.md`：补充 Agent 运行、认证和监控接口及权限边界。
- 更新 `docs/Preparation/file-guide.md` 和 `scripts/README.md`：同步当前目录职责和可执行脚本，删除过时的“后续实现”说明。
- 更新 `.gitignore`：排除 Chroma、本地缓存、覆盖率产物和备份目录；真实 `.env` 和运行时文件仍不入 Git。

## 交付检查

- `python -m pytest -q backend/tests`：86 passed。
- `python -m ruff check backend/app backend/tests scripts`：通过。
- `python -m ruff format --check backend/app backend/tests scripts`：125 files already formatted。
- `npm run type-check`：通过。
- `npm run build`：通过；Vite 仅提示现有 bundle 体积偏大。
- `git diff --check`：通过。

## 已知边界

Step 33 的真实 MySQL、Chroma、模型就绪门禁和 Step 34 的 MySQL 逻辑 dump 继续留待 Step 36 Compose 环境；本文档不把离线验证结果表述为真实依赖已通过。
