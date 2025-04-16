from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import os
from urllib.parse import urljoin, urlparse
from datetime import datetime
import time
import random
import json


# 定义常量
DEBUGGER = True  # 调试模式
SEND_TIME = 10  # 每投递一个岗位
REQUEST_TIME = 2  # 请求间隔时间


# 调试信息输出
import os
from datetime import datetime


class Logger:
    LEVELS = {"debug": 10, "info": 20, "warn": 30, "error": 40}

    COLORS = {
        "debug": "\033[90m",  # 灰色
        "info": "\033[92m",  # 绿色
        "warn": "\033[93m",  # 黄色
        "error": "\033[91m",  # 红色
    }

    STYLES = {
        "debug": "\033[0m",  # 默认样式（无加粗等）
        "info": "\033[1m",  # 加粗
        "warn": "\033[4m",  # 下划线
        "error": "\033[1;31m",  # 红色加粗
    }

    RESET = "\033[0m"  # 重置样式
    current_level = "debug"
    save_logs = False
    log_dir = "logs"  # 默认日志目录

    @classmethod
    def set_level(cls, level):
        """设置日志级别"""
        if level.lower() not in cls.LEVELS:
            raise ValueError(f"未知日志等级: {level}")
        cls.current_level = level.lower()

    @classmethod
    def enable_log_save(cls, base_path):
        """启用日志保存功能，并指定基础路径"""
        cls.save_logs = True
        cls.log_dir = os.path.join(base_path, "logs")  # 生成路径: path/logs

    @classmethod
    def disable_log_save(cls):
        """禁用日志保存功能"""
        cls.save_logs = False

    @classmethod
    def _should_log(cls, level):
        """判断是否满足日志等级输出条件"""
        return cls.LEVELS[level] >= cls.LEVELS[cls.current_level]

    @classmethod
    def _write_to_file(cls, log_message):
        """写入文件，路径动态生成：logs/yyyy-mm-dd.txt"""
        if cls.save_logs:
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file_path = os.path.join(cls.log_dir, f"{date_str}.txt")
            os.makedirs(cls.log_dir, exist_ok=True)  # 确保目录存在
            with open(log_file_path, "a", encoding="utf-8") as file:
                file.write(log_message + "\n")

    @classmethod
    def _log(cls, level, title, msg=None, data=None):
        """打印日志并保存到文件"""
        if not cls._should_log(level):
            return

        color = cls.COLORS.get(level, "")
        style = cls.STYLES.get(level, "")
        now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

        log_message = f"{now}"

        # 只有标题
        if msg is None and data is None:
            log_message += f" {title}"
        else:
            log_message += f"\n{title}"
            if msg:
                log_message += f"\n{msg}"
            if data and isinstance(data, dict):
                for k, v in data.items():
                    log_message += f"\n{k}: {v}"

        # 控制台输出
        print(f"{style}{color}{log_message}{cls.RESET}")

        # 如果启用了保存日志，则写入文件
        cls._write_to_file(log_message)

    @classmethod
    def debug(cls, title, msg=None, data=None):
        cls._log("debug", title, msg, data)

    @classmethod
    def info(cls, title, msg=None, data=None):
        cls._log("info", title, msg, data)

    @classmethod
    def warn(cls, title, msg=None, data=None):
        cls._log("warn", title, msg, data)

    @classmethod
    def error(cls, title, msg=None, data=None):
        cls._log("error", title, msg, data)


# 深度查询
def deep_get(d, keys, default=None):
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, default)
        else:
            return default
    return d


# 深度设置
def deep_set(data, path, value):
    for i, key in enumerate(path):
        is_last = i == len(path) - 1

        if isinstance(key, int):
            if not isinstance(data, list):
                raise TypeError(
                    f"预期 list，但找到 {type(data).__name__}，在路径 {path[:i]}"
                )

            while len(data) <= key:
                data.append({})

            if is_last:
                data[key] = value
            else:
                if not isinstance(data[key], (dict, list)):
                    data[key] = {}
                data = data[key]

        else:  # str 类型，处理 dict
            if not isinstance(data, dict):
                raise TypeError(
                    f"预期 dict，但找到 {type(data).__name__}，在路径 {path[:i]}"
                )

            if is_last:
                data[key] = value
            else:
                if key not in data or not isinstance(data[key], (dict, list)):
                    # 如果下一个是 int，自动生成 list，否则 dict
                    next_key = path[i + 1]
                    data[key] = [] if isinstance(next_key, int) else {}
                data = data[key]


class Url:

    base = None  # 基础url
    login = None  # 登录路径


