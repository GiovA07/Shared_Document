import socket, select
import json

HOST = "0.0.0.0"
PORT = 7777

doc = "Bienvenidos"                #documento 
revision = 0            #numero de revision
connections = []        #sockets conectados
log = []                # lista de operaciones
pending_changes = []    #Operaciones pendientes

#  {
#    "TYPE": "DOC_TYPE | OP_COMMIT |  OPERATION | ACK"
#    "doc": doc}
#    "op": {"kind": "insert", "pos": "7", "msg": "hola"},
#     "revision": 1,
#     "cliente": PORT
#   }



def send_msg (sock, msg):
    data = json.dumps(msg)
    try:
        sock.send(data.encode('utf-8'))
    except:
        print(f"Error enviando documento\n")
        sock.close()
        connections.remove(sock)

def send_document_client(sock):
    json_data = {
        "TYPE": "DOC_TYPE",
        "DOC": doc,
        "REVISION": revision,
    }
    send_msg(sock, json_data)

# aplica la operacion recibida el documento
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


# Manda la operacion realizada a todos los clientes (excepto el que la envio)
def broadcast (msg, socket_invalid):
    data = json.dumps(msg)
    for sock in connections:
        if sock is server_socket or sock is socket_invalid:
            continue
        try: 
            send_msg(sock, msg)
        except:
            print(f"Error al enviar al cliente")


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
            try:
                send_document_client(sockfd)
            except Exception as e:
                print(f"[!] Error enviando el Documento a {addr}: {e}")
                connections.remove(sockfd)
                sockfd.close()
        else:
            # Data received from some client, process it
            try:
                data = sock.recv(4096)
                if data:
                    data = data.decode('utf-8').strip()
                    print(f'data: [{data}]')
                    
                    #Obtengo el mensaje y saco su tipo
                    msg = json.loads(data)
                    msg_type = msg.get("TYPE")

                    if msg_type == "OPERATOR":
                        op = msg.get("OP")
                        print(op)
                        new_doc = apply_op(doc, op)
                        print(new_doc)

                        if (new_doc != doc):
                            doc = new_doc
                            revision = revision + 1

                            operator_msg = {
                                "TYPE": "OPERATOR",
                                "REVISION": revision,
                                "OP": op, 
                            }
                            broadcast(operator_msg,sock)
                        else:
                            print(f"La Operacion No cambio el Documento. IGNORADA")

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