# This file is part of the project mb-netmgmt
#
# (C) 2022 Deutsche Telekom AG
#
# Deutsche Telekom AG and all other contributors / copyright
# owners license this file to you under the terms of the GPL-2.0:
#
# mb-netmgmt is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# mb-netmgmt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mb-netmgmt. If not, see <https://www.gnu.org/licenses/

from ncclient.devices.default import DefaultDeviceHandler
from ncclient.manager import connect
from ncclient.transport.parser import DefaultXMLParser
from ncclient.transport.session import (
    HelloHandler,
    SessionListener,
    qualify,
    sub_ele,
    to_ele,
    to_xml,
)
from ncclient.transport.ssh import (
    END_DELIM,
    MSG_DELIM,
    PORT_NETCONF_DEFAULT,
    SSHSession,
)

from mb_netmgmt.ssh import Handler as SshHandler
from mb_netmgmt.ssh import Server, get_message_id, replace_message_id


class Handler(SshHandler):
    message_terminators = [MSG_DELIM, END_DELIM]
    default_port = 830

    def __init__(self, request, client_address, server):
        session = SSHSession(DefaultDeviceHandler())
        session.add_listener(Listener(super().handle_request))
        self.parser = DefaultXMLParser(session)
        super().__init__(request, client_address, server)

    def open_upstream(self):
        to = self.get_to()
        if not to:
            return
        self.manager = connect(
            host=to.hostname,
            port=to.port or PORT_NETCONF_DEFAULT,
            username=to.username,
            password=to.password,
            hostkey_verify=False,
        )

    def handle_prompt(self):
        hello = to_ele(HelloHandler.build([], None))

        # A server sending the <hello> element MUST include a <session-id>
        # element containing the session ID for this NETCONF session.
        # https://datatracker.ietf.org/doc/html/rfc6241#section-8.1
        session_id = sub_ele(hello, "session-id")
        session_id.text = "1"

        self.channel.sendall(to_xml(hello) + MSG_DELIM.decode())
        self.read_message(self.channel)

    def read_proxy_response(self):
        return {
            "response": replace_message_id(self.rpc_reply.xml, "") + MSG_DELIM.decode()
        }

    def send_upstream(self, request, request_id):
        self.rpc_reply = self.manager.rpc(
            to_ele(request["command"][: -len(MSG_DELIM)])[0]
        )

    def read_message(self, channel):
        message = super().read_message(channel)
        self.parser.parse(message)
        return b""

    def handle_request(self, request, request_id):
        pass


class Listener(SessionListener):
    def __init__(self, handle_request):
        self.handle_request = handle_request

    def callback(self, root, raw):
        tag, attrs = root
        if (tag == qualify("hello")) or (tag == "hello"):
            return
        request = {"command": replace_message_id(raw, "") + MSG_DELIM.decode()}
        request_id = get_message_id(raw)
        self.handle_request(request, request_id)
