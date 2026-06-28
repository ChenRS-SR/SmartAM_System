# SLM 7103 故障识别模型报告

本文档说明当前 SLM 故障识别模型的数据来源、标签构建、样本划分、实验指标和后台接入方式。所有统计均来自 `/home/gjw/SLM/7103` 目录中的真实导出文件；不使用人工编造样本。

## 1. 结论

当前系统包含两类产物：

| 产物 | 路径 | 作用 |
|---|---|---|
| 规则/银标签诊断报告 | `diagnosis/slm_fault_report.json` | 从真实 CSV、报警日志、故障文件名构建全量标签和诊断结果 |
| 规则模型 | `diagnosis/slm_fault_rules.json` | 保存状态码、故障类别、关键词规则 |
| 数据集统计 | `diagnosis/slm_fault_dataset_summary.json` | 设备数、样本数、故障数等可复现统计 |
| 100 样本测试表 | `diagnosis/slm_fault_100_sample_test.csv` | 真实数据、真实标签、预测值、置信度、是否正确 |
| 在线统计模型 | `backend/models/slm_fault_diagnosis.joblib` | 后台实时接口使用的 joblib 模型 |
| 训练指标 | `backend/models/slm_fault_diagnosis_report.json` | 训练/留出集指标 |
| 运行时服务 | `backend/core/slm_realtime.py` | 实时参数/报警接入和诊断输出 |

当前 `7103` 全量数据统计：

| 指标 | 数值 |
|---|---:|
| CSV 文件总数 | 6310 |
| 样本总数 | 1590 |
| 设备数量 | 25 |
| 健康样本数 | 930 |
| 故障样本数 | 660 |
| 当前出现故障状态码数 | 14 |
| 故障 CSV 文件数 | 325 |
| 故障证据记录数 | 2132 |

设备列表：

`B10, B14, B15, B16, B17, B19, B20, B26, B27, B28, B29, B30, B33, B34, B35, B38, B39, B40, B43, B44, B45, B46, B5, B6, B8`

## 2. 数据来源

数据根目录为：

```text
/home/gjw/SLM/7103
```

参与诊断的数据文件包括：

- `报警日志.csv`
- `设备信息.csv` / `设备信息_设备信息.csv`
- `*故障*.csv`
- `*样本数据.csv`
- `伺服温度*`、`温度及其他参数*` 等过程参数表

很多 `output1/output2/output3` 中的故障 CSV 是空文件，但文件名本身包含设备导出的故障类别和报警描述；这些文件名仍然是真实导出数据的一部分，因此作为标签证据保留。

## 3. 样本构建逻辑

样本单位为“一个导出批次目录”，不是单行 CSV 记录。

构建步骤：

1. 递归扫描 `7103` 下所有 `.csv` 文件。
2. 按 CSV 所在目录聚合，一个目录生成一个样本。
3. 从路径中自动提取设备号 `Bxx`。
4. 读取目录中的报警日志、故障文件名和参数表。
5. 生成一次批次级诊断结果。

这样做的原因是：同一目录中的 `设备信息`、`报警日志`、`故障窗口参数` 和 `样本数据` 描述同一次导出或同一个报警窗口，目录级样本比单行传感器数据更符合设备故障事件的粒度。

CSV 编码按以下顺序尝试：

```text
utf-8-sig -> utf-16 -> gb18030
```

## 4. 标签来源

标签来自真实导出文件中的显式故障证据，属于设备日志“银标签”，不是人工专家金标。

标签证据来源：

| 来源 | 字段/形式 | 示例 |
|---|---|---|
| 故障文件名 | 文件名中的故障文本 | `刮刀故障_故障暂停，刮刀扭矩故障.csv` |
| 报警日志 | `报警日志.csv` 的 `报警内容` | `故障暂停，成形室氧含量高于上限报警值` |
| 健康标签 | 同批次无故障文件名、报警日志无有效报警内容 | `0=健康` |

