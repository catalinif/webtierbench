import os
import time
import psutil
from _base import Application
from _base import consoleLogger
from _base import debugLogger
from _base import set_env
from _base import del_env
import socket
import sys

_MB = (1024*1024)
port_increment = 0

LOCALHOST_DOCKER_IP = '10.10.10.1'

MEMCACHED_CONTAINER_IP = '10.10.10.9'
CASSANDRA_CONTAINER_IP = '10.10.10.10'
DJANGO_CONTAINER_IP = '10.10.10.11' # Django IP = uWSGI IP
SIEGE_CONTAINER_IP = '10.10.10.12'
GRAPHITE_CONTAINER_IP = '10.10.10.13'

# Timeout in seconds to wait for a service to start
WAIT_FOR_SERVICE_TIMEOUT = 120

#TODO: add all apps here
def gen_perf_filename():
    return '%s.data' % time.strftime('%Y%m%d%H%M%S', time.localtime())

def wait_net_service(server, port, timeout=1):
    """ Wait for network service to appear
        @param timeout: in seconds
        @return: True of False
    """
    debugLogger("Wait for " + server + ":" + str(port) + " timeout=" + str(timeout))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(timeout)
        s.connect((server, port))
    except socket.timeout, err:
        consoleLogger("Got socket.timeout while waiting for " + server)
        return False
    except socket.error, err:
        consoleLogger("Got socket.error: " + str(err[0]) + " while waiting for " + server)
        return False
    except:
        consoleLogger("Got general exception: " + str(sys.exc_info()[0]) + " while waiting for " + server)
        return False
    else:
        s.close()
        return True

###############################################################################
# Applications
###############################################################################
class Apache2(Application):
    def __init__(self, deploy_config, deploy_platform):
        super(Apache2, self).__init__("apache2", deploy_config, deploy_platform)

    def deploy(self, async=False):
        set_env('WEBTIER_APACHE_IP', self.deploy_config["ip"])
        set_env('WEBTIER_APACHE_PORT', self.deploy_config["port"])
        return super(Apache2, self).deploy(async)

    def undeploy(self, async=False):
        return super(Apache2, self).undeploy(async)


class Django(Application):
    def __init__(self, deploy_config, deploy_platform):
        super(Django, self).__init__("django", deploy_config, deploy_platform)

    def deploy(self, async=False):
        set_env('WEBTIER_DJANGO_REVISION', '1109c7eecf23584fd3520bd7257f8b1268b78c3b')
        set_env('WEBTIER_DJANGO_WORKERS', self.deploy_config['workers'])
        return super(Django, self).deploy(async)

    def start(self, async=False):
        set_env('CASSANDRA_IP', LOCALHOST_DOCKER_IP)
        set_env('MEMCACHED_IP', LOCALHOST_DOCKER_IP)
        set_env('SIEGE_IP', LOCALHOST_DOCKER_IP)
        set_env('GRAPHITE_IP', GRAPHITE_CONTAINER_IP)

        set_env('LOCALHOST_IP', LOCALHOST_DOCKER_IP)

        if "memcached_docker" in os.environ:
            set_env('MEMCACHED_IP', MEMCACHED_CONTAINER_IP)
        if "cassandra_docker" in os.environ:
            set_env('CASSANDRA_IP', CASSANDRA_CONTAINER_IP)
        if "siege_docker" in os.environ:
            set_env('SIEGE_IP', SIEGE_CONTAINER_IP)

        #Wait for databases to start
        if 'db' in self.deploy_config:
            for i in xrange(len(self.deploy_config['db'])):
                obj = self.deploy_config['db'][i]
                wait_net_service(obj['ip'], obj['port'], WAIT_FOR_SERVICE_TIMEOUT)


        return super(Django, self).start(async)

    def undeploy(self, async=False):
        os.system('rm -rf django-workload')
        return super(Django, self).undeploy(async)

class Django_docker(Application):
    def __init__(self, deploy_config, deploy_platform):
        super(Django_docker, self).__init__("django_docker", deploy_config, deploy_platform)

    def deploy(self, async=False):
        return super(Django_docker, self).deploy(async)

    def start(self, async=False):
        set_env('CASSANDRA_IP', LOCALHOST_DOCKER_IP)
        set_env('MEMCACHED_IP', LOCALHOST_DOCKER_IP)
        set_env('SIEGE_IP', LOCALHOST_DOCKER_IP)
        set_env('GRAPHITE_IP', GRAPHITE_CONTAINER_IP)

        set_env('LOCALHOST_IP', LOCALHOST_DOCKER_IP)

        if "memcached_docker" in os.environ:
            set_env('MEMCACHED_IP', MEMCACHED_CONTAINER_IP)
        if "cassandra_docker" in os.environ:
            set_env('CASSANDRA_IP', CASSANDRA_CONTAINER_IP)
        if "siege_docker" in os.environ:
            set_env('SIEGE_IP', SIEGE_CONTAINER_IP)

        #Wait for databases to start
        if 'db' in self.deploy_config:
            for i in xrange(len(self.deploy_config['db'])):
                obj = self.deploy_config['db'][i]
                wait_net_service(obj['ip'], obj['port'], WAIT_FOR_SERVICE_TIMEOUT)

        return super(Django_docker, self).start(async)

    def undeploy(self, async=False):
        return super(Django_docker, self).undeploy(async)