class Core:
    name = None  # 平台名称
    driver = None  # 浏览器驱动
    esumes = {}  # 属于该平台的简历
    cookies = []  # cookies
    url = Url()  # url
    login_status = False  # 登录状态
    verify_status = False  # 验证状态
    assets_path = None  # 资源目录
    output_path = None  # 输出目录
    send_amount = None  # 投递总数
    last_send_time = time.time()  # 上次发送时间
    last_request_time = time.time()  # 上次请求时间
    info = {}  # 操作信息
    filter_dict = {}  # 筛选条件映射表

    def __init__(self, name, url_base, url_login, send_amount, filter_dict):
        # 创建名字
        self.name = name
        # 配置url
        self.url.base = url_base
        self.url.login = url_login
        # 请求总数
        self.send_amount = send_amount
        # 筛选条件映射表
        self.filter_dict = filter_dict
        # 获取简历
        for key, value in Info.resume_profiles.items():
            if self.name in value["platforms"]:
                self.esumes[key] = value
        if len(self.esumes) == 0:
            exit()
        # 配置资源目录
        self.assets_path = os.path.join(os.getcwd(), "assets", self.name)
        # 配置输出目录
        self.output_path = os.path.join(os.getcwd(), "output", self.name)
        try:
            if not os.path.exists(self.output_path):
                os.makedirs(self.output_path)
        except Exception as e:
            Logger.error("创建输出目录失败", e)
        # 配置信息
        info = {}
        try:
            with open(
                os.path.join(self.output_path, "info.json"),
                "r",
                encoding="utf-8",
            ) as f:
                info = json.load(f)
        except Exception as e:
            Logger.warn("没有读取到配置信息")
        if "date" not in info or info["date"] != datetime.now().strftime("%Y-%m-%d"):
            info = {"date": datetime.now().strftime("%Y-%m-%d"), "resumes": {}}
        self.info = info
        # 配置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--ignore-certificate-errors-spki-list")
        chrome_options.add_argument("--allow-insecure-localhost")
        # 新增以下选项
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--reduce-security-for-testing")
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-logging", "enable-automation"]
        )
        chrome_options.add_experimental_option("useAutomationExtension", False)
        # 设置偏好，禁用自动化提示
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            # 下面的设置对绕过检测很重要
            "excludeSwitches": ["enable-automation"],
            "useAutomationExtension": False,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # 使用随机用户代理
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

        # 使用隐身模式
        chrome_options.add_argument("--incognito")

        # 添加新的自动化相关选项
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        # 添加CDP命令，彻底禁用"Chrome正在被自动化软件控制"的提示
        chrome_options.add_argument("--remote-debugging-port=9222")
        # 添加新的自动化相关选项
        chrome_options.add_argument("--ignore-gpu-blocklist")
        chrome_options.add_argument("--use-gl=desktop")
        # 禁用"浏览器正在被自动化软件控制"的信息栏
        chrome_options.add_argument("--disable-infobars")

        # 创建Chrome浏览器实例
        self.driver = webdriver.Chrome(options=chrome_options)

        # 核心：先访问空白页面然后执行脚本移除webdriver属性
        self.driver.get("about:blank")

        # 立即执行脚本，移除webdriver标志
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # 执行CDP命令，修改navigator.webdriver标志位
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                // 覆盖 webdriver 属性
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });
                
                // 修改window.navigator.chrome.runtime
                if (window.navigator.chrome) {
                    window.navigator.chrome = {
                        runtime: {}
                    };
                }
                
                // 修改automation标识
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // 修改语言和插件
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // 添加指纹模拟
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en-US', 'en']
                });
                
                // 覆盖 Notification API
                const originalNotification = window.Notification;
                if (originalNotification) {
                    window.Notification = function(title, options) {
                        return new originalNotification(title, options);
                    };
                    window.Notification.permission = originalNotification.permission;
                    window.Notification.requestPermission = originalNotification.requestPermission;
                }
            """
            },
        )

    # 获取实际url
    def get_url(self, url_path=""):
        return urljoin(self.url.base, url_path)

    # 防止请求频繁
    def request_await(self):
        interval = time.time() - self.last_request_time
        if interval < REQUEST_TIME:
            rest = REQUEST_TIME - interval
            Logger.info(f"请求间隔过短,等待{rest}秒")
            time.sleep(rest)
        self.last_request_time = time.time()

    # 等待页面加载完成
    def page_load_await(self, timeout=10, wait_for_element=None):
        last_url = self.driver.current_url  # 记录初始 URL
        last_change_time = time.time()  # 记录 URL 变化的时间

        while True:
            try:
                # 检查文档加载状态
                ready_state = self.driver.execute_script("return document.readyState")

                # 检查 URL 是否变化并更新时间
                current_url = self.driver.current_url
                if current_url != last_url:
                    last_url = current_url
                    last_change_time = time.time()  # 更新时间
                    Logger.info("URL 发生变化，重新检测页面加载状态")

                # 如果 URL 没有变化超过两秒并且文档状态是 complete
                if time.time() - last_change_time > 2 and ready_state == "complete":
                    # 检查是否可以获取元素（确保 DOM 元素没有失效）
                    if wait_for_element:
                        try:
                            self.driver.find_element(*wait_for_element)
                        except Exception as e:
                            Logger.info(f"获取 DOM 元素时出错: {e}")
                            return False
                    return True

            except Exception as e:
                Logger.warn(f"检查页面加载状态时出错: {e}")

            # 如果在 timeout 时间内没有加载完成，退出等待
            if time.time() - last_change_time > timeout:
                Logger.warn("等待超时，退出")
                return False

            time.sleep(1)  # 每秒检测一次

    # 添加cookies
    def add_cookies(self, cookies_str=None):
        self.page_load_await()
        # 读取cookies
        if not cookies_str:
            try:
                with open(
                    os.path.join(self.output_path, "cookies.txt"),
                    "r",
                    encoding="utf-8",
                ) as f:
                    cookies_str = f.read()
            except Exception as e:
                Logger.info("读取cookies失败", e)
                return
        else:
            self.save_cookies(cookies_str)
        # 解析cookies
        try:
            cookies_list = []

            for item in cookies_str.split("; "):
                name, value = item.split("=", 1)
                cookie = {
                    "name": name,
                    "value": value,
                    "domain": urlparse(self.url.base).netloc,
                }
                cookies_list.append(cookie)

            self.cookies = cookies_list
        except Exception as e:
            Logger.warn("解析cookies失败", e, {"cookies_str": cookies_str})
            return

        # 添加cookies
        try:
            if self.cookies:
                for cookie in self.cookies:
                    self.driver.add_cookie(cookie)
                self.driver.refresh()
                Logger.info("添加cookie完成")
            else:
                Logger.info("没有cookie,添加失败")

        except Exception as e:
            Logger.info("添加cookie失败", e)

    # 保存cookies
    def save_cookies(self, cookies_str=None):
        try:
            if cookies_str is None:
                cookies = self.driver.get_cookies()
            cookies_str = "; ".join(
                [f"{cookie['name']}={cookie['value']}" for cookie in cookies]
            )
            with open(
                os.path.join(self.output_path, "cookies.txt"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write(cookies_str)
                Logger.info("保存cookie成功")
        except Exception as e:
            Logger.info("保存cookie失败", e)

    # 检测登录状态
    def detect_login(self):
        pass

    # 检测是否触发验证
    def detect_verify(self):
        pass

    # 所有检测+请求限制
    def detect(self):
        self.page_load_await()

        # self.detect_verify()
        # if self.verify_status:
        #     Logger.warn("当前处于人机验证")
        #     return True

        # self.detect_login()
        # if not self.login_status:
        #     Logger.warn("当前处于未登录状态")
        #     login_url = self.get_url(self.url.login)
        #     if self.driver.current_url != login_url:
        #         self.driver.get(login_url)
        #     else:
        #         time.sleep(5)
        #     return True
        self.request_await()
        return False

    # 获取城市链接
    def get_city_info(self, value):
        pass

    # 模拟真实移动
    def human_move(self, element, timeout=10):
        try:
            # 等待元素可见
            WebDriverWait(self.driver, timeout).until(EC.visibility_of(element))

            # 滚动到元素可见位置
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element,
            )
            time.sleep(random.uniform(0.3, 0.8))  # 等待滚动完成

            # 使用JavaScript直接高亮元素，模拟鼠标悬停效果
            self.driver.execute_script(
                """
                var element = arguments[0];
                var originalBackground = element.style.backgroundColor;
                var originalTransition = element.style.transition;
                
                element.style.transition = 'background-color 0.3s';
                element.style.backgroundColor = 'rgba(255, 255, 0, 0.3)';
                
                setTimeout(function() {
                    element.style.backgroundColor = originalBackground;
                    element.style.transition = originalTransition;
                }, 300);
            """,
                element,
            )

            # 直接移动到元素
            actions = ActionChains(self.driver)
            actions.move_to_element(element).perform()

            time.sleep(random.uniform(0.3, 0.8))
            return True
        except Exception as e:
            print(f"移动到元素失败，错误信息：{e}")
            return False

    # 模拟真实点击
    def human_click(self, element, timeout=10):
        try:
            # 滚动到元素中间
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element,
            )
            time.sleep(random.uniform(0.3, 0.8))

            # 确保滚动完成
            time.sleep(1)

            # 简化鼠标操作，避免复杂的动作链
            actions = ActionChains(self.driver)
            # 直接移动到元素
            actions.move_to_element(element)
            # 短暂停顿
            actions.pause(random.uniform(0.2, 0.5))
            # 点击
            actions.click()
            # 执行动作链
            actions.perform()

            time.sleep(random.uniform(0.2, 0.6))
            return True
        except Exception as e:
            Logger.error("点击失败", e)
            return False

    # 模拟真实输入
    def human_type(self, by, value, text, timeout=10):
        # 显式等待元素可输入
        wait = WebDriverWait(self.driver, timeout)
        input_element = wait.until(EC.element_to_be_clickable((by, value)))

        # 清空现有输入（如果有的话）
        input_element.clear()

        # 模拟键入的过程（逐个字符）
        actions = ActionChains(self.driver)
        for char in text:
            actions.send_keys(char)
            actions.pause(random.uniform(0.1, 0.4))  # 随机停顿模拟人类输入的速度

        actions.perform()

    # 投递
    def send(self):
        pass

    # 保存信息
    def save_info(self):
        try:
            with open(
                os.path.join(self.output_path, "info.json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(self.info, f, indent=4)
                Logger.info("保存信息成功")
        except Exception as e:
            Logger.info("保存信息失败", e)

    # 修改信息
    def set_info(self, paths, value):
        data = self.info
        for i, key in enumerate(paths):
            is_last = i == len(paths) - 1

            if isinstance(key, int):
                if not isinstance(data, list):
                    raise TypeError(
                        f"路径 {paths[:i]} 处应为 list，但实际为 {type(data).__name__}"
                    )
                while len(data) <= key:
                    data.append({})
                if is_last:
                    data[key] = value
                else:
                    if not isinstance(data[key], (dict, list)):
                        data[key] = {}
                    data = data[key]

            else:  # key 是 str，处理 dict
                if not isinstance(data, dict):
                    raise TypeError(
                        f"路径 {paths[:i]} 处应为 dict，但实际为 {type(data).__name__}"
                    )
                if is_last:
                    data[key] = value
                else:
                    if key not in data or not isinstance(data[key], (dict, list)):
                        next_key = paths[i + 1]
                        data[key] = [] if isinstance(next_key, int) else {}
                    data = data[key]


class Info:
    # 存储所有预定义的简历配置
    resume_profiles = {}

    # 默认配置
    DEFAULT_CONFIG = {
        "citys": {"全国": ["全国"]},
        "keywords": ["Python"],  # 需要搜索的职位,会依次投递
        "industry": ["不限"],  # 公司行业
        "experience": ["不限"],  # 工作经验
        "jobType": "不限",  # 求职类型
        "salary": "50K以上",  # 薪资（单选）："3K以下", "3-5K", "5-10K", "10-20K", "20-50K", "50K以上"
        "degree": [
            "不限"
        ],  # 学历: "初中及以下", "中专/中技", "高中", "大专", "本科", "硕士", "博士"
        "scale": [
            "不限"
        ],  # 公司规模："0-20人", "20-99人", "100-499人", "500-999人", "1000-9999人", "10000人以上"
        "stage": [
            "不限"
        ],  # "未融资", "天使轮", "A轮", "B轮", "C轮", "D轮及以上", "已上市", "不需要融资"
        "expectedSalary": [
            25
        ],  # 期望薪资，单位为K，第一个数字为最低薪资，第二个数字为最高薪资，只填一个数字默认为最低薪水
        "filterDeadHR": True,  # 是否过滤不活跃HR,该选项会过滤半年前活跃的HR
        "sayHi": "您好,我有8年工作经验,还有AIGC大模型、Java,Python,Golang和运维的相关经验,希望应聘这个岗位,期待可以与您进一步沟通,谢谢！",  # 必须要关闭boss的自动打招呼
        "platforms": ["boss"],
    }

    def __init__(self):
        # 初始化时加载默认配置
        if "default" not in Info.resume_profiles:
            Info.resume_profiles["default"] = Info.DEFAULT_CONFIG.copy()

    @classmethod
    def add_profile(cls, name, config_dict):
        """添加一个新的简历配置"""
        # 从默认配置创建一个新的配置副本
        new_config = cls.DEFAULT_CONFIG.copy()

        # 更新新的配置副本，只有在config_dict中有值的字段会被更新
        new_config.update(config_dict)

        # 将新的配置添加到resume_profiles
        cls.resume_profiles[name] = new_config
        return cls
