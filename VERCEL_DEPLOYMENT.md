# AI知识库系统 - Vercel部署指南

## 🚀 Vercel云端部署

本指南将帮助您将AI知识库系统部署到Vercel平台，实现生产环境的云端运行。

## 📋 部署前准备

### 1. 账户准备
- 注册Vercel账户: https://vercel.com
- 安装Vercel CLI: `npm i -g vercel`
- 准备GitHub仓库（推荐）

### 2. 项目结构
```
ai-knowledge-base/
├── api/
│   ├── index.py          # 用户前端API
│   └── admin.py          # 管理后台API
├── vercel.json           # Vercel配置文件
├── requirements-vercel.txt # Vercel专用依赖
└── VERCEL_DEPLOYMENT.md  # 本文档
```

## 🔧 部署步骤

### 方式一：一键部署脚本（推荐）

我们提供了自动化部署脚本，可以一键完成整个部署流程：

```bash
# 预览部署（推荐用于测试）
python deploy-vercel.py --preview

# 生产部署
python deploy-vercel.py --prod

# 交互式选择部署类型
python deploy-vercel.py
```

**脚本功能：**
- ✅ 自动检查前置条件（Node.js、npm）
- ✅ 自动安装Vercel CLI
- ✅ 引导完成Vercel登录
- ✅ 自动配置环境变量
- ✅ 执行部署并验证
- ✅ 显示访问地址和账户信息

### 方式二：通过Vercel CLI部署（手动）

1. **登录Vercel**
   ```bash
   vercel login
   ```

2. **进入项目目录**
   ```bash
   cd ai-knowledge-base
   ```

3. **初始化项目**
   ```bash
   vercel
   ```
   
   按提示选择：
   - Set up and deploy? `Y`
   - Which scope? 选择您的账户
   - Link to existing project? `N`
   - Project name: `ai-knowledge-base`
   - Directory: `./`

4. **部署到生产环境**
   ```bash
   vercel --prod
   ```

### 方式二：通过GitHub自动部署

1. **推送代码到GitHub**
   ```bash
   git add .
   git commit -m "Add Vercel deployment configuration"
   git push origin main
   ```

2. **在Vercel控制台导入项目**
   - 访问 https://vercel.com/dashboard
   - 点击 "New Project"
   - 选择您的GitHub仓库
   - 点击 "Import"

3. **配置项目设置**
   - Framework Preset: `Other`
   - Root Directory: `./`
   - Build Command: 留空
   - Output Directory: 留空
   - Install Command: `pip install -r requirements-vercel.txt`

## ⚙️ 环境变量配置

在Vercel控制台的项目设置中添加以下环境变量：

| 变量名 | 值 | 说明 |
|--------|----|---------|
| `SECRET_KEY` | `your-secret-key-here` | JWT密钥 |
| `ENVIRONMENT` | `production` | 运行环境 |
| `DEBUG` | `false` | 调试模式 |

## 🌐 访问地址

部署成功后，您将获得以下访问地址：

- **用户前端**: `https://your-project.vercel.app/`
- **管理后台**: `https://your-project.vercel.app/admin/`
- **API文档**: `https://your-project.vercel.app/docs`
- **管理后台API**: `https://your-project.vercel.app/admin/docs`

## 👤 默认管理员账户

- **用户名**: `vee5208`
- **密码**: `forxy131`

> ⚠️ **安全提示**: 部署后请立即修改默认密码！

## 🔍 功能验证

### 1. 用户前端测试
- 访问首页，检查页面加载
- 测试聊天功能
- 浏览知识库列表
- 验证API响应

### 2. 管理后台测试
- 使用默认账户登录
- 查看仪表板数据
- 测试各项管理功能
- 验证权限控制

### 3. API测试
```bash
# 健康检查
curl https://your-project.vercel.app/health

# 管理后台健康检查
curl https://your-project.vercel.app/admin/health
```

## 📊 监控和维护

### Vercel Analytics
- 在项目设置中启用Analytics
- 监控访问量和性能指标
- 查看错误日志和函数调用

### 日志查看
```bash
# 查看实时日志
vercel logs your-project.vercel.app

# 查看函数日志
vercel logs your-project.vercel.app --follow
```

### 性能优化
- 启用Edge Functions（如需要）
- 配置缓存策略
- 优化冷启动时间

## 🔄 更新部署

### 自动部署
如果使用GitHub集成，每次推送到main分支都会自动触发部署。

### 手动部署
```bash
# 部署到预览环境
vercel

# 部署到生产环境
vercel --prod
```

## 🛠️ 故障排除

### 常见问题

1. **部署失败**
   - 检查`requirements-vercel.txt`依赖
   - 确认Python版本兼容性
   - 查看构建日志

2. **函数超时**
   - 检查`vercel.json`中的`maxDuration`设置
   - 优化代码性能
   - 考虑使用Edge Functions

3. **环境变量问题**
   - 确认所有必需的环境变量已设置
   - 检查变量名拼写
   - 重新部署以应用变量更改

4. **API路由问题**
   - 检查`vercel.json`路由配置
   - 确认文件路径正确
   - 测试本地开发环境

### 调试技巧

```bash
# 本地测试Vercel函数
vercel dev

# 查看详细部署日志
vercel logs --follow

# 检查项目配置
vercel inspect
```

## 🔒 安全配置

### 域名配置
1. 在Vercel控制台添加自定义域名
2. 配置SSL证书（自动）
3. 设置重定向规则

### 访问控制
- 配置CORS策略
- 设置API速率限制
- 启用安全头部

## 💰 成本优化

### Vercel免费额度
- 100GB带宽/月
- 100GB-hours函数执行时间
- 无限静态部署

### 优化建议
- 合理使用函数执行时间
- 优化API响应大小
- 使用适当的缓存策略

## 📞 技术支持

如遇到部署问题：
1. 查看Vercel官方文档
2. 检查项目日志和错误信息
3. 参考本项目的GitHub Issues
4. 联系技术支持团队

---

**部署完成后，您的AI知识库系统将在Vercel云端稳定运行！**

🌐 **在线演示**: https://your-project.vercel.app
🔧 **管理后台**: https://your-project.vercel.app/admin