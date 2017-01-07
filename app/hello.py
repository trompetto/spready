import platform
import subprocess
from flask import Flask, Response, request
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
from Crypto.PublicKey import RSA
import psycopg2

app = Flask(__name__)

@app.route("/")
def running():
  return "Hello, World!"

@app.route("/pyver")
def pyver():
  return platform.python_version()

if __name__ == "__main__":
  print("#Before app.run()")
  app.run()
  print("##### After app.run()")
