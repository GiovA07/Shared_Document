from socket import *
import sys
import select
import json
from utils import transform, apply_op, send_msg, make_json

HOST = "localhost"
PORT = 7777

doc_copy = ""                   # documento local
current_revision = 0            # ultima revision conocida del servidor
pending_changes = []            # lista de mensajes JSON de operaciones locales pendientes a enviar
send_next = True                # indica si puedo mandar la proxima operacion
exit_loop = False               # booleano para cortar el ciclo principal


def send_next_operation(sock):
    global send_next, exit_loop

    if send_next and pending_changes:
        json_msg = pending_changes[0]
        try:
            send_next = False
            send_msg(sock, json_msg)
            print(f"[Cliente] Enviando operacion: {json_msg["OP"]}")
        except Exception:
            print("ERROR al enviar al servidor")
            exit_loop = True


def handle_server_message(sock):
    global doc_copy, current_revision, send_next, pending_changes, exit_loop
    
    data = sock.recv(4096)
    if not data:
        print("[Cliente] Servidor desconectado")
        exit_loop = True
        sock.close()
        return

    data_json = json.loads(data.decode("utf-8"))
    msg_type = data_json.get("TYPE")
    # ---------- Documento inicial ----------
    if msg_type == "DOC_TYPE":
        doc_copy = data_json.get("DOC", "")
        current_revision = data_json.get("REVISION", 0)

        print("[Cliente] Documento compartido inicial: ")
        print(f"  {doc_copy}")
        print(f"  Revision: {current_revision}")

    # ---------- Operacion remota ----------
    elif msg_type == "OPERATOR":
        op_msg = data_json.get("OP")
        current_revision = data_json.get("REVISION")
        print(
            f"\n[Cliente] Operacion del servidor: {op_msg} "
            f"\nrevision: {current_revision}"
        )

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
            print(f"[Cliente] Documento actualizado: ")
            print(doc_copy)
        else:
            print("[Cliente] Operacion remota anulada, no se aplica.")

    # ---------- ACK ----------
    elif msg_type == "ACK":
        # mandar otra operacion y desencolar de lista pendientes
        current_revision = data_json.get("REVISION")
        op = pending_changes.pop(0)
        print(f"\n[Cliente] ACK recibido para: {op["OP"]})")

        # si todavia queda otra pendiente, actualizo su revision base
        if pending_changes:
            pending_changes[0]["REVISION"] = current_revision

        send_next = True
        send_next_operation(sock)

    else:
        print("[Cliente] Mensaje no valido enviado desde el servidor:", data_json)



def operations(sock, cmd, pos , msg = None):
    global doc_copy, current_revision, pending_changes 

    op = {"KIND": cmd,"POS": pos}
    
    if cmd == "delete" and msg is not None:
        print("Error delete <pos> <msg> INVALIDO")
        return
    
    if msg is not None:
        # id del cliente, solo te sirve localmente
        op["ID"] = sock.getsockname()[1]
        op["MSG"] = msg

    doc_copy = apply_op(doc_copy, op)
    print(f"\n[Cliente] Documento local: {doc_copy}")
    # Mensaje JSON para enviar al servidor
    json_op = make_json(type="OPERATOR", rev=current_revision, op=op)
    pending_changes.append(json_op)
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
    if (cmd == "insert" 
        and len(input_parts) >= 2 and len(input_parts) <= 3 and input_parts[1].isdigit()):

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
        read, _, _ = select.select(socket_list, [], [])
    
        for sock in read:
            if sock == s:
                handle_server_message(s)
            else:
                handle_client_input(s)

    s.close()
    print("[Cliente] Cliente desconectado.")


if __name__ == "__main__":
    main()