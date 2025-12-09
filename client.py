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
        ## acutalizo ultima revision  en base al ultimo ack
        json_msg["REVISION"] = last_synced_revision
        try:
            send_next = False
            send_msg(sock, json_msg)
            print(f"[Cliente] Enviando operacion: {json_msg}")
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
            print("[Cliente] Documento compartido inicial: ")
            print(f"  '{doc_copy}'")
            print(f"  Revision: {last_synced_revision}")

        elif msg_type == "OPERATOR":
            op_msg = data_json.get("OP")
            last_synced_revision = data_json.get("REVISION")
            print(f"\n[Cliente] Operacion del servidor: {op_msg} revision: {last_synced_revision}")

            for operation in pending_changes:
                op_msg = transform(op_msg, operation.get("OP"))
                if(op_msg is None):
                    break 
            print(f"[Cliente] Operacion transformada: {op_msg}")
            doc_copy = apply_op(doc_copy, op_msg)
            print(f"[Cliente] Documento actualizado: '{doc_copy}'")

        elif msg_type == "ACK":
            # mandar otra opercion = desencolar de lista pendientes
            last_synced_revision = data_json.get("REVISION")
            op = pending_changes.pop(0)
            print(f"\n[Cliente] ACK recibido para: {op})")
            send_next = True
            send_next_operation(sock)
        else:
            print("Mensaje No Valido")

def operations(sock, cmd, pos , msg = None):
    global doc_copy, last_synced_revision, pending_changes 

    op = {"KIND": cmd,"POS": pos}
    
    if(cmd == "delete" and msg != None):
        print("Error delete <pos> <msg> INVALIDO")
        return
    
    if(msg != None):
        ## nesesario error de inserat en pos iguales
        op["ID"] = sock.getsockname()[1]
        op["MSG"] = msg

    doc_copy = apply_op(doc_copy, op)
    print(f"\n[Cliente] Documento local: {doc_copy}")
    #print(f"\n{sock}\n")
    # accedo al pueto me sirve como id del cliente solo sirve localmente
    ##print(sock.getsockname()[1])
    json_op = make_json(type="OPERATOR", rev=last_synced_revision, op=op)
    pending_changes.append(json_op)
    send_next_operation(sock)
    return


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
        operations(sock, cmd, pos, msg_text)
    elif cmd == "delete" and len(partes) == 2 and partes[1].isdigit():
        pos = int(partes[1])
        operations(sock, cmd, pos)
    else:
        print("Comandos Invalido.")
        return

def main():
    global exit_loop

    s = socket(AF_INET, SOCK_STREAM)
    s.connect((HOST, PORT))

    print("\nComandos Válidos:")
    print("  insert <pos> <texto>  - Insertar texto en posición")
    print("  insert <pos>          - Insertar espacio en posición")
    print("  delete <pos>          - Eliminar caracter en posición")
    print("  exit                  - Salir\n")
    
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
    print("Cliente desconectado.")


if __name__ == "__main__":
    main()