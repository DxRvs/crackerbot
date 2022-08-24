# Info
**It is simple telegram bot for use CrackerJack service (https://github.com/ctxis/crackerjack.git)**
## Environment [envlist.txt]
<pre>
proxy_host="socks5 server name"
proxy_port="tcp port"
bot_token="token of telegram bot"
service_url="url of CrackerJack server"
servcie_username="username for CrackerJack server"
service_passwords="password for CrackerJack server"
white_list=account1,account2,account2
</pre>

## Work with docker
### Build docker image
<pre>
docker build . -t tbot
</pre>
### Export docker image
<pre>
docker save --output="tbot_latest.tar" tbot:latest
</pre>
### Import docker image
<pre>
docker load -i ./tbot_latest.tar
</pre>
### Run docker container
<pre>
docker run --restart always -d  --env-file ./envlist.txt  tbot:latest
</pre>
