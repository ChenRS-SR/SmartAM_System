# SLM 表格故障诊断数据集与评估说明

## 1. 数据真实性与来源

本诊断模块只使用 `/home/gjw/SLM/7103` 目录中的真实导出文件，不使用人工编造样本。当前统计由以下命令重新生成：

```bash
python SmartAM_System/diagnosis/build_fault_evaluation.py
```

该脚本会重新扫描 `7103` 下所有 `.csv` 文件，并输出：

- `diagnosis/slm_fault_report.json`：全量诊断报告
- `diagnosis/slm_fault_dataset_summary.json`：数据集统计摘要
- `diagnosis/slm_fault_status_summary.csv`：各状态码样本数
- `diagnosis/slm_fault_eval_metrics.csv`：全量一致性评估指标
- `diagnosis/slm_fault_100_sample_test.csv`：100 条测试样本完整表
- `diagnosis/slm_fault_100_sample_test.md`：100 条测试样本 Markdown 表

## 2. 数据集构建方法

样本单位不是单行传感器数据，而是一个导出批次目录。脚本递归扫描 `7103` 下所有 CSV 文件，并按 CSV 所在目录聚合为一个样本。一个样本通常包含：

- `设备信息.csv` 或 `设备信息_设备信息.csv`
- `报警日志.csv`
- `*故障*.csv`
- `*样本数据.csv`
- `伺服温度*`、`温度及其他参数*` 等过程参数文件

这样划分的原因是：同一个目录对应一次设备导出或一次成形/报警窗口，目录内文件共同描述同一批次状态。脚本不写死设备号，不写死目录层级，设备号从路径中的 `Bxx` 自动提取。

CSV 编码按 `utf-8-sig`、`utf-16`、`gb18030` 依次尝试读取，覆盖当前数据中的 UTF-16 报警日志和 UTF-8 参数表。

## 3. 标签来源

标签来自真实导出文件中的显式故障信息，属于“银标签”，不是人工二次标注。

标签证据来源按优先级聚合：

- 故障文件名：例如 `2024-10-16_08-23-18_刮刀故障_故障暂停，刮刀扭矩故障.csv`
- 报警日志字段：`报警日志.csv` 中的 `报警内容`
- 健康样本：同一批次目录中没有故障文件名、报警日志中也没有有效报警内容，则标为 `0=健康`

过程参数表中的扭矩、压力、氧含量、风机转速、流量、滤芯阻力、温度等数值列会被统计为 `feature_summary`，用于复核和后续扩展，但当前标签主要来自设备导出的报警/故障文本。

## 4. 状态码定义

状态码依据 `7103` 中真实出现的异常文本归纳，不绑定旧界面的 `1-4`：

| 状态码 | 标签 | 7103 样本数 | 是否在当前数据出现 |
|---:|---|---:|---:|
| 0 | 健康 | 930 | 是 |
| 1 | 成形室氧含量异常 | 131 | 是 |
| 2 | 铺粉检测缺粉/重铺异常 | 116 | 是 |
| 3 | 刮刀扭矩/位置故障 | 60 | 是 |
| 4 | 刮刀/平台伺服故障 | 2 | 是 |
| 5 | 落粉轴故障 | 4 | 是 |
| 6 | 灰桶/收粉/卸灰故障 | 22 | 是 |
| 7 | 预涂料/储粉粉位故障 | 8 | 是 |
| 8 | 风机转速/变速故障 | 30 | 是 |
| 9 | 气源/压缩空气/蝶阀压力故障 | 10 | 是 |
| 10 | 过滤器/滤芯/反吹故障 | 8 | 是 |
| 11 | 蝶阀开关状态故障 | 2 | 是 |
| 12 | 激光器/水冷机故障 | 17 | 是 |
| 13 | 扫描/急停/安全回路故障 | 0 | 否 |
| 14 | 工艺参数/配置异常 | 20 | 是 |
| 90 | 多系统复合故障 | 230 | 是 |

当前 `7103` 中实际出现的故障状态码有 14 种，其中单类故障 13 种，复合故障 1 种。`13=扫描/急停/安全回路故障` 已在规则中保留，但按当前批次样本划分没有单独出现；它多出现在复合故障中。

## 5. 当前 7103 数据统计

统计来源：`diagnosis/slm_fault_dataset_summary.json`。

| 指标 | 数值 | 说明 |
|---|---:|---|
| CSV 文件总数 | 6310 | `7103` 下全部 CSV |
| 样本总数 | 1590 | 一个导出批次目录为一个样本 |
| 设备数量 | 25 | 从路径自动提取 `Bxx` |
| 健康样本数 | 930 | 无故障证据 |
| 故障样本数 | 660 | 状态码非 0 的批次样本 |
| 故障 CSV 文件数 | 325 | 文件名包含 `故障` 的 CSV |
| 故障证据记录数 | 2132 | 文件名证据 + 报警日志证据 |

设备列表为：

