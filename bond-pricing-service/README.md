# Bond Pricing & Rate Risk Engine

固定利率附息债（bullet bond）估值与利率风险核算引擎。只通过 HTTP + JSON 对外服务，
无页面、无账户、无持仓概念，供上游报价系统与风控系统直接调用。

- 后端：Python 3.12 + FastAPI
- 交付：容器化，单条命令构建并拉起
- 计算全程无共享可变状态，并发请求互不干扰

## 计价口径（固定约定，三处一致）

设每年付息 `m` 次，年化到期收益率 `y`，年化票息率 `c`，面值 `F`，总期数 `n = 年数 × m`：

| 量 | 约定 |
| --- | --- |
| 每期折现率 | `r = y / m` |
| 每期票息 | `C = c × F / m`，末期同时偿还面值 `F` |
| 折现因子 | `DF_k = (1 + r)^(-k)`，`k = 1..n` |
| 全价（脏价） | `P = Σ CF_k × DF_k` |
| 麦考利久期 | `MacDur = Σ (k/m) × PV_k / P`（时间以**年**计） |
| 修正久期 | `ModDur = MacDur / (1 + r)` |
| 凸性 | `Conv = Σ [k(k+1)/m²] × PV_k / P / (1 + r)²` |

在此口径下严格有 `ModDur = -(1/P)·dP/dy`、`Conv = (1/P)·d²P/dy²`（测试用引擎自身
价格函数的中心差分锁定，见 `tests/test_conventions.py`）。

敏感度估计（`Δy` 为年化收益率的平行移动量）：

- 一阶：`P₁ = P × (1 − ModDur × Δy)`
- 二阶：`P₂ = P × (1 − ModDur × Δy + ½ × Conv × Δy²)`
- 精确重定价：把 `y + Δy` 重新代入完整定价管线计算，非写死结论。

收益率上行时 `P₁ < P_exact` 且 `P₂` 比 `P₁` 更贴近 `P_exact`（跌得更少），
由 `/sensitivity` 当场重算印证。

## 快速开始

### 容器（单条命令构建并拉起）

```bash
docker compose up --build
```

服务监听 `http://localhost:8000`。不用 compose 时：

```bash
docker build -t bond-pricer . && docker run --rm -p 8000:8000 bond-pricer
```

运行时基础镜像固定为 `python:3.12-slim`。

### 本地开发

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000   # 在 bond-pricing-service/ 目录下
pytest                                       # 运行测试
```

交互式 API 文档（OpenAPI 自动生成）：`http://localhost:8000/docs`。

## API

所有请求与响应均为 JSON。五个输入字段：`face_value`（面值）、`coupon_rate`
（年化票息率，小数）、`frequency`（每年付息次数：1/2/4/12）、
`years_to_maturity`（剩余到期年数）、`ytm`（年化到期收益率，小数）。

### `GET /sample-bond`

返回内置示范债券（5 年期平价债：面值 1000、票息 5%、半年付息、收益率 5%），
加载后即可复现平价与久期关系。

### `POST /price` — 定价

```bash
curl -s localhost:8000/price -H 'Content-Type: application/json' -d '{
  "face_value": 1000, "coupon_rate": 0.05, "frequency": 2,
  "years_to_maturity": 5, "ytm": 0.05
}'
```

返回全价与逐期现值明细（期次、时间、现金流、折现因子、现值）：

```json
{
  "input": {"face_value": 1000.0, "coupon_rate": 0.05, "frequency": 2, "years_to_maturity": 5.0, "ytm": 0.05},
  "periods": 10,
  "per_period_rate": 0.025,
  "dirty_price": 1000.0000000000008,
  "cashflows": [
    {"period": 1, "time_years": 0.5, "cashflow": 25.0, "discount_factor": 0.9756097561, "present_value": 24.3902439024},
    "...": "共 10 期，末期 cashflow = 25 + 1000 = 1025"
  ]
}
```

### `POST /risk` — 久期与凸性

同样的请求体，返回：

```json
{
  "dirty_price": 1000.0000000000008,
  "macaulay_duration": 4.485432764622605,
  "modified_duration": 4.376031965485469,
  "convexity": 22.61232218513058,
  "periods": 10, "per_period_rate": 0.025, "input": {"...": "..."}
}
```

### `POST /sensitivity` — 敏感度对照

