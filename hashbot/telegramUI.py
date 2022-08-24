import os
from CrackerJack  import CJService
from crackerbot import CracerBotService
import logging
logging.basicConfig(level=logging.INFO)


proxy_host = os.environ.get('proxy_host',None)
proxy_port = os.environ.get('proxy_port',None)
bot_token = os.environ.get('bot_token')
cjServiceURL = os.environ.get('service_url')
servcie_username = os.environ.get('servcie_username')
service_passwords = os.environ.get('service_passwords')
white_list = os.environ.get('white_list')

if __name__ == '__main__':
    if not bot_token:
        raise Exception("wrong bot_token")
    if not cjServiceURL:
        raise Exception("wrong service_url")
    if not servcie_username:
        raise Exception("wrong servcie_username")
    if not service_passwords:
        raise Exception("wrong service_passwords")
    if not white_list:
        raise Exception("wrong white_list")
    cjs = CJService(url=cjServiceURL, login=servcie_username, password=service_passwords);
    bot = CracerBotService(cjs, bot_token, proxy_host, proxy_port)
    accaunt_list = white_list.split(",")
    logging.info("White list count:"+str(len(accaunt_list)))
    for accaunt in accaunt_list:
        bot.addAvailableUser(accaunt);
    logging.info("Service running")
    bot.start()
    logging.info("Service stopped")

