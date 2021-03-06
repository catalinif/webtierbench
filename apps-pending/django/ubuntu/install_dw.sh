#!/bin/bash

# Django workload setup
. utils.sh

check_root_privilege

# Check for proxy
if [ "$#" -gt "0" ]; then
    case "$1" in
        -p | --proxy)
            [ -z "$2" ] && usage "-p | --proxy <proxy_ip:proxy_port>"

            echo -e "\n\nSet proxy ..."

            proxy_endpoint="$2"
            http_proxy=http://"$proxy_endpoint"
            https_proxy=http://"$proxy_endpoint"
            export http_proxy
            export https_proxy

            apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --keyserver-options http-proxy="http://$proxy_endpoint" --recv 0xC2518248EEA14886

            # Set docker proxy
            mkdir -p /etc/systemd/system/docker.service.d
            echo "[Service]" >> /etc/systemd/system/docker.service.d/http-proxy.conf
            echo "Environment='HTTP_PROXY=http://$proxy_endpoint'" >> /etc/systemd/system/docker.service.d/http-proxy.conf
            ;;

        *)
            usage "-p | --proxy <proxy_ip:proxy_port>"
    esac
fi

if ! which curl > /dev/null; then
    echo "curl not found! Installing it ..."

    apt-get update
    apt-get install -y curl
fi

# Add apt repositories
echo -e "\n\nAdd apt repositories ..."

curl https://www.apache.org/dist/cassandra/KEYS | apt-key add -
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0xC2518248EEA14886

echo "deb http://ppa.launchpad.net/webupd8team/java/ubuntu xenial main" \
> /etc/apt/sources.list.d/webupd8team-ubuntu-java-xenial.list

echo "deb http://www.apache.org/dist/cassandra/debian 30x main" \
> /etc/apt/sources.list.d/cassandra.list

apt-key fingerprint 0EBFCD88

echo "deb [arch=amd64] https://download.docker.com/linux/ubuntu xenial stable" \
> /etc/apt/sources.list.d/docker.list

apt-get update

# Accept java license prompt
echo "oracle-java8-installer shared/accepted-oracle-license-v1-1 select true" | debconf-set-selections
echo "oracle-java8-installer shared/accepted-oracle-license-v1-1 seen true" | debconf-set-selections

echo -e "\n\nInstall packages ..."
apt-get install -y software-properties-common oracle-java8-installer    \
    cassandra memcached apt-transport-https ca-certificates docker-ce   \
    build-essential git libmemcached-dev python3-virtualenv python3-dev \
    zlib1g-dev siege python3-numpy

echo -e "\n\nConfiguring cassandra ..."
cp -f jvm.options.128_GB /etc/cassandra/jvm.options

sed -e "s/concurrent_reads: 32/concurrent_reads: 64/g"                                         \
    -e "s/concurrent_writes: 32/concurrent_writes: 128/g"                                      \
    -e "s/concurrent_counter_writes: 32/concurrent_counter_writes: 128/g"                      \
    -e "s/concurrent_materialized_view_writes: 32/# concurrent_materialized_view_writes: 32/g" \
    -i /etc/cassandra/cassandra.yaml

echo -e "\n\nDocker pull graphite image ..."
docker pull hopsoft/graphite-statsd

#Initialize docker container
echo -e "\n\nInitialize container ..."
docker run -d               \
    --name graphite         \
    -p 80:80                \
    -p 2003-2004:2003-2004  \
    -p 2023-2024:2023-2024  \
    -p 8125:8125/udp        \
    -p 8126:8126            \
    hopsoft/graphite-statsd

# Disable services
echo -e "\n\nDisable services ..."
systemctl disable memcached.service
systemctl disable cassandra.service
systemctl disable docker.service

# Sets up a memcached server with 5 GB memory
# Check if system it's having 5 GB memory
echo -e "\n\nCheck system memory ..."
mem_total_MB=$(free -m | grep Mem | awk '{print $2}')
mem_av_MB=$(free -m | grep Mem | awk '{print $NF}')

