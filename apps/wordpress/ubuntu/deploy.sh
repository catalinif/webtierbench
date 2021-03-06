#!/bin/bash
set -x

###############################################################################
# Environment data
###############################################################################
WEBTIER_HTTP_PROXY=${WEBTIER_HTTP_PROXY}
WEBTIER_PATH=${WEBTIER_PATH}

###############################################################################
# Commands
###############################################################################
. ${WEBTIER_PATH}/apps/common_func.sh

oss_dir="${WEBTIER_PATH}/oss-performance"

echo "deb http://dl.hhvm.com/ubuntu xenial-lts-3.18 main" > /etc/apt/sources.list.d/hhvm.list

http_proxy="${WEBTIER_HTTP_PROXY}" https_proxy="${WEBTIER_HTTP_PROXY}" apt-get update

# Install packages for oss performance
http_proxy="${WEBTIER_HTTP_PROXY}" https_proxy="${WEBTIER_HTTP_PROXY}"  apt-get install -y \
    nginx \
    unzip \
    coreutils \
    autotools-dev\
    autoconf \
	hhvm

echo 'Checking if oss-performance is already installed:'
if [ -d "$oss_dir" ]; then
	rm -rf "$oss_dir"
	echo ' - oss-performance was found and removed'
	echo '************************************************************'
else
	echo ' - oss-performance was not found'
	echo '************************************************************'
fi


su $SUDO_USER -c "HTTPS_PROXY=${WEBTIER_HTTP_PROXY}    \
git clone https://github.com/hhvm/oss-performance;		\
cd $oss_dir;							\
wget https://getcomposer.org/installer -O composer-setup.php;	\
hhvm composer-setup.php;					\
hhvm composer.phar install"

siege_output="${HOME}/siege.log"
sed "s|'--log='.\$logfile|'--log=${siege_output}'|" -i $oss_dir/base/Siege.php

start_service "mysql"
systemctl stop nginx.service
systemctl disable nginx.service