请求体在债券参数外增加 `yield_shift`（年化收益率移动量，小数，如 `0.01` = +100bp）：

```bash
curl -s localhost:8000/sensitivity -H 'Content-Type: application/json' -d '{
  "face_value": 1000, "coupon_rate": 0.05, "frequency": 2,
  "years_to_maturity": 5, "ytm": 0.05, "yield_shift": 0.01
}'
```

```json
{
  "yield_shift": 0.01,
  "shifted_ytm": 0.06,
  "base_dirty_price": 1000.0000000000008,
  "modified_duration": 4.376031965485469,
  "convexity": 22.61232218513058,
  "first_order_estimate": 956.2396803451461,
  "second_order_estimate": 957.3702964544026,
  "exact_reprice": 957.3489858161207,
  "first_order_error": -1.1093054709746184,
  "second_order_error": 0.02131063828187507,
  "input": {"...": "..."}
}
```

收益率上行 100bp 时：一阶估计跌过头（误差 −1.109），叠加凸性项的二阶估计
误差仅 +0.021，且二者都由服务按新收益率重新精确定价后对照给出。

### 示范债券手工核对

5 年期平价债（`GET /sample-bond`）：`r = 0.025`，`n = 10`，每期票息 25。

- 全价 = `25 × a(10, 2.5%) + 1000 × 1.025^-10`
  = `25 × 8.7520639 + 1000 × 0.7811984` = **1000.00**（= 面值，平价关系成立）
- 麦考利久期 ≈ **4.485433** 年，修正久期 ≈ **4.376032**，凸性 ≈ **22.612322**
- 把票息率改为 0（零息债），麦考利久期恰好 = 剩余到期年数 5.0

## 输入校验

计算前完成全部校验，非法输入一律返回 HTTP 422 与结构化错误体，
绝不抛出未处理异常或返回残缺数字：

```json
{
  "error": {
    "code": "INVALID_BOND_PARAMETERS",
    "message": "invalid bond parameters: face_value: must be a positive finite number, got -100.0",
    "details": [{"field": "face_value", "issue": "must be a positive finite number, got -100.0"}]
  }
}
```

校验规则：

| 规则 | 说明 |
| --- | --- |
| `face_value > 0` | 面值必须为正 |
| `years_to_maturity > 0` | 剩余到期年数必须为正 |
| `coupon_rate >= 0` | 票息率不得为负 |
| `frequency ∈ {1, 2, 4, 12}` | 年付 / 半年付 / 季付 / 月付 |
| `1 + ytm/frequency > 0` | 否则某期折现因子非正 |
| `years_to_maturity × frequency` 为正整数 | 且总期数 ≤ 1200 |
| 所有数值必须有限 | NaN / Inf 拒绝 |
| 请求体缺字段 / 类型错误 | 返回 `MALFORMED_REQUEST` 错误 |

`sensitivity` 端点中，移动后的收益率同样经过完整校验（例如移动后使
`1 + r ≤ 0` 会被拒绝）。

## 测试

```bash
pip install -r requirements-dev.txt
pytest
```

覆盖的基准行为：

- 平价债全价 = 面值（含各付息频率下仍平价）
- 零息债麦考利久期 = 剩余到期年数
- 仅抬高收益率 ⇒ 全价严格下降
- 付息频率成倍加密后：价格仍等于逐期现值之和，久期/凸性与引擎自身
  价格函数的数值微分一致（口径自洽）
- 一阶/二阶敏感度与精确重定价的对照关系（收益率上行时二阶更贴近）
- 各类非法输入被拒并返回结构化错误
- 并发请求相互隔离、结果各自正确

## 工程结构

```
app/
  cashflows.py     现金流梯子构建（末期票息 + 面值）
  pricing.py       折现因子、逐期贴现、全价求和
  risk.py          麦考利/修正久期、凸性
  sensitivity.py   一阶/二阶价格敏感度估计
  validation.py    计算前的输入校验与派生量
  engine.py        组合层：校验 → 梯子 → 定价 → 风险 → 敏感度（纯函数，无共享状态）
  models.py        HTTP 边界的请求/响应模型
  sample.py        内置示范债券（5 年期平价债）
  main.py          FastAPI 应用与路由、统一错误响应
tests/             上述各组基准行为的测试
Dockerfile         python:3.12-slim 运行时
docker-compose.yml 单命令构建并拉起
```
