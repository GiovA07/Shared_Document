from socket import*
import sys
import select
import json

HOST = 'localhost'
PORT = 7773
s = socket(AF_INET, SOCK_STREAM)
s.connect((HOST, PORT))

doc_copy = " "

exit = False

#  {
#    "type": "DOC_STATE | OPERATION | ACK"
#    "doc": doc}
#    "op": {"kind": "insert", "pos": "7", "msg": "hola"},
#    "revision": 1,
#    "cliente": PORT
#   }


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
                msg_type = data_json.get("type")
    
                if msg_type == "DOC_TYPE":
                    doc_copy = data_json.get("doc")
                    print(doc_copy)
                    
                elif msg_type == "operator":
                    op_msg = data_json.get("op")
                    pos = int(op_msg.get("pos"))
                    if(op_msg.get("kind") == "insert"):
                        print("Insert \n")
                        msg = op_msg.get("msg")
                        doc_copy = doc_copy[:pos] + msg + doc_copy[pos:]
                    else: 
                        print("Delete \n")
                        doc_copy = doc_copy[:pos] + doc_copy[pos+1:]

                    print("Nuevo documento: ", doc_copy)
                else:
                    print("Mensaje No Valido")
        else:
            #user entered data by stdin
            # insert pos char
            # delete pos
            msg = sys.stdin.readline().strip()
            partes = msg.split(" ")

            ## Forma de mensaje insert pos msg
            if partes[0] == "insert":
                
                print("[Client] Agrego Insert")
                
                json_data = {
                    "type" : "operator",
                    "op" : {
                    "kind": "insert", 
                    "pos": partes[1], 
                    "msg": partes[2]},
                }
                s.send(bytes(json.dumps(json_data), "utf-8"))

                doc_copy = doc_copy[:int(partes[1])] + partes[2] + doc_copy[int(partes[1]):]
                print(doc_copy)

                
            elif partes[0] == "delete":
                print("delete")

                json_data = {
                    "type" : "operator",
                    "op" : {
                    "kind": "delete", 
                    "pos": partes[1], 
                    },
                }
                s.send(bytes(json.dumps(json_data), "utf-8"))

                doc_copy = doc_copy[:int(partes[1])] + doc_copy[int(partes[1])+1:]
                print(doc_copy)
            else:
                print("Operacion Invalida")

            
            ##s.send(bytes(msg, "utf-8"))
            
            if msg.strip() == "quit":
                exit = True

s.close()