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

## 分段模型版本治理

模型只给归责建议，分段模型的训练、上线与作废由 `backend/domain/model_registry.py` 和 `model_tables.py` 治理，规则如下：

1. **只用已结案的人工归责训练**：训练样本取自 `resolved` 的 `count_loss` 差错，且必须有人工指定的责任段。
2. **同场婚宴不拆两边**：按婚宴（party）整组切分，同一场婚宴的箱不会同时出现在训练集和验收集（`_grouped_split`）。
3. **同一批评审箱对比**：一次评审（campaign）固定一整批验收箱，候选版与在用版在完全相同的箱上逐箱判别，结果记入 `model_validation_cases` 与 `model_evaluation_scores`。
4. **三段缺件都要有样本**：验收集缺任一段（后场装箱/宴台清点/撤席回收）即拒绝评审。
5. **任一段漏判更多就不换版**：逐段统计漏判，只有候选版每段漏判都不高于在用版才过关，否则候选置 `rejected`、在用版不动。
6. **过关一次性切换**：切换在单个事务内把旧在用版转 `superseded`、候选转 `active`，全局始终只有一个 `active`。
7. **排队清点按领号版本算**：清点领号（`/counts/review`）时把当前 `active` 版本钉进计算任务，之后即使切换版本，已排队任务仍按领号时的版本计算，签入时版本号落入 `count_frames.model_version`。
8. **更正结案归责即作废回退**：复核员更正已结案归责（`/custody/{code}/revise`）后，所有用过该箱旧归责的版本置 `invalid`；若作废的正是在用版，回退到最近一个未受影响的历史在用版，没有则由永不依赖人工归责的 `baseline-bag-linear-svc` 兜底。
9. **带过期归责拒绝上线**：训练晚结束的候选，在评审上线时再核对一次训练所用归责是否已被更正（`label_revised_at > trained_at`），命中即拒绝上线，不允许带病版本进入在用。
10. **清点页标明当前版本**：分段清点页顶部显示“当前给新单使用的模型版本”，每张清点单同时显示其领号时钉住的版本；模型治理页（仅复核员可操作）列出全部版本、评审记录与归责更正入口。

模拟基线 `baseline-bag-linear-svc` 不依赖任何人工归责、永不作废，是系统初始在用版和最终回退兜底。候选工件以 pickle 存于 `MODEL_ARTIFACT_DIR`（默认 `/results/models`，backend 与 worker 共享卷）。`POST /models/demo-dataset` 可生成跨三个婚宴、覆盖三个缺件段的已结案归责样本，便于端到端演示训练、评审、切换、作废与回退。

源码使用 MIT 许可，见 `LICENSE`。