if [ "$mem_total_MB" -ge "5120" ]; then
    if [ "$mem_av_MB" -ge "2048" ]; then
        echo "Found enough memory on the system! [OK]"
    else
        echo "Not enough available memory on the system! [FAIL]"
        exit 2
    fi
else
    echo "Not enough memory in the system! [FAIL]"
    exit 3
fi

echo -e "\n\n"

su "$SUDO_USER" -c "git clone https://github.com/Instagram/django-workload"
(
su "$SUDO_USER" -c "cd django-workload && git checkout 2600e3e784cb912fe7b9dbe4ebc8b26d43e1bacb"
)

#Config django-workload for statsd & graphite statistics
default_if=$(ip route sh | grep default | awk '{print $5}')
echo "Default iface is $default_if"
own_ip=$(ifconfig "$default_if" | grep "inet addr" | awk '{print substr($2,6)}')
echo "Own IP is $own_ip"

sed -e "s/STATSD_HOST = 'localhost'/STATSD_HOST = '$own_ip'/"       \
    -i django-workload/django-workload/cluster_settings_template.py

# Config memcached
# Backup old memcached config file
if [ -f /etc/memcached.conf ]; then
    mv /etc/memcached.conf /etc/memcached.conf.old
    echo -e "\n\nBackup /etc/memcached.conf to /etc/memcached.conf.old"
fi

. memcached.cfg

echo -e "\n\nWrite memcached config file ..."
cat > /etc/memcached.conf <<- EOF
	# Daemon mode
	-d
	logfile /var/log/memcached.log
	-m "$MEMORY"
	-p "$PORT"
	-u "$USER"
	-l "$LISTEN"
	-t "$THREADS"
EOF

echo -e "\n\nCreate python virtualenv ..."
su "$SUDO_USER" -c "(
    cd django-workload/django-workload || exit 4

    python3 -m virtualenv -p python3 venv
    . venv/bin/activate

    python -m pip install -r requirements.txt

    cp cluster_settings_template.py cluster_settings.py

    DJANGO_SETTINGS_MODULE=cluster_settings django-admin setup

    deactivate
)"

echo -e "\n\nGenerate siege urls file ..."
(
    su "$SUDO_USER" -c                    \
    "cd django-workload/client || exit 5; \
    ./gen-urls-file"
)

# Set cores count to uwsgi.ini
(
    su "$SUDO_USER" -c                             \
    "cd django-workload/django-workload || exit 6; \
    sed -i 's/processes = 88/processes = $(grep -c processor /proc/cpuinfo)/g' uwsgi.ini"
)

# Append client settings to /etc/sysctl.conf
echo -e "\nWrite sysctl settings ..."
cat >> /etc/sysctl.conf <<- EOF
	net.ipv4.tcp_tw_reuse=1
	net.ipv4.ip_local_port_range=1024 64000
	net.ipv4.tcp_fin_timeout=45
	net.core.netdev_max_backlog=10000
	net.ipv4.tcp_max_syn_backlog=12048
	net.core.somaxconn=1024
	net.netfilter.nf_conntrack_max=256000
EOF

echo -e "\n\nAdd nf_conntrack to modules ..."
echo "nf_conntrack" >> /etc/modules

echo -e "\n\nAdd limits settings ..."
cat >> /etc/security/limits.conf <<- EOF
	* soft nofile 1000000
	* hard nofile 1000000
EOF

# Create siegerc
echo -e "\n\nCreate siegerc ..."
su - "$SUDO_USER" -c "echo 'failures = 1000000' > .siegerc; \
                      echo 'protocol = HTTP/1.1' >> .siegerc"

unset http_proxy
unset https_proxy

echo -e "\n\n"
# Modifying limits.conf requires system reboot
read -rsn1 -p "Press any key to reboot"
reboot
