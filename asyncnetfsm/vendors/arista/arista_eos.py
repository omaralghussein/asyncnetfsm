from asyncnetfsm.vendors.ios_like import IOSLikeDevice


class AristaEOS(IOSLikeDevice):
    """Class for working with Arista EOS"""
    def __init__(self, secret=u"", *args, **kwargs):
        """
        Initialize class for asynchronous working with network devices

        :param str host: device hostname or ip address for connection
        :param str username: username for logging to device
        :param str password: user password for logging to device
        :param str secret: secret password for privilege mode
        :param int port: ssh port for connection. Default is 22
        :param str device_type: network device type
        :param known_hosts: file with known hosts. Default is None (no policy). With () it will use default file
        :param str local_addr: local address for binding source of tcp connection
        :param client_keys: path for client keys. Default in None. With () it will use default file in OS
        :param str passphrase: password for encrypted client keys
        :param float timeout: timeout in second for getting information from channel
        :param loop: asyncio loop object
        """
        super().__init__(*args, **kwargs)
        self._secret = secret

    _priv_enter = "enable"
    """Command for entering to privilege exec"""

    _priv_exit = "disable"
    """Command for existing from privilege exec to user exec"""

    _priv_check = "#"
    """Checking string in prompt. If it's exist im prompt - we are in privilege exec"""

    _config_enter = "conf t"
    """Command for entering to configuration mode"""

    _config_exit = "end"
    """Command for existing from configuration mode to privilege exec"""

    _config_check = ")#"
    """Checking string in prompt. If it's exist im prompt - we are in configuration mode"""
    pass
