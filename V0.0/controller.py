#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
舵机狗多设备控制程序

此模块提供了对多个舵机狗设备的统一控制功能，支持单个或批量执行预置动作、移动操作、
连续移动控制以及自定义动作序列。使用多线程技术实现高效并发控制多个设备。

依赖库：
    - requests: 用于发送HTTP控制命令到设备
    - threading: 用于实现连续移动的定时控制
    - json: 用于解析设备配置文件
    - os: 提供文件路径和系统操作功能
    - concurrent.futures: 提供线程池实现并发控制
    - typing: 提供类型注解支持
"""

import requests
import time
import threading
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

# 控制配置常量
MAX_CONCURRENT_THREADS = 20  # 最大并发线程数，用于多设备控制
CONTINUOUS_MOVE_INTERVAL = 500  # 连续移动的时间间隔（毫秒）

# 获取脚本所在目录（用于构建相对路径）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 读取扫描结果的文件路径（使用绝对路径，确保跨平台一致性）
DEVICE_FILE = os.path.join(SCRIPT_DIR, "devices.json")

# 动作ID到中文名称的映射表（用于用户界面显示）
ACTION_NAMES = {
    '1': '趴下', '2': '鞠躬', '3': '后仰', '4': '摇摆',
    '5': '前后', '6': '左右', '7': '握手', '8': '戳戳',
    '9': '抖腿', '10': '前跳', '11': '后跳', '12': '收腿',
    'F': '前进', 'B': '后退', 'L': '左转', 'R': '右转'
}

# HTTP请求头配置（模拟浏览器请求，确保设备能够正确响应）
CURL_HEADERS = [
    ("Accept", "*/*"),
    ("Accept-Language", "zh-CN,zh;q=0.9,zh-HK;q=0.8"),
    ("Connection", "keep-alive"),
    ("Content-Type", "application/json"),
    ("Origin", "http://esp-hi.local"),
    ("Referer", "http://esp-hi.local/"),
    ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
]

class ServoDogController:
    """
    单个舵机狗设备的控制器类
    
    提供与单个舵机狗设备通信的接口，包括执行动作、移动操作、连续移动控制和动作序列执行。
    封装了所有与设备控制相关的HTTP请求处理。
    """
    
    def __init__(self, device: str, port=80):
        """
        初始化设备控制器
        
        Args:
            device: 设备的IP地址或主机名
            port: 设备HTTP服务端口，默认为80
        """
        self.device = device  # 存储目标设备标识
        self.control_url = f"http://{device}:{port}/control"  # 控制接口URL
        
        # 配置HTTP请求头，并设置正确的Host字段
        self.headers = dict(CURL_HEADERS)
        self.headers["Host"] = device
        
        self.continuous_timer = None  # 用于连续移动的定时器实例
        
        # 创建并配置HTTP会话，重用连接以提高性能
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False  # 忽略SSL证书验证（开发环境）

    def _send_raw_command(self, data: str) -> Dict:
        """
        发送原始命令到设备
        
        将原始JSON字符串作为命令发送到设备的控制接口，处理响应和错误情况。
        
        Args:
            data: 要发送的JSON格式命令字符串
            
        Returns:
            包含请求结果的字典，格式为{"success": bool, "response": str}或{"success": bool, "error": str}
        """
        try:
            # 发送POST请求到设备控制接口
            response = self.session.post(
                url=self.control_url,
                data=data,  # 直接发送字符串数据而非JSON对象
                timeout=0.5,  # 设置较短的超时时间，提高响应速度
                allow_redirects=False  # 禁止自动重定向
            )
            
            response.raise_for_status()  # 如果响应状态码不是200，抛出HTTPError异常
            return {"success": True, "response": response.text}  # 请求成功返回响应内容
        except Exception as e:
            return {"success": False, "error": str(e)}  # 请求失败返回错误信息

    def execute_action(self, action_id: str) -> str:
        """
        执行指定的预置动作
        
        根据动作ID发送动作执行命令到设备，返回执行结果信息。
        
        Args:
            action_id: 动作ID字符串（如'1'代表'趴下'）
            
        Returns:
            执行结果的描述字符串，包含成功/失败状态和详细信息
        """
        # 验证动作ID是否有效
        if action_id not in ACTION_NAMES:
            return f"❌ 无效ID"
        
        # 构建并发送动作命令
        result = self._send_raw_command(f'{{"action":"{action_id}"}}')
        
        # 根据执行结果返回相应的状态信息
        return f"✅ 成功" if (result["success"] and result["response"] == '{"code":200}') else f"❌ 失败：{result['error'] or result['response']}"

    def execute_move(self, direction: str) -> str:
        """
        执行单次移动操作
        
        根据方向指令发送单次移动命令到设备，返回执行结果信息。
        
        Args:
            direction: 移动方向（'F'-前进, 'B'-后退, 'L'-左转, 'R'-右转），大小写不敏感
            
        Returns:
            执行结果的描述字符串，包含成功/失败状态和详细信息
        """
        direction = direction.upper()  # 将方向转换为大写以实现大小写不敏感
        
        # 验证方向是否有效
        if direction not in ['F', 'B', 'L', 'R']:
            return "❌ 无效方向"
        
        # 构建并发送移动命令
        result = self._send_raw_command(f'{{"move":"{direction}"}}')
        
        # 根据执行结果返回相应的状态信息
        return f"✅ 成功" if (result["success"] and result["response"] == '{"code":200}') else f"❌ 失败：{result['error'] or result['response']}"

    def start_continuous_move(self, direction: str, delay: float = None) -> str:
        """
        启动连续移动模式
        
        以指定的时间间隔持续发送移动命令，实现连续移动效果。
        如果已有连续移动在运行，会先停止之前的移动。
        
        Args:
            direction: 移动方向（'F'-前进, 'B'-后退, 'L'-左转, 'R'-右转），大小写不敏感
            delay: 移动间隔时间（秒），如果不指定则使用默认值
            
        Returns:
            操作结果的描述字符串
        """
        direction = direction.upper()  # 将方向转换为大写以实现大小写不敏感
        
        # 验证方向是否有效
        if direction not in ['F', 'B', 'L', 'R']:
            return "❌ 无效方向"
        
        # 计算移动间隔时间（转换为毫秒）
        move_interval = delay * 1000 if delay is not None else CONTINUOUS_MOVE_INTERVAL
        if move_interval <= 0:
            return "❌ 延迟时间必须大于0"
        
        # 确保停止之前可能正在运行的连续移动
        self.stop_continuous_move()
        
        def _send_continuous():
            """内部函数：持续发送移动命令的逻辑"""
            # 使用时间戳来确保精确的时间间隔，不受网络请求延迟影响
            next_send_time = time.time()
            while self.continuous_timer and self.continuous_timer.running:
                # 发送移动命令
                self._send_raw_command(f'{{"move":"{direction}"}}')
                
                # 计算下次发送时间并等待（确保间隔精度）
                next_send_time += move_interval / 1000
                current_time = time.time()
                if next_send_time > current_time:
                    time.sleep(next_send_time - current_time)
        
        # 创建并启动连续移动定时器
        self.continuous_timer = _ContinuousTimer(_send_continuous)
        self.continuous_timer.start()
        
        return f"✅ 已启动（延迟：{move_interval:.1f}ms）"

    def stop_continuous_move(self) -> str:
        """
        停止当前的连续移动
        
        停止正在运行的连续移动定时器，并清理相关资源。
        如果没有正在运行的连续移动，返回相应提示。
        
        Returns:
            操作结果的描述字符串
        """
        if self.continuous_timer:
            self.continuous_timer.stop()  # 停止定时器
            self.continuous_timer = None  # 清理引用
            return "✅ 已停止"
        return "ℹ️ 无连续移动"

    def run_sequence(self, sequence: List[Dict]) -> str:
        """
        执行自定义动作序列
        
        按照提供的动作序列依次执行动作或移动命令，每个操作之间有指定的延迟时间。
        
        Args:
            sequence: 动作序列列表，每个元素为包含'action'或'move'键的字典，以及可选的'delay'键
            
        Returns:
            序列执行结果的描述字符串
        """
        try:
            # 遍历序列中的每个动作项
            for item in sequence:
                # 根据动作项类型构建相应的命令
                if "action" in item:
                    cmd = f'{{"action":"{item["action"]}"}}'
                elif "move" in item:
                    cmd = f'{{"move":"{item["move"].upper()}"}}'
                else:
                    return "❌ 序列项格式错误"
                
                # 发送命令到设备
                self._send_raw_command(cmd)
                
                # 等待指定的延迟时间（默认为1秒）
                time.sleep(item.get("delay", 1.0))
            
            return "✅ 序列完成"
        except Exception as e:
            return f"❌ 序列失败：{str(e)}"

class _ContinuousTimer:
    """
    连续执行任务的定时器类（内部使用）
    
    在后台线程中定期执行指定的函数，提供启动和停止功能，
    包含错误处理和资源管理机制。
    """
    
    def __init__(self, func):
        """
        初始化定时器
        
        Args:
            func: 要定期执行的函数
        """
        self.func = func  # 存储要执行的函数
        self.running = False  # 运行状态标志
        # 创建守护线程，确保主线程结束时自动终止
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        """
        线程主循环，持续执行指定函数
        
        包含异常处理，确保即使函数执行出错也不会导致线程终止。
        """
        while self.running:
            try:
                self.func()  # 执行目标函数
            except Exception as e:
                print(f"⚠️ 连续移动出错：{str(e)}")
                # 出错时短暂等待避免CPU占用过高
                if self.running:  # 再次检查running状态，避免在except期间状态已改变
                    time.sleep(0.1)

    def start(self):
        """
        启动定时器
        
        设置运行标志并启动线程（如果线程尚未运行）
        """
        self.running = True
        if not self.thread.is_alive():
            self.thread.start()

    def stop(self):
        """
        停止定时器
        
        设置运行标志为False并等待线程结束，确保资源正确释放。
        """
        self.running = False
        # 等待线程结束，确保资源正确释放
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)  # 设置超时避免无限等待

class MultiDeviceManager:
    """
    多设备管理器类
    
    管理多个舵机狗设备的控制器，提供批量执行操作的功能。
    使用线程池实现高效并发控制。
    """
    
    def __init__(self, devices: List[str]):
        """
        初始化多设备管理器
        
        Args:
            devices: 要管理的设备IP地址列表
        """
        self.selected_devices = devices  # 存储所有选定的设备
        self.controllers = {}  # 设备ID到控制器实例的映射
        # 创建线程池用于并发控制多个设备
        self.executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_THREADS)
        # 初始化所有设备的控制器
        self._init_controllers()

    def _init_controllers(self):
        """初始化所有设备的控制器"""
        futures = []
        for device in self.selected_devices:
            futures.append(self.executor.submit(self._verify_device, device))
        
        for future in as_completed(futures):
            device, controller, success = future.result()
            if success:
                self.controllers[device] = controller
                print(f"✅ 设备 {device} 连接成功")
            else:
                print(f"❌ 设备 {device} 连接失败，已跳过")

    def _verify_device(self, device: str) -> tuple:
        """
        验证设备是否可连接并正常响应
        
        创建设备控制器并发送测试命令，检查设备是否在线且能正确响应。
        
        Args:
            device: 要验证的设备IP地址
            
        Returns:
            包含(device, controller, success)的元组，其中success表示验证是否成功
        """
        try:
            controller = ServoDogController(device)
            result = controller._send_raw_command('{}')
            return (device, controller, result["success"] and result["response"] == '{"code":200}')
        except Exception as e:
            print(f"⚠️ 设备 {device} 验证失败：{str(e)}")
            return (device, None, False)

    def batch_execute_action(self, action_id: str) -> None:
        """
        批量执行预置动作
        
        向所有连接的设备并发发送相同的动作命令，使用线程池提高效率。
        
        Args:
            action_id: 要执行的动作ID字符串
        """
        if not self.controllers:
            print("⚠️ 没有可用设备")
            return
        
        action_name = ACTION_NAMES.get(action_id, "未知动作")
        print(f"\n=== 向 {len(self.controllers)} 个设备并发发送动作：{action_name} ===")
        
        futures = []
        for device, controller in self.controllers.items():
            futures.append(self.executor.submit(
                lambda d, c: print(f"  {d}：{c.execute_action(action_id)}"),
                device, controller
            ))
        
        # 等待所有任务完成
        for future in as_completed(futures):
            pass

    def batch_execute_move(self, direction: str) -> None:
        """
        批量执行单次移动操作
        
        向所有连接的设备并发发送相同的单次移动命令，使用线程池提高效率。
        
        Args:
            direction: 移动方向（'F'-前进, 'B'-后退, 'L'-左转, 'R'-右转）
        """
        if not self.controllers:
            print("⚠️ 没有可用设备")
            return
        
        direction = direction.upper()
        move_name = ACTION_NAMES.get(direction, "未知移动")
        print(f"\n=== 向 {len(self.controllers)} 个设备并发发送移动：{move_name} ===")
        
        futures = []
        for device, controller in self.controllers.items():
            futures.append(self.executor.submit(
                lambda d, c, dir: print(f"  {d}：{c.execute_move(dir)}"),
                device, controller, direction
            ))
        
        # 等待所有任务完成
        for future in as_completed(futures):
            pass

    def batch_start_continuous_move(self, direction: str, delay: float = None) -> None:
        """
        批量启动连续移动模式
        
        向所有连接的设备并发发送启动连续移动命令，使用指定的移动间隔。
        
        Args:
            direction: 移动方向（'F'-前进, 'B'-后退, 'L'-左转, 'R'-右转）
            delay: 移动间隔时间（秒），如果为None则使用默认值
        """
        if not self.controllers:
            print("⚠️ 没有可用设备")
            return
        
        direction = direction.upper()
        move_name = ACTION_NAMES.get(direction, "未知移动")
        delay_info = f"（延迟：{delay}s）" if delay is not None else ""
        print(f"\n=== 向 {len(self.controllers)} 个设备并发启动连续{move_name}{delay_info} ===")
        
        futures = []
        for device, controller in self.controllers.items():
            futures.append(self.executor.submit(
                lambda d, c, dir, del_val: print(f"  {d}：{c.start_continuous_move(dir, del_val)}"),
                device, controller, direction, delay
            ))
        
        # 等待所有任务完成
        for future in as_completed(futures):
            pass

    def batch_stop_continuous_move(self) -> None:
        """
        批量停止所有设备的连续移动
        
        向所有连接的设备并发发送停止连续移动命令，确保所有设备停止移动。
        """
        if not self.controllers:
            print("⚠️ 没有可用设备")
            return
        
        print(f"\n=== 并发停止所有 {len(self.controllers)} 个设备的连续移动 ===")
        
        futures = []
        for device, controller in self.controllers.items():
            futures.append(self.executor.submit(
                lambda d, c: print(f"  {d}：{c.stop_continuous_move()}"),
                device, controller
            ))
        
        # 等待所有任务完成
        for future in as_completed(futures):
            pass

    def batch_run_sequence(self, sequence: List[Dict]) -> None:
        """
        批量执行自定义动作序列
        
        向所有连接的设备并发发送相同的自定义动作序列，每个设备独立执行序列。
        
        Args:
            sequence: 动作序列列表，每个元素为包含'action'或'move'键的字典，以及可选的'delay'键
        """
        if not self.controllers:
            print("⚠️ 没有可用设备")
            return
        
        print(f"\n=== 向 {len(self.controllers)} 个设备并发发送自定义序列 ===")
        
        futures = []
        for device, controller in self.controllers.items():
            futures.append(self.executor.submit(
                lambda d, c, seq: (print(f"\n--- 设备 {d} 执行序列 ---"), print(f"  结果：{c.run_sequence(seq)}")),
                device, controller, sequence
            ))
        
        # 等待所有任务完成
        for future in as_completed(futures):
            pass

def load_devices():
    """
    从文件加载设备列表
    
    读取之前扫描保存在devices.json文件中的设备IP地址列表，用于初始化控制器。
    处理文件不存在、文件为空或格式错误等异常情况。
    
    Returns:
        设备IP地址列表，如果加载失败则返回None
    """
    try:
        with open(DEVICE_FILE, "r", encoding="utf-8") as f:
            devices = json.load(f)
        if not devices:
            print(f"⚠️ {DEVICE_FILE} 中没有设备，请先运行扫描程序")
            return None
        return devices
    except FileNotFoundError:
        print(f"⚠️ 未找到 {DEVICE_FILE}，请先运行 scanner.py 扫描设备")
        return None
    except Exception as e:
        print(f"⚠️ 加载设备列表失败：{str(e)}")
        return None

def main():
    """
    程序主入口
    
    加载设备列表，处理用户输入选择设备，显示主控制菜单，并根据用户选择调用相应的功能。
    提供完整的用户交互界面，包括设备选择、动作执行、移动控制、自定义序列等功能。
    """
    print("=" * 60)
    print("    舵机狗多设备控制程序（分离扫描版）    ")
    print("=" * 60)
    
    # 加载扫描好的设备列表
    devices = load_devices()
    if not devices:
        return
    
    # 显示发现的设备
    print("\n已发现的设备：")
    for i, device in enumerate(devices):
        print(f"{i+1}. {device}")
    
    # 选择要控制的设备
    while True:
        user_input = input("\n选择要控制的设备（格式：1,3-5 或 all 选择全部，0退出）：").strip()
        if user_input.lower() == "0":
            print("👋 程序已退出，再见！")
            return
        if user_input.lower() == "all":
            selected = devices
            break
        try:
            # 解析用户输入的设备选择格式
            indices = set()
            for part in user_input.split(","):
                part = part.strip()
                if "-" in part:
                    # 处理范围选择（如3-5）
                    start, end = map(int, part.split("-"))
                    indices.update(range(start-1, end))
                else:
                    # 处理单个选择（如1）
                    indices.add(int(part)-1)
            # 过滤无效索引
            valid_indices = [i for i in indices if 0 <= i < len(devices)]
            if not valid_indices:
                print("❌ 无效选择")
                continue
            selected = [devices[i] for i in valid_indices]
            break
        except Exception as e:
            print(f"❌ 格式错误（示例：1,3-5 或 all）: {str(e)}")
    
    # 初始化多设备管理器
    manager = MultiDeviceManager(selected)
    if not manager.controllers:
        print("❌ 没有可用的设备，退出")
        return
    
    # 主控制菜单循环
    while True:
        print("\n" + "=" * 60)
        print("                控制菜单")
        print("=" * 60)
        print(f"当前选中 {len(manager.controllers)} 个设备：{', '.join(manager.controllers.keys())}")
        print("1. 执行预置动作（1-12）")
        print("2. 单次移动控制（前/后/左/右）")
        print("3. 连续移动控制（长按模式）")
        print("4. 运行自定义动作序列")
        print("5. 重新选择设备")
        print("0. 退出程序")
        print("=" * 60)
        
        choice = input("选择功能（0-5）：").strip()
        
        # 处理预置动作执行
        if choice == "1":
            while True:
                print("\n--- 预置动作列表 ---")
                for i in range(1, 13):
                    print(f"{i:2d}. {ACTION_NAMES[str(i)]}")
                print("0. 返回上一级")
                action_id = input("动作ID（1-12）或0返回：").strip()
                if action_id == "0":
                    break
                manager.batch_execute_action(action_id)
        
        # 处理单次移动控制
        elif choice == "2":
            dir_map = {"1": "F", "2": "B", "3": "L", "4": "R"}
            while True:
                print("\n--- 单次移动 ---")
                print("1. 前进(F)  2. 后退(B)  3. 左转(L)  4. 右转(R)")
                print("0. 返回上一级")
                dir_choice = input("方向选择：").strip()
                if dir_choice == "0":
                    break
                if dir_choice in dir_map:
                    manager.batch_execute_move(dir_map[dir_choice])
                else:
                    print("❌ 无效选择（0-4）")
        
        # 处理连续移动控制
        elif choice == "3":
            dir_map = {"1": "F", "2": "B", "3": "L", "4": "R"}
            while True:
                print("\n--- 连续移动 ---")
                print("1. 前进(F)  2. 后退(B)  3. 左转(L)  4. 右转(R)  0. 返回上一级")
                dir_choice = input("方向选择：").strip()
                if dir_choice == "0":
                    manager.batch_stop_continuous_move()  # 确保停止任何移动
                    break
                elif dir_choice in dir_map:
                    # 询问用户是否设置延迟
                    delay_input = input("输入延迟时间（秒），直接回车使用默认值：").strip()
                    delay = None
                    if delay_input:
                        try:
                            delay = float(delay_input)
                            if delay <= 0:
                                print("❌ 延迟时间必须大于0，使用默认值")
                                delay = None
                        except ValueError:
                            print("❌ 无效的延迟时间，使用默认值")
                            delay = None
                    
                    # 启动连续移动并等待用户停止
                    manager.batch_start_continuous_move(dir_map[dir_choice], delay)
                    input("按Enter键停止所有设备的连续移动...\n")
                    manager.batch_stop_continuous_move()
                else:
                    print("❌ 无效选择（0-4）")
        
        # 处理自定义动作序列
        elif choice == "4":
            while True:
                print("\n--- 自定义动作序列 ---")
                print("最多4个动作，支持动作（1-12）和移动（F/B/L/R），延迟0-10秒")
                sequence = []
                return_to_main = False
                while len(sequence) < 4:
                    # 显示当前序列
                    print(f"\n当前序列（{len(sequence)}/4）：")
                    for i, item in enumerate(sequence):
                        act_key = item.get("action") or item.get("move")
                        print(f"  {i+1}. {ACTION_NAMES[act_key]}（延迟{item['delay']}s）")
                    
                    # 子菜单选项
                    print("\n1. 添加预置动作  2. 添加移动  3. 完成并执行  0. 返回上一级")
                    sub_choice = input("选择：").strip()
                    
                    # 处理返回主菜单
                    if sub_choice == "0":
                        confirm = input("确定要返回吗？已创建的序列将不会保存。(y/n)：").strip().lower()
                        if confirm == 'y':
                            return_to_main = True
                            break
                        continue
                    
                    # 处理完成并执行
                    if sub_choice == "3":
                        if not sequence:
                            print("❌ 序列不能为空")
                            continue
                        break
                    
                    # 验证子菜单选择
                    if sub_choice not in ["1", "2"]:
                        print("❌ 请输入0、1、2或3")
                        continue
                    
                    # 获取延迟时间
                    try:
                        delay = float(input("动作后延迟（0-10秒）：").strip())
                        if not (0 <= delay <= 10):
                            print("❌ 延迟必须在0-10秒之间")
                            continue
                    except ValueError:
                        print("❌ 请输入数字")
                        continue
                    
                    # 添加预置动作
                    if sub_choice == "1":
                        action_id = input("动作ID（1-12）：").strip()
                        if action_id in ACTION_NAMES and action_id.isdigit():
                            sequence.append({"action": action_id, "delay": delay})
                            print(f"✅ 添加动作：{ACTION_NAMES[action_id]}")
                        else:
                            print("❌ 无效动作ID")
                    # 添加移动操作
                    else:
                        move_dir = input("移动方向（F/B/L/R）：").strip().upper()
                        if move_dir in ['F', 'B', 'L', 'R']:
                            sequence.append({"move": move_dir, "delay": delay})
                            print(f"✅ 添加移动：{ACTION_NAMES[move_dir]}")
                        else:
                            print("❌ 无效方向")
                
                if return_to_main:
                    break
                if sequence:
                    manager.batch_run_sequence(sequence)
        
        # 处理重新选择设备
        elif choice == "5":
            print("\n--- 重新选择设备 ---")
            print("0. 返回上一级")
            
            # 显示发现的设备
            print("\n已发现的设备：")
            for i, device in enumerate(devices):
                print(f"{i+1}. {device}")
            
            # 选择要控制的设备
            while True:
                user_input = input("\n选择要控制的设备（格式：1,3-5 或 all 选择全部，0返回）：").strip()
                if user_input.lower() == "0":
                    break
                if user_input.lower() == "all":
                    selected = devices
                    break
                try:
                    # 解析用户输入的设备选择格式
                    indices = set()
                    for part in user_input.split(","):
                        part = part.strip()
                        if "-" in part:
                            start, end = map(int, part.split("-"))
                            indices.update(range(start-1, end))
                        else:
                            indices.add(int(part)-1)
                    valid_indices = [i for i in indices if 0 <= i < len(devices)]
                    if not valid_indices:
                        print("❌ 无效选择")
                        continue
                    selected = [devices[i] for i in valid_indices]
                    break
                except:
                    print("❌ 格式错误（示例：1,3-5 或 all）")
            
            # 如果用户选择了设备而不是返回
            if user_input.lower() != "0":
                # 初始化新的管理器
                manager = MultiDeviceManager(selected)
                if not manager.controllers:
                    print("❌ 没有可用的设备，将保留之前的选择")
        
        # 处理退出程序
        elif choice == "0":
            print("\n👋 程序已退出，再见！")
            break
        
        # 处理无效选择
        else:
            print("❌ 无效选择，请输入0-5")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()