from socket import *
import sys
import select
import json
from utils import transform, apply_op, send_msg, make_json

HOST = "localhost"
PORT = 7777

doc_copy = ""
last_synced_revision = 0
pending_changes = []
send_next = True
exit_loop = False


def send_next_operation(sock):
    global send_next, exit_loop
    if send_next and pending_changes:
        json_msg = pending_changes[0]
        try:
            send_next = False
            send_msg(sock, json_msg)
        except Exception:
            print("ERROR al enviar al servidor")
            exit_loop = True


def handle_server_message(sock):
    global doc_copy, last_synced_revision, send_next, pending_changes, exit_loop
    data = sock.recv(1024)

    if not data:
        print("Servidor desconectado")
        exit_loop = True
        sock.close()
        return

    if data:
        json_str = data.decode("utf-8")
        data_json = json.loads(json_str)
        msg_type = data_json.get("TYPE")
        
        if msg_type == "DOC_TYPE":
            doc_copy = data_json.get("DOC")
            last_synced_revision = data_json.get("REVISION", 0)
            print("Documento actual: ")
            print(doc_copy)
        elif msg_type == "OPERATOR":
            op_msg = data_json.get("OP")
            last_synced_revision = data_json.get("REVISION")
            for operation in pending_changes:
                op_msg = transform(op_msg, operation.get("OP"))
                if(op_msg is None):
                    break 
            doc_copy = apply_op(doc_copy, op_msg)
            print("Nuevo documento: ", doc_copy)
        elif msg_type == "ACK":
            # mandar otra opercion = desencolar de lista pendientes
            last_synced_revision = data_json.get("REVISION")
            print("Se recibio el ACK")
            pending_changes.pop(0)
            send_next = True
            send_next_operation(sock)
        else:
            print("Mensaje No Valido")


def handle_client_input(sock):
    global doc_copy, last_synced_revision, pending_changes, exit_loop
    # user entered data by stdin
    user_input = sys.stdin.readline().strip()

    if user_input == "exit":
        exit_loop = True
        return
    
    partes = user_input.split(" ")
    if not partes:
        print("Comando vacio")
        return

    ## insert pos texto --- insert pos  (espacio)
    cmd = partes[0]
    if (cmd == "insert" and partes[1].isdigit() and
        (len(partes) == 3 or len(partes) == 2) ):
        pos = int(partes[1])
        msg_text = " " if len(partes) == 2 else partes[2]
        op = {"KIND": cmd,"POS": pos,"MSG": msg_text,}
    elif cmd == "delete" and len(partes) == 2 and partes[1].isdigit():
        pos = int(partes[1])
        op = { "KIND": cmd, "POS": pos, }
    else:
        print("Comandos Invalido.")
        return
    
    doc_copy = apply_op(doc_copy, op)
    print("Documento (local):")
    print(doc_copy)
    json_op = make_json(type="OPERATOR", rev=last_synced_revision, op=op)
    pending_changes.append(json_op)
    send_next_operation(sock)

def main():
    global exit_loop

    s = socket(AF_INET, SOCK_STREAM)
    s.connect((HOST, PORT))

    print("Comandos Validos:")
    print("  insert <pos> <caracter>")
    print("  insert <pos>  (agregar espacio en blanco)")
    print("  delete <pos> ")
    print("  exit")
    
    while not exit_loop:
        socket_list = [sys.stdin, s]
        # Get the list sockets which are readable
        read, write, error = select.select(socket_list, [], [])
    
        for sock in read:
            if sock == s:
                # incoming message from remote server
                handle_server_message(s)
            else:
                # user entered data by stdin
                handle_client_input(s)
    s.close()


if __name__ == "__main__":
    main()