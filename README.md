# 4S店回访续保预测

`dealer-renewal-score` 是给华东星驰 4S 店客户经营组使用的小型续保经营工作台。它把保养事件、车主档案、Python 续保预测、经营审核和回访队列连成一条业务链。

## 业务场景

客户经营组每天从 DMS 导出保养工单，再人工筛选未来 60 天可能续保的车主。原流程依赖 Excel，存在保养间隔难以比较、到期客户遗漏、顾问重复触达三个痛点。本应用位于 DMS 与客户经营团队之间，上游是车主和保养事件，下游是回访顾问及续保活动排期。

演示主流程为 `保养数据 → 续保预测 → 客户经营审核 → 安排回访`。客户明确拒绝联系后，系统会冻结该车主的预测触达。保单已过期的车主会从预测结果和回访队列中排除。

## 运行

```bash
docker compose config --quiet
docker compose up -d --build
# 登录后即可使用，后端启动时会执行幂等 seed
docker compose exec -T backend python -m scripts.seed_demo
docker compose down -v --remove-orphans
```

服务端口为前端 `18253`、后端 `19253`、MySQL `17753`。Compose 共包含 `frontend`、`backend`、`worker`、`db`、`redis` 五个服务。

## 演示账号

| 账号 | 密码 | 角色 | 主要动作 |
|---|---|---|---|
| advisor@autohub.local | dealer123 | 回访顾问 | 查看车主、保养和回访任务，登记回访结果 |
| manager@autohub.local | dealer123 | 客户经营经理 | 运行预测、审核线索、安排回访、冻结触达 |
| admin@autohub.local | dealer123 | 经营管理员 | 访问全部页面和审计记录 |

## 算法口径

后端用固定随机种子生成可复现训练样本，使用 `GradientBoostingClassifier` 预测未来续保概率。输入特征为距离最近保养的天数、距保单到期天数、最近一年保养次数、维修金额和满意度。特征贡献采用单特征置为训练中位数后的概率差值近似解释，所有结果由 Python 计算并持久化到线索记录。

## 前后端共享枚举

- `lead_status`：`predicted`、`reviewed`、`queued`、`frozen`、`expired`、`rejected`
- `followup_status`：`scheduled`、`contacted`、`declined`、`completed`
- `contact_status`：`open`、`rejected`

后端定义于 `backend/src/constants.py`，前端定义于 `frontend/src/domain.js`，数据库约束位于 `backend/migrations/001_schema.sql`。
