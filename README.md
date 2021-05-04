# littleshot - Work-in-progress (at least the documentation part...)
webpage screenshot and metadata capture webapp

# Use case

# Technologies
- Docker - https://www.docker.com/
- Python - https://www.python.org/
- Flask - https://flask.palletsprojects.com/en/1.1.x/
- Mongodb - https://www.mongodb.com/
- Mongoexpress - https://github.com/mongo-express/mongo-express
- Redis - https://redis.io/
- Python-rq - https://python-rq.org/
- RQ Dashboard - https://github.com/Parallels/rq-dashboard
- Minio - https://min.io/
- Caddy - https://caddyserver.com/

# Running the project
## requirements
- Docker - easy way to install: https://get.docker.com/
- Docker-compose - https://docs.docker.com/compose/install/

```
git clone https://github.com/BoredHackerBlog/littleshot
cd littleshot
docker-compose up --build -d caddy
```

# Usage
Visit http://your_docker_host_ip:8888/

# Modifying the project

# Warning
Read through the docker-compose file comments and comments in the code. Be sure to change default passwords as well. Be careful with where/how you host this project and who has access to use it. By screenshotting other sites, you could be revealing your IP. In addition to that, there may be some injection vulns with how queries to mongodb are done. (feel free to use this app as a target for your next CTF)
