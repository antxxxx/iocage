# Copyright (c) 2014-2017, iocage
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted providing that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""upgrade module for the cli."""
import click

import iocage.lib.ioc_common as ioc_common
import iocage.lib.ioc_json as ioc_json
import iocage.lib.ioc_list as ioc_list
import iocage.lib.ioc_start as ioc_start
import iocage.lib.ioc_stop as ioc_stop
import iocage.lib.ioc_upgrade as ioc_upgrade

__rootcmd__ = True


@click.command(name="upgrade", help="Run freebsd-update to upgrade a specified"
                                    " jail to the RELEASE given.")
@click.argument("jail", required=True)
@click.option("--release", "-r", required=True, help="RELEASE to upgrade to")
def cli(jail, release):
    """Runs upgrade with the command given inside the specified jail."""
    jails, paths = ioc_list.IOCList("uuid").list_datasets()
    _jail = {tag: uuid for (tag, uuid) in jails.items() if
             uuid.startswith(jail) or tag == jail}

    if len(_jail) == 1:
        tag, uuid = next(iter(_jail.items()))
        path = paths[tag]
        root_path = "{}/root".format(path)
    elif len(_jail) > 1:
        ioc_common.logit({
            "level"  : "ERROR",
            "message": f"Multiple jails found for {jail}:"
        })
        for t, u in sorted(_jail.items()):
            ioc_common.logit({
                "level"  : "ERROR",
                "message": f"  {u} ({t})"
            })
        exit(1)
    else:
        ioc_common.logit({
            "level"  : "ERROR",
            "message": f"{jail} not found!"
        })
        exit(1)

    status, jid = ioc_list.IOCList.list_get_jid(uuid)
    conf = ioc_json.IOCJson(path).json_load()
    jail_release = conf["release"]
    started = False

    if conf["release"] == "EMPTY":
        ioc_common.logit({
            "level"  : "ERROR",
            "message": "Upgrading is not supported for empty jails."
        })
        exit(1)
    if conf["type"] == "jail":
        if not status:
            ioc_start.IOCStart(uuid, tag, path, conf, silent=True)
            started = True

            new_release = ioc_upgrade.IOCUpgrade(conf, release,
                                                 root_path).upgrade_jail()
    elif conf["type"] == "basejail":
        ioc_common.logit({
            "level"  : "ERROR",
            "message": "Please run \"iocage migrate\" before trying"
                       f" to upgrade {uuid} ({tag})"
        })
        exit(1)
    elif conf["type"] == "template":
        ioc_common.logit({
            "level"  : "ERROR",
            "message": "Please convert back to a jail before trying"
                       f" to upgrade {uuid} ({tag})"
        })
        exit(1)
    else:
        ioc_common.logit({
            "level"  : "ERROR",
            "message": f"{conf['type']} is not a supported jail type."
        })
        exit(1)

    if started:
        ioc_stop.IOCStop(uuid, tag, path, conf, silent=True)

        ioc_common.logit({
            "level"  : "INFO",
            "message": f"\n{uuid} ({tag}) successfully upgraded from"
                       f" {jail_release} to {new_release}!"
        })