过程参数表中的扭矩、压力、氧含量、风机转速、流量、滤芯阻力、温度等数值列被统计到 `feature_summary`，用于复核和后续模型扩展；当前标签主要由报警/故障文本给出。

## 5. 状态码和故障分布

状态码依据 `7103` 中真实出现的异常文本归纳，不绑定旧界面的 `1-4`。

| 状态码 | 故障类别 | 样本数 |
|---:|---|---:|
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
| 13 | 扫描/急停/安全回路故障 | 0 |
| 14 | 工艺参数/配置异常 | 20 |
| 90 | 多系统复合故障 | 230 |

说明：`13=扫描/急停/安全回路故障` 已在规则中保留，但当前按批次聚合后没有作为单类故障独立出现；相关证据多出现在 `90=多系统复合故障` 中。

## 6. 规则模型

规则模型路径：

```text
diagnosis/slm_fault_rules.json
```

规则构建流程：

1. 扫描全部故障文件名和报警日志文本。
2. 统计高频真实异常短语。
3. 将同义或同系统异常合并为稳定状态码。
4. 同一批次命中多个故障类别时，输出 `90=多系统复合故障`。
5. 在 `status_labels` 中保留具体命中类别和关键词证据，供界面或人工复核显示。

规则层输出置信度不是概率模型输出，而是基于命中关键词数量和类别数的启发式分数，最高限制为 `0.95`，避免被误读为神经网络概率。

## 7. 100 条真实样本测试表

100 条测试样本由 `build_fault_evaluation.py` 确定性分层抽取：

1. 按 `status_code` 分组。
2. 每个已出现状态码至少抽取 1 条。
3. 剩余名额按全量样本分布比例分配。
4. 组内按 `status_code, device_id, case_dir` 排序抽取，不使用随机数。

完整表：

```text
diagnosis/slm_fault_100_sample_test.csv
diagnosis/slm_fault_100_sample_test.md
```

表字段包括：

| 字段 | 含义 |
|---|---|
| `sample_id` | 样本序号 |
| `device_id` | 设备号 |
| `case_dir` | 样本目录 |
| `evidence_source` | 证据来源 |
| `evidence_file` | 原始证据文件 |
| `real_data_text` | 真实报警/故障文本 |
| `true_status_code` | 真实状态码 |
| `true_label` | 真实标签 |
| `pred_status_code` | 预测状态码 |
| `pred_label` | 预测标签 |
| `confidence` | 置信度 |
| `correct` | 是否正确 |

示例：

| sample_id | device_id | true_status_code | true_label | pred_status_code | pred_label | confidence | real_data_text |
|---:|---|---:|---|---:|---|---:|---|
| 2 | B14 | 1 | 成形室氧含量异常 | 1 | 成形室氧含量异常 | 0.78 | 故障暂停，成形室氧含量高于上限报警值 |
| 3 | B10 | 2 | 铺粉检测缺粉/重铺异常 | 2 | 铺粉检测缺粉/重铺异常 | 0.86 | 故障暂停，铺粉检测AI检测到缺粉!层号：1655 |
| 4 | B14 | 3 | 刮刀扭矩/位置故障 | 3 | 刮刀扭矩/位置故障 | 0.78 | 2024-10-16 08-23-18 刮刀故障 故障暂停，刮刀扭矩故障 |

## 8. 规则/银标签一致性指标

评估文件：

```text
diagnosis/slm_fault_eval_metrics.csv
```

该指标表示规则诊断结果与设备日志银标签的一致性，不等同于人工专家金标泛化准确率。

| 范围 | Support | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| 全量样本 | 1590 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 100 条分层测试样本 | 100 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

为什么是 100%：当前规则和银标签都来自同一批设备导出的报警/故障文本，评估目标是证明规则对已归纳标签体系的覆盖一致性。若要声称“人工金标准确率 >95%”，需要另行抽样人工复核，使用人工标签替换 `true_label` 后重新计算。

## 9. 在线统计模型

在线模型路径：

```text
backend/models/slm_fault_diagnosis.joblib
```

训练脚本：

```text
scripts/train_slm_fault_model.py
```

