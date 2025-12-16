import json


def send_msg(sock, msg):
    data = json.dumps(msg)
    sock.sendall((data + "\n").encode("utf-8"))

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


def apply_op(document, op):
    if op == None:
        return document

    kind = op.get("KIND")
    pos = int(op.get("POS"))

    if kind == "insert":
        if pos < 0:
            pos = 0
            op["POS"] = 0
        elif pos > len(document):
            pos = len(document)
            op["POS"] = len(document)
            
        msg = op.get("MSG")
        return document[:pos] + msg + document[pos:]

    elif kind == "delete":
        if pos < 0:
            return document
        return document[:pos] + document[pos + 1 :]

    else:  # operacion que no existe
        return document