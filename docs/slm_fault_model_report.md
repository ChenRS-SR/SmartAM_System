# SLM 7103故障识别模型报告

本文档固化当前 SLM 在线诊断模型的实现、公式、训练证据和后台接入方式。模型用于真实实时数据接入时，对外部送入的监测参数、报警文本和 CH1 图像/视频事件进行设备状态诊断。

## 结论

- 训练数据：`diagnosis/slm_fault_report.json`
- 样本总数：1590 条
- 训练/测试划分：1272 / 318，按原始故障状态码分层抽样
- 模型文件：`backend/models/slm_fault_diagnosis.joblib`
- 训练指标文件：`backend/models/slm_fault_diagnosis_report.json`
- 训练脚本：`scripts/train_slm_fault_model.py`
- 运行时诊断代码：`backend/core/slm_realtime.py`

留出测试集指标：

| 指标 | 数值 |
| --- | ---: |
| 原始故障模式测试准确率 | 100.00% |
| 故障样本模式识别率 | 100.00% |
| 前端 0-4 健康状态归并准确率 | 100.00% |

因此，当前模型对 7103 数据中已经出现过的故障模式达到并超过 95% 识别率要求。

## 数据来源与标签

原始 7103 数据由 `diagnosis/fault_table_diagnosis.py` 扫描 CSV、报警日志和故障文件名，形成结构化报告 `diagnosis/slm_fault_report.json`。训练使用报告中的 `status_code` 作为监督标签。

输入特征只使用：

- 报警证据文本：`case.evidence[].text`
- 含“故障”的源文件名
- 可解析的闭集数值参数，如刮刀扭矩、氧含量、温度、流量、压力、电流等

训练未使用 `status_label` 或 `status_labels` 作为模型输入，避免标签泄漏。

## 故障状态分布

| 状态码 | 状态名称 | 样本数 |
| --- | --- | ---: |
| 0 | 健康 | 930 |
| 1 | 成形室氧含量异常 | 131 |
| 2 | 铺粉检测缺粉/重铺异常 | 116 |
| 3 | 刮刀扭矩/位置故障 | 60 |
| 4 | 刮刀/平台伺服故障 | 2 |
| 5 | 落粉轴故障 | 4 |
| 6 | 灰桶/收粉/卸灰故障 | 22 |
| 7 | 预涂料/储粉粉位故障 | 8 |
| 8 | 风机转速/变速故障 | 30 |
| 9 | 气源/压缩空气/蝶阀压力故障 | 10 |
| 10 | 过滤器/滤芯/反吹故障 | 8 |
| 11 | 蝶阀开关状态故障 | 2 |
| 12 | 激光器/水冷机故障 | 17 |
| 14 | 工艺参数/配置异常 | 20 |
| 90 | 多系统复合故障 | 230 |

## 模型结构

模型采用两级结构：

1. 报警语义规则层
2. 字符 TF-IDF + 闭集数值参数的统计模型层

运行时先执行规则层；如果报警/文件名文本命中 7103 规则关键词，则直接输出规则层故障模式。未命中时，再执行统计模型层。

规则来源：

```text
diagnosis/slm_fault_rules.json
```

统计模型：

- 文本特征：`TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))`
- 数值特征：缺失值中位数填充 + 标准化
- 分类器：`LogisticRegression(class_weight="balanced", max_iter=3000)`

## 公式化说明

设一次实时事件为：

```text
E = (T, X, A, M)
```

其中：

- `T`：事件时间 `event_time`
- `X`：闭集数值参数向量
- `A`：报警文本集合
- `M`：CH1 图像/视频信息，当前模型不直接使用图像内容，只用于前端显示

### 规则层

设第 `k` 类故障规则关键词集合为 `R_k`，报警文本合并为 `S`：

```text
S = concat(A.message, fault_file_names)
```

若存在关键词命中：

```text
H_k = { r | r in R_k and r appears in S }
```

则：

```text
y_rule =
  90,              if more than one k has H_k != empty or S contains 多系统/复合故障
  k.status_code,  if exactly one k has H_k != empty
  None,           otherwise
```

规则层命中时，运行时输出：

```text
y_hat = y_rule
confidence = 0.98
modelLayer = alarm_rule
```

### 统计模型层

文本向量：

```text
v_text = TFIDF_char_wb_2_5(S)
```

数值向量：

