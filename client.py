from socket import*
import sys
import select
import json

HOST = 'localhost'
PORT = 7777
s = socket(AF_INET, SOCK_STREAM)
s.connect((HOST, PORT))

doc_copy = ""
revision = 0

exit = False

#  {
#    "type": "DOC_TYPE | OPERATION | OP_COMMIT | ACK"
#    "doc": doc}
#    "op": {"kind": "insert", "pos": "7", "msg": "hola"},
#    "revision": 1,
#    "cliente": PORT
#   }


def send_msg (msg):
    data = json.dumps(msg)
    s.send(data.encode('utf-8'))


def apply_op(document, op):
    kind    = op.get("KIND")
    pos     = int(op.get("POS"))

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
                    doc_copy = data_json.get("DOC")
                    revision = data_json.get("REVISION")
                    print("Documento actual: ")
                    print(doc_copy)
                    
                elif msg_type == "OPERATOR":
                    op_msg = data_json.get("OP")
                    revision = data_json.get("revision")
                    doc_copy = apply_op(doc_copy, op_msg)
                    print("Nuevo documento: ", doc_copy)
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

                json_data = {
                    "TYPE" : "OPERATOR",
                    "OP" : op
                }
                send_msg(json_data)
                doc_copy = apply_op(doc_copy, op)
                print("Documento (local):")
                print(doc_copy)

                
            elif partes[0] == "delete" and len(partes) >= 2:
                print("delete")

                pos = int(partes[1])
                op = {
                    "KIND": "delete", 
                    "POS": partes[1], 
                }
                json_data = {
                    "TYPE" : "OPERATOR",
                    "OP" : op
                }
                send_msg(json_data)
                doc_copy = apply_op(doc_copy, op)
                print(doc_copy)
            else:
                print("Comandos Validos:")
                print("  insert <pos> <caracter>")
                print("  delete <pos>")

s.close()