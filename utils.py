import json


def send_msg(sock, msg):
    data = json.dumps(msg)
    sock.send(data.encode("utf-8"))

def make_json (type = None, rev=None, op=None, doc=None):
    json_data = {}
    if type is not None:
        json_data["TYPE"] = type
    if rev is not None:
        json_data["REVISION"] = rev
    if op is not None:
        json_data["OP"] = op
    if doc is not None:
        json_data["DOC"] = doc
    return json_data
