import time
import base
from base import Logger
from selenium.webdriver.common.by import By
import json
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import consts


class BossCore(base.Core):
    citys = {}

    def __init__(self):
        super().__init__(
            name="boss",
            url_base="https://www.zhipin.com/",
            url_login="/web/user/?ka=header-login",
            send_amount=300,
            filter_dict={
                "公司行业": "industry",
                "工作经验": "experience",
                "求职类型": "jobType",
                "薪资待遇": "salary",
                "学历要求": "degree",
                "公司规模": "scale",
                "融资阶段": "stage",
            },
        )

    def detect_login(self):
        last_status = self.login_status
        self.login_status = (
            len(self.driver.find_elements(By.CLASS_NAME, "link-logout")) > 0
        )
        if not last_status and self.login_status:
            self.save_cookies()

    def detect_verify(self):
        self.verify_status = (
            len(self.driver.find_elements(By.CLASS_NAME, "validate_button_click")) > 0
        )

    def get_city_info(self, value):
        province = next(iter(value.keys()))
        city = next(iter(value.keys()))
        if province in self.citys.keys():
            if city in self.citys[province].keys():
                return self.citys[province][city]

        try:
            with open(
                os.path.join(self.assets_path + "\site.json"), "r", encoding="utf-8"
            ) as f:
                allData = json.load(f)
                ProvinceData = None
                Data = None
                # 获取省份数据
                for item in allData["siteList"]:
                    if item["name"] == province:
                        ProvinceData = item
                        self.citys[province] = {}
                        break
                if ProvinceData is None:
                    Logger.warn(f"没有找到省份 {province} 的信息")
                    return
                # 获取城市数据
                for item in ProvinceData["subLevelModelList"]:
                    if item["name"] == city:
                        Data = item
                        self.citys[province][city] = {}
                        break
                if Data is None:
                    Logger.warn(f"没有找到城市 {city} 的信息")
                    return
                self.citys[province][city]["url"] = Data["url"]
                self.citys[province][city]["code"] = Data["code"]
                return self.citys[province][city]
        except Exception as e:
            Logger.warn(f"获取城市信息失败", e, {"province": province, "city": city})
            return

    def send(self):
        # 所有检查
        if core.detect():
            self.send()
            return
        # 检查简历信息
        if len(self.info["resumes"]) == 0:
            send_amount = 0

            for name, resume in self.esumes.items():
                send_amount += len(resume["keywords"]) * len(resume["citys"])
                self.info["resumes"][name] = {}

            for name, resume in self.esumes.items():
                for province, citys in resume["citys"].items():
                    self.info["resumes"][name][province] = {}
                    for city in citys:
                        self.info["resumes"][name][province][city] = {}
                        for keyword in resume["keywords"]:
                            self.info["resumes"][name][province][city][keyword] = {
                                "expected": self.send_amount // send_amount,
                                "actual": 0,
                                "page": 1,
                                "surplus": False,
                            }
            self.save_info()
        # 取出本次需要投递的
        current_name = None
        current_keyword = None
        current_province = None
        current_city = None
        actual_amount = 0

        for name, provinces in self.info["resumes"].items():
            for province, citys in provinces.items():
                for city, kywords in citys.items():
                    for keyword, info in kywords.items():
                        if (
                            info["surplus"] == False
                            and info["actual"] < info["expected"]
                        ):
                            current_province = province
                            current_city = city
                            current_keyword = keyword
                            current_name = name
                            break
                    if current_name is not None:
                        break
                if current_name is not None:
                    break
            if current_name is not None:
                break

        if actual_amount < self.send_amount and current_keyword is None:
            for name, provinces in self.info["resumes"].items():
                for province, citys in provinces.items():
                    for city, kywords in citys.items():
                        for keyword, info in kywords.items():
                            if info["surplus"] == False:
                                current_province = province
                                current_city = city
                                current_keyword = keyword
                                current_name = name
                                break
                        if current_name is not None:
                            break
                    if current_name is not None:
                        break
                if current_name is not None:
                    break
        if current_keyword is None:
            Logger.info("投递完毕")
            self.driver.close()
            exit()

        info_path = [
            "resumes",
            current_name,
            current_province,
            current_city,
            current_keyword,
        ]
        Logger.info(
            f"当前投递 {current_name} - {current_province} - {current_city} - {current_keyword}"
        )
        # 获取要投递的城市链接
        city_info = self.get_city_info({current_province: [current_city]})
        if city_info is None:
            self.info["resumes"][current_name][current_province][current_city][
                current_keyword
            ]["surplus"] = True
            self.save_info()
            return
        # 跳转到搜索页面
        self.driver.get(
            self.get_url(
                f"/web/geek/job?query={current_keyword}&city={city_info['code']}&page={base.deep_get(self.info, info_path)['page']}"
            )
        )

        # 筛选函数
        def set_filter(tag_name, filter_name):
            if filter_name == "不限":
                return True
            if core.detect():
                return False
            level_ones_dict = {}
            try:
                level_ones = self.driver.find_elements(
                    By.CLASS_NAME, "placeholder-text"
                )
                for item in level_ones:
                    s = item.find_element(By.XPATH, "./..")
                    box = s.find_element(By.XPATH, "./..")
                    level_ones_dict[item.text] = {}
                    level_ones_dict[item.text]["father"] = box
                    level_ones_dict[item.text]["self"] = item
            except Exception as e:
                Logger.error("筛选的一级菜单盒子查找失败", e)
            if level_ones_dict == 0:
                Logger.error("筛选的一级菜单盒子查找失败")
                return False
            

            try:
                level_one_box = level_ones_dict[tag_name]["father"]
                level_two_box = level_one_box.find_element(
                    By.CLASS_NAME, "filter-select-dropdown"
                )
                level_twos = level_two_box.find_elements(By.TAG_NAME, "a")
                if len(level_twos) == 0:
                    level_twos = level_two_box.find_elements(By.TAG_NAME, "li")
                if len(level_twos) == 0:
                    Logger.warn(f"筛选的二级菜单列表内容查找失败 {tag_name}")
                for item in level_twos:
                    tag_text = item.get_attribute("innerText").strip()
                    if tag_text == filter_name:
                        core.human_move(level_ones_dict[tag_name]["self"])
                        core.human_click(item)
                        Logger.info(f"设置筛选条件成功 {tag_name}-{filter_name}")
                        self.request_await()
                        try:
                            WebDriverWait(self.driver, 10).until(EC.staleness_of(item))
                        finally:
                            return True
                Logger.info(f"设置筛选条件失败 {tag_name}-{filter_name}")
            except:
                Logger.info(f"设置筛选条件失败 {tag_name}-{filter_name}")

        # 筛选
        for key,value in self.filter_dict.items():
            data = self.esumes[current_name][value]
            if isinstance(data, str):
                if set_filter(key,data) is False:
                    return
            elif isinstance(data, list):
                for name in data:
                    if set_filter(key,name) is False:
                        return
            else:
                Logger.info("格式错误 {key}")
        Logger.info("应用筛选标签完成")
            



        time.sleep(1000)


core = BossCore()

# 配置日志输出
Logger.enable_log_save(core.output_path)

# 首次打开页面
core.request_await()
core.driver.get(core.get_url())
core.page_load_await()
# 添加cookies
# core.request_await()
# core.add_cookies()
# core.page_load_await()
# 投递
core.send()

core.driver.close()
