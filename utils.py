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

# ---------- OT: Transformaciones ----------
# Transformaciones OT basicas:
#   tii: transform insert vs insert
#   tid: transform insert vs delete
#   tdi: transform delete vs insert
#   tdd: transform delete vs delete
# doc A insert A 0 => "A" Server => Doc A => "BA"
# doc B insert B 0 => "B" Server => Doc B => "AB"

def tii(op1, op2):
    new = op1.copy()
    p1 = int(op1.get("POS"))
    p2 = int(op2.get("POS"))
    p1_id = op1.get("ID")
    p2_id = op2.get("ID")

    if p1 < p2 :
        return op1
    elif p1 > p2:
        new["POS"] = p1 + 1
        return new
    else:
        if p1_id < p2_id:
            return new
        else:
            new["POS"] = p1 + 1
            return new

def tid(op1, op2):
    new = op1.copy()
    p1 = int(op1["POS"])
    p2 = int(op2["POS"])
    if p1 <= p2:
        return op1
    else:
        new["POS"] = p1 - 1
        return new


def tdi(op1, op2):
    new = op1.copy()
    p1 = int(op1["POS"])
    p2 = int(op2["POS"])
    if p1 < p2:
        return new
    else:
        new["POS"] = p1 + 1
        return new


def tdd(op1, op2):
    new = op1.copy()
    p1 = int(op1["POS"])
    p2 = int(op2["POS"])
    if p1 < p2:
        return new
    elif p1 > p2:
        new["POS"] = p1 - 1
        return new
    else:
        return None


def transform(op1, op2):
    if op1 is None:
        return None
    k1 = op1.get("KIND")
    k2 = op2.get("KIND")

    if k1 == "insert" and k2 == "insert":
        return tii(op1, op2)
    elif k1 == "insert" and k2 == "delete":
        return tid(op1, op2)
    elif k1 == "delete" and k2 == "insert":
        return tdi(op1, op2)
    elif k1 == "delete" and k2 == "delete":
        return tdd(op1, op2)
    else:
        return op1.copy()


def apply_op(document, op):
    if op == None:
        return document

    kind = op.get("KIND")
    pos = int(op.get("POS"))

    if kind == "insert":
        msg = op.get("MSG")
        return document[:pos] + msg + document[pos:]

    elif kind == "delete":
        return document[:pos] + document[pos + 1 :]

    else:  # operacion que no existe
        return document
