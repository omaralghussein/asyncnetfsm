from asyncnetfsm.logger import logger
from asyncnetfsm.vendors.junos_like import JunOSLikeDevice


class JuniperJunOS(JunOSLikeDevice):
    """Class for working with Juniper JunOS"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    _cli_check = ">"
    """Checking string for shell mode"""

    _cli_command = "cli"
    """Command for entering to cli mode"""



        # self.current_terminal = None  # State Machine for the current Terminal mode of the session
        # self.config_mode = ConfigMode(
        #     enter_command=type(self)._config_enter,
        #     exit_command=type(self)._config_check,
        #     check_string=type(self)._config_exit,
        #     device=self
        # )
    async def _session_preparation(self):
        """ Prepare session before start using it """
        await super()._session_preparation()
        await self.cli_mode()

    async def check_cli_mode(self):
        """Check if we are in cli mode. Return boolean"""
        logger.info("Host {}: Checking shell mode".format(self._host))
        cli_check = type(self)._cli_check
        self._conn.send(self._normalize_cmd("\n"))
        output = await self._conn.read_until_prompt()
        return cli_check in output

    async def cli_mode(self):
        """Enter to cli mode"""
        logger.info("Host {}: Entering to cli mode".format(self._host))
        output = ""
        cli_command = type(self)._cli_command
        if not await self.check_cli_mode():
            self._conn.send(self._normalize_cmd(cli_command))
            output += await self._conn.read_until_prompt()
            if not await self.check_cli_mode():
                raise ValueError("Failed to enter to cli mode")
        return output