class Wordpress(Application):
    def __init__(self, deploy_config, deploy_platform):
        super(Wordpress, self).__init__("wordpress", deploy_config, deploy_platform)

    def deploy(self, async=False):
        set_env('WEBTIER_OSS_PERFROMANCE_REV', '9b1a334c4fd0974cdb52dfb5a0862f77e5d2a9c0')
        return super(Wordpress, self).deploy(async)

    def start(self, async=False):
        set_env('WEBTIER_WORDPRESS_WORKERS', self.deploy_config['workers'])

        #Wait for databases to start
        if 'db' in self.deploy_config:
            for i in xrange(len(self.deploy_config['db'])):
                obj = self.deploy_config['db'][i]
                wait_net_service(obj['ip'], obj['port'], WAIT_FOR_SERVICE_TIMEOUT)

        return super(Wordpress, self).start(async)

    def stop(self, async=False):
        return super(Wordpress, self).stop(async)

    def undeploy(self, async=False):
        os.system('rm -rf oss-performance')
        return super(Wordpress, self).undeploy(async)



###############################################################################
# Caching
###############################################################################
class Memcached(Application):
    def __init__(self, deploy_config, deploy_platform):
        super(Memcached, self).__init__("memcached", deploy_config, deploy_platform)

    def start(self, async=False):
        return super(Memcached, self).start(async)

    def deploy(self, async=False):
        usage = psutil.virtual_memory()
        if os.path.exists("/etc/memcached.conf"):
            os.rename("/etc/memcached.conf","/etc/memcached.conf.old")
        with open("/etc/memcached.conf", "w") as outfile:
            if 'user' not in self.deploy_config:
                self.deploy_config['user'] = "memcache"
            outfile.writelines("MEMORY:" + str(self.deploy_config['minrequiredMemory']))
            outfile.write("LISTEN:" +  self.deploy_config['ip'])
            outfile.write("PORT:" + str(self.deploy_config['port']))
            outfile.write("USER:" + self.deploy_config['user'])
        if usage.free <= self.deploy_config['minrequiredMemory']:
            mem_size = usage.free/_MB
            consoleLogger(str(mem_size)+"Mb not enough free memmory space for memcached. Minimum required 5Gb")
            exit()
        return super(Memcached, self).deploy(async)

    def undeploy(self, async=False):
        return super(Memcached, self).undeploy(async)

class Memcached_docker(Application):
    def __init__(self, deploy_config, deploy_platform):
        super(Memcached_docker, self).__init__("memcached_docker", deploy_config, deploy_platform)

    def start(self, async=False):
        return super(Memcached_docker, self).start(async)

    def deploy(self, async=False):
        return super(Memcached_docker, self).deploy(async)

    def undeploy(self, async=False):
        return super(Memcached_docker, self).undeploy(async)

###############################################################################
# Databases
###############################################################################
class Cassandra(Application):
    def __init__(self, deploy_config, deploy_platform):
        super(Cassandra, self).__init__("cassandra", deploy_config, deploy_platform)

    def start(self, async=False):
        return super(Cassandra, self).start(async)

    def undeploy(self, async=False):
        return super(Cassandra, self).undeploy(async)

class Cassandra_docker(Application):
    def __init__(self, deploy_config, deploy_platform):
        super(Cassandra_docker, self).__init__("cassandra_docker", deploy_config, deploy_platform)

    def deploy(self, async=False):
        return super(Cassandra_docker, self).deploy(async)

    def start(self, async=False):
        return super(Cassandra_docker, self).start(async)

    def stop(self, async=False):
        return super(Cassandra_docker, self).stop(async)

    def undeploy(self, async=False):
        return super(Cassandra_docker, self).undeploy(async)

class MariaDb(Application):
    def __init__(self, deploy_config, deploy_platform):
        super(MariaDb, self).__init__("mariadb", deploy_config, deploy_platform)

    def start(self, async=False):
        return super(MariaDb, self).start(async)

    def undeploy(self, async=False):
        return super(MariaDb, self).undeploy(async)


