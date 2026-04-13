# Launch Ollama docker from command line interface
```bash
#first clean all images and containners
sudo docker stop $(docker ps -q) &&
sudo docker rm $(docker ps -aq) &&
sudo docker rmi -f $(docker images -aq) &&
sudo docker volume rm $(docker volume ls -q) &&
sudo docker network rm $(docker network ls -q) &&
cd /home/operador/Documents/kamerdyner-dev &&
sudo docker compose -f ci-scripts/dockerfiles/ollama/docker-compose.yaml up -d --build
```
# Run all
```bash
cd /home/operador/Documents/brain-ws/docker/model &&
sudo docker compose down -v && sudo docker compose build --no-cache --progress=plain && sudo docker compose up -d
```