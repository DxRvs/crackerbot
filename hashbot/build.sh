rm -rf ./__pycache__
docker build . -t tbot
docker save --output="tbot_latest.tar" tbot:latest
chmod +r ./tbot_latest.tar
