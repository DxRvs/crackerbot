FROM python:3.9-slim-buster
LABEL MAINTAINER="df000f5@gmail.com"
WORKDIR /root
RUN apt-get update && apt-get upgrade -y && apt-get install -y python3-pip 
RUN pip3 install --upgrade pip
COPY telegramUI.py /root/
COPY CrackerJack.py /root/
COPY crackerbot.py /root/
COPY requirements.txt /root/
RUN pip3 install -r /root/requirements.txt
ENTRYPOINT ["python","telegramUI.py"]
