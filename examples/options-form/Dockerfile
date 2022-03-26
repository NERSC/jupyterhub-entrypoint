FROM jupyterhub/jupyterhub:2

RUN \
    python3 -m pip install --no-cache   \
        aiosqlite                       \
        jupyterlab

RUN \
    adduser -q --gecos "" --disabled-password admin     && \
    echo admin:admin | chpasswd

RUN \
    adduser -q --gecos "" --disabled-password user1     && \
    echo user1:user1 | chpasswd

ADD . src/jupyterhub-entrypoint
RUN \
    cd src/jupyterhub-entrypoint                                    &&  \
    pip install --no-cache .                                        &&  \
    cd examples/options-form                                        &&  \
    cp example-entrypoint.sh /usr/local/bin/example-entrypoint.sh   &&  \
    chmod a+x /usr/local/bin/example-entrypoint.sh                  &&  \
    cp                                                                  \
        docker-entrypoint.sh                                            \
        entrypoint_config.py                                            \
        image-server.py                                                 \
        jupyterhub-entrypoint-cookie-secret                             \
        jupyterhub_config.py                                            \
        ../../../..                                                 &&  \
    cd ../../../..                                                  &&  \
    chmod u+x docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["jupyterhub"]
