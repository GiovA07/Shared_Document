# ---------- OT: Transformaciones ----------
# Transformaciones OT basicas:
#   tii: transform insert vs insert
#   tid: transform insert vs delete
#   tdi: transform delete vs insert
#   tdd: transform delete vs delete
# doc A insert A 0 => "A" Server => Doc A => "BA"
# doc B insert B 0 => "B" Server => Doc B => "AB"

def tii(op1, op2):
    p1 = int(op1.get("POS"))
    p2 = int(op2.get("POS"))
    p1_id = op1.get("ID")
    p2_id = op2.get("ID")

    if p1 < p2 or (p1 == p2 and p1_id < p2_id):
        return op1
    op1["POS"] = p1 + 1
    return op1

def tid(op1, op2):
    p1 = int(op1["POS"])
    p2 = int(op2["POS"])
    if p1 <= p2:
        return op1
    op1["POS"] = p1 - 1
    return op1


def tdi(op1, op2):
    p1 = int(op1["POS"])
    p2 = int(op2["POS"])
    if p1 < p2:
        return op1
    op1["POS"] = p1 + 1
    return op1


def tdd(op1, op2):
    p1 = int(op1["POS"])
    p2 = int(op2["POS"])
    if p1 < p2:
        return op1
    elif p1 > p2:
        op1["POS"] = p1 - 1
        return op1
    else:
        return None


def transform(op1, op2):
    if op1 is None:
        return None
    if op2 is None:
        return op1 
    k1 = op1.get("KIND")
    k2 = op2.get("KIND")

    op1 = op1.copy()
    if k1 == "insert" and k2 == "insert":
        return tii(op1, op2)
    elif k1 == "insert" and k2 == "delete":
        return tid(op1, op2)
    elif k1 == "delete" and k2 == "insert":
        return tdi(op1, op2)
    elif k1 == "delete" and k2 == "delete":
        return tdd(op1, op2)
    else:
        return op1
