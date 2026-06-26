# SLM表格故障诊断接入说明

## 目标

本模块读取设备导出的CSV数据，输出SLM界面可直接使用的健康状态码。状态码不是固定在旧界面的 `1-4`，而是依据 `7103` 数据中真实出现的异常类别归纳：

- `0`：健康
- `1`：成形室氧含量异常
- `2`：铺粉检测缺粉/重铺异常
- `3`：刮刀扭矩/位置故障
- `4`：刮刀/平台伺服故障
- `5`：落粉轴故障
- `6`：灰桶/收粉/卸灰故障
- `7`：预涂料/储粉粉位故障
- `8`：风机转速/变速故障
- `9`：气源/压缩空气/蝶阀压力故障
- `10`：过滤器/滤芯/反吹故障
- `11`：蝶阀开关状态故障
- `12`：激光器/水冷机故障
- `13`：扫描/急停/安全回路故障
- `14`：工艺参数/配置异常
- `90`：多系统复合故障

规则模型文件固定在 `diagnosis/slm_fault_rules.json`。后续新增设备或新增批次时，不需要改代码，只要把CSV继续放到数据根目录下重新运行脚本，或使用 `--watch` 持续监控。

## 数据读取逻辑

脚本递归扫描 `--data-root` 下所有 `.csv` 文件，并按CSV所在目录聚合为一个诊断批次。设备号从路径中的 `Bxx` 自动提取，不绑定固定设备列表。

证据来源包括：

- 文件名中的故障描述，例如 `2025-01-21_09-30-57_刮刀故障_故障暂停，刮刀扭矩故障.csv`
- `报警日志.csv` 中的 `报警内容`
- 故障窗口表格中的关键数值列统计，例如扭矩、压力、氧含量、风机转速、流量、滤芯阻力、温度

很多 `output1/output2` 故障CSV为空文件，但文件名包含有效故障信息；脚本会正常使用文件名作为证据。

## 运行命令

在仓库根目录执行：

```bash
python SmartAM_System/diagnosis/slm_fault_diagnose.py \
  --data-root 7103 \
  --output SmartAM_System/diagnosis/slm_fault_report.json
```

输出JSON中的关键字段：

- `status_counts`：所有批次的状态码分布
- `fault_type_counts`：故障类型分布
- `device_latest_status`：每台设备当前应展示的最新状态
- `cases`：每个批次的完整诊断结果和证据

`device_latest_status` 和 `cases` 中都会给出 `status_code`、`status_label`、`status_labels`、`categories` 和 `evidence`。前端后续可以按 `diagnosis/slm_fault_rules.json` 中的 `status_codes` 自动扩展界面状态。

## 持续新增数据

如果后续CSV会持续追加到目录中，使用轮询模式：

```bash
python SmartAM_System/diagnosis/slm_fault_diagnose.py \
  --data-root 7103 \
  --output SmartAM_System/diagnosis/slm_fault_report.json \
  --watch \
  --interval 30
```

`--watch` 会在CSV数量或最新修改时间变化时重新生成报告。

## 接入SLM界面

现有后端已经提供健康状态接口：

```text
POST /slm/health/status
GET  /slm/health/status
```

可以直接把脚本结果中的 `status_code` 和 `status_labels` 推送给后端：

```bash
python SmartAM_System/diagnosis/slm_fault_diagnose.py \
  --data-root 7103 \
  --output SmartAM_System/diagnosis/slm_fault_report.json \
  --api-url http://127.0.0.1:8000/slm/health/status \
  --device-id B40
```

后端内部调用时，也可以读取报告中的 `device_latest_status[设备号]`，再调用：

```python
acquisition.update_health_status(result["status_code"], result["status_labels"])
```

## 模型调整

如果需要新增故障类别，优先修改 `diagnosis/slm_fault_rules.json`：

- 在 `status_codes` 中增加状态码名称
- 在 `rules` 中增加 `category/status_code/label/keywords`

当前前端健康组件原先主要支持旧的 `0-4`，后续接入时应按本模型的 `status_codes` 扩展状态图片和 `SLMHealthState.update_health_status()` 映射。模型本身不限制状态码数量，真实故障类别变化时可继续增删规则。
