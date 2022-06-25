FROM python:3.7.7-alpine3.10
RUN mkdir /etc/script /etc/monit /etc/download
RUN pip3 install configparser argparse requests
COPY script.py config.in[i] /etc/script/
WORKDIR /etc/script
ENTRYPOINT ["python3", "script.py"]
