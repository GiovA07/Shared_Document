import socket, select
import json
import time
from utils import  send_msg, make_json, apply_op
from ot import transform

HOST = "localhost"
PORT = 7777

doc = "Bienvenidos"     # Documento compartido
revision = 0            # Numero de revision
connections = []        # Sockets conectados
op_log = []             # Historial de operaciones {"REVISION", "OP"}
id_clients = 0
last_num_seq = {}       # llevo el numero de la ultima operacion mandada de cada cliente {"ID_client" : num_seq}

SNAPSHOT_FILE = "snapshot.json"

# ====== Archivo de estado (snapshot) ======
def save_snapshot():
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json_data = {"DOC": doc, "REVISION": revision, "LOG": op_log, "LAST_NUM_SEQ": last_num_seq, "ID_CLIENTS": id_clients}
        json.dump(json_data, f)


def load_snapshot():
    global doc, revision, op_log, last_num_seq, id_clients
    try:
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            doc = state["DOC"]
            revision = state["REVISION"]
            op_log = state["LOG"]
            id_clients = int(state["ID_CLIENTS"])
            
            str_last_seq = state["LAST_NUM_SEQ"]
            last_num_seq = {int(k): int(v) for k, v in str_last_seq.items()}

            print(f"[Servidor] Snapshot cargado: rev={revision}, len(doc)={len(doc)}")
    except FileNotFoundError:
        print("[Servidor] No hay snapshot previo.")
    except Exception:
        print(f"[Servidor] Error cargando snapshot.")

# ====== Envio de mensajes / helpers ======
def send_initial_document(sock):
    global id_clients
    json_data = make_json(type="DOC_TYPE", rev=revision, doc=doc)
    
    id_clients += 1
    json_data["ID"] = id_clients
    
    send_msg(sock, json_data)
    print(f"[Servidor] Documento inicial enviado a cliente {id_clients}")


# ====== comunicacion con clientes ======
def send_ack(sock):
    try:
        data = make_json(type="ACK", rev=revision)
        send_msg(sock, data)
    except:
        print("[Servidor] Error al enviar ack")
        close_connection(sock)


# Manda la operacion realizada a todos los clientes (excepto el que la envio)
def broadcast (msg, origin_sock):
    for sock in list(connections):
        if sock == server_socket:
            continue

        # el que envio la op recibe solo un ACK
        if sock == origin_sock:
                send_ack(sock)
                continue
        try:
            send_msg(sock, msg)
        except:
            print("[Server] Error al enviar a cliente.")
            close_connection(sock)

def close_connection(client_socket):
    client_socket.close()

    if client_socket in connections:
        connections.remove(client_socket)
    
    print("[Servidor] Cliente desconectado")

# ====== Eventos ======
def handle_new_connection():
    global connections

    sockfd, addr = server_socket.accept()
    connections.append(sockfd)
    print(f"[Servidor] Nueva Conexion desde {addr}")

def handle_client(sock):
    global doc, revision, op_log, connections

    try:
        data = sock.recv(4096)
        if not data:
            close_connection(sock)
            return

        if data:
            msg = json.loads(data.decode("utf-8").strip())
            msg_type = msg.get("TYPE")
            if msg_type == "GET_DOC":
                send_initial_document(sock)
            elif msg_type == "OPERATOR":
                # Simulamos latencia
                time.sleep(10)
                op = msg.get("OP")
                base_revision = msg.get("REVISION")
                if op is None:
                    send_ack(sock)
                    return
                id_op = op.get("ID", 0)
                seq_num_op = op.get("SEQ_NUM", -1)
                prev_seq = last_num_seq.get(id_op, -1)

                if prev_seq < seq_num_op:
                    last_num_seq[id_op] = seq_num_op
                else:
                    print("Operacion ya recibida")
                    send_ack(sock)
                    return

                print("[Cliente] Operacion :", op, "BASE_REVISION:", base_revision)

                # aplicar transformador
                for operation in op_log:
                    if operation.get("REVISION") > base_revision:
                        op = transform(op, operation.get("OP"))
                        if op is None:
                            print("[Server] Operacion anulada por OT. Envia solo ACK.")
                            send_ack(sock)
                            return

                # aplicar operacion al documento
                new_doc = apply_op(doc, op)

                if new_doc != doc:
                    doc = new_doc
                    revision = revision + 1
                    op_log.append({"REVISION": revision, "OP": op})
                    save_snapshot()

                    print(f"[Servidor] Nuevo documento: {new_doc}")
                    print(f"[Servidor] Nueva revisión: {revision}")

                    operator_msg = make_json(type="OPERATOR", rev=revision, op=op)
                    broadcast(operator_msg, sock)
                else:
                    # No cambio el documento (delete fuera de rango)
                    send_ack(sock)
                    print("[Server] La operacion no cambio el documento. IGNORADA.")

            elif msg_type == "GET_LOG":                
                ops = op_log
                reply = {
                    "TYPE": "LOG_RESTORAGE",
                    "REVISION": revision,
                    "OPERATIONS": ops
                }
                print(f"reply revision: {reply["REVISION"]}")
                send_msg(sock, reply)
            else:
                print(f"[Server] El tipo del mensaje no coincide {msg_type}")
    except:
        print("[Server] Error con cliente. ")
        close_connection(sock)


def main():
    global server_socket
    
    load_snapshot()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    connections.append(server_socket)

    print(f"[Servidor] Escuchando en {HOST}:{PORT}")
    print(f"[Servidor] Documento inicial: '{doc}' (rev={revision})")

    while True:
        # Get the list sockets which are ready to be read through select
        read_sockets, write_sockets, error_sockets = select.select(connections, [], [])

        for sock in read_sockets:
            if sock == server_socket:
                handle_new_connection()
            else:
                handle_client(sock)


if __name__ == "__main__":
    main()
