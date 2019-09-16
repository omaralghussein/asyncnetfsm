"""
JunOSLikeDevice Class is abstract class for using in Juniper JunOS like devices

Connection Method are based upon AsyncSSH and should be running in asyncio loop
"""

import re

from asyncnetfsm.logger import logger
from asyncnetfsm.vendors.base import BaseDevice
from asyncnetfsm import utils


class JunOSLikeDevice(BaseDevice):
    """
    JunOSLikeDevice Class for working with Juniper JunOS like devices

    Juniper JunOS like devices having several concepts:

    * shell mode (csh). This is csh shell for FreeBSD. This mode is not covered by this Class.
    * cli mode (specific shell). The entire configuration is usual configured in this shell:

      * operation mode. This mode is using for getting information from device
      * configuration mode. This mode is using for configuration system
    """

    _delimiter_list = ["%", ">", "#"]
    """All this characters will stop reading from buffer. It mean the end of device prompt"""

    _pattern = r"\w+(\@[\-\w]*)?[{delimiters}]"
    """Pattern for using in reading buffer. When it found processing ends"""

    _disable_paging_command = "set cli screen-length 0"
    """Command for disabling paging"""

    _config_enter = "configure"
    """Command for entering to configuration mode"""

    _config_exit = "exit configuration-mode"
    """Command for existing from configuration mode to privilege exec"""

    _config_check = "#"
    """Checking string in prompt. If it's exist im prompt - we are in configuration mode"""

    _commit_command = "commit"
    """Command for committing changes"""

    _commit_comment_command = "commit comment {}"
    """Command for committing changes with comment"""

    async def _flush_buffer(self):
        """ flush unnecessary data """
        logger.debug("Flushing buffers")
        await self._read_until_pattern(self._base_pattern)

    async def send_command(
        self,
        command_string,
        pattern="",
        re_flags=0,
        strip_command=True,
        strip_prompt=True,
        use_textfsm=False
    ):
        """
        Sending command to device (support interactive commands with pattern)

        :param str command_string: command for executing basically in privilege mode
        :param str pattern: pattern for waiting in output (for interactive commands)
        :param re.flags re_flags: re flags for pattern
        :param bool strip_command: True or False for stripping command from output
        :param bool strip_prompt: True or False for stripping ending device prompt
        :return: The output of the command
        """
        logger.info("Host {}: Sending command".format(self._host))
        output = ""
        command_string = self._normalize_cmd(command_string)
        logger.info(
            "Host {}: Send command: {}".format(self._host, repr(command_string))
        )
        self._stdin.write(command_string)
        output = await self._read_until_pattern(pattern, re_flags)

        # Some platforms have ansi_escape codes
        if self._ansi_escape_codes:
            output = self._strip_ansi_escape_codes(output)
        output = self._normalize_linefeeds(output)
        if strip_prompt:
            output = self._strip_prompt(output)
        if strip_command:
            output = self._strip_command(command_string, output)

        if use_textfsm:
            logger.info("parsing output using texfsm, command=%r," % command_string)
            output = utils.get_structured_data(output, self._device_type, command_string)
        logger.info(
            "Host {}: Send command output: {}".format(self._host, repr(output))
        )
        return output

    async def _set_base_prompt(self):
        """
        Setting two important vars
            base_prompt - textual prompt in CLI (usually username or hostname)
            base_pattern - regexp for finding the end of command. IT's platform specific parameter

        For JunOS devices base_pattern is "user(@[hostname])?[>|#]
        """
        logger.info("Host {}: Setting base prompt".format(self._host))
        prompt = await self._find_prompt()
        prompt = prompt[:-1]
        # Strip off trailing terminator
        if "@" in prompt:
            prompt = prompt.split("@")[1]
        self._base_prompt = prompt
        delimiters = map(re.escape, type(self)._delimiter_list)
        delimiters = r"|".join(delimiters)
        base_prompt = re.escape(self._base_prompt[:12])
        pattern = type(self)._pattern
        self._base_pattern = pattern.format(delimiters=delimiters)
        logger.info("Host {}: Base Prompt: {}".format(self._host, self._base_prompt))
        logger.info("Host {}: Base Pattern: {}".format(self._host, self._base_pattern))
        return self._base_prompt

    async def check_config_mode(self):
        """Check if are in configuration mode. Return boolean"""
        logger.info("Host {}: Checking configuration mode".format(self._host))
        check_string = type(self)._config_check
        self._stdin.write(self._normalize_cmd("\n"))
        output = await self._read_until_prompt()
        return check_string in output

    async def config_mode(self):
        """Enter to configuration mode"""
        logger.info("Host {}: Entering to configuration mode".format(self._host))
        output = ""
        config_enter = type(self)._config_enter
        if not await self.check_config_mode():
            self._stdin.write(self._normalize_cmd(config_enter))
            output += await self._read_until_prompt()
            if not await self.check_config_mode():
                raise ValueError("Failed to enter to configuration mode")
        return output

    async def exit_config_mode(self):
        """Exit from configuration mode"""
        logger.info("Host {}: Exiting from configuration mode".format(self._host))
        output = ""
        config_exit = type(self)._config_exit
        if await self.check_config_mode():
            self._stdin.write(self._normalize_cmd(config_exit))
            output += await self._read_until_prompt()
            if await self.check_config_mode():
                raise ValueError("Failed to exit from configuration mode")
        return output

    async def send_config_set(
        self,
        config_commands=None,
        with_commit=True,
        commit_comment="",
        exit_config_mode=True,
    ):
        """
        Sending configuration commands to device
        By default automatically exits/enters configuration mode.

        :param list config_commands: iterable string list with commands for applying to network devices in system view
        :param bool with_commit: if true it commit all changes after applying all config_commands
        :param string commit_comment: message for configuration commit
        :param bool exit_config_mode: If true it will quit from configuration mode automatically
        :return: The output of these commands
        """

        if config_commands is None:
            return ""

        # Send config commands
        await self.config_mode()
        output = ''
        output += await super().send_config_set(config_commands=config_commands)
        if with_commit:
            commit = type(self)._commit_command
            if commit_comment:
                commit = type(self)._commit_comment_command.format(commit_comment)

            self._stdin.write(self._normalize_cmd(commit))
            output += await self._read_until_prompt()

        if exit_config_mode:
            output += await self.exit_config_mode()

        output = self._normalize_linefeeds(output)
        logger.debug(
            "Host {}: Config commands output: {}".format(self._host, repr(output))
        )
        return output
