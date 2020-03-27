# Copyright (C) 2020 Adek Maulana.
# All rights reserved.
"""
   Heroku manager for your userbot
"""

import heroku3
import asyncio
import os
import requests
import math

from asyncio import create_subprocess_shell as asyncSubprocess
from asyncio.subprocess import PIPE as asyncPIPE

from userbot import CMD_HELP, LOGS, HEROKU_APP_NAME, HEROKU_API_KEY
from userbot.events import register
from userbot.prettyjson import prettyjson

Heroku = heroku3.from_key(HEROKU_API_KEY)
heroku_api = "https://api.heroku.com"


async def subprocess_run(cmd, heroku):
    subproc = await asyncSubprocess(cmd, stdout=asyncPIPE, stderr=asyncPIPE)
    stdout, stderr = await subproc.communicate()
    exitCode = subproc.returncode
    if exitCode != 0:
        await heroku.edit(
            '**An error was detected while running subprocess**\n'
            f'```exitCode: {exitCode}\n'
            f'stdout: {stdout.decode().strip()}\n'
            f'stderr: {stderr.decode().strip()}```')
        return exitCode
    return stdout.decode().strip(), stderr.decode().strip(), exitCode


@register(outgoing=True, pattern=r"^.(set|get|del) var(?: |$)(.*)(?: |$)")
async def variable(var):
    """
        Manage most of ConfigVars setting, set new var, get current var,
        or delete var...
    """
    if HEROKU_APP_NAME is not None:
        app = Heroku.app(HEROKU_APP_NAME)
    else:
        await var.edit("`[HEROKU]:\nPlease setup your` **HEROKU_APP_NAME**")
        return
    exe = var.pattern_match.group(1)
    heroku_var = app.config()
    if exe == "get":
        await var.edit("`Getting information...`")
        await asyncio.sleep(3)
        try:
            val = var.pattern_match.group(2).split()[0]
            if val in heroku_var:
                await var.edit("**Config vars**:"
                               f"\n\n`{val} = {heroku_var[val]}`\n")
            else:
                await var.edit("**Config vars**:"
                               f"\n\n`Error -> {val} not exists`\n")
            return
        except IndexError:
            configs = prettyjson(heroku_var.to_dict(), indent=2)
            with open("configs.json", "w") as fp:
                fp.write(configs)
            with open("configs.json", "r") as fp:
                result = fp.read()
                if len(result) >= 4096:
                    await var.client.send_file(
                        var.chat_id,
                        "configs.json",
                        reply_to=var.id,
                        caption="`Output too large, sending it as a file`",
                    )
                else:
                    await var.edit("`[HEROKU]` variables:\n\n"
                                   "================================"
                                   f"\n```{result}```\n"
                                   "================================"
                                   )
            os.remove("configs.json")
            return
    elif exe == "set":
        await var.edit("`Setting information...`")
        val = var.pattern_match.group(2).split()
        try:
            val[1]
        except IndexError:
            await var.edit("`.set var <config name> <value>`")
            return
        await asyncio.sleep(3)
        if val[0] in heroku_var:
            await var.edit(f"**{val[0]}**  `successfully changed to`  **{val[1]}**")
        else:
            await var.edit(f"**{val[0]}**  `successfully added with value: **{val[1]}**")
        heroku_var[val[0]] = val[1]
        return
    elif exe == "del":
        await var.edit("`Getting information to deleting vars...`")
        try:
            val = var.pattern_match.group(2).split()[0]
        except IndexError:
            await var.edit("`Please specify config vars you want to delete`")
            return
        await asyncio.sleep(3)
        if val in heroku_var:
            await var.edit(f"**{val}**  `successfully deleted`")
            del heroku_var[val]
        else:
            await var.edit(f"**{val}**  `is not exists`")
        return


@register(outgoing=True, pattern=r"^.usage(?: |$)")
async def dyno_usage(dyno):
    """
        Get your account Dyno Usage
    """
    await dyno.edit("`Processing...`")
    useragent = ('Mozilla/5.0 (Linux; Android 10; SM-G975F) '
                 'AppleWebKit/537.36 (KHTML, like Gecko) '
                 'Chrome/80.0.3987.149 Mobile Safari/537.36'
                 )
    user_id = Heroku.account().id
    headers = {
     'User-Agent': useragent,
     'Authorization': f'Bearer {HEROKU_API_KEY}',
     'Accept': 'application/vnd.heroku+json; version=3.account-quotas',
    }
    path = "/accounts/" + user_id + "/actions/get-quota"
    r = requests.get(heroku_api + path, headers=headers)
    if r.status_code != 200:
        await dyno.edit(f"`Error: something bad happened`\n\n > `{r.reason}`\n")
        return
    result = r.json()
    quota = result['account_quota']
    quota_used = result['quota_used']

    """ - Used - """
    remaining_quota = quota - quota_used
    percentage = math.floor(remaining_quota / quota * 100)
    minutes_remaining = remaining_quota / 60
    hours = math.floor(minutes_remaining / 60)
    minutes = math.floor(minutes_remaining % 60)

    """ - Current - """
    App = result['apps']
    AppQuotaUsed = App[0]['quota_used'] / 60
    AppPercentage = math.floor(App[0]['quota_used'] * 100 / quota)
    AppHours = math.floor(AppQuotaUsed / 60)
    AppMinutes = math.floor(AppQuotaUsed % 60)

    await asyncio.sleep(3)

    await dyno.edit("**Dyno Usage**:\n\n"
                    f" -> `Dyno usage for`  **{HEROKU_APP_NAME}**:\n"
                    f"     •  `{AppHours}`**h**  `{AppMinutes}`**m**  **|**  [`{AppPercentage}`**%**]"
                    "\n"
                    " -> `Dyno hours quota remaining this month`:\n"
                    f"     •  `{hours}`**h**  `{minutes}`**m**  **|**  [`{percentage}`**%**]"
                    )
    return


CMD_HELP.update({
    "heroku":
    ".usage"
    "\nUsage: Check your heroku dyno hours remaining"
    "\n\n.set var <NEW VAR> <VALUE>"
    "\nUsage: add new variable or update existing value variable"
    "\n!!! WARNING !!!, after setting a variable the bot will restarted"
    "\n\n.get var or .get var <VAR>"
    "\nUsage: get your existing varibles, use it only on your private group!"
    "\nThis returns all of your private information, please be caution..."
    "\n\n.del var <VAR>"
    "\nUsage: delete existing variable"
    "\n!!! WARNING !!!, after deleting variable the bot will restarted"
})