`B10, B14, B15, B16, B17, B19, B20, B26, B27, B28, B29, B30, B33, B34, B35, B38, B39, B40, B43, B44, B45, B46, B5, B6, B8`

## 6. 规则模型如何构建

规则文件为 `diagnosis/slm_fault_rules.json`。构建流程如下：

1. 扫描所有故障文件名和报警日志文本。
2. 统计高频真实异常短语，例如 `成形室氧含量高于上限报警值`、`铺粉检测AI检测到缺粉`、`刮刀扭矩故障`、`风机转速高于上限报警值`、`激光器水冷机故障`。
3. 将同义或同系统异常合并为状态码类别。
4. 若同一批次命中多个类别，则输出 `90=多系统复合故障`，并在 `status_labels` 中保留包含的具体故障类别。

模型是规则模型，不是神经网络或统计学习模型，因此没有训练参数，也不存在训练集/验证集的随机划分。这里的“实验评估”是对真实导出日志银标签的覆盖一致性检查。

## 7. 样本抽取和测试划分

全量评估使用所有 1590 个样本。

100 条样本测试表采用确定性分层抽样：

1. 按 `status_code` 分组。
2. 每个已出现状态码至少抽取 1 条样本。
3. 剩余名额按各状态码在全量数据中的样本数比例分配。
4. 每组内部按 `status_code, device_id, case_dir` 排序后抽取，不使用随机数。

完整 100 条表见：

- `diagnosis/slm_fault_100_sample_test.csv`
- `diagnosis/slm_fault_100_sample_test.md`

表中字段包括：设备号、样本目录、真实数据文本、证据文件、真实标签、预测标签、置信度、是否正确。

## 8. 实验指标

评估文件：`diagnosis/slm_fault_eval_metrics.csv`。

这里的 `ACC/Precision/Recall/F1` 是相对于设备导出日志银标签的一致性指标。它证明当前规则能完整覆盖本批 `7103` 已归纳的标签体系，但不等同于人工专家金标或跨新设备泛化准确率。

| 范围 | Support | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| 全量 1590 样本 | 1590 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 100 条分层测试样本 | 100 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

按状态码的详细指标在 `slm_fault_eval_metrics.csv` 中。之所以当前指标为 100%，是因为标签和模型均基于同一批真实导出报警/故障文本，属于规则映射一致性测试。后续如果要声称“人工金标准确率 >95%”，需要人工复核一批独立样本后，把人工标签作为 `true_label` 重新计算。

## 9. 100 样本测试表说明

`diagnosis/slm_fault_100_sample_test.md` 中每一行都包含真实数据证据。例如：

| sample_id | device_id | true_status_code | true_label | pred_status_code | pred_label | confidence | real_data_text |
|---:|---|---:|---|---:|---|---:|---|
| 2 | B14 | 1 | 成形室氧含量异常 | 1 | 成形室氧含量异常 | 0.78 | 故障暂停，成形室氧含量高于上限报警值 |
| 3 | B10 | 2 | 铺粉检测缺粉/重铺异常 | 2 | 铺粉检测缺粉/重铺异常 | 0.86 | 故障暂停，铺粉检测AI检测到缺粉!层号：1655 |
| 4 | B14 | 3 | 刮刀扭矩/位置故障 | 3 | 刮刀扭矩/位置故障 | 0.78 | 2024-10-16 08-23-18 刮刀故障 故障暂停，刮刀扭矩故障 |

完整表中保留了 `evidence_file`，可以直接回溯到 `7103` 中的原始 CSV 文件。

## 10. 使用方式

全量诊断：

```bash
python SmartAM_System/diagnosis/slm_fault_diagnose.py \
  --data-root 7103 \
  --output SmartAM_System/diagnosis/slm_fault_report.json
```

重新生成统计和实验表：

```bash
python SmartAM_System/diagnosis/build_fault_evaluation.py
```

持续监控新增 CSV：

```bash
python SmartAM_System/diagnosis/slm_fault_diagnose.py \
  --data-root 7103 \
  --output SmartAM_System/diagnosis/slm_fault_report.json \
  --watch \
  --interval 30
```

推送到现有 SLM 后端：

```bash
python SmartAM_System/diagnosis/slm_fault_diagnose.py \
  --data-root 7103 \
  --output SmartAM_System/diagnosis/slm_fault_report.json \
  --api-url http://127.0.0.1:8000/slm/health/status \
  --device-id B40
```

后端内部也可以读取报告中的 `device_latest_status[设备号]`，再调用：

```python
acquisition.update_health_status(result["status_code"], result["status_labels"])
```

## 11. 后续接入注意

前端目前如果只支持旧状态码 `0-4`，需要按 `diagnosis/slm_fault_rules.json` 中的 `status_codes` 扩展图标、文字和颜色。状态码可以继续增删，但应同步更新：

- `diagnosis/slm_fault_rules.json`
- SLM 后端健康状态映射
- 前端设备状态显示组件
- 本说明文档中的状态码表
