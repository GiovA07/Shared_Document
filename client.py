from socket import *
import sys
import select
import json
from utils import send_msg, make_json
from ot import transform, apply_op

HOST = "localhost"
PORT = 7773

doc_copy = ""  # documento local
current_revision = 0  # ultima revision conocida del servidor
pending_changes = (
    []
)  # lista de mensajes JSON de operaciones locales pendientes a enviar
send_next = True  # indica si puedo mandar la proxima operacion
exit_loop = False  # booleano para cortar el ciclo principal
offline = False  # booleano para ver si estoy offline
syncing = False
client_socket = None


def send_next_operation(sock):
    global send_next, exit_loop, offline

    if send_next and pending_changes:
        json_msg = pending_changes[0]
        try:
            send_next = False
            send_msg(sock, json_msg)
            print(f"\n[Cliente] Enviando operacion: {json_msg['OP']}")
        except Exception:
            sock.close()
            print("[Cliente] Conexion fallo")
            offline = True
            send_next = True
            # exit_loop = True


def handle_server_message(sock):
    global doc_copy, current_revision, send_next, pending_changes, exit_loop, offline, syncing

    data = sock.recv(4096)
    if not data:
        sock.close()
        print("[Cliente] Servidor desconectado")
        offline = True
        send_next = True
        return

    data_json = json.loads(data.decode("utf-8"))
    msg_type = data_json.get("TYPE")
    # ---------- Documento inicial ----------
    if msg_type == "DOC_TYPE":
        if syncing:
            syncing = False
            return

        doc_copy = data_json.get("DOC", "")
        current_revision = data_json.get("REVISION", 0)

        print("[Servidor] Documento compartido inicial: ")
        print(f"  {doc_copy}")
        print(f"Revision: {current_revision}")

    elif msg_type == "LOG_RESTORAGE":
        operations_entry = data_json.get("OPERATIONS")
        for op_entry in operations_entry:
            op = op_entry.get("OP")
            current_revision = op_entry.get("REVISION")
            if op is None:
                continue

            for pending in pending_changes:
                local_op = pending.get("OP")
                if local_op is None:
                    continue
                pending["OP"] = transform(local_op.copy(), op)
                op = transform(op.copy(), local_op)

            if op is not None:
                doc_copy = apply_op(doc_copy, op)
                print(f"[Cliente] Documento actualizado:  \n {doc_copy}")

            else:
                print("[Cliente] Operacion remota anulada, no se aplica.")
   
        send_next = True
        send_next_operation(client_socket)
    # ---------- Operacion remota ----------
    elif msg_type == "OPERATOR":
        op_msg = data_json.get("OP")
        current_revision = data_json.get("REVISION")
        print(f"\n[Servidor] Operacion: {op_msg} " f"Revision: {current_revision}\n")

        for operation in pending_changes:
            if op_msg is None:
                break

            local_op = operation.get("OP")
            if local_op is None:
                continue

            # actualizo las operaciones que todavia no se enviaron
            operation["OP"] = transform(local_op.copy(), op_msg)
            # actualizo la operacion que llego (remota)
            op_msg = transform(op_msg.copy(), local_op)

        print(f"[Cliente] Operacion transformada: {op_msg}")

        # si la remota se anula, no la aplicamos
        if op_msg is not None:
            doc_copy = apply_op(doc_copy, op_msg)
            print(f"[Cliente] Documento actualizado:  \n {doc_copy}")
        else:
            print("[Cliente] Operacion remota anulada, no se aplica.")

    # ---------- ACK ----------
    elif msg_type == "ACK":
        # mandar otra operacion y desencolar de lista pendientes
        current_revision = data_json.get("REVISION")
        op = pending_changes.pop(0)
        print(f"[Cliente] ACK recibido para: {op['OP']})")

        # si todavia queda otra pendiente, actualizo su revision base
        if pending_changes:
            pending_changes[0]["REVISION"] = current_revision

        send_next = True
        send_next_operation(client_socket)

    else:
        print("[Cliente] Mensaje no valido enviado desde el servidor:", data_json)


def operations(sock, cmd, pos, msg=None):
    global doc_copy, current_revision, pending_changes

    op = {"KIND": cmd, "POS": pos}

    if cmd == "delete" and msg is not None:
        print("Error delete <pos> <msg> INVALIDO")
        return

    if msg is not None:
        # id del cliente, solo te sirve localmente
        ##op["ID"] = sock.getsockname()[1]
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
    else:
        print("[Cliente] Comando invalido.")
        return


def handler_recconection():
    global client_socket, offline, send_next, syncing
    try:
        sock = socket(AF_INET, SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect((HOST, PORT))
        sock.settimeout(None)
        client_socket = sock
        offline = False
        send_next = True
        syncing = True

        msg = {
            "TYPE": "GET_LOG",
            "REVISION": current_revision
        }

        send_msg(sock,msg)
    except Exception:
        print("No se pudo reconectar al servidor")
        return


def main():
    global exit_loop, client_socket, offline

    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((HOST, PORT))


    print("\nComandos Válidos:")
    print("  insert <pos> <texto>  - Insertar texto en posición")
    print("  insert <pos>          - Insertar espacio en posición")
    print("  delete <pos>          - Eliminar caracter en posición")
    print("  exit                  - Salir\n")

    while not exit_loop:

        readers = [sys.stdin]
        # si estoy en linea escucho al server
        if not offline:
            readers.append(client_socket)

        # pongo como parametro el 1 segundo para que salga del for
        read, _, _ = select.select(readers, [], [], 5.0)

        for sock in read:
            if sock == client_socket:
                handle_server_message(client_socket)
            else:
                handle_client_input(client_socket)

        if offline:
            print("Reconectando...")
            handler_recconection()

    client_socket.close()
    print("[Cliente] Cliente desconectado.")


if __name__ == "__main__":
    main()
