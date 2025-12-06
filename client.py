from socket import*
import sys
import select
import json

HOST = 'localhost'
PORT = 7777
s = socket(AF_INET, SOCK_STREAM)
s.connect((HOST, PORT))

doc_copy = ""
last_synced_revision = 0
pending_changes = []

send_next = True

exit = False



def tii(op1, op2):
    p1 = int(op1.get("POS"))
    p2 = int(op2.get("POS"))
    if p1 < p2 or p1 == p2:
        return op1
    else:
        op1["POS"] = p1 + 1
        return op1

def tid(op1, op2):
    p1 = int(op1["POS"])
    p2 = int(op2["POS"])
    if p1 <= p2:
        return op1
    else:
        op1["POS"] = p1 - 1
        return op1

def tdi(op1, op2):
    p1 = int(op1["POS"])
    p2 = int(op2["POS"])
    if p1 < p2:
        return op1
    else:
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
        return op1



def send_next_operation():
    global send_next
    if send_next and pending_changes:
        first = pending_changes[0]
        json_data = {
            "TYPE": "OPERATOR",
            "REVISION": first.get("REVISION"),
            "OP": first.get("OP")
        }
        send_next = False
        
        send_msg(json_data)


def send_msg (msg):
    data = json.dumps(msg)
    s.send(data.encode('utf-8'))


def apply_op(document, op):
    kind    = op.get("KIND")
    pos     = op.get("POS")
    
    try:
        pos = int(pos)
    except (TypeError, ValueError):
        return document
    
    if kind == "insert":
        msg = op.get("MSG")
        return document[:pos] + msg + document[pos:]
    
    elif kind == "delete":
        return document[:pos] + document[pos+1:]

    else: #operacion que no existe
        return document

while not exit:
    socket_list = [sys.stdin, s]

    # Get the list sockets which are readable
    read, write, error = select.select(socket_list, [], [])

    for sock in read:
        if sock == s:
            #incoming message from remote server
            data = sock.recv(1024)
            if data:
                json_str = data.decode('utf-8')
                data_json = json.loads(json_str)
                msg_type = data_json.get("TYPE")
    
                if msg_type == "DOC_TYPE":
                    doc_copy = data_json.get("DOC", "")
                    last_synced_revision = data_json.get("REVISION", 0)
                    print("Documento actual: ")
                    print(doc_copy)
                    
                elif msg_type == "OPERATOR":
                    op_msg = data_json.get("OP")
                    last_synced_revision = data_json.get("REVISION")
                    

                    for operation in pending_changes:
                            op_msg = transform(op_msg, operation.get("OP"))
                    
                    

                    doc_copy = apply_op(doc_copy, op_msg)
                    print("Nuevo documento: ", doc_copy)
                


                elif msg_type == "ACK":
                    # mandar otra opercion = desencolar de lista pendientes
                    last_synced_revision = data_json.get("REVISION")
                    print("Se recibio el ACK")
                    pending_changes.pop(0)
                    send_next = True
                    send_next_operation()
                    
                else:
                    print("Mensaje No Valido")
        else:
            #user entered data by stdin
            user_input = sys.stdin.readline().strip()

            if user_input in ("quit", "exit"):
                exit = True
                break

            partes = user_input.split(" ")
            ## Forma de mensaje insert pos msg
            if partes[0] == "insert" and len(partes) == 3:
                
                print("[Client] Agrego Insert")
                pos = int(partes[1])
                msg_text = partes[2]


                op = {
                    "KIND": "insert", 
                    "POS": pos, 
                    "MSG": msg_text,
                }

                doc_copy = apply_op(doc_copy, op)
                print("Documento (local):")
                print(doc_copy)

                json_op = {
                    "REVISION": last_synced_revision,
                    "OP": op
                }

                pending_changes.append(json_op)
                send_next_operation()


                
            elif partes[0] == "delete" and len(partes) >= 2:
                print("delete")

                pos = int(partes[1])
                op = {
                    "KIND": "delete", 
                    "POS": partes[1], 
                }
                doc_copy = apply_op(doc_copy, op)
                
                print("Documento (local):")
                print(doc_copy)

                json_op = {
                    "REVISION": last_synced_revision,
                    "OP": op
                }

                pending_changes.append(json_op)
                send_next_operation()
            else:
                print("Comandos Validos:")
                print("  insert <pos> <caracter>")
                print("  delete <pos>")
                continue

s.close()