# AI知识库系统 - 部署指南

## 📋 系统要求

### 最低配置
- **CPU**: 2核心
- **内存**: 4GB RAM
- **存储**: 20GB 可用空间
- **操作系统**: Linux/Windows/macOS
- **Python**: 3.8+
- **Docker**: 20.10+ (可选)

### 推荐配置
- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 50GB SSD
- **网络**: 100Mbps+

## 🚀 部署方式

### 方式一：Docker 部署（推荐）

#### 1. 克隆项目
```bash
git clone <repository-url>
cd ai-knowledge-base
```

#### 2. 配置环境变量
```bash
cp .env.example .env.production
# 编辑 .env.production 文件，配置相关参数
```

#### 3. 构建并启动
```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

#### 4. 访问服务
- **用户前端**: http://localhost:8000
- **管理后台**: http://localhost:8003
- **Nginx代理**: http://localhost:80

### 方式二：直接部署

#### 1. 安装依赖
```bash
pip install -r requirements.txt
```

#### 2. 配置环境
```bash
cp .env.example .env
# 编辑配置文件
```

#### 3. 启动服务
```bash
# 生产环境启动
python deploy.py

# 或者分别启动
uvicorn main_user_frontend:app --host 0.0.0.0 --port 8000 --workers 4
uvicorn admin_backend:app --host 0.0.0.0 --port 8003 --workers 2
```

### 方式三：系统服务部署

#### 1. 创建服务文件
```bash
sudo nano /etc/systemd/system/ai-knowledge-base.service
```

```ini
[Unit]
Description=AI Knowledge Base System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/ai-knowledge-base
ExecStart=/usr/bin/python3 deploy.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 2. 启用服务
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-knowledge-base
sudo systemctl start ai-knowledge-base
sudo systemctl status ai-knowledge-base
```

## 🔧 配置说明

### 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ENVIRONMENT` | 运行环境 | `production` |
| `DEBUG` | 调试模式 | `false` |
| `HOST` | 监听地址 | `0.0.0.0` |
| `FRONTEND_PORT` | 前端端口 | `8000` |
| `BACKEND_PORT` | 后台端口 | `8003` |
| `SECRET_KEY` | 安全密钥 | 随机生成 |
| `ALLOWED_HOSTS` | 允许的主机 | `localhost` |

### 管理员账户

**默认管理员账户**:
- 用户名: `vee5208`
- 密码: `forxy131`

> ⚠️ **安全提示**: 部署后请立即修改默认密码！

## 🔒 安全配置

### 1. HTTPS 配置

```bash
# 生成SSL证书（Let's Encrypt）
sudo certbot --nginx -d your-domain.com
```

### 2. 防火墙配置

```bash
# Ubuntu/Debian
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 8003/tcp
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=8003/tcp
sudo firewall-cmd --reload
```

### 3. 反向代理配置

使用 Nginx 作为反向代理，配置文件已包含在 `nginx.conf` 中。

## 📊 监控和维护

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/health
curl http://localhost:8003/health
```

### 日志管理

```bash
# 查看应用日志
tail -f logs/app.log

# 查看Docker日志
docker-compose logs -f ai-knowledge-base

# 查看Nginx日志
docker-compose logs -f nginx
```

### 备份策略

```bash
# 备份数据
tar -czf backup-$(date +%Y%m%d).tar.gz uploads/ logs/ .env.production

# 定期备份（添加到crontab）
0 2 * * * /path/to/backup-script.sh
```

## 🔄 更新部署

### Docker 更新

```bash
# 拉取最新代码
git pull origin main

# 重新构建
docker-compose build --no-cache

# 重启服务
docker-compose down
docker-compose up -d
```

### 直接部署更新

```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt

# 重启服务
sudo systemctl restart ai-knowledge-base
```

## 🐛 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 查看端口占用
   netstat -tulpn | grep :8000
   # 杀死进程
   sudo kill -9 <PID>
   ```

2. **权限问题**
   ```bash
   # 修改文件权限
   sudo chown -R www-data:www-data /path/to/ai-knowledge-base
   sudo chmod -R 755 /path/to/ai-knowledge-base
   ```

3. **内存不足**
   ```bash
   # 检查内存使用
   free -h
   # 添加交换空间
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

### 性能优化

1. **调整Worker数量**
   ```bash
   # 根据CPU核心数调整
   uvicorn app:app --workers $(($(nproc) * 2 + 1))
   ```

2. **启用缓存**
   ```bash
   # 安装Redis
   sudo apt-get install redis-server
   # 配置缓存
   export REDIS_URL=redis://localhost:6379/0
   ```

## 📞 技术支持

如遇到部署问题，请检查：
1. 系统要求是否满足
2. 端口是否被占用
3. 防火墙配置是否正确
4. 日志文件中的错误信息

---

**部署完成后，请访问管理后台修改默认密码并进行系统配置！**