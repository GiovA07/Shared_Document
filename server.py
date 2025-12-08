import socket, select
import json
import time
from utils import transform, apply_op, send_msg, make_json

HOST = "0.0.0.0"
PORT = 7773

doc             = "Bienvenidos"     # Documento 
revision        = 0            # Numero de revision
connections     = []        # Sockets conectados
log             = []                # Lista de operaciones
pending_changes = []    # Operaciones pendientes


# ====== Envio de mensajes / helpers ======
def send_document_client(sock):
    json_data = make_json(type = "DOC_TYPE", rev = revision, doc = doc) 
    send_msg(sock, json_data)

def send_ack(sock):
    data = make_json(type = "ACK", rev = revision)
    try:
        send_msg(sock, data)
    except:
        print("Error al enviar ack")
        sock.close()
        if sock in connections:
            connections.remove(sock)

# Manda la operacion realizada a todos los clientes (excepto el que la envio)
def broadcast (msg, socket_invalid):
    for sock in list(connections):
        if sock is server_socket:
            continue
        if sock is socket_invalid :
            send_ack(sock)
            continue
        try:
            send_msg(sock, msg)
        except:
            sock.close()
            if sock in connections:
                connections.remove(sock)
            print(f"Error al enviar al cliente")
            

# ====== Eventos ======
def handle_new_connection():
    global connections
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

def handle_client(sock):
    global doc, revision, log, connections
    try:
        data = sock.recv(4096)

        if not data:
            print("Client disconnected")
            if sock in connections:
                connections.remove(sock)
            sock.close()
            return
    
        if data:
            data = data.decode('utf-8').strip()
            #Obtengo el mensaje y saco su tipo
            msg = json.loads(data)
            msg_type = msg.get("TYPE")

            if msg_type == "OPERATOR":
                time.sleep(10)
                op = msg.get("OP")
                last_revision = msg.get("REVISION")
                print("op:", op, "BASE_REVISION:", last_revision)
                
                # aplicar transformador
                for operation in log:
                    if(operation.get("REVISION") >  last_revision):
                        op = transform(op, operation.get("OP"))
                        if op is None:
                            print("Operación anulada por OT. Envia solo ACK.")
                            send_ack(sock)
                            return

                new_doc = apply_op(doc, op)   
                print(new_doc)

                if (new_doc != doc):
                    doc = new_doc
                    revision = revision + 1
                    log.append({"REVISION": revision, "OP": op})
                    operator_msg = make_json(type = "OPERATOR", rev = revision, op = op)
                    broadcast(operator_msg,sock)
                else:
                    send_ack(sock)
                    print("La Operacion No cambio el Documento. IGNORADA")
            else:
                print(f"El tipo del mensaje no coincide {msg_type}")
    except:
        print(f"Client disconnected")
        connections.remove(sock)
        sock.close()


def main():
    global server_socket

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    connections.append(server_socket)

    while True:
        # Get the list sockets which are ready to be read through select
        read_sockets,write_sockets,error_sockets = select.select(connections,[],[])

        for sock in read_sockets:
            if sock == server_socket:
                handle_new_connection()
            else:
                # Data received from some client, process it
                handle_client(sock)


if __name__ == "__main__":
    main()