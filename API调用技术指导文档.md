# ESP-HI 机器狗集群管理系统 - API 调用技术指导文档

***

## 📋 目录

1. [基础信息](#基础信息)
2. [快速开始](#快速开始)
3. [HTTP REST API 详解](#http-rest-api-详解)
4. [WebSocket 实时通信](#websocket-实时通信)
5. [多语言调用示例](#多语言调用示例)
6. [错误处理](#错误处理)
7. [实践方案](#实践方案)

***

## 基础信息

### 服务器配置

| 配置项          | 值                       | 说明                  |
| ------------ | ----------------------- | ------------------- |
| 服务地址         | `http://localhost:5000` | 默认本地地址              |
| 绑定地址         | `0.0.0.0`               | 监听所有网卡，支持局域网访问      |
| 端口           | `5000`                  | HTTP/WebSocket 共用端口 |
| 跨域支持         | 已启用 CORS                | 允许任意来源访问            |
| Content-Type | `application/json`      | 请求/响应数据格式           |

### 接口通用规范

**请求格式**:

```json
{
  "key": "value"
}
```

**成功响应格式**:

```json
{
  "success": true,
  "data": { }
}
```

**错误响应格式**:

```json
{
  "success": false,
  "error": "错误描述信息"
}
```

***

## 快速开始

### 1. 检查服务状态

```bash
curl http://localhost:5000/api/health
```

**响应示例**:

```json
{
  "status": "healthy",
  "timestamp": "2026-05-06T10:30:00",
  "active_devices": 2,
  "version": "1.0.2"
}
```

### 2. 获取设备列表

```bash
curl http://localhost:5000/api/devices
```

***

## HTTP REST API 详解

### 一、设备管理接口

#### 1. 扫描设备

**接口**: `POST /api/scan/start`

**说明**: 扫描局域网内的 ESP-HI 设备

**请求参数**: 无

**响应示例**:

```json
{
  "success": true,
  "devices": [
    {
      "ip": "192.168.1.100",
      "name": "机器狗-01",
      "status": "online"
    }
  ],
  "count": 1
}
```

#### 2. 获取设备列表

**接口**: `GET /api/devices`

**响应示例**:

```json
{
  "success": true,
  "devices": [
    {
      "ip": "192.168.1.100",
      "name": "机器狗-01",
      "status": "online"
    }
  ],
  "connected_devices": ["192.168.1.100"],
  "calibration_device": null,
  "count": 1
}
```

#### 3. 添加设备

**接口**: `POST /api/devices/add`

**请求参数**:

| 参数   | 类型     | 必填 | 说明     |
| ---- | ------ | -- | ------ |
| ip   | string | 是  | 设备IP地址 |
| name | string | 否  | 设备名称   |

**请求示例**:

```json
{
  "ip": "192.168.1.101",
  "name": "机器狗-02"
}
```

#### 4. 删除设备

**接口**: `POST /api/devices/delete`

**请求参数**:

| 参数 | 类型     | 必填 | 说明     |
| -- | ------ | -- | ------ |
| ip | string | 是  | 设备IP地址 |

#### 5. 选择/连接设备

**接口**: `POST /api/devices/select`

**说明**: 连接一个或多个设备进行控制

**请求参数**:

| 参数      | 类型    | 必填 | 说明     |
| ------- | ----- | -- | ------ |
| devices | array | 是  | IP地址数组 |

**请求示例**:

```json
{
  "devices": ["192.168.1.100", "192.168.1.101"]
}
```

**响应示例**:

```json
{
  "success": true,
  "selected_count": 2,
  "success_devices": ["192.168.1.100", "192.168.1.101"],
  "failed_devices": []
}
```

#### 6. 断开设备连接

**接口**: `POST /api/devices/disconnect`

**请求参数**:

| 参数 | 类型     | 必填 | 说明     |
| -- | ------ | -- | ------ |
| ip | string | 是  | 设备IP地址 |

#### 7. 重命名设备

**接口**: `POST /api/devices/rename`

**请求参数**:

| 参数   | 类型     | 必填 | 说明            |
| ---- | ------ | -- | ------------- |
| ip   | string | 是  | 设备IP地址        |
| name | string | 是  | 新名称（空字符串清除名称） |

***

### 二、运动控制接口

#### 1. 执行预设动作

**接口**: `POST /api/control/action`

**请求参数**:

| 参数         | 类型     | 必填 | 说明   |
| ---------- | ------ | -- | ---- |
| action\_id | string | 是  | 动作ID |

**动作ID列表**:

| 动作ID               | 动作名称 | 说明    |
| ------------------ | ---- | ----- |
| `down`             | 趴下   | 机器狗趴下 |
| `bow`              | 鞠躬   | 机器狗鞠躬 |
| `lean_back`        | 后仰   | 机器狗后仰 |
| `swing`            | 摇摆   | 左右摇摆  |
| `forward_backward` | 前后   | 前后移动  |
| `left_right`       | 左右   | 左右移动  |
| `shake_hand`       | 握手   | 握手动作  |
| `poke`             | 戳戳   | 戳戳动作  |
| `shake_leg`        | 抖腿   | 抖腿动作  |
| `jump_forward`     | 前跳   | 向前跳跃  |
| `jump_backward`    | 后跳   | 向后跳跃  |
| `retract`          | 收腿   | 收腿动作  |

**请求示例**:

```json
{
  "action_id": "bow"
}
```

#### 2. 执行移动控制

**接口**: `POST /api/control/move`

**请求参数**:

| 参数        | 类型     | 必填 | 说明   |
| --------- | ------ | -- | ---- |
| direction | string | 是  | 移动方向 |

**方向值**:

- `forward` - 前进
- `backward` - 后退
- `left` - 左转
- `right` - 右转

**请求示例**:

```json
{
  "direction": "forward"
}
```

#### 3. 开始连续移动

**接口**: `POST /api/control/continuous/start`

**请求参数**:

| 参数        | 类型     | 必填 | 说明                 |
| --------- | ------ | -- | ------------------ |
| direction | string | 是  | 移动方向               |
| delay     | int    | 否  | 指令下发延迟(ms)，默认500ms |

#### 4. 停止连续移动

**接口**: `POST /api/control/continuous/stop`

**请求参数**: 无

#### 5. 执行动作序列

**接口**: `POST /api/control/sequence`

**请求参数**:

| 参数       | 类型    | 必填 | 说明     |
| -------- | ----- | -- | ------ |
| sequence | array | 是  | 动作序列数组 |

**序列项格式**:

```json
{
  "action": "动作ID或方向",
  "delay": 1.5
}
```

**请求示例**:

```json
{
  "sequence": [
    {"action": "bow", "delay": 1.0},
    {"action": "forward", "delay": 0.5},
    {"action": "down", "delay": 0}
  ]
}
```

***

### 三、舵机校准接口

#### 1. 进入校准模式

**接口**: `POST /api/calibration/start`

**请求参数**:

| 参数     | 类型     | 必填 | 说明     |
| ------ | ------ | -- | ------ |
| device | string | 是  | 设备IP地址 |

#### 2. 退出校准模式

**接口**: `POST /api/calibration/exit`

**请求参数**:

| 参数    | 类型      | 必填 | 说明           |
| ----- | ------- | -- | ------------ |
| force | boolean | 否  | 强制退出，默认false |

#### 3. 调整舵机角度

**接口**: `POST /api/calibration/adjust`

**请求参数**:

| 参数    | 类型     | 必填 | 说明         |
| ----- | ------ | -- | ---------- |
| servo | string | 是  | 舵机标识       |
| value | int    | 是  | 角度调整值（±1度） |

**舵机标识**:

- `FL` - 前左腿 (Front Left)
- `FR` - 前右腿 (Front Right)
- `BL` - 后左腿 (Back Left)
- `BR` - 后右腿 (Back Right)

**请求示例**:

```json
{
  "servo": "FL",
  "value": 5
}
```

***

### 四、健康检查

**接口**: `GET /api/health`

**响应示例**:

```json
{
  "status": "healthy",
  "timestamp": "2026-05-06T10:30:00",
  "active_devices": 2,
  "version": "1.0.2"
}
```

***

## WebSocket 实时通信

### 连接信息

| 配置项  | 值                     |
| ---- | --------------------- |
| 连接地址 | `ws://localhost:5000` |
| 协议   | Socket.IO             |
| 跨域   | 允许任意来源                |

### 客户端连接事件

| 事件           | 方向  | 说明    |
| ------------ | --- | ----- |
| `connect`    | C→S | 连接服务器 |
| `disconnect` | C→S | 断开连接  |
| `ping`       | C→S | 心跳检测  |

### 服务端推送事件

| 事件                      | 方向  | 说明     | 数据格式                                      |
| ----------------------- | --- | ------ | ----------------------------------------- |
| `connected`             | S→C | 连接成功通知 | `{"message": "已连接到服务器"}`                  |
| `pong`                  | S→C | 心跳响应   | `{"timestamp": "..."}`                    |
| `scan_complete`         | S→C | 扫描完成   | `{"devices": [], "count": 1}`             |
| `device_status_changed` | S→C | 设备状态变化 | `{"ip": "...", "status": {...}}`          |
| `action_executed`       | S→C | 动作执行完成 | `{"action_id": "...", "results": {}}`     |
| `sequence_status`       | S→C | 序列执行状态 | `{"status": "started", "message": "..."}` |
| `servo_adjusted`        | S→C | 舵机调整结果 | `{"servo": "FL", "value": 5}`             |

***

## 多语言调用示例

### Python 示例

```python
import requests
import json

BASE_URL = "http://localhost:5000"

class EspHiClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
  
    def health_check(self):
        """健康检查"""
        resp = requests.get(f"{self.base_url}/api/health")
        return resp.json()
  
    def get_devices(self):
        """获取设备列表"""
        resp = requests.get(f"{self.base_url}/api/devices")
        return resp.json()
  
    def scan_devices(self):
        """扫描设备"""
        resp = requests.post(f"{self.base_url}/api/scan/start")
        return resp.json()
  
    def connect_devices(self, device_ips):
        """连接设备
        :param device_ips: IP地址列表，如 ["192.168.1.100"]
        """
        resp = requests.post(
            f"{self.base_url}/api/devices/select",
            json={"devices": device_ips}
        )
        return resp.json()
  
    def execute_action(self, action_id):
        """执行动作
        :param action_id: 动作ID，如 "bow", "jump_forward"
        """
        resp = requests.post(
            f"{self.base_url}/api/control/action",
            json={"action_id": action_id}
        )
        return resp.json()
  
    def move(self, direction):
        """移动控制
        :param direction: 方向，如 "forward", "backward", "left", "right"
        """
        resp = requests.post(
            f"{self.base_url}/api/control/move",
            json={"direction": direction}
        )
        return resp.json()
  
    def start_continuous_move(self, direction, delay=500):
        """开始连续移动"""
        resp = requests.post(
            f"{self.base_url}/api/control/continuous/start",
            json={"direction": direction, "delay": delay}
        )
        return resp.json()
  
    def stop_continuous_move(self):
        """停止连续移动"""
        resp = requests.post(f"{self.base_url}/api/control/continuous/stop")
        return resp.json()
  
    def execute_sequence(self, sequence):
        """执行动作序列
        :param sequence: 动作序列列表
        """
        resp = requests.post(
            f"{self.base_url}/api/control/sequence",
            json={"sequence": sequence}
        )
        return resp.json()


# ============ 使用示例 ============

if __name__ == "__main__":
    client = EspHiClient()
  
    # 1. 检查服务状态
    health = client.health_check()
    print(f"服务状态: {health}")
  
    # 2. 扫描设备
    scan_result = client.scan_devices()
    print(f"扫描结果: {scan_result}")
  
    # 3. 获取设备列表
    devices = client.get_devices()
    print(f"设备列表: {devices}")
  
    # 4. 连接设备（假设有一个设备IP）
    if devices.get('devices'):
        ip = devices['devices'][0]['ip']
        connect_result = client.connect_devices([ip])
        print(f"连接结果: {connect_result}")
      
        # 5. 执行动作 - 鞠躬
        action_result = client.execute_action("bow")
        print(f"动作执行: {action_result}")
      
        # 6. 移动控制 - 前进
        move_result = client.move("forward")
        print(f"移动结果: {move_result}")
      
        # 7. 执行动作序列
        sequence = [
            {"action": "bow", "delay": 1.0},
            {"action": "swing", "delay": 2.0},
            {"action": "down", "delay": 0}
        ]
        seq_result = client.execute_sequence(sequence)
        print(f"序列执行: {seq_result}")
```

### JavaScript (浏览器) 示例

```javascript
class EspHiClient {
  constructor(baseUrl = 'http://localhost:5000') {
    this.baseUrl = baseUrl;
  }

  // HTTP API 调用
  async request(endpoint, method = 'GET', data = null) {
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json'
      }
    };
    if (data) {
      options.body = JSON.stringify(data);
    }
  
    const response = await fetch(`${this.baseUrl}${endpoint}`, options);
    return response.json();
  }

  async healthCheck() {
    return this.request('/api/health');
  }

  async getDevices() {
    return this.request('/api/devices');
  }

  async scanDevices() {
    return this.request('/api/scan/start', 'POST');
  }

  async connectDevices(deviceIps) {
    return this.request('/api/devices/select', 'POST', { devices: deviceIps });
  }

  async executeAction(actionId) {
    return this.request('/api/control/action', 'POST', { action_id: actionId });
  }

  async move(direction) {
    return this.request('/api/control/move', 'POST', { direction });
  }

  async executeSequence(sequence) {
    return this.request('/api/control/sequence', 'POST', { sequence });
  }
}

// ============ 使用示例 ============

const client = new EspHiClient();

async function main() {
  try {
    // 检查服务
    const health = await client.healthCheck();
    console.log('服务状态:', health);

    // 获取设备
    const devices = await client.getDevices();
    console.log('设备列表:', devices);

    // 连接设备并执行动作
    if (devices.devices && devices.devices.length > 0) {
      const ip = devices.devices[0].ip;
    
      await client.connectDevices([ip]);
      console.log('设备已连接');

      // 执行动作
      await client.executeAction('bow');
      console.log('鞠躬动作已执行');

      // 移动
      await client.move('forward');
      console.log('前进指令已发送');
    }
  } catch (error) {
    console.error('错误:', error);
  }
}

main();
```

### JavaScript (Node.js) 示例

```javascript
const axios = require('axios');

class EspHiClient {
  constructor(baseUrl = 'http://localhost:5000') {
    this.client = axios.create({
      baseURL: baseUrl,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  async healthCheck() {
    const resp = await this.client.get('/api/health');
    return resp.data;
  }

  async getDevices() {
    const resp = await this.client.get('/api/devices');
    return resp.data;
  }

  async scanDevices() {
    const resp = await this.client.post('/api/scan/start');
    return resp.data;
  }

  async connectDevices(deviceIps) {
    const resp = await this.client.post('/api/devices/select', {
      devices: deviceIps
    });
    return resp.data;
  }

  async executeAction(actionId) {
    const resp = await this.client.post('/api/control/action', {
      action_id: actionId
    });
    return resp.data;
  }

  async move(direction) {
    const resp = await this.client.post('/api/control/move', {
      direction
    });
    return resp.data;
  }

  async startContinuousMove(direction, delay = 500) {
    const resp = await this.client.post('/api/control/continuous/start', {
      direction,
      delay
    });
    return resp.data;
  }

  async stopContinuousMove() {
    const resp = await this.client.post('/api/control/continuous/stop');
    return resp.data;
  }

  async executeSequence(sequence) {
    const resp = await this.client.post('/api/control/sequence', {
      sequence
    });
    return resp.data;
  }
}

module.exports = EspHiClient;

// ============ 使用示例 ============

async function main() {
  const client = new EspHiClient();
  
  try {
    const health = await client.healthCheck();
    console.log('服务状态:', health.status);
  
    const devices = await client.getDevices();
    console.log('已发现设备:', devices.count);
  
    if (devices.count > 0) {
      const ip = devices.devices[0].ip;
      await client.connectDevices([ip]);
    
      await client.executeAction('jump_forward');
      console.log('前跳动作已执行');
    }
  } catch (error) {
    console.error('调用失败:', error.message);
  }
}

main();
```

### C# 示例

```csharp
using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

public class EspHiClient
{
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;

    public EspHiClient(string baseUrl = "http://localhost:5000")
    {
        _baseUrl = baseUrl;
        _httpClient = new HttpClient();
        _httpClient.DefaultRequestHeaders.Add("Accept", "application/json");
    }

    public async Task<JsonElement> HealthCheckAsync()
    {
        var response = await _httpClient.GetAsync($"{_baseUrl}/api/health");
        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(content);
    }

    public async Task<JsonElement> GetDevicesAsync()
    {
        var response = await _httpClient.GetAsync($"{_baseUrl}/api/devices");
        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(content);
    }

    public async Task<JsonElement> ScanDevicesAsync()
    {
        var response = await _httpClient.PostAsync($"{_baseUrl}/api/scan/start", null);
        var content = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(content);
    }

    public async Task<JsonElement> ConnectDevicesAsync(List<string> deviceIps)
    {
        var data = new { devices = deviceIps };
        var json = JsonSerializer.Serialize(data);
        var content = new StringContent(json, Encoding.UTF8, "application/json");
      
        var response = await _httpClient.PostAsync($"{_baseUrl}/api/devices/select", content);
        var respContent = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(respContent);
    }

    public async Task<JsonElement> ExecuteActionAsync(string actionId)
    {
        var data = new { action_id = actionId };
        var json = JsonSerializer.Serialize(data);
        var content = new StringContent(json, Encoding.UTF8, "application/json");
      
        var response = await _httpClient.PostAsync($"{_baseUrl}/api/control/action", content);
        var respContent = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(respContent);
    }

    public async Task<JsonElement> MoveAsync(string direction)
    {
        var data = new { direction };
        var json = JsonSerializer.Serialize(data);
        var content = new StringContent(json, Encoding.UTF8, "application/json");
      
        var response = await _httpClient.PostAsync($"{_baseUrl}/api/control/move", content);
        var respContent = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(respContent);
    }

    public async Task<JsonElement> ExecuteSequenceAsync(List<SequenceItem> sequence)
    {
        var data = new { sequence };
        var json = JsonSerializer.Serialize(data);
        var content = new StringContent(json, Encoding.UTF8, "application/json");
      
        var response = await _httpClient.PostAsync($"{_baseUrl}/api/control/sequence", content);
        var respContent = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(respContent);
    }
}

public class SequenceItem
{
    public string Action { get; set; }
    public double Delay { get; set; }
}

// ============ 使用示例 ============

class Program
{
    static async Task Main(string[] args)
    {
        var client = new EspHiClient();
      
        try
        {
            // 健康检查
            var health = await client.HealthCheckAsync();
            Console.WriteLine($"服务状态: {health.GetProperty("status")}");
          
            // 获取设备
            var devices = await client.GetDevicesAsync();
            Console.WriteLine($"设备数量: {devices.GetProperty("count")}");
          
            // 连接设备并执行动作
            var deviceCount = devices.GetProperty("count").GetInt32();
            if (deviceCount > 0)
            {
                var ip = devices.GetProperty("devices")[0].GetProperty("ip").GetString();
                await client.ConnectDevicesAsync(new List<string> { ip });
                Console.WriteLine("设备已连接");
              
                // 执行动作
                var result = await client.ExecuteActionAsync("bow");
                Console.WriteLine($"动作执行: {result.GetProperty("success")}");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"错误: {ex.Message}");
        }
    }
}
```

### Java 示例

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import java.util.List;
import java.util.Map;

public class EspHiClient {
    private final HttpClient httpClient;
    private final Gson gson;
    private final String baseUrl;
  
    public EspHiClient(String baseUrl) {
        this.baseUrl = baseUrl;
        this.httpClient = HttpClient.newHttpClient();
        this.gson = new Gson();
    }
  
    public EspHiClient() {
        this("http://localhost:5000");
    }
  
    public JsonObject healthCheck() throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/api/health"))
            .GET()
            .build();
      
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return gson.fromJson(response.body(), JsonObject.class);
    }
  
    public JsonObject getDevices() throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/api/devices"))
            .GET()
            .build();
      
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return gson.fromJson(response.body(), JsonObject.class);
    }
  
    public JsonObject scanDevices() throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/api/scan/start"))
            .POST(HttpRequest.BodyPublishers.noBody())
            .header("Content-Type", "application/json")
            .build();
      
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return gson.fromJson(response.body(), JsonObject.class);
    }
  
    public JsonObject connectDevices(List<String> deviceIps) throws Exception {
        Map<String, Object> data = Map.of("devices", deviceIps);
        String json = gson.toJson(data);
      
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/api/devices/select"))
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .header("Content-Type", "application/json")
            .build();
      
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return gson.fromJson(response.body(), JsonObject.class);
    }
  
    public JsonObject executeAction(String actionId) throws Exception {
        Map<String, String> data = Map.of("action_id", actionId);
        String json = gson.toJson(data);
      
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/api/control/action"))
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .header("Content-Type", "application/json")
            .build();
      
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return gson.fromJson(response.body(), JsonObject.class);
    }
  
    public JsonObject move(String direction) throws Exception {
        Map<String, String> data = Map.of("direction", direction);
        String json = gson.toJson(data);
      
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/api/control/move"))
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .header("Content-Type", "application/json")
            .build();
      
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return gson.fromJson(response.body(), JsonObject.class);
    }
  
    // ============ 使用示例 ============
  
    public static void main(String[] args) {
        EspHiClient client = new EspHiClient();
      
        try {
            // 健康检查
            JsonObject health = client.healthCheck();
            System.out.println("服务状态: " + health.get("status").getAsString());
          
            // 获取设备
            JsonObject devices = client.getDevices();
            System.out.println("设备数量: " + devices.get("count").getAsInt());
          
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

### WebSocket (JavaScript) 示例

```javascript
// 使用 socket.io-client
const io = require('socket.io-client');

class EspHiWebSocketClient {
  constructor(url = 'http://localhost:5000') {
    this.socket = io(url);
    this.setupEventHandlers();
  }

  setupEventHandlers() {
    // 连接成功
    this.socket.on('connect', () => {
      console.log('已连接到服务器');
    });

    // 断开连接
    this.socket.on('disconnect', () => {
      console.log('与服务器断开连接');
    });

    // 连接成功通知
    this.socket.on('connected', (data) => {
      console.log('服务器消息:', data.message);
    });

    // 心跳响应
    this.socket.on('pong', (data) => {
      console.log('心跳响应:', data.timestamp);
    });

    // 扫描完成
    this.socket.on('scan_complete', (data) => {
      console.log('扫描完成:', data);
    });

    // 设备状态变化
    this.socket.on('device_status_changed', (data) => {
      console.log('设备状态变化:', data);
    });

    // 动作执行结果
    this.socket.on('action_executed', (data) => {
      console.log('动作执行:', data);
    });

    // 序列执行状态
    this.socket.on('sequence_status', (data) => {
      console.log('序列状态:', data);
    });

    // 舵机调整
    this.socket.on('servo_adjusted', (data) => {
      console.log('舵机调整:', data);
    });
  }

  // 发送心跳
  ping() {
    this.socket.emit('ping');
  }

  // 断开连接
  disconnect() {
    this.socket.disconnect();
  }
}

// ============ 使用示例 ============

const wsClient = new EspHiWebSocketClient();

// 定时发送心跳
setInterval(() => {
  wsClient.ping();
}, 30000); // 每30秒
```

***

## 错误处理

### HTTP 状态码

| 状态码 | 说明      |
| --- | ------- |
| 200 | 请求成功    |
| 400 | 请求参数错误  |
| 500 | 服务器内部错误 |

### 错误响应示例

```json
{
  "success": false,
  "error": "没有已连接的设备，请先连接设备"
}
```

### 常见错误

| 错误信息                        | 说明         | 解决方案                             |
| --------------------------- | ---------- | -------------------------------- |
| `没有已连接的设备，请先连接设备`           | 执行动作前未连接设备 | 先调用 `/api/devices/select` 连接设备   |
| `舵机校准模式下无法执行此操作，请先退出舵机校准模式` | 正在进行舵机校准   | 先调用 `/api/calibration/exit` 退出校准 |
| `IP address required`       | 缺少IP地址参数   | 提供正确的IP地址                        |
| `请至少选择一个设备`                 | 设备选择列表为空   | 提供至少一个设备IP                       |

### 错误处理示例 (Python)

```python
import requests

def safe_request(func):
    """请求装饰器，统一处理错误"""
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            if not result.get('success'):
                print(f"操作失败: {result.get('error')}")
                return None
            return result
        except requests.exceptions.ConnectionError:
            print("错误: 无法连接到服务器，请检查服务是否启动")
            return None
        except requests.exceptions.Timeout:
            print("错误: 请求超时")
            return None
        except Exception as e:
            print(f"错误: {str(e)}")
            return None
    return wrapper

# 使用示例
@safe_request
def execute_action(client, action_id):
    return client.execute_action(action_id)

# 调用
result = execute_action(client, "bow")
if result:
    print("动作执行成功")
```

***

## 实践方案

### 1. 连接流程建议

```
1. 健康检查 (/api/health)
   ↓
2. 扫描设备 (/api/scan/start) [可选]
   ↓
3. 获取设备列表 (/api/devices)
   ↓
4. 选择要控制的设备 (/api/devices/select)
   ↓
5. 执行控制指令 (/api/control/*)
```

### 2. 批量控制

如需同时控制多台设备，建议在连接时一次性传入所有设备IP：

```python
# 推荐：一次性连接多台设备
client.connect_devices(["192.168.1.100", "192.168.1.101", "192.168.1.102"])

# 执行动作时会自动应用到所有已连接设备
client.execute_action("bow")
```

### 3. 使用 WebSocket 获取实时状态

对于需要实时监控的场景，建议同时使用 WebSocket：

```python
import requests
from socketio import Client

sio = Client()

@sio.on('device_status_changed')
def on_device_status_changed(data):
    print(f"设备 {data['ip']} 状态变化: {data['status']}")

@sio.on('action_executed')
def on_action_executed(data):
    print(f"动作 {data['action_id']} 执行完成")

sio.connect('http://localhost:5000')

# 现在通过 HTTP API 执行动作，WebSocket 会推送结果
client.execute_action("bow")
```

### 4. 舵机校准注意事项

- 进入校准模式后，其他控制功能将被锁定
- 校准模式下只能调用校准相关接口
- 设备意外断电时，使用 `force=true` 强制退出校准模式

```python
# 正常退出
calibration_service.exit_calibration()

# 强制退出（设备断电时使用）
calibration_service.exit_calibration(force=True)
```

### 5. 动作序列设计

动作序列会异步执行，通过 WebSocket 获取执行状态：

```python
sequence = [
    {"action": "bow", "delay": 1.0},        # 鞠躬，等待1秒
    {"action": "forward", "delay": 0.5},    # 前进，等待0.5秒
    {"action": "swing", "delay": 2.0},      # 摇摆，等待2秒
    {"action": "down", "delay": 0}          # 趴下，结束
]

# 启动序列（异步执行）
client.execute_sequence(sequence)

# 通过 WebSocket 监听序列状态
```

### 6. 连续移动控制

连续移动需要显式启动和停止：

```python
# 开始连续前进（每500ms发送一次指令）
client.start_continuous_move("forward", delay=500)

# ... 持续移动中 ...

# 停止连续移动
client.stop_continuous_move()
```

***

## 附录

### 动作ID速查表

| 动作 | ID                 | 图标 |
| -- | ------------------ | -- |
| 趴下 | `down`             | 💤 |
| 鞠躬 | `bow`              | 🙇 |
| 后仰 | `lean_back`        | 🧘 |
| 摇摆 | `swing`            | 💃 |
| 前后 | `forward_backward` | ↕️ |
| 左右 | `left_right`       | ↔️ |
| 握手 | `shake_hand`       | 🤝 |
| 戳戳 | `poke`             | 👉 |
| 抖腿 | `shake_leg`        | 🦵 |
| 前跳 | `jump_forward`     | 🐇 |
| 后跳 | `jump_backward`    | 🔙 |
| 收腿 | `retract`          | 📦 |

### 移动方向速查表

| 方向 | ID         |
| -- | ---------- |
| 前进 | `forward`  |
| 后退 | `backward` |
| 左转 | `left`     |
| 右转 | `right`    |

### 舵机标识速查表

| 位置  | 标识   | 全称          |
| --- | ---- | ----------- |
| 前左腿 | `FL` | Front Left  |
| 前右腿 | `FR` | Front Right |
| 后左腿 | `BL` | Back Left   |
| 后右腿 | `BR` | Back Right  |

***

