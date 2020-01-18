from asyncnetfsm.vendors.ios_like import IOSLikeDevice
from asyncnetfsm.logger import logger


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

    async def exit_config_mode(self):
        """Exit from configuration mode"""
        logger.info("Host {}: Exiting from configuration mode".format(self._host))
        output = ""
        exit_config = type(self)._config_exit
        if await self.check_config_mode():
            self._conn.send(self._normalize_cmd(exit_config))
            output = await self._conn.read_until_prompt()
            output = output.replace("(s1)", "")
            output = output.replace("(s2)", "")
            if await self.check_config_mode():
                raise ValueError("Failed to exit from configuration mode")
        return output

    async def check_config_mode(self):
        """Checks if the device is in configuration mode or not"""
        logger.info("Host {}: Checking configuration mode".format(self._host))
        check_string = type(self)._config_check
        self._conn.send(self._normalize_cmd("\n"))
        output = await self._conn.read_until_prompt()
        output = output.replace("(s1)", "")
        output = output.replace("(s2)", "")
        return check_string in output

    pass
