import socket, select
import json

HOST = ""
PORT = 7773

doc = "Bienvenidos"                #documento 
revision = 0            #numero de revision
connections = []        #sockets conectados
log = []                # lista de operaciones
pending_changes = []    #Operaciones pendientes

#  {
#    "type": "DOC_TYPE | OPERATION"
#    "doc": doc}
#    "op": {"kind": "insert", "pos": "7", "msg": "hola"},
#     "revision": 1,
#     "cliente": PORT
#   }

def send_document_client(sock, addr):
    json_data = {
        "type": "DOC_TYPE",
        "doc": doc,
        "revision": revision,
    }

    data = json.dumps(json_data)
    try:
        sock.send(data.encode('utf-8'))
    except:
        print(f"Error enviando documento a {addr}\n")
        sock.close()
        connections.remove(sock)

# Manda la operacion realizada a todos los clientes (excepto el que la envio)
def broadcast (msg, socket_invalid):
    data = json.dumps(msg)
    for sock in connections:
        if sock is server_socket or sock is socket_invalid:
            continue
        try: 
            sock.send(data.encode('utf-8'))
        except:
            print(f"Error al enviar al cliente")

# aplica la operacion recibida el documento
def apply_op(document, op):
    kind    = op.get("kind")
    pos     = int(op.get("pos"))
    msg     = op.get("msg")

    if kind == "insert":
        return document[:pos] + msg + document[pos:]
    
    elif kind == "delete":
        return document[:pos] + document[pos+1:]

    else: #operacion que no existe
        return 0



server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()

# Add server socket to the list of readable connections
connections.append(server_socket)

while True:
    # Get the list sockets which are ready to be read through select
    read_sockets,write_sockets,error_sockets = select.select(connections,[],[])

    for sock in read_sockets:
        if sock == server_socket:
            #New connection
            sockfd, addr = server_socket.accept()
            connections.append(sockfd)
            print(f"Client {addr} connected")
            send_document_client(sockfd, addr)

        else:
            # Data received from some client, process it
            try:
                data = sock.recv(1024)
                if data:
                    data = data.decode('utf-8').strip()
                    print(f'data: [{data}]')
                    
                    #Obtengo el mensaje y saco su tipo
                    msg = json.loads(data)
                    msg_type = msg.get("type")

                    if msg_type == "operator":
                        op = msg.get("op")
                        print(op)

                        new_doc = apply_op(doc, op)
                        print(new_doc)

                        if (new_doc != doc):
                            doc = new_doc
                            revision = revision + 1

                            operator_msg = {
                                "type": "operator",
                                "revision": revision,
                                "op": op,
                                
                            }
                            broadcast(operator_msg,sock)


                    else:
                        print(f"El tipo del mensaje no coincide {msg_type}")

                    # pending_changes.remove(data)
                    
                    
                    #doc = doc[:pos] + msg + doc[pos:]


                    #broadcast(sock, msg)
                    #if str(data) == 'quit':
                    #    connections.remove(sock)
            except:
                print(f"Client {addr} disconnected")
                sock.close()
                connections.remove(sock)
    







# Tii(Ins[p1, c1], Ins[p2, c2]) {
#   if (p1 < p2) || ((p1 == p2) && (order() == -1))  // order() – order calculation
# 	return Ins[p1, c1]; // Tii(Ins[3, ‘a’], Ins[4, ‘b’]) = Ins[3, ‘a’]
#   else
# 	return Ins[p1 + 1, c1]; // Tii(Ins[3, ‘a’], Ins[1, ‘b’]) = Ins[4, ‘a’]
# }

# Tid(Ins[p1, c1], Del[p2]) {
#   if (p1 <= p2)
#     return Ins[p1, c1]; // Tid(Ins[3, ‘a’], Del[4]) = Ins[3, ‘a’]
#   else
#     return Ins[p1 – 1, c1]; // Tid(Ins[3, ‘a’], Del[1]) = Ins[2, ‘a’]
# }

# Tdi(Del[p1], Ins[p2, c1]) {
#   // Exercise
# }

# Tdd(Del[p1], Del[p2]) {
#   if (p1 < p2)
#     return Del[p1]; // Tdd(Del[3], Del[4]) = Del[3]
#   else
#     if (p1 > p2) return Del[p1 – 1]; // Tdd(Del[3], Del[1]) = Del[2]
#   else
#     return Id; // Id – identity operator
# }