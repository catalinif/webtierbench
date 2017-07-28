#!/bin/bash

###############################################################################
# Environment data
###############################################################################


###############################################################################
# Commands
###############################################################################

docker run -tid -h uwsgi --name uwsgi_container --network django_network --ip 10.10.10.11 -e CASSANDRA_ENDPOINT=10.10.10.10 -e MEMCACHED_ENDPOINT=10.10.10.9 rinftech/webtierbench:uwsgi-webtier