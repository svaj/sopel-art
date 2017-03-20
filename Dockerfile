FROM python:3.6-alpine

RUN apk add --update --no-cache \
    ca-certificates \
    py-mysqldb \
    enchant \
    && pip install \
    flask \
    ipython \
    && rm -rf /tmp/* /var/cache/apk/*


RUN pip install git+https://github.com/sopel-irc/sopel.git


VOLUME ["/sopel"]



ENTRYPOINT ["/init"]