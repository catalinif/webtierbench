FROM ubuntu:16.04

ENV DEBIAN_FRONTEND noninteractive

RUN useradd -m tester                                                    \
    && apt-get update                                                    \
    && apt-get -y install git siege python3 python3-numpy netcat-openbsd \
    && git clone https://github.com/Instagram/django-workload            \
        /home/tester/django-workload                                     \
    && cd /home/tester/django-workload/                                  \
    && git checkout 2600e3e784cb912fe7b9dbe4ebc8b26d43e1bacb             \
    && echo "failures = 1000000" > /home/tester/.siegerc                 \
    && echo "protocol = HTTP/1.1" >> /home/tester/.siegerc               \
    && mkdir -p /home/tester/scripts

COPY wait-for-uwsgi.sh siege_init.sh /home/tester/scripts/

RUN chown -R tester:tester /home/tester \
    && echo "Add nf_conntrack to modules ...\n"\
    && echo "nf_conntrack" >> /etc/modules \
    && echo "Add limits settings ...\n"\
    && echo "* soft nofile 1000000\n\
* hard nofile 1000000" >> /etc/security/limits.conf

ENV DEBIAN_FRONTEND teletype

CMD /home/tester/scripts/wait-for-uwsgi.sh && /home/tester/scripts/siege_init.sh
