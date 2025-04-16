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

        # 所有检查
        if core.detect():
            self.send()
            return

        ## 设置筛选标签
        def get_level_ones():
            if core.detect():
                return
            try:
                level_ones = self.driver.find_elements(By.CLASS_NAME, "placeholder-text")
                level_ones_dict = {}
                for item in level_ones:
                    s = item.find_element(By.XPATH, "./..")
                    box = s.find_element(By.XPATH, "./..")
                    level_ones_dict[item.text] = {}
                    level_ones_dict[item.text]["father"] = box
                    level_ones_dict[item.text]["self"] = item
                if len(level_ones_dict)!=0:
                    return level_ones_dict
                else:
                    Logger.error("筛选的一级菜单盒子查找失败")
            except Exception as e:
                Logger.error("筛选的一级菜单盒子查找失败")


        # 设置公司行业
        current_industry_site = 0
        while current_industry_site < len(self.esumes[current_name]["industry"]):
            try:
                level_ones_dict = get_level_ones()
                if level_ones_dict is None: return
                is_select = False
                level_one_box = level_ones_dict["公司行业"]["father"]
                level_two_box = level_one_box.find_element(
                    By.CLASS_NAME, "filter-select-dropdown"
                )
                if level_two_box is None:
                    Logger.error("公司行业的二级菜单盒子查找失败")
                level_twos = level_two_box.find_elements(By.TAG_NAME, "a")
                if level_twos is None:
                    Logger.error("公司行业的二级菜单选项查找失败")
                while not is_select and current_industry_site < len(
                    self.esumes[current_name]["industry"]
                ):
                    for item in level_twos:
                        tag_text = item.get_attribute("innerText")
                        if (
                            tag_text
                            == self.esumes[current_name]["industry"][
                                current_industry_site
                            ]
                        ):
                            core.human_move(level_ones_dict["公司行业"]["self"])
                            core.human_click(item)
                            is_select = True
                            WebDriverWait(self.driver, 10).until(EC.staleness_of(item))
                            break
            except Exception as e:
                Logger.error(
                    "设置公司行业失败",
                    e,
                    {
                        "industry": self.esumes[current_name]["industry"][
                            current_industry_site
                        ]
                    },
                )
            finally:
                current_industry_site += 1
        

        Logger.info("设置公司行业完成")
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
