import asyncio
import asyncnetfsm


async def task(param):
    async with asyncnetfsm.create(**param) as ios:
        # Testing sending simple command
        out = await ios.send_command("show ver")
        print(out)


async def run():
    dev1 = {'username': 'user',
            'password': 'pass',
            'device_type': 'cisco_ios',
            'ip': '8.8.8.8',
            'protocol': 'telnet'
            }

    devices = [dev1]
    tasks = [task(dev) for dev in devices]
    await asyncio.wait(tasks)


loop = asyncio.get_event_loop()
loop.run_until_complete(run())



