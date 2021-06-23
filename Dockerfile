FROM jupyterhub/jupyterhub

#######################################
# For ssh
RUN \
    python3 -m pip install asyncssh aiocache

RUN \
    apt-get update          &&  \
    apt-get upgrade --yes   &&  \
    apt-get install --yes       \
    openssh-client
#######################################

ADD docker-entrypoint.sh docker-entrypoint.sh
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python3", "-u", "-m", "jupyterhub_entrypoint"]
