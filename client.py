from socket import *
import sys
import select
import json
import time
from utils import send_msg, make_json, apply_op
from ot import transform

HOST = "localhost"
PORT = 7777

doc_copy = ""          # documento local
current_revision = 0   # ultima revision conocida del servidor
pending_changes = []   # lista de mensajes JSON de operaciones locales pendientes a enviar
send_next = True       # indica si puedo mandar la proxima operacion
exit_loop = False      # booleano para cortar el ciclo principal
offline = False        # booleano para ver si estoy offline
auto_reconnect = False

id_client = 0
client_socket = None


# ====== Funciones de conexion ======
def reconect_to_server():
    global client_socket, offline, send_next
    try:
        sock = socket(AF_INET, SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect((HOST, PORT))
        sock.settimeout(None)

        client_socket = sock
        offline = False
        send_next = True

        msg = {
            "TYPE": "GET_LOG",
            "REVISION": current_revision
        }

        send_msg(sock,msg)
        print("[Cliente] Reconexion exitosa. Sincronizando...")

    except Exception:
        print("No se pudo reconectar al servidor")
        return

def disconnect():
    global client_socket, offline, send_next
    if socket:
        try:
            client_socket.close()
        except:
            pass
        client_socket = None
    
    offline = True
    send_next = True

# ====== Envio de Operaciones ======

def send_next_operation(sock):
    global send_next, exit_loop, offline

    if offline or client_socket is None:
        return

    if send_next and pending_changes:
        json_msg = pending_changes[0]
        try:
            send_next = False
            send_msg(sock, json_msg)
            print(f"\n[Cliente] Enviando operacion: {json_msg['OP']}")
        except Exception:
            print("[Cliente] Error al enviar operacion.")
            disconnect()

# ====== Manejo de mensajes del servidor ======
def handle_log_restorage(data_json):
    global pending_changes, send_next, doc_copy, current_revision
    operations_entry = data_json.get("OPERATIONS")
    if not operations:
        print("[Cliente] No hay operaciones nuevas en el servidor")
    else:
        print(f"[Cliente] Sincronizando con operaciones del servidor...")
    
    for op_entry in operations_entry:
        server_op = op_entry.get("OP")
        if server_op is None:
            continue

        for pending in pending_changes:
            if server_op is None:
                break

            local_op = pending.get("OP")
            if local_op is None:
                continue

            pending["OP"] = transform(local_op.copy(), server_op)
            server_op = transform(server_op.copy(), local_op)
        if server_op is not None:
            doc_copy = apply_op(doc_copy, server_op)
        else:
            print("[Cliente] Operacion remota anulada, no se aplica.")
    
    current_revision = data_json.get("REVISION", current_revision)
    if pending_changes:
        pending_changes[0]["REVISION"] = current_revision
    
    print(f"[Cliente] Sincronización completa. Documento:\n  '{doc_copy}'")
    print(f"[Cliente] Revisión actual: {current_revision}\n")
    
    send_next = True
    send_next_operation(client_socket)

def handle_remote_operation(data_json):
    global pending_changes, doc_copy, current_revision
    remote_op = data_json.get("OP")
    current_revision = data_json.get("REVISION")
    print(f"\n[Servidor] Operacion remota: {remote_op} " f"Revision: {current_revision}\n")

    for pending_msg in pending_changes:
        if remote_op is None:
            break

        local_op = pending_msg.get("OP")
        if local_op is None:
            continue

        # actualizo las operaciones que todavia no se enviaron
        pending_msg["OP"] = transform(local_op.copy(), remote_op)
        # actualizo la operacion que llego (remota)
        remote_op = transform(remote_op.copy(), local_op)

    # si la remota se anula, no la aplicamos
    if remote_op is not None:
        doc_copy = apply_op(doc_copy, remote_op)
        print(f"[Cliente] Documento actualizado:  \n {doc_copy}")
    else:
        print("[Cliente] Operacion remota anulada, no se aplica.")

def handle_ack(data_json):
    global current_revision, pending_changes, send_next
    
    if not pending_changes:
        print("[Cliente] ACK inesperado (no hay operaciones pendientes)")
        return
    
    current_revision = data_json.get("REVISION")
    # Quitamos la operacion confirmada de la cola
    op = pending_changes.pop(0)
    print(f"[Cliente] ACK recibido para: {op['OP']})")

    # Actualizo la revision de la siguiente operacion
    if pending_changes:
        pending_changes[0]["REVISION"] = current_revision
    # Enviamos la siguiente operacion
    send_next = True
    send_next_operation(client_socket)


def handle_server_message(sock):
    global doc_copy, current_revision, send_next, pending_changes, offline, id_client

    data = sock.recv(4096)
    if not data:
        print("[Cliente] Servidor desconectado")
        disconnect()
        return

    data_json = json.loads(data.decode("utf-8"))
    msg_type = data_json.get("TYPE")
    # ---------- Documento inicial ----------
    if msg_type == "DOC_TYPE":
        id_client = data_json.get("ID")

        doc_copy = data_json.get("DOC", "")
        current_revision = data_json.get("REVISION", 0)

        print("[Servidor] Documento compartido inicial: ")
        print(f"  {doc_copy}")
        print(f"Revision: {current_revision}")

    elif msg_type == "LOG_RESTORAGE":
        handle_log_restorage(data_json)
    elif msg_type == "OPERATOR":
        handle_remote_operation(data_json)
    elif msg_type == "ACK":
        handle_ack(data_json)
    else:
        print("[Cliente] Mensaje no valido enviado desde el servidor:", data_json)


def operations(sock, cmd, pos, msg=None):
    global doc_copy, current_revision, pending_changes

    op = {"KIND": cmd, "POS": pos, "ID" :id_client}
    
    if cmd == "delete" and msg is not None:
        print("Error delete <pos> <msg> INVALIDO")
        return


    if msg is not None:
        op["MSG"] = msg

    doc_copy = apply_op(doc_copy, op)
    print(f"\n[Cliente] Documento local: \n {doc_copy}")

    json_op = make_json(type="OPERATOR", rev=current_revision, op=op)
    pending_changes.append(json_op)

    ## si esty offline sigo encolando en cambios pendiente sin mandarlo al servidor
    if not offline:
        # Mensaje JSON para enviar al servidor
        send_next_operation(sock)


def handle_client_input(sock):
    global exit_loop

    user_input = sys.stdin.readline().strip()

    if user_input == "exit":
        exit_loop = True
        return

    input_parts = user_input.split(" ")
    if not input_parts:
        print("[Cliente] Comando vacio")
        return

    cmd = input_parts[0]
    # ----- insert -----
    if (
        cmd == "insert"
        and len(input_parts) >= 2
        and len(input_parts) <= 3
        and input_parts[1].isdigit()
    ):

        pos = int(input_parts[1])
        msg_text = " " if len(input_parts) == 2 else input_parts[2]
        operations(sock, cmd, pos, msg_text)

    # ----- delete -----
    elif cmd == "delete" and len(input_parts) == 2 and input_parts[1].isdigit():
        pos = int(input_parts[1])
        operations(sock, cmd, pos)
    
    elif user_input == "crash":
        print("[Cliente] Cortando la conexion a proposito")
        
        global client_socket, offline, send_next
        print("[Cliente] ¡Simulando corte de cable!")
        disconnect()
        print("[Cliente] Desconectado. Usa 'reconnect' para reconectar.\n")
        return
    
    elif user_input == "reconect":
        print("[Cliente] Intentando reconectar...")
        reconect_to_server()
        return
    else:
        print("[Cliente] Comando invalido.")
        return

def main():
    global exit_loop, client_socket, offline

    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((HOST, PORT))

    send_msg(client_socket, {"TYPE":"GET_DOC"})  

    print("\nComandos Válidos:")
    print("  insert <pos> <texto>  - Insertar texto en posición")
    print("  insert <pos>          - Insertar espacio en posición")
    print("  delete <pos>          - Eliminar caracter en posición")
    print("  exit                  - Salir\n")

    while not exit_loop:

        readers = [sys.stdin]
        if not offline and client_socket is not None and client_socket.fileno() >= 0:
            readers.append(client_socket)
        # pongo como parametro el 1 segundo para que salga del for
        read, _, _ = select.select(readers, [], [], 1.0)

        for sock in read:
            if sock == client_socket:
                handle_server_message(client_socket)
            else:
                handle_client_input(client_socket)

    disconnect()
    print("[Cliente] Cliente desconectado.")


if __name__ == "__main__":
    main()
