# 贡献指南 (Contributing Guide)

感谢您对 SmartAM_System 项目的关注！本文档将帮助您了解如何参与项目开发。

## 📋 目录

- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [分支策略](#分支策略)
- [Pull Request 流程](#pull-request-流程)

---

## 开发流程

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/SmartAM_System.git
cd SmartAM_System
```

### 2. 创建开发分支

```bash
# 从 main 分支创建新分支
git checkout -b feature/your-feature-name

# 或者修复 bug
git checkout -b fix/bug-description
```

### 3. 安装依赖

**后端:**
```bash
cd backend
conda create -n pytorch_env python=3.9
conda activate pytorch_env
pip install -r requirements.txt
```

**前端:**
```bash
cd frontend
npm install
```

### 4. 开发与测试

- 编写代码
- 添加必要的注释
- 本地测试通过

### 5. 提交代码

```bash
git add .
git commit -m "feat: 添加新功能"
git push origin feature/your-feature-name
```

---

## 代码规范

### Python 代码规范

- 遵循 PEP 8 规范
- 使用 4 空格缩进
- 函数和类添加 docstring
- 关键逻辑添加注释

```python
def example_function(param1: str, param2: int) -> bool:
    """
    函数简要说明
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
    
    Returns:
        返回值说明
    """
    # 实现代码
    return True
```

### JavaScript/Vue 代码规范

- 使用 2 空格缩进
- 组件名使用 PascalCase
- 变量名使用 camelCase
- 常量使用 UPPER_SNAKE_CASE

```javascript
// 常量
const MAX_RETRY_COUNT = 3

// 函数
function fetchData() {
  // 实现
}

// 组件
export default {
  name: 'MyComponent',
  data() {
    return {
      count: 0
    }
  }
}
```

---

## 提交规范

使用 **Conventional Commits** 规范：

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加红外相机支持` |
| `fix` | 修复 bug | `fix: 修复 M114 坐标解析问题` |
| `docs` | 文档更新 | `docs: 更新 API 文档` |
| `style` | 代码格式 | `style: 格式化代码` |
| `refactor` | 重构 | `refactor: 优化数据采集逻辑` |
| `test` | 测试相关 | `test: 添加单元测试` |
| `chore` | 构建/工具 | `chore: 更新依赖` |

### 提交示例

```bash
# 新功能
git commit -m "feat: 添加9组标准塔采集模式"

# 修复 bug
git commit -m "fix: 修复 Z 偏移计算错误

- 修复了 initial_z_offset 和 z_offset 的混淆
- 更新了相关文档"

# 文档更新
git commit -m "docs: 添加部署指南"

# 作用域示例
git commit -m "feat(backend): 添加 WebSocket 重连机制"
git commit -m "feat(frontend): 优化 Dashboard 性能"
```

---

## 分支策略

```
main (生产分支)
  ↑
  │
develop (开发分支) ←── feature/xxx (功能分支)
  ↑                      │
  │                      └── PR → develop
  │
  └── hotfix/xxx (紧急修复) → main + develop
```

### 分支命名

- `feature/description` - 新功能
- `fix/description` - 修复 bug
- `docs/description` - 文档更新
- `refactor/description` - 代码重构
- `hotfix/description` - 紧急修复

---

## Pull Request 流程

### 1. 创建 PR 前检查

- [ ] 代码已通过本地测试
- [ ] 更新了相关文档
- [ ] 没有合并冲突
- [ ] 提交信息符合规范

### 2. PR 标题格式

```
[type](scope): 简要描述

示例:
feat(backend): 添加闭环控制算法
fix(frontend): 修复视频流显示问题
docs: 更新 README 安装说明
```

### 3. PR 描述模板

```markdown
## 变更内容
简要说明这次 PR 做了什么

## 解决的问题
- 问题1
- 问题2

## 测试方式
- [ ] 本地测试通过
- [ ] 单元测试通过

## 截图（如有 UI 变更）

## 注意事项
- 需要注意的点
- 破坏性变更说明
```

### 4. 代码审查

- 至少需要 1 个 Reviewer 批准
- 解决所有评论问题
- CI 检查通过

---

## 协作建议

### 与团队成员协作

1. **保持沟通**: 在开始大规模改动前，先在 Issue 中讨论
2. **小步快跑**: 提交小而完整的改动，方便审查
3. **及时同步**: 定期从主分支同步代码，减少冲突
4. **文档同步**: 代码改动时同步更新文档

### 解决冲突

```bash
# 1. 同步主分支最新代码
git checkout main
git pull origin main

# 2. 切换到功能分支并合并
git checkout feature/xxx
git merge main

# 3. 解决冲突后提交
git add .
git commit -m "merge: 解决合并冲突"
```

---

## 开发环境配置

### 推荐 IDE

- **Python**: VS Code + Python 插件 + Pylance
- **Vue**: VS Code + Volar + ESLint

### VS Code 配置

项目已包含 `.vscode/settings.json`：

```json
{
  "editor.tabSize": 2,
  "editor.insertSpaces": true,
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "eslint.workingDirectories": ["./frontend"]
}
```

---

## 获取帮助

- 📧 邮件: your-email@example.com
- 💬 微信工作群: xxx
- 📋 Issues: https://github.com/your-username/SmartAM_System/issues

感谢您对项目的贡献！🎉
