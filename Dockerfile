FROM continuumio/miniconda3

ENV http_proxy "http://proxy-chain.intel.com:911"
ENV https_proxy "http://proxy-chain.intel.com:912"

EXPOSE 8019
EXPOSE 8000


WORKDIR /var/dl-modeling
ADD . /var/dl-modeling

ENV no_proxy "localhost,intel.com,192.168.0.0/16,172.16.0.0/12,127.0.0.0/8,10.0.0.0/8"

COPY environment.yml .
RUN conda env create --name myenv -f environment.yml

WORKDIR /var/dl-modeling/mysite

# Make RUN commands use the new environment:
SHELL ["conda", "run", "-n", "myenv", "/bin/bash", "-c"]

ENTRYPOINT ["conda", "run", "-n", "myenv", "/var/dl-modeling/mysite/docker-entrypoint.sh"]

