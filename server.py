import socket, select
import json

HOST = "localhost"
PORT = 7777

doc = ""                #documento 
revision = 0            #numero de revision
connections = []         #sockets conectados
log = []                # lista de operaciones
pending_changes = []    #Operaciones pendientes


# Manda la operacion realizada a todos los clientes (excepto el que la envio)
def broadcast ():
    return 0

# envia el mensaje 
def send ():
    return 0

# aplica la operacion recibida el documento
def apply():
    return 0




server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("192.168.2.124", port))
server_socket.listen(10)

# Add server socket to the list of readable connections
connections.append(server_socket)
print(f"Chat server started on {server_socket} ")

while True:
    # Get the list sockets which are ready to be read through select
    read_sockets,write_sockets,error_sockets = select.select(connections,[],[])

    for sock in read_sockets:
        if sock == server_socket:
            #New connection
            sockfd, addr = server_socket.accept()
            connections.append(sockfd)
            print(f"Client {addr} connected")
            broadcast(sockfd, f"Client {addr} joined to Archive")
    