import base
import time
from selenium.webdriver.common.by import By

test = base.Core("test", "https://www.baidu.com", "/login", 100)

test.driver.get(test.get_url())
test.page_load_await()
submit = test.driver.find_element(By.ID, "su")
print(submit.text)
test.human_move(submit)

time.sleep(1000)
