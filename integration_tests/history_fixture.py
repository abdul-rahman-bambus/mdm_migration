"""Synthetic Odoo 12-shaped RPC source. Never claims live source compatibility."""

import threading
import xmlrpc.client
from http.server import BaseHTTPRequestHandler, HTTPServer

from migration_lab.contact_history import Source
from migration_lab.preflight import Settings


class HistoryFixture:
    def __enter__(self):
        self.calls = []
        self.phone = "+12025550100"
        fixture = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                args, method = xmlrpc.client.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if method == "version":
                    result = {"server_version_info": [12, 0]}
                elif method == "authenticate":
                    result = 1
                else:
                    _, _, _, model, operation, positional, kwargs = args
                    fixture.calls.append((model, operation))
                    assert operation == "search_read"
                    rows = {
                        "res.partner": [{"id": 41, "name": "Synthetic chatter contact", "email": "history@example.invalid",
                                         "phone": fixture.phone, "is_company": False, "active": True, "parent_id": False, "country_id": False, "vat": ""}],
                        "res.users": [],
                        "mail.message": [{"id": 101, "date": "2019-10-01 09:30:00", "author_id": [7, "Synthetic author"],
                                          "subject": "History", "body": "<p>Synthetic historical note</p>", "message_type": "comment", "subtype_id": [2, "Note"], "email_from": False,
                                          "tracking_value_ids": [201], "attachment_ids": [301]}],
                        "mail.tracking.value": [{"id": 201, "field_desc": "Phone", "field_type": "char", "old_value_char": "100", "new_value_char": "200"}],
                        "ir.attachment": [{"id": 301, "name": "synthetic.txt", "type": "binary", "file_size": 5, "datas": "dHJpYWw="}],
                    }[model]
                    result = [{field: row.get(field, False) for field in ["id", *kwargs["fields"]]} for row in rows]
                payload = xmlrpc.client.dumps((result,), methodresponse=True, allow_none=True).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.source = Source(Settings("http://127.0.0.1:" + str(self.server.server_port), "odoo12_demo", "synthetic", "synthetic"))
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
