"""
Base Class for using in connection to network devices

Connections Method are based upon AsyncSSH and should be running in asyncio loop
"""

import asyncio
import re
import time

import asyncssh

from asyncnetfsm.exceptions import AsyncnetfsmAuthenticationError, AsyncnetfsmTimeoutError,AsyncnetfsmConnectionError
from asyncnetfsm.logger import logger
from asyncnetfsm import utils
from asyncnetfsm.connections import TelnetConnection, SSHConnection


class BaseDevice(object):
    """
    Base Abstract Class for working with network devices
    """

    def __init__(
            self,
            ip=u"",
            host=u"",
            username=u"",
            password=u"",
            port=None,
            protocol='ssh',
            device_type=u"",
            timeout=15,
            loop=None,
            known_hosts=None,
            local_addr=None,
            client_keys=None,
            passphrase=None,
            tunnel=None,
            pattern=None,
            agent_forwarding=False,
            agent_path=(),
            client_version=u"AsyncNetFSM",
            family=0,
            kex_algs=(),
            encryption_algs=(),
            mac_algs=(),
            compression_algs=(),
            signature_algs=(),
    ):
        """
        Initialize base class for asynchronous working with network devices

        :param host: device hostname or ip address for connection
        :param username: username for logging to device
        :param password: user password for logging to device
        :param port: ssh port for connection. Default is 22
        :param device_type: network device type
        :param timeout: timeout in second for getting information from channel
        :param loop: asyncio loop object
        :param known_hosts: file with known hosts. Default is None (no policy). With () it will use default file
        :param local_addr: local address for binding source of tcp connection
        :param client_keys: path for client keys. Default in None. With () it will use default file in OS
        :param passphrase: password for encrypted client keys
        :param tunnel: An existing SSH connection that this new connection should be tunneled over
        :param pattern: pattern for searching the end of device prompt.
                Example: r"{hostname}.*?(\(.*?\))?[{delimeters}]"
        :param agent_forwarding: Allow or not allow agent forward for server
        :param agent_path:
            The path of a UNIX domain socket to use to contact an ssh-agent
            process which will perform the operations needed for client
            public key authentication. If this is not specified and the environment
            variable `SSH_AUTH_SOCK` is set, its value will be used as the path.
            If `client_keys` is specified or this argument is explicitly set to `None`,
            an ssh-agent will not be used.
        :param client_version: version which advertised to ssh server
        :param family:
           The address family to use when creating the socket. By default,
           the address family is automatically selected based on the host.
        :param kex_algs:
            A list of allowed key exchange algorithms in the SSH handshake,
            taken from `key exchange algorithms
            <https://asyncssh.readthedocs.io/en/latest/api.html#kexalgs>`_
        :param encryption_algs:
            A list of encryption algorithms to use during the SSH handshake,
            taken from `encryption algorithms
            <https://asyncssh.readthedocs.io/en/latest/api.html#encryptionalgs>`_
        :param mac_algs:
            A list of MAC algorithms to use during the SSH handshake, taken
            from `MAC algorithms <https://asyncssh.readthedocs.io/en/latest/api.html#macalgs>`_
        :param compression_algs:
            A list of compression algorithms to use during the SSH handshake,
            taken from `compression algorithms
            <https://asyncssh.readthedocs.io/en/latest/api.html#compressionalgs>`_, or
            `None` to disable compression
        :param signature_algs:
            A list of public key signature algorithms to use during the SSH
            handshake, taken from `signature algorithms
            <https://asyncssh.readthedocs.io/en/latest/api.html#signaturealgs>`_


        :type host: str
        :type username: str
        :type password: str
        :type port: int
        :type device_type: str
        :type timeout: int
        :type known_hosts:
            *see* `SpecifyingKnownHosts
            <https://asyncssh.readthedocs.io/en/latest/api.html#specifyingknownhosts>`_
        :type loop: :class:`AbstractEventLoop <asyncio.AbstractEventLoop>`
        :type pattern: str
        :type tunnel: :class:`BaseDevice <netdev.vendors.BaseDevice>`
        :type family:
            :class:`socket.AF_UNSPEC` or :class:`socket.AF_INET` or :class:`socket.AF_INET6`
        :type local_addr: tuple(str, int)
        :type client_keys:
            *see* `SpecifyingPrivateKeys
            <https://asyncssh.readthedocs.io/en/latest/api.html#specifyingprivatekeys>`_
        :type passphrase: str
        :type agent_path: str
        :type agent_forwarding: bool
        :type client_version: str
        :type kex_algs: list[str]
        :type encryption_algs: list[str]
        :type mac_algs: list[str]
        :type compression_algs: list[str]
        :type signature_algs: list[str]
        """
        if ip:
            self._host = ip
            self.host = ip
        else:
            raise ValueError("Host must be set")
        self._protocol = protocol
        self._device_type = device_type
        self._timeout = timeout
        if loop is None:
            self._loop = asyncio.get_event_loop()
        else:
            self._loop = loop

        """Convert needed connect params to a dictionary for simplicity"""
        if self._protocol == 'ssh':
            self._port = port or 22
            self._port = int(self._port)
            self._connect_params_dict = {
                "host": self.host,
                "port": self._port,
                "username": username,
                "password": password,
                "known_hosts": known_hosts,
                "local_addr": local_addr,
                "client_keys": client_keys,
                "passphrase": passphrase,
                "tunnel": tunnel,
                "agent_forwarding": agent_forwarding,
                "loop": loop,
                "family": family,
                "agent_path": agent_path,
                "client_version": client_version,
                "kex_algs": kex_algs,
                "encryption_algs": encryption_algs,
                "mac_algs": mac_algs,
                "compression_algs": compression_algs,
                "signature_algs": signature_algs,
            }
        elif self._protocol == 'telnet':
            self._port = port or 23
            self._port = int(self._port)
            self._connect_params_dict = {
                "host": self.host,
                "port": self._port,
                "username": username,
                "password": password,
            }
        else:
            raise ValueError("unknown protocol {} , only telnet and ssh supported".format(self._protocol))
        self.current_terminal = None

        if pattern is not None:
            self._pattern = pattern

        # Filling internal vars
        # self._stdin = self._stdout = self._stderr = self._conn = None
        # self._base_prompt = self._base_pattern = ""
        self._MAX_BUFFER = 65535
        self.device_prompt = ''
        self.prompt_pattern = ''
        self._ansi_escape_codes = False

    _delimiter_list = [">", "#"]
    """All this characters will stop reading from buffer. It mean the end of device prompt"""

    _pattern = r"{prompt}.*?(\(.*?\))?[{delimiters}]"
    """Pattern for using in reading buffer. When it found processing ends"""

    _disable_paging_command = "terminal length 0"
    """Command for disabling paging"""

    @property
    def base_prompt(self):
         """Returning base prompt for this network device"""
         return self.base_prompt

    async def __aenter__(self):
        """Async Context Manager"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async Context Manager"""
        await self.disconnect()

    async def connect(self):
        """
        Basic asynchronous connection method

        It connects to device and makes some preparation steps for working.
        Usual using 3 functions:

        * _establish_connection() for connecting to device
        * _set_base_prompt() for finding and setting device prompt
        * _disable_paging() for non interactive output in commands
        """
        logger.info("Host {}: Trying to connect to the device".format(self._host))
        logger.info("Trying to connect to the device")
        try:
            await self._establish_connection()
        except OSError as e:
            raise AsyncnetfsmConnectionError(self.host, None, str(e))
        await self._session_preparation()
        logger.info("Has connected to the device")

    async def _establish_connection(self):
        """Establishing SSH connection to the network device"""
        logger.info("Establishing connection")
        # initiate SSH connection
        if self._protocol == 'ssh':
            conn = SSHConnection(**self._connect_params_dict)
        elif self._protocol == 'telnet':
            conn = TelnetConnection(**self._connect_params_dict)
        else:
            raise ValueError("only SSH connection is supported")

        await conn.connect()
        self._conn = conn
        logger.info("Connection is established")
        return self._conn

    async def _session_preparation(self):
        """ Prepare session before start using it """
        await self._flush_buffer()
        await self._set_base_prompt()

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
        if not base_prompt:
            raise ValueError("unable to find base_prompt")
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

    async def _find_prompt(self):
        """Finds the current network device prompt, last line only"""
        logger.info("Host {}: Finding prompt".format(self._host))
        self._conn.send(self._normalize_cmd("\n"))
        prompt = ""
        delimiters = map(re.escape, type(self)._delimiter_list)
        delimiters = r"|".join(delimiters)
        prompt = await self._conn.read_until_pattern(delimiters)
        prompt = prompt.strip()
        if self._ansi_escape_codes:
            prompt = self._strip_ansi_escape_codes(prompt)
        if not prompt:
            raise ValueError(
                "Host {}: Unable to find prompt: {}".format(self._host, repr(prompt))
            )
        logger.debug("Host {}: Found Prompt: {}".format(self._host, repr(prompt)))
        return prompt

    async def send_command_expect(self, command,
                                  pattern='',
                                  re_flags=0, dont_read=False,
                                  read_for=0):
        """ Send a single line of command and readuntil prompte"""
        self._conn.send(self._normalize_cmd(command))
        if dont_read:
            return ''
        if pattern:
            output = await self._conn.read_until_prompt_or_pattern(pattern, re_flags)

        else:
            output = await self._conn.read_until_prompt(read_for=read_for)

        return output

    async def send_command_timing(self,
                                  command_string,
                                  read_for_seconds=2):
        """
        send command and keep reading for the specified time in wait or until_prompt
        :param command_string: command
        :type command_string: str
        :param read_for_seconds: seconds of reading
        :type read_for_seconds: int
        :return: command output
        """

        output = await self.send_command_expect(command_string, read_for=read_for_seconds)
        return output

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
        # self._conn.send(command_string)
        output = await self.send_command_expect(command_string, pattern, re_flags)

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

    async def _flush_buffer(self):
        """ flush unnecessary data """
        logger.debug("Flushing buffers")

        delimiters = map(re.escape, type(self)._delimiter_list)
        delimiters = r"|".join(delimiters)
        # await self.send_new_line(pattern=delimiters)
        await self._conn.read_until_pattern(delimiters)

    def _strip_prompt(self, a_string):
        """Strip the trailing router prompt from the output"""
        logger.info("Host {}: Stripping prompt".format(self._host))
        response_list = a_string.split("\n")
        last_line = response_list[-1]
        if self._conn._base_prompt in last_line:
            return "\n".join(response_list[:-1])
        else:
            return a_string


    @staticmethod
    def _strip_backspaces(output):
        """Strip any backspace characters out of the output"""
        backspace_char = "\x08"
        return output.replace(backspace_char, "")

    @staticmethod
    def _strip_command(command_string, output):
        """
        Strip command_string from output string

        Cisco IOS adds backspaces into output for long commands (i.e. for commands that line wrap)
        """
        logger.info("Stripping command")
        backspace_char = "\x08"

        # Check for line wrap (remove backspaces)
        if backspace_char in output:
            output = output.replace(backspace_char, "")
            output_lines = output.split("\n")
            new_output = output_lines[1:]
            return "\n".join(new_output)
        else:
            command_length = len(command_string)
            return output[command_length:]

    @staticmethod
    def _normalize_linefeeds(a_string):
        """Convert '\r\r\n','\r\n', '\n\r' to '\n"""
        newline = re.compile(r"(\r\r\n|\r\n|\n\r)")
        return newline.sub("\n", a_string)

    @staticmethod
    def _normalize_cmd(command):
        """Normalize CLI commands to have a single trailing newline"""
        command = command.rstrip("\n")
        command += "\n"
        return command

    async def send_config_set(self, config_commands=None):
        """
        Sending configuration commands to device

        The commands will be executed one after the other.

        :param list config_commands: iterable string list with commands for applying to network device
        :return: The output of this commands
        """
        logger.info("Host {}: Sending configuration settings".format(self._host))
        if config_commands is None:
            return ""
        if not hasattr(config_commands, "__iter__"):
            raise ValueError(
                "Host {}: Invalid argument passed into send_config_set".format(
                    self._host
                )
            )

        # Send config commands
        logger.debug("Host {}: Config commands: {}".format(self._host, config_commands))
        output = ""
        config_commands = ['\n'] + config_commands
        for cmd in config_commands:
            # self._conn.send(self._normalize_cmd(cmd))
            output += await self.send_command_expect(cmd)

        if self._ansi_escape_codes:
            output = self._strip_ansi_escape_codes(output)

        output = self._normalize_linefeeds(output)
        print(
            "Host {}: Config commands output: {}".format(self._host, repr(output))
        )
        return output

    @staticmethod
    def _strip_ansi_escape_codes(string_buffer):
        """
        Remove some ANSI ESC codes from the output

        http://en.wikipedia.org/wiki/ANSI_escape_code

        Note: this does not capture ALL possible ANSI Escape Codes only the ones
        I have encountered

        Current codes that are filtered:
        ESC = '\x1b' or chr(27)
        ESC = is the escape character [^ in hex ('\x1b')
        ESC[24;27H   Position cursor
        ESC[?25h     Show the cursor
        ESC[E        Next line (HP does ESC-E)
        ESC[2K       Erase line
        ESC[1;24r    Enable scrolling from start to row end
        ESC7         Save cursor position
        ESC[r        Scroll all screen
        ESC8         Restore cursor position
        ESC[nA       Move cursor up to n cells
        ESC[nB       Move cursor down to n cells

        require:
            HP ProCurve
            F5 LTM's
            Mikrotik
        """
        logger.info("Stripping ansi escape codes")
        logger.debug("Unstripped output: {}".format(repr(string_buffer)))

        code_save_cursor = chr(27) + r"7"
        code_scroll_screen = chr(27) + r"\[r"
        code_restore_cursor = chr(27) + r"8"
        code_cursor_up = chr(27) + r"\[\d+A"
        code_cursor_down = chr(27) + r"\[\d+B"

        code_position_cursor = chr(27) + r"\[\d+;\d+H"
        code_show_cursor = chr(27) + r"\[\?25h"
        code_next_line = chr(27) + r"E"
        code_erase_line = chr(27) + r"\[2K"
        code_enable_scroll = chr(27) + r"\[\d+;\d+r"

        code_set = [
            code_save_cursor,
            code_scroll_screen,
            code_restore_cursor,
            code_cursor_up,
            code_cursor_down,
            code_position_cursor,
            code_show_cursor,
            code_erase_line,
            code_enable_scroll,
        ]

        output = string_buffer
        for ansi_esc_code in code_set:
            output = re.sub(ansi_esc_code, "", output)

        # CODE_NEXT_LINE must substitute with '\n'
        output = re.sub(code_next_line, "\n", output)

        logger.debug("Stripped output: {}".format(repr(output)))

        return output

    async def _cleanup(self):
        """ Any needed cleanup before closing connection """
        logger.info("Host {}: Cleanup session".format(self._host))
        pass

    async def _disable_paging(self):
        """Disable paging method"""
        logger.info("Host {}: Trying to disable paging".format(self._host))
        command = type(self)._disable_paging_command
        command = self._normalize_cmd(command)
        logger.debug(
            "Host {}: Disable paging command: {}".format(self._host, repr(command))
        )
        self._conn.send(command)
        output = await self._conn.read_until_prompt()
        logger.debug(
            "Host {}: Disable paging output: {}".format(self._host, repr(output))
        )
        if self._ansi_escape_codes:
            output = self._strip_ansi_escape_codes(output)
        return output


    async def disconnect(self):
        """ Gracefully close the SSH connection """
        logger.info("Host {}: Disconnecting".format(self._host))
        await self._cleanup()
        await self._conn.close()
        # await self._conn.wait_closed()
