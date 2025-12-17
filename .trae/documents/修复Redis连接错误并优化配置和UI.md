# 修复Redis连接错误并优化配置和UI

## 1. 优化Redis连接处理

**问题**：系统反复尝试连接Redis，导致大量错误日志

**解决方案**：
- 修改 `utils/queue_manager.py`，减少Redis连接尝试频率
- 实现连接缓存，避免重复连接尝试
- 优化错误处理，只在必要时记录错误
- 增加Redis可用性检查，只在连接成功后才使用

**修改点**：
```python
# 在QueueManager类中添加连接缓存和优化
class QueueManager:
    def __init__(self):
        self.redis_conn = None
        self.queue = None
        self.redis_available = False
        self.connection_checked = False
        
        # 其他初始化代码
    
    def is_connected(self):
        # 优化连接检查逻辑
        if self.connection_checked:
            return self.redis_available
        # 只检查一次
        self.connection_checked = True
        # 连接逻辑
```

## 2. 添加可选择性监控配置

**需求**：用户可以选择性监控CVE、GitHub仓库和安全文章

**解决方案**：
- 在 `config.yaml` 中添加监控开关
- 更新配置解析逻辑
- 修改主程序流程，尊重配置开关

**修改点**：
```yaml
# config.yaml 新增
monitoring:
  enabled: true
  cve: true
  github: true
  articles: true
```

## 3. 优化UI数据处理

**问题**：UI在加载不到数据时可能无法正常显示

**解决方案**：
- 确保API返回空数据时的正确格式
- 优化前端代码，处理空数据情况
- 添加加载状态和错误提示
- 确保UI可以优雅降级

**修改点**：
```javascript
// 在前端代码中添加空数据处理
if (data.length === 0) {
    // 显示暂无数据提示
    container.innerHTML = '<div class="no-data">暂无数据</div>';
} else {
    // 渲染数据
}
```

## 4. 完善错误日志

**问题**：Redis错误日志过多，影响系统可读性

**解决方案**：
- 减少Redis连接错误的日志频率
- 合并重复错误信息
- 添加错误级别控制
- 只在首次连接失败时记录详细错误

## 5. 测试和验证

**验证步骤**：
1. 确保Redis未运行时，系统能正常降级运行
2. 测试各监控开关的功能
3. 验证UI在空数据下的表现
4. 检查日志文件，确保错误日志合理

**预期结果**：
- 系统不再产生大量Redis连接错误日志
- 用户可以通过配置选择性启用监控模块
- UI在无数据时显示友好提示
- 系统保持正常运行，不受Redis影响