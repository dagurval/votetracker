docker stop infraweb
docker rm infraweb
docker run \
    -d \
    --name=infraweb \
    -v $PWD/web:/web \
    --net=bu \
    halverneus/static-file-server:latest
