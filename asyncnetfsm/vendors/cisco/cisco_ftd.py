"""Subclass specific to Cisco ASA"""
import re
from asyncnetfsm.vendors.ios_like import IOSLikeDevice
from asyncnetfsm.logger import logger
from asyncnetfsm import utils


class CiscoFTD(IOSLikeDevice):
    """Class for working with Cisco Firepower Threat Defense  """

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self._multiple_mode = False

    _disable_paging_command = "terminal pager 0"

    async def _session_preparation(self):
        await self._flush_buffer()
        await self._set_base_prompt()

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
        self._conn.send(command_string)
        output = await self._conn.read_until_pattern('>', re_flags=0, read_for=0)

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
        Setting two important vars:

            base_prompt - textual prompt in CLI (usually hostname)
            base_pattern - regexp for finding the end of command. It's platform specific parameter

        For Cisco devices base_pattern is "prompt(\(.*?\))?[#|>]
        """
        logger.info("Setting base prompt")
        prompt = await self._find_prompt()

        # Strip off trailing terminator
        base_prompt = prompt[:-1]
        self.device_prompt = base_prompt
        self._conn.set_base_prompt(base_prompt)

        delimiters = map(re.escape, type(self)._delimiter_list)
        delimiters = r"|".join(delimiters)
        base_prompt = re.escape(base_prompt[:12])
        pattern = type(self)._pattern
        base_pattern = pattern.format(prompt=base_prompt, delimiters=delimiters)
        logger.debug("Base Prompt: %s" % base_prompt)
        logger.debug("Base Pattern: %s" % base_pattern)
        if not base_pattern:
            raise ValueError("unable to find base_pattern")
        self.prompt_pattern = base_pattern
        self._conn.set_base_pattern(base_pattern)

    @property
    def multiple_mode(self):
        """ Returning Bool True if ASA in multiple mode"""
        return self._multiple_mode



    async def _disable_width(self):
        logger.info("setting terminal width to 511")
        await self.send_config_set([type(self)._disable_width_command])

    async def _check_multiple_mode(self):
        """Check mode multiple. If mode is multiple we adding info about contexts"""
        logger.info("Checking multiple mode")
        out = await self.send_command_expect("show mode")
        if "multiple" in out:
            self._multiple_mode = True

        logger.debug("Multiple mode: %s" % self._multiple_mode)
