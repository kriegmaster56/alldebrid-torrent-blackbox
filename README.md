# alldebrid-torrent-blackbox
## Goal

the goal of this project is to be fed .torrent file, upload it to alldebrid, let alldebrid download it and upload to a direct download service and then use the debrided link to download the file.

## How to use this project

1- complete config.ini file with api key 

2- build docker image

```docker build -t alldebrid-torrent-blackbox . ```

3- run docker image

```docker run -v <directory on host to store .torrent file>:/etc/monit/ -v <directory on host to get downloaded files>:/etc/download/ -d alldebrid-torrent-blackbox:latest ```

alternatively you can build the image without the config.ini by commenting the line in the Dockerfile and pass your alldebrid API key in the docker run command

```docker run -v <directory on host to store .torrent file>:/etc/monit/ -v <directory on host to get downloaded files>:/etc/download/ -d alldebrid-torrent-blackbox:latest --api "XXXXXX" ```
