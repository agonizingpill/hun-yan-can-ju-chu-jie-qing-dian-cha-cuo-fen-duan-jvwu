# 曼禾宴台盖箱

曼禾餐具工场将婚宴餐盘按宴台装入盖箱。发箱时核对独立箱签，途中保留唯一的原台归属。席间和撤席清点后，复核员处理差错并签收宴台。

模拟客户是一支 11 人婚宴出借组。原来的厅面单和收箱纸票分开保存，常见问题为同一箱码在两张席卡出现、缺盘无法定位在后场还是台面，以及撤席后才看到还没归责的账单。布席班的桌号和实物箱签进入交接，撤席复核员给工场结算和厅面领班发送已签责任与收场记录。

| 角色 | 演示账号 | 办理权限 |
|---|---|---|
| 作业员 | `operator@demo.test` | 验箱并交接宴台、录各段清点读数、计算和签入 |
| 复核员 | `reviewer@demo.test` | 含作业员操作，另可解除箱锁、指定责任段、签撤席 |
| 只读访客 | `viewer@demo.test` | 查阅布席、交接、清点和差错 |

演示口令均为 `DemoC0de!2026`。

## 运行

```bash
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
```

前端 `http://localhost:18316`，API 文档 `http://localhost:19316/docs`，PostgreSQL 17816，用户和数据库均为 `desk`。停止用 `docker compose down`。

| 服务 | 实现 |
|---|---|
| frontend | Nginx + HTML、CSS、ES modules |
| backend | Python 3.11 + FastAPI + SQLAlchemy |
| worker | 从 Redis 消费清点计算并运行 Bagging + LinearSVC |
| db | PostgreSQL 16 领域表、约束和事务锁 |
| redis | 计算队列、结果凭证、心跳 |

`.env.example` 提供 Compose 项目名称、端口、`DB_PASSWORD`、`JWT_SECRET` 和 `SEED_DEMO`。本地开发安装 `backend/requirements.txt` 后可设置 `DATABASE_URL`、`REDIS_URL`、`JWT_SECRET` 和 `SEED_DEMO=true`，从 `backend/` 启动 `uvicorn core.app:app` 以及 `python -m core.worker`。浏览器调用 nginx 前缀挂载的 API。

## 甄林婚宴作业剧本

1. 16:30，玉兰厅 `MH-A08` 为 10 席冷盘，后场拿到可装 12 件的金边盘箱 `CASE-R08`。
2. 16:35，扫封签 `LID-R08` 签交接 `PL-1124-A08`，发 12 件。
3. 17:00，另一名桌长在 `MH-A10` 扫到同箱，箱锁定。保留原 `MH-A08` 归属，禁写清点。
4. 17:10，复核员核对原台号、箱签与 12 件，恢复原宴台。
5. 18:45，A08 席间点 8 件、回收 7 件，盘沿重叠比 0.76、盖面遮挡比 0.75。统计模型提供宴台清点段建议。
6. 18:50，签入清点产生 5 件差额并锁箱。复核员明确责任段与何师傅。
7. 19:00，以实收 7 件及原箱签结案，复核员签撤席。
8. 19:10，敬茶小席 `MH-C01` 使用 8 件入、8 件出的一套甜羹碗，直接平衡结单。

## 计算和代码

Python 把整箱应有数与各阶段实数换成三段差额比，再附加盖面遮挡、模糊影像、盘沿重叠与交接间隔的归一值。训练使用 200 条固定种子模拟数据，独立模拟留出 56 条。48 个 bootstrap 基学习器分别做标准化和 LinearSVC，按基学习器类别票数汇总。留出准确率只对应模拟分布。模型给复核员提示，归责需要人工选择段和责任人，最终数量来自真实录入读数。

`backend/domain/manifest.py` 与 `evidence_tables.py` 定义领域表。业务链在 `placement.py`、`counting.py` 和 `disposition.py`。模型在 `learning.py`，页面在 `frontend/src/pages/`。箱状态、宴台状态、差错状态、分段字典在 `backend/domain/labels.py` 和 `frontend/src/custody-state.js`，用于表约束和办理提示。角色也分别定义为 `backend/core/roles.py`、`frontend/src/store.js`。

源码使用 MIT 许可，见 `LICENSE`。