###############################################################################
# Performance measurements
###############################################################################
class Perf(Application):
    def __init__(self, deploy_config, deploy_platform):
        super(Perf, self).__init__("perf", deploy_config, deploy_platform)

    def start(self, async=False):
        set_env('PERF_FILENAME', gen_perf_filename())
        return super(Perf, self).start(async)

    def undeploy(self, async=False):
        return super(Perf, self).undeploy(async)


class Sar(Application):
    def __init__(self, deploy_config, deploy_platform):
        super(Sar, self).__init__("sar", deploy_config, deploy_platform)

    def start(self, async=False):
        set_env('SAR_FILENAME', gen_perf_filename())
        return super(Sar, self).start(async)

    def undeploy(self, async=False):
        return super(Sar, self).undeploy(async)


class Statsd(Application):
    def __init__(self, deploy_config, deploy_platform):
        super(Statsd, self).__init__("statsd", deploy_config, deploy_platform)

    def start(self, async=False):
        set_env('SAR_FILENAME', gen_perf_filename())
        return super(Statsd, self).start(async)

    def undeploy(self, async=False):
        return super(Statsd, self).undeploy(async)


###############################################################################
# Benchmark clients
###############################################################################
class ApacheBenchmark(Application):
    def __init__(self, deploy_config, deploy_platform):
        self.benchmark_config = {}
        super(ApacheBenchmark, self).__init__("ab", deploy_config, deploy_platform)

    def set_benchmark_config(self, benchmark_config):
        self.benchmark_config = benchmark_config

    def start(self, async=False):
        set_env('WEBTIER_AB_WORKERS', self.benchmark_config['workers'])
        set_env('WEBTIER_AB_REQUESTS', 1000)
        set_env('WEBTIER_AB_ENDPOINT', "http://localhost:80/index.html")
        return super(ApacheBenchmark, self).start(async)

    def undeploy(self, async=False):
        return super(ApacheBenchmark, self).undeploy(async)


class Siege(Application):
    def __init__(self, deploy_config, deploy_platform):
        self.benchmark_config = {}
        super(Siege, self).__init__("siege", deploy_config, deploy_platform)

    def set_benchmark_config(self, benchmark_config):
        self.benchmark_config = benchmark_config
        if "username_db" in self.benchmark_config['settings']:
            set_env('WEBTIER_OSS_RUNNIG_MODE', self.benchmark_config['settings']['options'])
            set_env('WEBTIER_DB_USER', self.benchmark_config['settings']['username_db'])
            set_env('WEBTIER_DB_PWD', self.benchmark_config['settings']['password_db'])

    def deploy(self, async=False):
        set_env('WEBTIER_DJANGO_REVISION', '1109c7eecf23584fd3520bd7257f8b1268b78c3b')
        return super(Siege, self).deploy(async)

    def start(self, async=False):

        if 'customrun' in self.benchmark_config:
            set_env('WEBTIER_SIEGE_RUNMODE', self.benchmark_config['customrun'])
            consoleLogger("Be aware that the siege will run in a custom way decided by the user in the json file")
            set_env('WEBTIER_SIEGE_WORKERS', self.benchmark_config['workers'])

        if os.path.isfile('siege-2.78.tar.gz'):
            set_env("WEBTIER_SIEGE_WORDPRESS", self.deploy_config['name'])
        else:
            # Wait for workload to start for django
            if 'workload' in self.deploy_config:
                obj = self.deploy_config['workload']
                wait_net_service(obj['ip'], obj['port'], WAIT_FOR_SERVICE_TIMEOUT)

        set_env('DJANGO_IP', LOCALHOST_DOCKER_IP)

        if "django_docker" in os.environ:
            set_env('DJANGO_IP', DJANGO_CONTAINER_IP)
        else:
            set_env('DJANGO_IP', LOCALHOST_DOCKER_IP)

        return super(Siege, self).start(async)

    def undeploy(self, async=False ):
        if os.path.isfile('siege-2.78.tar.gz'):
            os.system('rm -rf siege-2.78.tar.gz')
            os.system('rm -rf siege-2.78')
        return super(Siege, self).undeploy(async)

class Siege_docker(Application):
    def __init__(self, deploy_config, deploy_platform):
        self.benchmark_config = {}
        super(Siege_docker, self).__init__("siege_docker", deploy_config, deploy_platform)

    def set_benchmark_config(self, benchmark_config):
        self.benchmark_config = benchmark_config

    def deploy(self, async=False):
        return super(Siege_docker, self).deploy(async)

    def start(self, async=False):
        set_env('DJANGO_IP', LOCALHOST_DOCKER_IP)

        if "django_docker" in os.environ:
            set_env('DJANGO_IP', DJANGO_CONTAINER_IP)

        return super(Siege_docker, self).start(async)

    def stop(self, async=False):
        return super(Siege_docker, self).stop(async)

    def undeploy(self, async=False ):
        return super(Siege_docker, self).undeploy(async)
