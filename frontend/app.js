// 全局配置
// 自动获取当前主机地址，支持 localhost, 127.0.0.1 或 局域网IP
const API_BASE = '/api';

// 事件总线类，用于组件间通信
class EventBus {
    constructor() {
        this.events = new Map();
    }

    // 订阅事件
    on(event, callback) {
        if (!this.events.has(event)) {
            this.events.set(event, []);
        }
        this.events.get(event).push(callback);
    }

    // 取消订阅
    off(event, callback) {
        if (this.events.has(event)) {
            this.events.set(event, this.events.get(event).filter(cb => cb !== callback));
        }
    }

    // 发布事件
    emit(event, data) {
        if (this.events.has(event)) {
            this.events.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error emitting event ${event}:`, error);
                }
            });
        }
    }

    // 订阅一次事件
    once(event, callback) {
        const onceCallback = (data) => {
            callback(data);
            this.off(event, onceCallback);
        };
        this.on(event, onceCallback);
    }
}

// 设备状态管理器类
class DeviceStateManager {
    constructor() {
        this.devices = []; // 设备列表
        this.deviceMap = new Map(); // 设备状态映射，key: ip, value: {online, connected, name}
        this.eventBus = new EventBus();
    }

    // 获取设备列表
    getDevices() {
        return this.devices;
    }

    // 添加设备
    addDevice(ip, name = '') {
        if (!this.deviceMap.has(ip)) {
            this.deviceMap.set(ip, {
                online: false,
                connected: false,
                name: name
            });
            this.devices.push(ip);
            this.devices.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
            this.eventBus.emit('device:added', ip);
        }
    }

    // 删除设备
    removeDevice(ip) {
        if (this.deviceMap.has(ip)) {
            this.deviceMap.delete(ip);
            this.devices = this.devices.filter(d => d !== ip);
            this.eventBus.emit('device:removed', ip);
        }
    }

    // 设置设备在线状态
    setDeviceOnline(ip, online) {
        const device = this.deviceMap.get(ip);
        if (device && device.online !== online) {
            device.online = online;
            this.eventBus.emit('device:statusChanged', {
                ip: ip,
                type: 'online',
                value: online
            });
        }
    }

    // 设置设备连接状态
    setDeviceConnected(ip, connected) {
        const device = this.deviceMap.get(ip);
        if (device && device.connected !== connected) {
            device.connected = connected;
            this.eventBus.emit('device:statusChanged', {
                ip: ip,
                type: 'connected',
                value: connected
            });
        }
    }

    // 设置设备名称
    setDeviceName(ip, name) {
        const device = this.deviceMap.get(ip);
        if (device && device.name !== name) {
            device.name = name;
            this.eventBus.emit('device:statusChanged', {
                ip: ip,
                type: 'name',
                value: name
            });
        }
    }

    // 获取设备状态
    getDeviceStatus(ip) {
        return this.deviceMap.get(ip) || { online: false, connected: false, name: '' };
    }

    // 获取在线设备列表
    getOnlineDevices() {
        return this.devices.filter(ip => this.deviceMap.get(ip).online);
    }

    // 获取已连接设备列表
    getConnectedDevices() {
        return this.devices.filter(ip => this.deviceMap.get(ip).connected);
    }

    // 获取所有设备列表
    getAllDevices() {
        return [...this.deviceMap.keys()];
    }

    // 批量更新设备状态
    updateDeviceStates(states) {
        states.forEach(state => {
            this.addDevice(state.ip, state.name);
            if (state.online !== undefined) {
                this.setDeviceOnline(state.ip, state.online);
            }
            if (state.connected !== undefined) {
                this.setDeviceConnected(state.ip, state.connected);
            }
        });
    }

    // 清空所有设备
    clearDevices() {
        this.devices = [];
        this.deviceMap.clear();
        this.eventBus.emit('device:cleared');
    }
}

// 动作定义
const ACTIONS = {
    '1': { name: '趴下', icon: '💤' },
    '2': { name: '鞠躬', icon: '🙇' },
    '3': { name: '后仰', icon: '🧘' },
    '4': { name: '摇摆', icon: '💃' },
    '5': { name: '前后', icon: '↕️' },
    '6': { name: '左右', icon: '↔️' },
    '7': { name: '握手', icon: '🤝' },
    '8': { name: '戳戳', icon: '👉' },
    '9': { name: '抖腿', icon: '🦵' },
    '10': { name: '前跳', icon: '🐇' },
    '11': { name: '后跳', icon: '🔙' },
    '12': { name: '收腿', icon: '📦' }
};

// 舵机定义
const SERVOS = [
    { id: 'fl', name: '前左腿' },
    { id: 'fr', name: '前右腿' },
    { id: 'bl', name: '后左腿' },
    { id: 'br', name: '后右腿' }
];

class App {
    constructor() {
        // 设备状态管理器
        this.deviceState = new DeviceStateManager();
        
        // 初始化设备集合
        this.connectedDevices = new Set();
        this.allDevices = new Set();
        this.onlineDevices = new Set();
        this.deviceNames = new Map();
        
        // 其他状态
        this.socket = null;
        this.selectedDevices = new Set();
        this.sequence = [];
        this.joystickActive = false;
        this.showAllDevices = false;
        
        // 页面设备选择状态
        this.pageDeviceSelections = {
            'control': new Set(),
            'actions': new Set(),
            'sequence': new Set(),
            'calibration': new Set()
        };
        
        // 循环执行相关属性
        this.isLoopRunning = false;
        this.loopInterval = null;
        this.selectedActionId = null;
        
        // 序列循环相关属性
        this.sequenceLoopInterval = null;
        this.isSequenceLoopRunning = false;
        
        // 状态更新防抖定时器
        this.statusUpdateTimeout = null;
        
        // 渲染状态标记
        this.isRendering = {
            devices: false,
            deviceLibrary: false,
            connectedDevices: false
        };
        
        this.init();
    }

    // 获取设备显示名称（优先使用自定义名称，否则生成默认名称）
    getDeviceDisplayName(ip) {
        // 从设备状态管理器获取设备名称
        const deviceStatus = this.deviceState.getDeviceStatus(ip);
        if (deviceStatus.name) {
            return deviceStatus.name;
        }
        
        // 生成默认名称：设备+IP地址的最后三位数字
        const ipParts = ip.split('.');
        if (ipParts.length === 4) {
            const lastOctet = ipParts[3];
            return `设备${lastOctet}`;
        }
        
        // 如果IP格式不正确，使用原始IP
        return ip;
    }

    init() {
        this.initSocket();
        this.initNavigation();
        this.initDeviceManager();
        this.initDeviceLibrary();
        this.initPageDeviceSelectors();
        this.initJoystick();
        this.initActions();
        this.initCalibration();
        this.initSequenceBuilder();
        this.initThemeToggle();
        this.initActionLoop();
        this.initSequenceLoop();

        // 初始加载设备
        this.loadDevices();
    }

    // 初始化主题切换功能
    initThemeToggle() {
        // 从localStorage加载保存的主题偏好
        const savedTheme = localStorage.getItem('theme') || 'default';
        document.body.setAttribute('data-theme', savedTheme);

        // 添加主题切换按钮事件监听
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            // 设置初始图标
            this.updateThemeIcon(savedTheme);
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    // 更新主题图标
    updateThemeIcon(theme) {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            // 默认主题显示彩虹，马卡龙主题显示纸杯蛋糕
            themeToggle.textContent = theme === 'pastel' ? '🧁' : '🌈';
        }
    }

    // 切换主题
    toggleTheme() {
        const currentTheme = document.body.getAttribute('data-theme') || 'default';
        const newTheme = currentTheme === 'default' ? 'pastel' : 'default';

        document.body.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);

        // 更新图标
        this.updateThemeIcon(newTheme);

        this.showNotification(
            newTheme === 'pastel' ? '已切换到马卡龙主题' : '已切换到默认主题',
            'info'
        );
    }

    // ==================== Socket.IO 初始化 ====================
    initSocket() {
        // 配置自动重连
        this.socket = io({
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 5
        });

        this.socket.on('connect', () => {
            this.updateConnectionStatus(true);
            this.showNotification('已连接到服务器', 'success');
        });

        this.socket.on('disconnect', () => {
            this.updateConnectionStatus(false);
            this.showNotification('与服务器断开连接，正在尝试重连...', 'warning');
        });

        this.socket.on('reconnect', () => {
            this.showNotification('已重新连接到服务器', 'success');
        });

        this.socket.on('reconnect_failed', () => {
            this.showNotification('重连失败，请刷新页面', 'error');
        });

        this.socket.on('scan_complete', (data) => {
            const currentOnline = new Set(data.devices);

            // Check for lost connections (connected devices that are no longer online)
            const lostConnections = [];
            this.deviceState.getConnectedDevices().forEach(ip => {
                if (!currentOnline.has(ip)) {
                    lostConnections.push(ip);
                }
            });

            // Process lost connections
            if (lostConnections.length > 0) {
                const disconnectPromises = lostConnections.map(ip => {
                    this.deviceState.setDeviceConnected(ip, false);
                    this.selectedDevices.delete(ip);
                    this.librarySelectedDevices.delete(ip);
                    this.updateDeviceItem(ip);
                    
                    return fetch(`${API_BASE}/devices/disconnect`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ip })
                    }).catch(e => {
                        console.error(`Auto-disconnect failed for ${ip}:`, e);
                        return { error: true, ip };
                    });
                });

                Promise.allSettled(disconnectPromises).then(results => {
                    const failed = results.filter(r => r.status === 'rejected' || r.value?.error);
                    if (failed.length > 0) {
                        console.warn(`${failed.length} 个设备断开连接失败`);
                    }
                });

                this.showNotification(`${lostConnections.length} 个设备已断开连接（离线）`, 'warning');

                // Update connected devices UI immediately
                this.renderConnectedDevices();
                this.syncPageSelections(); // Sync dropdowns after auto-disconnect
            }

            // Update online devices and add to all devices
            data.devices.forEach(ip => {
                this.deviceState.addDevice(ip);
                this.deviceState.setDeviceOnline(ip, true);
            });

            // 增量更新在线设备状态
            this.deviceState.getAllDevices().forEach(ip => {
                const isOnline = currentOnline.has(ip);
                if (this.deviceState.getDeviceStatus(ip).online !== isOnline) {
                    this.deviceState.setDeviceOnline(ip, isOnline);
                    this.updateDeviceItem(ip);
                }
            });

            this.renderDevices();
            this.renderDeviceLibrary(); // 更新设备库页面的设备列表
            this.updateStatus();
            this.updateAllPageDeviceSelectors(); // 更新所有页面的设备选择器

            const scanBtn = document.getElementById('scan-btn');
            const statusDiv = document.getElementById('scan-status');
            scanBtn.disabled = false;
            scanBtn.innerHTML = '<span class="btn-icon">🔍</span><span>开始扫描</span>';
            statusDiv.textContent = `扫描完成，发现 ${data.count} 个设备`;

            if (data.count > 0) {
                this.showNotification(`扫描完成，发现 ${data.count} 个设备`, 'success');
            } else {
                this.showNotification('未发现设备', 'info');
            }
        });

        // 监听设备状态变化事件
        this.socket.on('device_status_changed', (data) => {
            const { ip, status } = data;
            
            // 更新设备状态
            if (status.online !== undefined) {
                this.deviceState.setDeviceOnline(ip, status.online);
            }
            if (status.connected !== undefined) {
                this.deviceState.setDeviceConnected(ip, status.connected);
            }
            if (status.name !== undefined) {
                this.deviceState.setDeviceName(ip, status.name);
            }
            
            // 如果设备断开连接，停止连续移动
            if (status.connected === false || status.online === false) {
                this.stopContinuousMove();
                
                // 如果校准中的设备断开连接，提示用户
                const calibrationDevice = this.pageDeviceSelections['calibration'];
                if (calibrationDevice && calibrationDevice.has(ip)) {
                    this.showNotification('校准设备已断开连接', 'warning');
                }
            }
            
            // 增量更新设备项
            this.updateDeviceItem(ip);
            
            // 防抖更新UI
            if (this.statusUpdateTimeout) {
                clearTimeout(this.statusUpdateTimeout);
            }
            this.statusUpdateTimeout = setTimeout(() => {
                // 清除渲染状态标记，允许重新渲染
                this.isRendering.devices = false;
                this.isRendering.deviceLibrary = false;
                this.isRendering.connectedDevices = false;
                
                this.renderConnectedDevices();
                this.renderDeviceLibrary();
                this.updateStatus();
                this.updateAllPageDeviceSelectors();
            }, 100);
            
            // 显示状态变化通知
            let msg = '';
            if (status.connected) {
                msg = `设备 ${this.getDeviceDisplayName(ip)} 已连接`;
            } else if (!status.online) {
                msg = `设备 ${this.getDeviceDisplayName(ip)} 离线`;
            }
            if (msg) {
                this.showNotification(msg, status.connected ? 'success' : 'warning');
            }
        });

        this.socket.on('action_executed', (data) => {
            console.log('动作执行:', data);
        });

        this.socket.on('servo_adjusted', (data) => {
            // 可以在这里更新UI显示的当前角度
        });

        // 监听序列执行状态
        this.socket.on('sequence_status', (data) => {
            const executeBtn = document.getElementById('execute-sequence-btn');

            if (data.status === 'started') {
                this.showNotification(data.message, 'info');
            } else if (data.status === 'completed') {
                this.showNotification(data.message, 'success');
                executeBtn.disabled = false;
                executeBtn.innerHTML = '<span class="btn-icon">▶️</span><span>执行序列</span>';
            } else if (data.status === 'error') {
                this.showNotification(data.message, 'error');
                executeBtn.disabled = false;
                executeBtn.innerHTML = '<span class="btn-icon">▶️</span><span>执行序列</span>';
            }
        });
    }

    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connection-status');

        if (connected) {
            statusEl.innerHTML = `
                <span class="status-dot online"></span>
                <span>已连接服务器</span>
            `;
        } else {
            statusEl.innerHTML = `
                <span class="status-dot offline"></span>
                <span>服务器断开</span>
            `;
        }
    }

    // ==================== 页面设备选择器 ====================
    initPageDeviceSelectors() {
        // 初始化所有页面的设备选择器
        const pages = ['control', 'actions', 'sequence', 'calibration'];
        pages.forEach(page => this.initSinglePageDeviceSelector(page));
    }

    initSinglePageDeviceSelector(pageId) {
        const selectBtn = document.getElementById(`${pageId}-device-select`);
        const dropdown = document.getElementById(`${pageId}-device-dropdown`);
        const connectBtn = document.getElementById(`${pageId}-connect-btn`);

        if (!selectBtn || !dropdown) return;

        // 连接按钮事件（仅非校准页面需要）
        if (connectBtn) {
            connectBtn.addEventListener('click', () => this.connectPageDevices(pageId));
        }

        // 下拉菜单切换
        selectBtn.addEventListener('click', () => {
            dropdown.classList.toggle('hidden');
            selectBtn.classList.toggle('active');
        });

        // 点击外部关闭下拉菜单
        document.addEventListener('click', (e) => {
            if (!selectBtn.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.add('hidden');
                selectBtn.classList.remove('active');
            }
        });

        // 渲染设备选择器
        this.renderPageDeviceSelector(pageId);
    }

    renderPageDeviceSelector(pageId) {
        const dropdown = document.getElementById(`${pageId}-device-dropdown`);
        const selectedDisplay = document.getElementById(`${pageId}-selected-devices`);
        const connectBtn = document.getElementById(`${pageId}-connect-btn`);

        if (!dropdown || !selectedDisplay) return;

        // 清空下拉菜单
        dropdown.innerHTML = '';

        // 所有页面只显示在线设备
        const displayDevices = this.deviceState.getOnlineDevices();

        // 如果没有在线设备，显示提示
        if (displayDevices.length === 0) {
            const emptyText = '暂无在线设备';
            dropdown.innerHTML = `<div class="device-dropdown-item empty">${emptyText}</div>`;
            return;
        }

        // 生成设备选项前，先将已连接设备添加到选择中
        if (pageId !== 'calibration') {
            // 清空之前的选择
            this.pageDeviceSelections[pageId].clear();
            // 将所有已连接设备添加到选择中
            this.deviceState.getConnectedDevices().forEach(ip => {
                if (this.deviceState.getDeviceStatus(ip).online) {
                    this.pageDeviceSelections[pageId].add(ip);
                }
            });
        }

        // 生成设备选项
        displayDevices.forEach(ip => {
            const item = document.createElement('div');
            const displayName = this.getDeviceDisplayName(ip);

            // 校准页面使用单选逻辑，其他页面使用多选逻辑
            if (pageId === 'calibration') {
                item.className = `device-dropdown-item ${this.pageDeviceSelections[pageId].has(ip) ? 'selected' : ''}`;
                item.innerHTML = `<label>${displayName} <span style="color: var(--text-secondary); font-size: 0.8em;">${ip}</span></label>`;

                // 添加点击事件（单选）
                item.addEventListener('click', () => {
                    // 清空之前的选择
                    this.pageDeviceSelections[pageId].clear();
                    // 添加新选择
                    this.pageDeviceSelections[pageId].add(ip);
                    // 更新显示
                    this.renderPageDeviceSelector(pageId);
                    // 关闭下拉菜单
                    dropdown.classList.add('hidden');
                    const selectBtn = document.getElementById(`${pageId}-device-select`);
                    selectBtn.classList.remove('active');
                    // 触发校准设备选择变化
                    this.onCalibrationDeviceChange(ip);
                    // 自动连接到所选设备
                    this.autoConnectCalibrationDevice(ip);
                });
            } else {
                // 非校准页面：复选框状态基于是否已连接
                const isConnected = this.deviceState.getDeviceStatus(ip).connected;
                const isSelected = this.pageDeviceSelections[pageId].has(ip);
                item.className = `device-dropdown-item ${isSelected ? 'selected' : ''}`;
                item.innerHTML = `
                    <input type="checkbox" id="${pageId}-device-${ip}" ${isSelected ? 'checked' : ''}>
                    <label for="${pageId}-device-${ip}">${displayName} <span style="color: var(--text-secondary); font-size: 0.8em;">${ip}</span></label>
                `;

                // 添加点击事件
                item.addEventListener('click', (e) => {
                    // 防止复选框重复触发
                    if (e.target.tagName === 'INPUT') return;

                    const checkbox = item.querySelector('input');
                    // 直接将当前设备加入选择，不管之前的状态
                    checkbox.checked = true;
                    this.pageDeviceSelections[pageId].add(ip);
                    this.updateSelectedDevicesDisplay(pageId);
                });

                // 添加复选框事件
                const checkbox = item.querySelector('input');
                checkbox.addEventListener('change', () => {
                    // 复选框状态变化时，直接更新选择状态
                    if (checkbox.checked) {
                        this.pageDeviceSelections[pageId].add(ip);
                    } else {
                        this.pageDeviceSelections[pageId].delete(ip);
                    }
                    this.updateSelectedDevicesDisplay(pageId);
                });
            }

            dropdown.appendChild(item);
        });

        // 更新已选设备显示
        this.updateSelectedDevicesDisplay(pageId);
    }

    togglePageDeviceSelection(pageId, deviceIp, isSelected) {
        if (isSelected) {
            this.pageDeviceSelections[pageId].add(deviceIp);
        } else {
            this.pageDeviceSelections[pageId].delete(deviceIp);
        }
        this.updateSelectedDevicesDisplay(pageId);
    }

    updateSelectedDevicesDisplay(pageId) {
        const selectedDevices = this.pageDeviceSelections[pageId];
        const selectedDisplay = document.getElementById(`${pageId}-selected-devices`);
        const connectBtn = document.getElementById(`${pageId}-connect-btn`);

        if (!selectedDisplay) return;

        // 更新已选设备显示
        if (selectedDevices.size === 0) {
            selectedDisplay.textContent = '请选择设备';
        } else if (selectedDevices.size === 1) {
            const ip = Array.from(selectedDevices)[0];
            selectedDisplay.textContent = this.getDeviceDisplayName(ip);
        } else {
            selectedDisplay.textContent = `${selectedDevices.size} 台设备`;
        }

        // 更新连接按钮状态（仅非校准页面需要）
        if (connectBtn) {
            connectBtn.disabled = selectedDevices.size === 0;
        }
    }

    updateAllPageDeviceSelectors() {
        // 更新所有页面的设备选择器
        const pages = ['control', 'actions', 'sequence', 'calibration'];
        pages.forEach(page => this.renderPageDeviceSelector(page));
    }

    async connectPageDevices(pageId) {
        const selectedDevices = Array.from(this.pageDeviceSelections[pageId]);
        if (selectedDevices.length === 0) return;

        const connectBtn = document.getElementById(`${pageId}-connect-btn`);
        const originalText = connectBtn ? connectBtn.innerHTML : '';

        if (connectBtn) {
            // 更新UI状态
            connectBtn.disabled = true;
            connectBtn.innerHTML = '<span class="btn-icon">⏳</span><span>连接中...</span>';
        }

        try {
            // 调用API连接设备
            const response = await fetch(`${API_BASE}/devices/select`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ devices: selectedDevices })
            });
            const data = await response.json();

            if (data.success) {
                // 更新设备连接状态
                // 先将所有设备的连接状态设置为false
                this.deviceState.getAllDevices().forEach(ip => {
                    this.deviceState.setDeviceConnected(ip, false);
                });
                // 然后将成功连接的设备设置为true
                data.success_devices.forEach(ip => {
                    this.deviceState.setDeviceConnected(ip, true);
                });
                // 同步更新主设备管理界面的连接状态
            this.selectedDevices = new Set(data.success_devices); // 同步选中状态
            this.connectedDevices = new Set(data.success_devices); // 更新已连接设备集合
            this.renderConnectedDevices();
            this.renderDevices(); // 刷新设备列表以显示选中状态
            this.updateStatus();

                // 始终更新校准下拉框（因为可能有新设备连接）
                this.updateCalibrationSelect();
                this.syncPageSelections(); // Sync dropdowns with new connection state
                this.updateAllPageDeviceSelectors(); // 确保所有页面设备选择器都更新


                // 构建详细反馈消息
                let msg = '';
                let statusType = 'success';

                if (data.success_devices.length > 0) {
                    msg += `成功连接 ${data.success_devices.length} 台设备: ${data.success_devices.join(', ')}.`;
                }
                if (data.failed_devices.length > 0) {
                    msg += ` 连接失败: ${data.failed_devices.join(', ')}.`;
                    statusType = 'warning';
                }

                this.showNotification(msg, statusType);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            // 显示连接失败
            const errorMsg = `连接失败: ${error.message}`;
            this.showNotification(errorMsg, 'error');
        } finally {
            // 恢复按钮状态
            if (connectBtn) {
                connectBtn.disabled = false;
                connectBtn.innerHTML = originalText;
            }
        }
    }



    syncPageSelections() {
        // 重新渲染所有设备选择器以反映最新的连接状态
        // 复选框状态现在直接基于 connectedDevices，无需手动同步 pageDeviceSelections
        const pagesToSync = ['control', 'actions', 'sequence'];
        pagesToSync.forEach(page => {
            this.renderPageDeviceSelector(page);
        });
    }

    // 自动连接校准设备
    async autoConnectCalibrationDevice(deviceIp) {
        try {
            // 调用API连接设备
            const response = await fetch(`${API_BASE}/devices/select`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ devices: [deviceIp] })
            });
            const data = await response.json();

            if (data.success) {
                // 更新设备连接状态
                // 先将所有设备的连接状态设置为false
                this.deviceState.getAllDevices().forEach(ip => {
                    this.deviceState.setDeviceConnected(ip, false);
                });
                // 然后将成功连接的设备设置为true
                data.success_devices.forEach(ip => {
                    this.deviceState.setDeviceConnected(ip, true);
                });
                // 更新已连接设备集合
                this.connectedDevices = new Set(data.success_devices);
                // 更新连接状态显示
                this.renderConnectedDevices();
                this.updateStatus();
                this.updateCalibrationSelect();
                this.syncPageSelections(); // Sync dropdowns with new connection state
                this.updateAllPageDeviceSelectors(); // 确保所有页面设备选择器都更新

                // 构建详细反馈消息
                let msg = '';
                let statusType = 'success';

                if (data.success_devices.length > 0) {
                    msg += `成功连接设备: ${data.success_devices.join(', ')}.`;
                }
                if (data.failed_devices.length > 0) {
                    msg += ` 连接失败: ${data.failed_devices.join(', ')}.`;
                    statusType = 'warning';
                }

                this.showNotification(msg, statusType);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            // 显示连接失败
            const errorMsg = `连接失败: ${error.message}`;
            this.showNotification(errorMsg, 'error');
        }
    }

    // ==================== 导航逻辑 ====================
    initNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        const pages = document.querySelectorAll('.page');

        navItems.forEach(item => {
            item.addEventListener('click', () => {
                const targetPageId = item.dataset.page + '-page';

                // 更新导航状态
                navItems.forEach(nav => nav.classList.remove('active'));
                item.classList.add('active');

                // 更新页面显示
                pages.forEach(page => {
                    if (page.id === targetPageId) {
                        page.classList.add('active');
                    } else {
                        page.classList.remove('active');
                    }
                });
            });
        });
    }

    // ==================== 设备管理 ====================
    initDeviceManager() {
        const scanBtn = document.getElementById('scan-btn');
        const connectBtn = document.getElementById('connect-selected-btn');
        const toggle = document.getElementById('show-all-toggle');

        scanBtn.addEventListener('click', () => this.startScan());
        connectBtn.addEventListener('click', () => this.connectSelectedDevices());

        if (toggle) {
            toggle.addEventListener('change', (e) => {
                this.showAllDevices = e.target.checked;
                this.renderDevices();
            });
        }
    }

    // ==================== 设备库管理 ====================
    initDeviceLibrary() {
        // 设备库页面不提供设备连接服务功能，但提供批量删除功能
        this.librarySelectedDevices = new Set();

        const batchDeleteBtn = document.getElementById('batch-delete-btn');
        if (batchDeleteBtn) {
            batchDeleteBtn.addEventListener('click', () => this.batchDeleteDevices());
        }
        
        // 初始化导入导出功能
        this.initImportExport();
    }
    
    // 初始化导入导出功能
    initImportExport() {
        const importBtn = document.getElementById('import-devices-btn');
        const exportBtn = document.getElementById('export-devices-btn');
        const fileInput = document.getElementById('file-input');
        
        // 导出按钮事件
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportDevicesToFile());
        }
        
        // 导入按钮事件
        if (importBtn && fileInput) {
            importBtn.addEventListener('click', () => {
                fileInput.click();
            });
            
            // 文件选择事件
            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    this.importDevicesFromFile(file);
                    // 清空文件输入，允许重新选择同一个文件
                    fileInput.value = '';
                }
            });
        }
    }
    
    // 验证设备数据格式
    validateDeviceData(data) {
        // 检查是否为数组
        if (!Array.isArray(data)) {
            return { valid: false, message: '设备数据必须是数组格式' };
        }
        
        // 检查数组是否为空
        if (data.length === 0) {
            return { valid: false, message: '设备数据不能为空' };
        }
        
        // 验证每个设备的格式
        for (let i = 0; i < data.length; i++) {
            const device = data[i];
            
            // 检查是否为对象
            if (typeof device !== 'object' || device === null) {
                return { valid: false, message: `第 ${i + 1} 个设备数据必须是对象格式` };
            }
            
            // 检查是否包含ip字段
            if (!device.ip) {
                return { valid: false, message: `第 ${i + 1} 个设备缺少必要的ip字段` };
            }
            
            // 检查ip格式是否合法
            const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
            if (!ipRegex.test(device.ip)) {
                return { valid: false, message: `第 ${i + 1} 个设备的ip地址格式不合法: ${device.ip}` };
            }
        }
        
        return { valid: true, message: '设备数据格式验证通过' };
    }
    
    // 从文件导入设备
    async importDevicesFromFile(file) {
        try {
            // 读取文件内容
            const reader = new FileReader();
            
            // 创建Promise封装FileReader
            const fileContent = await new Promise((resolve, reject) => {
                reader.onload = (e) => resolve(e.target.result);
                reader.onerror = (e) => reject(new Error('读取文件失败'));
                reader.readAsText(file);
            });
            
            // 解析JSON
            let deviceData;
            try {
                deviceData = JSON.parse(fileContent);
            } catch (error) {
                this.showNotification('JSON格式错误，请检查文件内容', 'error');
                return;
            }
            
            // 验证数据格式
            const validationResult = this.validateDeviceData(deviceData);
            if (!validationResult.valid) {
                this.showNotification(validationResult.message, 'error');
                return;
            }
            
            // 批量添加设备
            let successCount = 0;
            let duplicateCount = 0;
            
            for (const device of deviceData) {
                // 检查设备是否已存在
                const existingDevice = this.deviceState.getAllDevices().find(ip => ip === device.ip);
                
                if (!existingDevice) {
                    // 调用API添加设备
                    try {
                        const response = await fetch(`${API_BASE}/devices/add`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ ip: device.ip, name: device.name || '' })
                        });
                        const data = await response.json();
                        
                        if (data.success) {
                            // 更新设备状态管理器
                            this.deviceState.addDevice(device.ip, device.name || '');
                            successCount++;
                        }
                    } catch (error) {
                        console.error(`添加设备 ${device.ip} 失败:`, error);
                    }
                } else {
                    duplicateCount++;
                }
            }
            
            // 更新UI
            this.renderDeviceLibrary();
            this.updateStatus();
            this.updateAllPageDeviceSelectors();
            
            // 显示导入结果
            let message = `成功导入 ${successCount} 个设备`;
            if (duplicateCount > 0) {
                message += `，${duplicateCount} 个设备已存在`;
            }
            this.showNotification(message, 'success');
            
        } catch (error) {
            this.showNotification(`导入失败: ${error.message}`, 'error');
            console.error('导入设备失败:', error);
        }
    }
    
    // 导出设备到文件
    async exportDevicesToFile() {
        try {
            // 获取所有设备数据
            const allIps = this.deviceState.getAllDevices();
            const devicesData = allIps.map(ip => {
                const status = this.deviceState.getDeviceStatus(ip);
                return {
                    ip: ip,
                    name: status.name || ''
                };
            });
            
            // 转换为JSON格式
            const jsonContent = JSON.stringify(devicesData, null, 2);
            
            // 创建Blob对象
            const blob = new Blob([jsonContent], { type: 'application/json' });
            
            // 使用文件系统访问API让用户选择保存位置
            try {
                // 检查浏览器是否支持showSaveFilePicker
                if ('showSaveFilePicker' in window) {
                    // 使用现代浏览器的文件系统访问API
                    const handle = await window.showSaveFilePicker({
                        suggestedName: 'devices.json',
                        types: [
                            {
                                description: 'JSON文件',
                                accept: {
                                    'application/json': ['.json']
                                }
                            }
                        ]
                    });
                    
                    // 写入文件
                    const writable = await handle.createWritable();
                    await writable.write(blob);
                    await writable.close();
                    
                    // 显示导出成功通知
                    this.showNotification(`成功导出 ${devicesData.length} 个设备数据`, 'success');
                } else {
                    //  fallback: 使用传统的下载方式
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'devices.json';
                    
                    // 触发下载
                    document.body.appendChild(a);
                    a.click();
                    
                    // 清理
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    
                    // 显示导出成功通知
                    this.showNotification(`成功导出 ${devicesData.length} 个设备数据`, 'success');
                }
            } catch (error) {
                // 用户取消了文件选择
                if (error.name === 'AbortError') {
                    return;
                }
                throw error;
            }
            
        } catch (error) {
            this.showNotification(`导出失败: ${error.message}`, 'error');
            console.error('导出设备失败:', error);
        }
    }

    async startScan() {
        const scanBtn = document.getElementById('scan-btn');
        const statusDiv = document.getElementById('scan-status');

        scanBtn.disabled = true;
        scanBtn.innerHTML = '<span class="btn-icon">⏳</span><span>扫描中...</span>';
        statusDiv.textContent = '正在扫描局域网设备...';

        try {
            await fetch(`${API_BASE}/scan/start`, { method: 'POST' });
        } catch (error) {
            this.showNotification('扫描请求失败', 'error');
            scanBtn.disabled = false;
            scanBtn.innerHTML = '<span class="btn-icon">🔍</span><span>开始扫描</span>';
            statusDiv.textContent = '';
        }
    }

    async loadDevices() {
        try {
            const response = await fetch(`${API_BASE}/devices`);
            const data = await response.json();
            if (data.success) {
                // 处理设备对象格式 {ip, name}
                const deviceObjects = data.devices;
                
                // 清空设备状态管理器
                this.deviceState.clearDevices();
                
                // 批量添加设备到状态管理器
                deviceObjects.forEach(device => {
                    this.deviceState.addDevice(device.ip, device.name);
                });

                // 恢复已连接设备状态
                if (data.connected_devices && data.connected_devices.length > 0) {
                    // 设置已连接设备状态
                    data.connected_devices.forEach(ip => {
                        this.deviceState.setDeviceConnected(ip, true);
                        this.deviceState.setDeviceOnline(ip, true);
                    });
                    // 同时将这些设备标记为选中，方便用户操作
                    this.selectedDevices = new Set(data.connected_devices);
                }

                this.renderDevices();
                this.renderDeviceLibrary();
                this.renderConnectedDevices();
                this.updateStatus();
                this.updateCalibrationSelect(); // 确保校准下拉框有值
                this.syncPageSelections(); // Sync dropdowns with loaded connections
                this.updateAllPageDeviceSelectors(); // 更新所有页面的设备选择器

                // 恢复校准状态
                if (data.calibration_device) {
                    this.restoreCalibrationState(data.calibration_device);
                }
            }
        } catch (error) {
            console.error('加载设备失败:', error);
        }
    }

    restoreCalibrationState(deviceIp) {
        const startBtn = document.getElementById('start-calibration-btn');
        const exitBtn = document.getElementById('exit-calibration-btn');
        const forceExitBtn = document.getElementById('force-exit-calibration-btn');
        const selectBtn = document.getElementById('calibration-device-select');

        // 选中当前校准设备
        this.pageDeviceSelections['calibration'].clear();
        this.pageDeviceSelections['calibration'].add(deviceIp);

        // 更新设备选择器显示
        this.renderPageDeviceSelector('calibration');

        // 更新UI状态为"校准中"
        startBtn.disabled = true;
        exitBtn.disabled = false;
        if (forceExitBtn) forceExitBtn.disabled = false;
        selectBtn.disabled = true;

        // 启用舵机控制
        document.querySelectorAll('.servo-btn').forEach(el => el.disabled = false);
        document.querySelectorAll('.servo-control-item input').forEach(el => el.disabled = false);

        this.showNotification(`已恢复设备 ${deviceIp} 的校准会话`, 'info');
    }

    renderDevices() {
        if (this.isRendering.devices) return;
        this.isRendering.devices = true;
        
        const list = document.getElementById('devices-list');
        const badge = document.getElementById('devices-badge');
        const connectBtn = document.getElementById('connect-selected-btn');
        const title = document.getElementById('discovered-devices-title');

        // Update Title
        if (title) {
            title.textContent = this.showAllDevices ? "全部设备" : "已发现设备";
        }

        // Filter devices
        let devicesToShow = [];
        if (this.showAllDevices) {
            devicesToShow = this.deviceState.getAllDevices();
        } else {
            devicesToShow = this.deviceState.getOnlineDevices();
        }

        // Sort devices: Connected > Online > Offline, then by IP
        devicesToShow.sort((a, b) => {
            const aStatus = this.deviceState.getDeviceStatus(a);
            const bStatus = this.deviceState.getDeviceStatus(b);
            
            const aConnected = aStatus.connected ? 1 : 0;
            const bConnected = bStatus.connected ? 1 : 0;
            if (aConnected !== bConnected) return bConnected - aConnected;

            const aOnline = aStatus.online ? 1 : 0;
            const bOnline = bStatus.online ? 1 : 0;
            if (aOnline !== bOnline) return bOnline - aOnline;

            return a.localeCompare(b, undefined, { numeric: true });
        });

        badge.textContent = devicesToShow.length;

        if (devicesToShow.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📡</div>
                    <p>尚未扫描设备</p>
                    <p class="empty-hint">点击上方"开始扫描"按钮发现设备</p>
                </div>
            `;
            connectBtn.disabled = true;
            return;
        }

        list.innerHTML = '';
        devicesToShow.forEach(ip => {
            const deviceStatus = this.deviceState.getDeviceStatus(ip);
            const isSelected = this.selectedDevices.has(ip);

            const item = document.createElement('div');
            let classes = ['device-item'];
            
            // 应用颜色编码：已连接 > 在线 > 离线
            if (deviceStatus.connected) {
                classes.push('connected');
            } else if (deviceStatus.online) {
                classes.push('online');
            } else {
                classes.push('offline');
            }
            
            if (isSelected) classes.push('selected');

            item.className = classes.join(' ');

            const displayName = this.getDeviceDisplayName(ip);
            
            // 为设备项添加data-ip属性，方便后续增量更新
            item.dataset.ip = ip;

            item.innerHTML = `
                <div class="device-info">
                    <div class="device-icon">🤖</div>
                    <div class="device-name-container">
                        <div class="device-ip">${displayName}</div>
                        <div class="device-ip-secondary">${ip}</div>
                    </div>
                </div>
                <button class="device-delete-btn" title="删除设备">×</button>
            `;

            // 点击选择设备
            item.addEventListener('click', (e) => {
                if (e.target.classList.contains('device-delete-btn')) return;

                if (this.selectedDevices.has(ip)) {
                    this.selectedDevices.delete(ip);
                    item.classList.remove('selected');
                } else {
                    this.selectedDevices.add(ip);
                    item.classList.add('selected');
                }
                connectBtn.disabled = this.selectedDevices.size === 0;
            });

            // 删除按钮事件
            item.querySelector('.device-delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                if (confirm(`确定要删除设备 ${ip} 吗？`)) {
                    this.deleteDevice(ip);
                }
            });

            list.appendChild(item);
        });

        connectBtn.disabled = this.selectedDevices.size === 0;
        this.isRendering.devices = false;
    }
    
    // 更新单个设备项的状态（增量更新）
    updateDeviceItem(ip) {
        // 查找设备管理页面的设备项
        const list = document.getElementById('devices-list');
        const item = list.querySelector(`[data-ip="${ip}"]`);
        if (item) {
            this._updateDeviceItemElement(item, ip);
        }
        
        // 查找设备库页面的设备项
        const libraryList = document.getElementById('device-library-list');
        const libraryItem = libraryList.querySelector(`[data-ip="${ip}"]`);
        if (libraryItem) {
            this._updateDeviceItemElement(libraryItem, ip);
        }
    }
    
    // 更新单个设备项元素
    _updateDeviceItemElement(item, ip) {
        const deviceStatus = this.deviceState.getDeviceStatus(ip);
        
        // 判断设备项是否在设备库页面（通过检查是否有复选框）
        const isLibraryItem = item.querySelector('.device-checkbox') !== null;
        
        // 根据设备项所在页面使用不同的选中状态判断逻辑
        let isSelected = false;
        if (isLibraryItem) {
            // 设备库页面：只使用librarySelectedDevices
            isSelected = this.librarySelectedDevices && this.librarySelectedDevices.has(ip);
        } else {
            // 设备管理页面：只使用selectedDevices
            isSelected = this.selectedDevices.has(ip);
        }
        
        // 更新设备项的类名
        let classes = ['device-item'];
        if (deviceStatus.connected) {
            classes.push('connected');
        } else if (deviceStatus.online) {
            classes.push('online');
        } else {
            classes.push('offline');
        }
        if (isSelected) classes.push('selected');
        
        item.className = classes.join(' ');
        
        // 更新复选框状态（仅设备库页面）
        if (isLibraryItem) {
            const checkbox = item.querySelector('.device-checkbox');
            if (checkbox) {
                checkbox.checked = isSelected;
            }
        }
        
        // 更新设备显示名称
        const displayName = this.getDeviceDisplayName(ip);
        const nameElement = item.querySelector('.device-ip');
        if (nameElement) {
            nameElement.textContent = displayName;
        }
    }

    // 渲染设备库页面的设备列表
    renderDeviceLibrary() {
        if (this.isRendering.deviceLibrary) return;
        this.isRendering.deviceLibrary = true;
        
        const list = document.getElementById('device-library-list');
        const badge = document.getElementById('device-library-badge');
        const batchDeleteBtn = document.getElementById('batch-delete-btn');

        // 显示所有设备
        let devicesToShow = this.deviceState.getAllDevices();

        // Sort devices: Connected > Online > Offline, then by IP
        devicesToShow.sort((a, b) => {
            const aStatus = this.deviceState.getDeviceStatus(a);
            const bStatus = this.deviceState.getDeviceStatus(b);
            
            const aConnected = aStatus.connected ? 1 : 0;
            const bConnected = bStatus.connected ? 1 : 0;
            if (aConnected !== bConnected) return bConnected - aConnected;

            const aOnline = aStatus.online ? 1 : 0;
            const bOnline = bStatus.online ? 1 : 0;
            if (aOnline !== bOnline) return bOnline - aOnline;

            return a.localeCompare(b, undefined, { numeric: true });
        });

        // 更新徽章数量
        if (badge) {
            badge.textContent = devicesToShow.length;
        }

        if (devicesToShow.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📚</div>
                    <p>设备库为空</p>
                    <p class="empty-hint">在设备管理页面添加设备到设备库</p>
                </div>
            `;
            if (batchDeleteBtn) batchDeleteBtn.disabled = true;
            return;
        }

        list.innerHTML = '';
        devicesToShow.forEach(ip => {
            const deviceStatus = this.deviceState.getDeviceStatus(ip);
            const isSelected = this.librarySelectedDevices && this.librarySelectedDevices.has(ip);

            const item = document.createElement('div');
            let classes = ['device-item'];

            // 应用颜色编码：已连接 > 在线 > 离线
            if (deviceStatus.connected) {
                classes.push('connected');
            } else if (deviceStatus.online) {
                classes.push('online');
            } else {
                classes.push('offline');
            }

            if (isSelected) {
                classes.push('selected');
            }

            item.className = classes.join(' ');
            
            // 为设备项添加data-ip属性，方便后续增量更新
            item.dataset.ip = ip;

            const displayName = this.getDeviceDisplayName(ip);

            item.innerHTML = `
                <input type="checkbox" class="device-checkbox" ${isSelected ? 'checked' : ''}>
                <div class="device-info">
                    <div class="device-icon">🤖</div>
                    <div class="device-name-container">
                        <div class="device-ip">${displayName}</div>
                        <div class="device-ip-secondary">${ip}</div>
                    </div>
                </div>
                <button class="device-rename-btn" title="重命名设备">✏️</button>
                <button class="device-delete-btn" title="删除设备">×</button>
            `;

            // 复选框点击事件
            const checkbox = item.querySelector('.device-checkbox');
            checkbox.addEventListener('click', (e) => {
                e.stopPropagation();
                if (checkbox.checked) {
                    this.librarySelectedDevices.add(ip);
                    item.classList.add('selected');
                } else {
                    this.librarySelectedDevices.delete(ip);
                    item.classList.remove('selected');
                }
                this.updateBatchDeleteButton();
            });

            // 点击设备项切换选中状态
            item.addEventListener('click', (e) => {
                if (e.target.classList.contains('device-delete-btn')) return;
                if (e.target.classList.contains('device-checkbox')) return;

                checkbox.checked = !checkbox.checked;
                if (checkbox.checked) {
                    this.librarySelectedDevices.add(ip);
                    item.classList.add('selected');
                } else {
                    this.librarySelectedDevices.delete(ip);
                    item.classList.remove('selected');
                }
                this.updateBatchDeleteButton();
            });

            // 重命名按钮事件
            item.querySelector('.device-rename-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.showRenameDialog(ip);
            });

            // 删除按钮事件
            item.querySelector('.device-delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                const displayName = this.getDeviceDisplayName(ip);
                if (confirm(`确定要删除设备 ${displayName} 吗？`)) {
                    this.deleteDevice(ip);
                }
            });

            list.appendChild(item);
        });

        this.updateBatchDeleteButton();
        this.isRendering.deviceLibrary = false;
    }

    updateBatchDeleteButton() {
        const batchDeleteBtn = document.getElementById('batch-delete-btn');
        if (batchDeleteBtn) {
            batchDeleteBtn.disabled = !this.librarySelectedDevices || this.librarySelectedDevices.size === 0;
            if (this.librarySelectedDevices && this.librarySelectedDevices.size > 0) {
                batchDeleteBtn.innerHTML = `
                    <span class="btn-icon">🗑️</span>
                    <span>批量删除 (${this.librarySelectedDevices.size})</span>
                `;
            } else {
                batchDeleteBtn.innerHTML = `
                    <span class="btn-icon">🗑️</span>
                    <span>批量删除</span>
                `;
            }
        }
    }

    async batchDeleteDevices() {
        if (!this.librarySelectedDevices || this.librarySelectedDevices.size === 0) return;

        const devicesToDelete = Array.from(this.librarySelectedDevices);
        const count = devicesToDelete.length;

        if (!confirm(`确定要删除选中的 ${count} 个设备吗？`)) return;

        const batchDeleteBtn = document.getElementById('batch-delete-btn');
        const originalText = batchDeleteBtn.innerHTML;
        batchDeleteBtn.disabled = true;
        batchDeleteBtn.innerHTML = '<span class="btn-icon">⏳</span><span>删除中...</span>';

        let successCount = 0;
        let failedDevices = [];

        for (const ip of devicesToDelete) {
            try {
                const response = await fetch(`${API_BASE}/devices/delete`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ip })
                });
                const data = await response.json();

                if (data.success) {
                    // 使用deviceState的方法删除设备
                    this.deviceState.removeDevice(ip);
                    this.selectedDevices.delete(ip);
                    this.librarySelectedDevices.delete(ip);
                    successCount++;
                } else {
                    failedDevices.push(ip);
                }
            } catch (error) {
                failedDevices.push(ip);
            }
        }

        // 更新UI
        this.isRendering.devices = false;
        this.isRendering.deviceLibrary = false;
        this.isRendering.connectedDevices = false;
        
        this.renderDevices();
        this.renderDeviceLibrary();
        this.renderConnectedDevices();
        this.updateStatus();

        // 显示结果通知
        if (successCount > 0) {
            this.showNotification(`成功删除 ${successCount} 个设备`, 'success');
        }
        if (failedDevices.length > 0) {
            this.showNotification(`${failedDevices.length} 个设备删除失败: ${failedDevices.join(', ')}`, 'error');
        }

        batchDeleteBtn.innerHTML = originalText;
        batchDeleteBtn.disabled = false;
    }

    async deleteDevice(ip) {
        try {
            const response = await fetch(`${API_BASE}/devices/delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip })
            });
            const data = await response.json();

            if (data.success) {
                // 使用deviceState的方法删除设备
                this.deviceState.removeDevice(ip);
                this.selectedDevices.delete(ip);
                this.librarySelectedDevices.delete(ip);
                
                this.isRendering.devices = false;
                this.isRendering.deviceLibrary = false;
                this.isRendering.connectedDevices = false;
                
                this.renderDevices();
                this.renderDeviceLibrary();
                this.renderConnectedDevices();
                this.updateStatus();
                this.showNotification(`设备 ${ip} 已删除`, 'success');
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            this.showNotification(`删除失败: ${error.message}`, 'error');
        }
    }

    showRenameDialog(ip) {
        const currentName = this.deviceState.getDeviceStatus(ip).name || '';
        const newName = prompt(`请输入设备的新名称：\n\n设备IP: ${ip}\n当前名称: ${currentName || '(未设置)'}\n\n留空以清除自定义名称`, currentName);

        if (newName !== null) {  // 用户点击了确定（包括空字符串）
            this.renameDevice(ip, newName.trim());
        }
    }

    async renameDevice(ip, name) {
        try {
            const response = await fetch(`${API_BASE}/devices/rename`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip, name })
            });
            const data = await response.json();

            if (data.success) {
                // 更新设备名称
                this.deviceState.setDeviceName(ip, name);

                // 清除渲染状态标记
                this.isRendering.devices = false;
                this.isRendering.deviceLibrary = false;
                this.isRendering.connectedDevices = false;

                // 重新渲染所有设备列表
                this.renderDevices();
                this.renderDeviceLibrary();
                this.renderConnectedDevices();

                this.showNotification(data.message, 'success');
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            this.showNotification(`重命名失败: ${error.message}`, 'error');
        }
    }

    async connectSelectedDevices() {
        const devices = Array.from(this.selectedDevices);
        if (devices.length === 0) return;

        const btn = document.getElementById('connect-selected-btn');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="btn-icon">⏳</span><span>连接中...</span>';

        try {
            const response = await fetch(`${API_BASE}/devices/select`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ devices })
            });
            const data = await response.json();

            if (data.success) {
                // 更新设备连接状态
                // 先将所有设备的连接状态设置为false
                this.deviceState.getAllDevices().forEach(ip => {
                    this.deviceState.setDeviceConnected(ip, false);
                });
                // 然后将成功连接的设备设置为true
                data.success_devices.forEach(ip => {
                    this.deviceState.setDeviceConnected(ip, true);
                });
                // 更新已连接设备列表
                this.connectedDevices = new Set(data.success_devices);
                
                // 清除渲染状态标记
                this.isRendering.devices = false;
                this.isRendering.deviceLibrary = false;
                this.isRendering.connectedDevices = false;
                
                this.renderConnectedDevices();
                this.updateStatus();
                this.updateCalibrationSelect(); // 更新校准下拉框
                this.syncPageSelections(); // Sync dropdowns with new connection state
                this.updateAllPageDeviceSelectors(); // 确保所有页面设备选择器都更新

                // 构建详细反馈消息
                let msg = '';
                if (data.success_devices.length > 0) {
                    msg += `成功连接 ${data.success_devices.length} 台设备: ${data.success_devices.join(', ')}。`;
                }
                if (data.failed_devices.length > 0) {
                    msg += ` 连接失败: ${data.failed_devices.join(', ')}。`;
                }

                this.showNotification(msg, data.failed_devices.length > 0 ? 'warning' : 'success');
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            this.showNotification(`连接失败: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }

    renderConnectedDevices() {
        if (this.isRendering.connectedDevices) return;
        this.isRendering.connectedDevices = true;
        
        const lists = [
            document.getElementById('connected-devices-list'),
            document.getElementById('library-connected-devices-list')
        ];
        const badges = [
            document.getElementById('connected-badge'),
            document.getElementById('library-connected-badge')
        ];
        const connectedArray = this.deviceState.getConnectedDevices();

        // 更新所有已连接设备列表的徽章数量
        badges.forEach(badge => {
            if (badge) {
                badge.textContent = connectedArray.length;
            }
        });

        // 渲染所有已连接设备列表
        lists.forEach(list => {
            if (!list) return;

            if (connectedArray.length === 0) {
                list.innerHTML = `
                    <div class="empty-state">
                        <p class="empty-hint">暂无已连接设备</p>
                    </div>
                `;
                return;
            }

            list.innerHTML = '';
            connectedArray.forEach(ip => {
                const item = document.createElement('div');
                item.className = 'device-item';

                const displayName = this.getDeviceDisplayName(ip);
                const deviceStatus = this.deviceState.getDeviceStatus(ip);
                const hasCustomName = !!deviceStatus.name;

                item.innerHTML = `
                <div class="device-info">
                    <div class="device-icon">🔗</div>
                    <div class="device-name-container">
                        <div class="device-ip">${displayName}</div>
                        <div class="device-ip-secondary">${ip}</div>
                    </div>
                </div>
                <button class="device-delete-btn" title="断开连接">×</button>
            `;

                // 添加断开连接按钮的点击事件
                const deleteBtn = item.querySelector('.device-delete-btn');
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (confirm(`确定要断开设备 ${ip} 的连接吗？`)) {
                        this.disconnectDevice(ip);
                    }
                });

                list.appendChild(item);
            });
        });
        
        this.isRendering.connectedDevices = false;
    }

    async disconnectDevice(ip) {
        try {
            const response = await fetch(`${API_BASE}/devices/disconnect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip })
            });
            const data = await response.json();

            if (data.success) {
                // 更新设备连接状态
                this.deviceState.setDeviceConnected(ip, false);
                this.selectedDevices.delete(ip);
                this.renderConnectedDevices();
                this.renderDevices(); // Update discovered devices list to reflect status change
                this.renderDeviceLibrary(); // Update device library list to reflect status change
                this.updateStatus();
                this.updateCalibrationSelect(); // 更新校准下拉框
                this.syncPageSelections(); // Sync dropdowns with new connection state
                this.updateAllPageDeviceSelectors(); // 确保所有页面设备选择器都更新
                this.showNotification(`设备 ${ip} 已断开连接`, 'success');
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            this.showNotification(`断开连接失败: ${error.message}`, 'error');
        }
    }

    updateStatus() {
        // 使用deviceState管理器获取设备数量
        const allDevicesCount = this.deviceState.getAllDevices().length;
        const connectedDevicesCount = this.deviceState.getConnectedDevices().length;
        
        document.getElementById('recorded-count').textContent = `已记录 ${allDevicesCount} 设备`;
        document.getElementById('connected-count').textContent = `已连接 ${connectedDevicesCount} 设备`;

        // 更新动作循环按钮状态
        const startLoopBtn = document.getElementById('start-loop-btn');
        if (startLoopBtn) {
            startLoopBtn.disabled = connectedDevicesCount === 0 || !this.selectedActionId || this.isLoopRunning;
        }

        // 更新序列循环按钮状态
        const startSequenceLoopBtn = document.getElementById('start-sequence-loop-btn');
        const stopSequenceLoopBtn = document.getElementById('stop-sequence-loop-btn');

        if (startSequenceLoopBtn && stopSequenceLoopBtn) {
            if (connectedDevicesCount > 0) {
                // 启用序列循环按钮（如果有序列且不在循环中）
                startSequenceLoopBtn.disabled = this.isSequenceLoopRunning || this.sequence.length === 0;
            } else {
                // 禁用序列循环按钮
                startSequenceLoopBtn.disabled = true;

                // 如果连接断开，停止所有循环
                this.stopSequenceLoop();
            }

            // 序列循环停止按钮状态
            stopSequenceLoopBtn.disabled = !this.isSequenceLoopRunning;
        }
    }

    // ==================== 虚拟摇杆 ====================
    initJoystick() {
        const joystick = document.getElementById('joystick');
        const stick = document.getElementById('joystick-stick');
        const status = document.getElementById('joystick-direction');
        let isDragging = false;
        let currentDirection = null; // 记录当前方向，但不发送

        const handleMove = (x, y) => {
            const rect = joystick.getBoundingClientRect();
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            // 计算相对中心的位置
            let deltaX = x - centerX;
            let deltaY = y - centerY;

            // 限制移动范围
            const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
            const maxDist = 60; // 摇杆最大移动半径

            if (distance > maxDist) {
                const angle = Math.atan2(deltaY, deltaX);
                deltaX = Math.cos(angle) * maxDist;
                deltaY = Math.sin(angle) * maxDist;
            }

            // 更新摇杆位置
            stick.style.transform = `translate(calc(-50% + ${deltaX}px), calc(-50% + ${deltaY}px))`;

            // 判定方向（只记录，不发送）
            let direction = null;
            const threshold = 20;

            if (Math.abs(deltaX) > Math.abs(deltaY)) {
                if (deltaX > threshold) direction = 'R'; // 右
                else if (deltaX < -threshold) direction = 'L'; // 左
            } else {
                if (deltaY > threshold) direction = 'B'; // 后
                else if (deltaY < -threshold) direction = 'F'; // 前
            }

            // 更新当前方向和UI显示
            currentDirection = direction;
            if (direction) {
                const dirNames = { 'F': '前进', 'B': '后退', 'L': '左转', 'R': '右转' };
                status.textContent = dirNames[direction];
            } else {
                status.textContent = '停止';
            }
        };

        const resetJoystick = () => {
            if (!isDragging) return;

            isDragging = false;
            stick.style.transform = 'translate(-50%, -50%)';
            stick.style.transition = 'transform 0.2s ease-out'; // 添加回弹动画

            // 只在释放时发送最后记录的方向指令
            if (currentDirection) {
                this.executeMove(currentDirection);
            }

            currentDirection = null;
            status.textContent = '等待操作';

            // 移除动画以便下次拖动
            setTimeout(() => {
                stick.style.transition = '';
            }, 200);
        };

        // 鼠标事件
        joystick.addEventListener('mousedown', (e) => {
            isDragging = true;
            stick.style.transition = ''; // 拖动时移除过渡动画
            const rect = joystick.getBoundingClientRect();
            handleMove(e.clientX - rect.left, e.clientY - rect.top);
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const rect = joystick.getBoundingClientRect();
            // 允许计算超出范围的坐标，handleMove 内部会限制距离
            handleMove(e.clientX - rect.left, e.clientY - rect.top);
        });

        document.addEventListener('mouseup', resetJoystick);

        // 键盘控制（保持原有的连续移动逻辑）
        document.addEventListener('keydown', (e) => {
            if (e.repeat) return;
            const keyMap = { 'w': 'F', 's': 'B', 'a': 'L', 'd': 'R' };
            const dir = keyMap[e.key.toLowerCase()];
            if (dir) {
                this.startContinuousMove(dir);
                const dirNames = { 'F': '前进', 'B': '后退', 'L': '左转', 'R': '右转' };
                status.textContent = dirNames[dir] + ' (键盘)';
            }
        });

        document.addEventListener('keyup', (e) => {
            const keyMap = { 'w': 'F', 's': 'B', 'a': 'L', 'd': 'R' };
            if (keyMap[e.key.toLowerCase()]) {
                this.stopContinuousMove();
                status.textContent = '等待操作';
            }
        });
    }

    async startContinuousMove(direction) {
        if (this.deviceState.getConnectedDevices().length === 0) {
            this.showNotification('请先连接设备', 'warning');
            return;
        }

        const delay = document.getElementById('move-delay').value / 1000;
        try {
            const response = await fetch(`${API_BASE}/control/continuous/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ direction, delay })
            });
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('移动失败:', error);
            this.showNotification(`移动失败: ${error.message}`, 'error');
        }
    }

    async stopContinuousMove() {
        try {
            await fetch(`${API_BASE}/control/continuous/stop`, { method: 'POST' });
        } catch (error) {
            console.error('停止失败:', error);
        }
    }

    async executeMove(direction) {
        if (this.deviceState.getConnectedDevices().length === 0) {
            this.showNotification('请先连接设备', 'warning');
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/control/move`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ direction })
            });
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('移动失败:', error);
            this.showNotification(`移动失败: ${error.message}`, 'error');
        }
    }

    // ==================== 预设动作 ====================
    initActions() {
        const grid = document.getElementById('actions-grid');

        Object.entries(ACTIONS).forEach(([id, action]) => {
            const btn = document.createElement('div');
            btn.className = 'action-btn';
            btn.innerHTML = `
                <span class="action-icon">${action.icon}</span>
                <span class="action-name">${action.name}</span>
            `;
            btn.addEventListener('click', () => this.executeAction(id));
            grid.appendChild(btn);
        });
    }

    // ==================== 动作循环功能 ====================
    initActionLoop() {
        const selectBtn = document.getElementById('loop-action-select');
        const dropdown = document.getElementById('action-dropdown');
        const startBtn = document.getElementById('start-loop-btn');
        const stopBtn = document.getElementById('stop-loop-btn');
        const delayInput = document.getElementById('loop-delay');

        // 填充动作下拉菜单
        Object.entries(ACTIONS).forEach(([id, action]) => {
            const item = document.createElement('div');
            item.className = 'action-dropdown-item';
            item.innerHTML = `
                <span class="action-dropdown-item-icon">${action.icon}</span>
                <span>${action.name}</span>
            `;
            item.addEventListener('click', () => {
                this.selectedActionId = id;
                document.getElementById('selected-action-display').textContent = `${action.icon} ${action.name}`;
                dropdown.classList.add('hidden');
                selectBtn.classList.remove('active');

                // 启用开始按钮
                startBtn.disabled = false;
            });
            dropdown.appendChild(item);
        });

        // 切换下拉菜单显示
        selectBtn.addEventListener('click', () => {
            dropdown.classList.toggle('hidden');
            selectBtn.classList.toggle('active');
        });

        // 点击外部关闭下拉菜单
        document.addEventListener('click', (e) => {
            if (!selectBtn.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.add('hidden');
                selectBtn.classList.remove('active');
            }
        });

        // 开始循环执行
        startBtn.addEventListener('click', () => {
            if (!this.selectedActionId) return;

            const delay = parseFloat(delayInput.value) * 1000; // 转换为毫秒
            this.startActionLoop(this.selectedActionId, delay);
        });

        // 停止循环执行
        stopBtn.addEventListener('click', () => {
            this.stopActionLoop();
        });

        // 更新连接设备状态时检查循环按钮状态
        this.updateStatus();
    }

    startActionLoop(actionId, delay) {
        if (this.isLoopRunning) return;

        this.isLoopRunning = true;
        const startBtn = document.getElementById('start-loop-btn');
        const stopBtn = document.getElementById('stop-loop-btn');
        const selectBtn = document.getElementById('loop-action-select');
        const delayInput = document.getElementById('loop-delay');

        // 更新UI状态
        startBtn.disabled = true;
        stopBtn.disabled = false;
        selectBtn.disabled = true;
        delayInput.disabled = true;

        // 立即执行一次动作
        this.executeAction(actionId);

        // 设置循环执行
        this.loopInterval = setInterval(() => {
            this.executeAction(actionId);
        }, delay);

        // 显示通知
        this.showNotification('开始循环执行', 'info');
    }

    stopActionLoop() {
        if (!this.isLoopRunning) return;

        this.isLoopRunning = false;

        // 清除定时器
        if (this.loopInterval) {
            clearInterval(this.loopInterval);
            this.loopInterval = null;
        }

        // 更新UI状态
        const startBtn = document.getElementById('start-loop-btn');
        const stopBtn = document.getElementById('stop-loop-btn');
        const selectBtn = document.getElementById('loop-action-select');
        const delayInput = document.getElementById('loop-delay');

        startBtn.disabled = this.deviceState.getConnectedDevices().length === 0;
        stopBtn.disabled = true;
        selectBtn.disabled = false;
        delayInput.disabled = false;

        // 显示通知
        this.showNotification('已停止', 'info');
    }

    async executeAction(actionId) {
        if (this.deviceState.getConnectedDevices().length === 0) {
            this.showNotification('请先连接设备', 'warning');
            // 如果在循环中执行，停止循环
            if (this.isLoopRunning) {
                this.stopActionLoop();
            }
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/control/action`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action_id: actionId })
            });
            const data = await response.json();
            if (data.success) {
                this.showNotification(`执行动作: ${ACTIONS[actionId].name}`, 'info');
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            this.showNotification(`执行失败: ${error.message}`, 'error');
            // 如果在循环中执行失败，停止循环
            if (this.isLoopRunning) {
                this.stopActionLoop();
            }
        }
    }

    // ==================== 舵机校准 ====================
    initCalibration() {
        const startBtn = document.getElementById('start-calibration-btn');
        const exitBtn = document.getElementById('exit-calibration-btn');
        const forceExitBtn = document.getElementById('force-exit-calibration-btn');
        const servoControls = document.getElementById('servo-controls');

        // 生成舵机控制滑块
        servoControls.innerHTML = '';
        SERVOS.forEach(servo => {
            const div = document.createElement('div');
            div.className = 'servo-control-item';
            div.innerHTML = `
                <div class="servo-header">
                    <span>${servo.name}</span>
                    <span class="servo-value" id="val-${servo.id}">0</span>
                </div>
                <div class="servo-slider-container">
                    <button class="servo-btn" id="btn-dec-${servo.id}" disabled>-</button>
                    <input type="range" id="slider-${servo.id}" min="-25" max="25" value="0" disabled>
                    <button class="servo-btn" id="btn-inc-${servo.id}" disabled>+</button>
                </div>
            `;
            servoControls.appendChild(div);

            const slider = div.querySelector('input');
            const valDisplay = document.getElementById(`val-${servo.id}`);
            const btnDec = document.getElementById(`btn-dec-${servo.id}`);
            const btnInc = document.getElementById(`btn-inc-${servo.id}`);

            // 禁用滑块交互并显示提示
            slider.addEventListener('mousedown', (e) => {
                e.preventDefault();
                if (!slider.disabled) {
                    this.showNotification('请使用两侧的加减按钮进行微调', 'info');
                }
            });

            // 兼容触摸设备
            slider.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (!slider.disabled) {
                    this.showNotification('请使用两侧的加减按钮进行微调', 'info');
                }
            });

            // 减号按钮逻辑
            btnDec.addEventListener('click', () => {
                let val = parseInt(slider.value);
                if (val > -25) {
                    val--;
                    slider.value = val;
                    valDisplay.textContent = val;
                    this.adjustServo(servo.id, val);
                }
            });

            // 加号按钮逻辑
            btnInc.addEventListener('click', () => {
                let val = parseInt(slider.value);
                if (val < 25) {
                    val++;
                    slider.value = val;
                    valDisplay.textContent = val;
                    this.adjustServo(servo.id, val);
                }
            });
        });

        // 进入校准模式
        startBtn.addEventListener('click', async () => {
            // 从新的设备选择器中获取选中的设备
            const selectedDevices = this.pageDeviceSelections['calibration'];
            if (selectedDevices.size === 0) {
                this.showNotification('请选择要校准的设备', 'warning');
                return;
            }
            const device = Array.from(selectedDevices)[0];

            startBtn.disabled = true;

            try {
                const response = await fetch(`${API_BASE}/calibration/start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ device })
                });

                const data = await response.json();
                if (data.success) {
                    this.showNotification('已进入校准模式', 'success');
                    exitBtn.disabled = false;
                    if (forceExitBtn) forceExitBtn.disabled = false;

                    // 禁用设备选择器
                    const selectBtn = document.getElementById('calibration-device-select');
                    selectBtn.disabled = true;

                    // 启用舵机控制
                    document.querySelectorAll('.servo-btn').forEach(el => el.disabled = false);
                    document.querySelectorAll('.servo-control-item input').forEach(el => el.disabled = false);
                } else {
                    this.showNotification(data.error, 'error');
                    startBtn.disabled = false;
                }
            } catch (error) {
                this.showNotification('请求失败', 'error');
                startBtn.disabled = false;
            }
        });

        // 退出校准模式
        const handleExit = async (force = false) => {
            const btn = force ? forceExitBtn : exitBtn;

            // 同时禁用两个退出按钮，防止用户在等待期间重复点击
            exitBtn.disabled = true;
            if (forceExitBtn) forceExitBtn.disabled = true;

            try {
                const response = await fetch(`${API_BASE}/calibration/exit`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ force })
                });

                const data = await response.json();
                if (data.success) {
                    this.showNotification(data.message || '已退出校准模式', force && data.warning ? 'warning' : 'success');
                    startBtn.disabled = false;
                    exitBtn.disabled = true;
                    if (forceExitBtn) forceExitBtn.disabled = true;

                    // 启用设备选择器
                    const selectBtn = document.getElementById('calibration-device-select');
                    selectBtn.disabled = false;

                    // 禁用舵机控制
                    document.querySelectorAll('.servo-btn').forEach(el => el.disabled = true);
                    document.querySelectorAll('.servo-control-item input').forEach(el => {
                        el.disabled = true;
                        el.value = 0;
                    });
                    document.querySelectorAll('.servo-value').forEach(el => el.textContent = '0');
                } else {
                    this.showNotification(data.error, 'error');

                    // 失败时重新启用退出按钮（因为仍在校准状态）
                    exitBtn.disabled = false;
                    if (forceExitBtn) forceExitBtn.disabled = false;

                    // 如果是普通退出失败，且错误不是"没有活动的校准会话"，则提示用户可以使用强制退出
                    if (!force && !data.error.includes('没有活动的校准会话')) {
                        this.showNotification('若设备已断开连接，请尝试使用旁边的强制退出按钮', 'info');
                    }
                }
            } catch (error) {
                this.showNotification('请求失败', 'error');

                // 请求异常时重新启用退出按钮
                exitBtn.disabled = false;
                if (forceExitBtn) forceExitBtn.disabled = false;
            }
        };

        exitBtn.addEventListener('click', () => handleExit(false));
        if (forceExitBtn) {
            forceExitBtn.addEventListener('click', () => {
                if (confirm('确定要强制退出校准模式吗？这将清除服务器端的校准状态，但不会向设备发送指令（适用于设备已断开连接的情况）。')) {
                    handleExit(true);
                }
            });
        }
    }

    updateCalibrationSelect() {
        // 更新校准页面的设备选择器
        this.renderPageDeviceSelector('calibration');
    }

    async adjustServo(servo, value) {
        try {
            await fetch(`${API_BASE}/calibration/adjust`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ servo, value })
            });
        } catch (error) {
            this.showNotification(`调整失败: ${error.message}`, 'error');
        }
    }

    onCalibrationDeviceChange(deviceIp) {
        const startBtn = document.getElementById('start-calibration-btn');
        startBtn.disabled = !deviceIp;
    }

    // ==================== 动作序列 ====================
    initSequenceBuilder() {
        const actionsList = document.getElementById('sequence-actions-list');
        const timeline = document.getElementById('sequence-timeline');
        const clearBtn = document.getElementById('clear-sequence-btn');
        const executeBtn = document.getElementById('execute-sequence-btn');
        const delayInput = document.getElementById('sequence-delay');

        // 生成动作选择按钮
        Object.entries(ACTIONS).forEach(([id, action]) => {
            const btn = document.createElement('button');
            btn.className = 'btn btn-sm btn-outline';
            btn.textContent = action.name;
            btn.addEventListener('click', () => this.addToSequence({ action: id }, action.name));
            actionsList.appendChild(btn);
        });

        // 移动按钮事件
        document.querySelectorAll('.sequence-moves-list button').forEach(btn => {
            btn.addEventListener('click', () => {
                const move = btn.dataset.move;
                const names = { 'F': '前进', 'B': '后退', 'L': '左转', 'R': '右转' };
                this.addToSequence({ move }, names[move]);
            });
        });

        clearBtn.addEventListener('click', () => {
            this.sequence = [];
            this.renderSequence();
        });

        executeBtn.addEventListener('click', () => this.executeSequence());
    }

    addToSequence(item, name) {
        if (this.sequence.length >= 10) {
            this.showNotification('序列最多支持10个动作', 'warning');
            return;
        }

        const delay = parseFloat(document.getElementById('sequence-delay').value);
        this.sequence.push({ ...item, delay, name });
        this.renderSequence();
    }

    renderSequence() {
        const timeline = document.getElementById('sequence-timeline');
        const executeBtn = document.getElementById('execute-sequence-btn');
        const startLoopBtn = document.getElementById('start-sequence-loop-btn');

        if (this.sequence.length === 0) {
            timeline.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🎬</div>
                    <p>序列为空</p>
                    <p class="empty-hint">从右侧添加动作或移动指令</p>
                </div>
            `;
            executeBtn.disabled = true;
            startLoopBtn.disabled = true;
            return;
        }

        timeline.innerHTML = '';
        this.sequence.forEach((item, index) => {
            const el = document.createElement('div');
            el.className = 'sequence-item';
            el.innerHTML = `
                <span>${index + 1}. ${item.name}</span>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="seq-delay">${item.delay}s</span>
                    <button class="sequence-delete-btn" title="删除此动作" data-index="${index}">×</button>
                </div>
            `;

            // 添加删除按钮的点击事件
            const deleteBtn = el.querySelector('.sequence-delete-btn');
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.removeFromSequence(index);
            });

            timeline.appendChild(el);
        });
        executeBtn.disabled = false;
        startLoopBtn.disabled = this.isSequenceLoopRunning;
    }

    removeFromSequence(index) {
        // 删除指定索引的动作
        this.sequence.splice(index, 1);
        // 重新渲染序列（后续动作会自动向前移动）
        this.renderSequence();
        this.showNotification('已删除动作', 'info');
    }

    async executeSequence() {
        const executeBtn = document.getElementById('execute-sequence-btn');

        if (this.deviceState.getConnectedDevices().length === 0) {
            this.showNotification('请先连接设备', 'warning');
            return false;
        }

        try {
            // 立即更新UI状态
            executeBtn.disabled = true;
            executeBtn.innerHTML = '<span class="btn-icon">⏳</span><span>执行中...</span>';

            const response = await fetch(`${API_BASE}/control/sequence`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sequence: this.sequence })
            });
            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error);
            }
            // 成功启动后，等待 WebSocket 通知完成
            return true;
        } catch (error) {
            this.showNotification(`启动失败: ${error.message}`, 'error');
            executeBtn.disabled = false;
            executeBtn.innerHTML = '<span class="btn-icon">▶️</span><span>执行序列</span>';
            return false;
        }
    }

    initSequenceLoop() {
        const startLoopBtn = document.getElementById('start-sequence-loop-btn');
        const stopLoopBtn = document.getElementById('stop-sequence-loop-btn');

        // 设置初始状态
        startLoopBtn.disabled = true;
        stopLoopBtn.disabled = true;

        // 添加事件监听
        startLoopBtn.addEventListener('click', () => this.startSequenceLoop());
        stopLoopBtn.addEventListener('click', () => this.stopSequenceLoop());
    }

    async startSequenceLoop() {
        const startLoopBtn = document.getElementById('start-sequence-loop-btn');
        const stopLoopBtn = document.getElementById('stop-sequence-loop-btn');
        const delayInput = document.getElementById('sequence-loop-delay');
        const delay = parseInt(delayInput.value) || 5;

        // 验证延迟值
        if (delay < 1 || delay > 300) {
            this.showNotification('延迟时间应在1-300秒之间', 'error');
            return;
        }

        // 更新状态
        this.isSequenceLoopRunning = true;
        startLoopBtn.disabled = true;
        stopLoopBtn.disabled = false;

        // 显示通知
        this.showNotification('开始序列循环执行', 'info');

        // 执行第一次序列
        const firstResult = await this.executeSequence();
        if (!firstResult) {
            // 如果第一次执行失败，不启动循环
            this.isSequenceLoopRunning = false;
            startLoopBtn.disabled = this.sequence.length === 0;
            stopLoopBtn.disabled = true;
            return;
        }

        // 设置循环间隔
        this.sequenceLoopInterval = setInterval(async () => {
            const result = await this.executeSequence();
            if (!result) {
                // 如果执行失败，停止循环
                this.stopSequenceLoop();
            }
        }, delay * 1000);
    }

    stopSequenceLoop() {
        const startLoopBtn = document.getElementById('start-sequence-loop-btn');
        const stopLoopBtn = document.getElementById('stop-sequence-loop-btn');

        // 只有在循环真正运行时才显示通知
        const wasRunning = this.isSequenceLoopRunning;

        // 清除循环
        if (this.sequenceLoopInterval) {
            clearInterval(this.sequenceLoopInterval);
            this.sequenceLoopInterval = null;
        }

        // 更新状态
        this.isSequenceLoopRunning = false;
        startLoopBtn.disabled = this.sequence.length === 0;
        stopLoopBtn.disabled = true;

        // 只在循环确实在运行时才显示通知
        if (wasRunning) {
            this.showNotification('已停止序列循环', 'info');
        }
    }

    // ==================== 通用功能 ====================
    showNotification(message, type = 'info') {
        const container = document.getElementById('notifications');
        
        // 限制通知数量，最多显示5个
        while (container.children.length >= 5) {
            container.removeChild(container.firstChild);
        }
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;

        const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️';

        notification.innerHTML = `
            <span class="notification-icon">${icon}</span>
            <span class="notification-message">${message}</span>
        `;

        container.appendChild(notification);

        // 3秒后自动消失
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(50px)';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// 启动应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
