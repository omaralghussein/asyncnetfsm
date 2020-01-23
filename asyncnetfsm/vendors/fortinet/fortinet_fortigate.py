from asyncnetfsm.vendors.ios_like import IOSLikeDevice


class FortinetFortigate(IOSLikeDevice):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _session_preparation(self):
        await self._flush_buffer()
        await self._set_base_prompt()

    async def config_mode(self, config_command=""):
        """No config mode for Fortinet devices."""
        return ""

    async def exit_config_mode(self, exit_config=""):
        """No config mode for Fortinet devices."""
        return ""