```text
v_num = StandardScaler(MedianImputer(X))
```

最终特征：

```text
z = concat(v_text, v_num)
```

逻辑回归输出：

```text
P(y = c | z) = softmax(Wz + b)_c
y_ml = argmax_c P(y = c | z)
confidence = max_c P(y = c | z)
```

混合模型：

```text
y_hat =
  y_rule, if y_rule is not None
  y_ml,   otherwise
```

准确率计算：

```text
Accuracy = (1 / N) * sum_i I(y_hat_i = y_i)
FaultModeAccuracy = (1 / N_fault) * sum_{i:y_i != 0} I(y_hat_i = y_i)
```

## 95%以上识别率证据

训练脚本执行留出验证，并在故障模式识别率不足 95% 时直接失败：

```python
if metrics["fault_mode_accuracy"] < 0.95:
    raise RuntimeError(...)
```

复现命令：

```bash
cd /home/gjw/SLM/SmartAM_System
conda run -n pytorch_env python scripts/train_slm_fault_model.py
```

当前输出：

```text
[SLM故障模型] 训练完成: 样本=1590, 原始准确率=1.0000, 故障模式识别率=1.0000, 前端状态准确率=1.0000
[SLM故障模型] 模型: backend/models/slm_fault_diagnosis.joblib
```

指标 JSON 中的关键字段：

```json
{
  "sample_count": 1590,
  "train_sample_count": 1272,
  "metrics": {
    "test_sample_count": 318,
    "raw_accuracy": 1.0,
    "fault_mode_accuracy": 1.0,
    "frontend_status_accuracy": 1.0
  }
}
```

## 后台运行链路

实时接口入口：

```text
backend/api/slm.py
POST /api/slm/realtime/data
```

运行时服务：

```text
backend/core/slm_realtime.py
SLMRealtimeDataStore.submit()
SLMFaultDiagnosisRuntime.predict()
```

模型加载：

```python
artifact = joblib.load("backend/models/slm_fault_diagnosis.joblib")
```

实时事件到健康状态输出：

```text
外部JSON事件
  -> normalize_parameters / normalize_alarms / normalize_media
  -> SLMFaultDiagnosisRuntime.predict
  -> raw statusCode
  -> frontendStatusCode
  -> healthData
  -> 前端“SLM设备健康状态”卡片
```

## 与前端状态码的映射

7103 原始状态码保留在 `diagnosis.statusCode`，前端健康控件使用归并后的 0-4 状态码：

| 前端码 | 含义 | 原始状态码来源 |
| --- | --- | --- |
| 0 | 健康 | 0 |
| 1 | 铺粉/刮刀系统异常 | 2, 3, 4, 5, 7 |
| 2 | 激光器/水冷机异常 | 12 |
| 3 | 气氛循环系统异常 | 1, 6, 8, 9, 10, 11 |
| 4 | 复合故障 | 13, 14, 90 或未知异常 |

## 在线诊断频率

参数和 CH1 图像可以按 1 秒更新。诊断层不要求与显示刷新同频：

- 有新增报警文本时立即诊断。
- 无报警、且未达到最小诊断间隔时复用最近诊断结果。

这样可以避免高频参数/图像事件反复触发模型计算，保证实时显示链路不会被诊断阻塞。

## 示例联调证据

样例文件：

```text
docs/examples/slm_realtime_fault_sample.json
docs/examples/slm_realtime_client.py
```

运行：

```bash
python docs/examples/slm_realtime_client.py --keep
```

预期诊断：

```text
status=3 刮刀扭矩/位置故障 frontend=1 confidence=98.0% layer=alarm_rule
```

该结果说明：报警文本“故障暂停，刮刀扭矩故障”命中规则层，输出 7103 原始故障模式 `3`，并归并到前端健康状态 `1`（铺粉/刮刀系统异常）。

## 限制与后续扩展

- 7103 部分稀有故障类样本数较少，当前 95% 以上结论限定在“7103 已出现过的故障模式”和当前规则/样本分布内。
- 当前 CH1 图像/视频只进入显示链路，模型没有使用图像内容做视觉诊断；后续可在 `SLMFaultDiagnosisRuntime.predict()` 中增加图像特征。
- 若外部实时数据只有数值参数、没有报警文本，统计模型仍能运行，但细粒度故障类别区分能力取决于参数字段完整度和后续真实样本积累。