训练报告：

```text
backend/models/slm_fault_diagnosis_report.json
```

训练输入来自 `diagnosis/slm_fault_report.json`，监督标签为 `status_code`。模型输入不直接使用 `status_label` 或 `status_labels`，避免标签泄漏。

输入特征包括：

- 报警证据文本：`case.evidence[].text`
- 含 `故障` 的源文件名
- 可解析的闭集数值参数，如刮刀扭矩、氧含量、温度、流量、压力、电流等

统计模型结构：

| 模块 | 配置 |
|---|---|
| 文本特征 | `TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))` |
| 数值特征 | 缺失值中位数填充 + 标准化 |
| 分类器 | `LogisticRegression(class_weight="balanced", max_iter=3000)` |

训练/测试划分：

| 项目 | 数值 |
|---|---:|
| 总样本数 | 1590 |
| 训练样本数 | 1272 |
| 测试样本数 | 318 |
| 划分方式 | 按状态码分层留出 |

留出测试集指标：

| 指标 | 数值 |
|---|---:|
| 原始故障模式测试准确率 | 1.0000 |
| 故障样本模式识别率 | 1.0000 |
| 前端 0-4 健康状态归并准确率 | 1.0000 |

同样需要注意：该结果仍然基于 `7103` 银标签，不代表跨新设备、人工金标场景一定达到 100%。

## 10. 公式化说明

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

关键词命中集合：

```text
H_k = { r | r in R_k and r appears in S }
```

规则输出：

```text
y_rule =
  90,              if more than one k has H_k != empty or S contains 多系统/复合故障
  k.status_code,  if exactly one k has H_k != empty
  None,           otherwise
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

混合输出：

```text
y_hat =
  y_rule, if y_rule is not None
  y_ml,   otherwise
```

准确率：

```text
Accuracy = (1 / N) * sum_i I(y_hat_i = y_i)
FaultModeAccuracy = (1 / N_fault) * sum_{i:y_i != 0} I(y_hat_i = y_i)
```

## 11. 后台运行链路

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

## 12. 与前端状态码的映射

`7103` 原始状态码保留在 `diagnosis.statusCode`，当前前端健康控件使用归并后的 `0-4` 状态码：

| 前端码 | 含义 | 原始状态码来源 |
|---:|---|---|
| 0 | 健康 | 0 |
| 1 | 铺粉/刮刀系统异常 | 2, 3, 4, 5, 7 |
| 2 | 激光器/水冷机异常 | 12 |
| 3 | 气氛循环系统异常 | 1, 6, 8, 9, 10, 11 |
| 4 | 复合故障 | 13, 14, 90 或未知异常 |

## 13. 复现命令

重新生成规则诊断报告、数据集统计、100 样本表和银标签指标：

```bash
cd /home/gjw/SLM
python SmartAM_System/diagnosis/build_fault_evaluation.py
```

重新训练在线统计模型：

```bash
cd /home/gjw/SLM/SmartAM_System
conda run -n pytorch_env python scripts/train_slm_fault_model.py
```

基础语法检查：

```bash
cd /home/gjw/SLM
python -m py_compile \
  SmartAM_System/diagnosis/fault_table_diagnosis.py \
  SmartAM_System/diagnosis/slm_fault_diagnose.py \
  SmartAM_System/diagnosis/build_fault_evaluation.py
```

## 14. 结论边界

当前结果可以支持以下结论：

- 对 `7103` 已归纳的设备导出银标签，规则诊断全量一致性为 100%。
- 100 条分层真实样本表中，预测标签与银标签一致率为 100%。
- 在线统计模型在 `7103` 银标签分层留出测试集上，原始故障模式准确率为 100%。

当前结果不能直接支持以下结论：

- 人工专家金标准确率为 100%。
- 新设备、新故障类型或未见报警文本上仍保持 100%。
- 图像内容本身已参与故障分类。

若后续需要正式宣称“>95% 人工金标准确率”，应新增人工复核样本表，并使用人工标签重新计算 ACC、Precision、Recall、F1。
