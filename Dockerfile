FROM python:3.6-alpine

RUN apk add --update --no-cache \
    ca-certificates \
    py-mysqldb \
    enchant \
    git \
    && pip install \
    flask \
    ipython \
    && rm -rf /tmp/* /var/cache/apk/*


RUN pip install git+https://github.com/sopel-irc/sopel.git

RUN adduser -D -u 1000 sopel


VOLUME ["/home/sopel/.sopel"]

USER sopel
CMD ["sopel"]