import socket, select
import json
import time
from utils import send_msg, make_json, apply_op, op_is_none
from ot import transform

HOST = "localhost"
PORT = 7777

doc = "Bienvenidos"
revision = 0
connections = []
op_log = [] 
id_clients = 0
last_num_seq = {}

SNAPSHOT_FILE = "snapshot.json"

# ===== snapshot =====
def save_snapshot():
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json_data = {
            "DOC": doc,
            "REVISION": revision,
            "LOG": op_log,
            "LAST_NUM_SEQ": last_num_seq,
            "ID_CLIENTS": id_clients
        }
        json.dump(json_data, f)

def load_snapshot():
    global doc, revision, op_log, last_num_seq, id_clients
    try:
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

        doc = state["DOC"]
        revision = int(state["REVISION"])
        op_log = state.get("LOG", [])
        id_clients = int(state.get("ID_CLIENTS", 0))

        str_last_seq = state.get("LAST_NUM_SEQ", {})
        last_num_seq = {int(k): int(v) for k, v in str_last_seq.items()}

        print(f"[Servidor] Snapshot cargado: rev={revision}, len(doc)={len(doc)}")
    except FileNotFoundError:
        print("[Servidor] No hay snapshot previo.")
    except Exception as e:
        print(f"[Servidor] Error cargando snapshot: {e}")


# ===== helpers =====
def send_initial_document(sock):
    global id_clients
    id_clients += 1

    json_data = make_json(type="DOC_TYPE", rev=revision, doc=doc)
    json_data["ID"] = id_clients

    send_msg(sock, json_data)
    print(f"[Servidor] Documento inicial enviado a cliente {id_clients}")

def send_ack(sock):
    try:
        data = make_json(type="ACK", rev=revision)
        send_msg(sock, data)
    except Exception as e:
        print(f"[Servidor] Error al enviar ACK: {e}")
        close_connection(sock)

def close_connection(client_socket):
    if client_socket not in connections:
        return
    
    connections.remove(client_socket)
    try:
        client_socket.close()
    except:
        pass

    print("[Servidor] Cliente desconectado")

def broadcast(msg, origin_sock):
    for s in list(connections):
        if s == server_socket:
            continue
        if s == origin_sock:
            send_ack(s)
            continue
        try:
            send_msg(s, msg)
        except:
            print("[Servidor] Error al enviar a cliente.")
            close_connection(s)


# ===== eventos =====
def handle_new_connection():
    sockfd, addr = server_socket.accept()
    connections.append(sockfd)
    print(f"[Servidor] Nueva Conexion desde {addr}")

def handle_get_log(sock, msg):
    rev_cliente = int(msg.get("REVISION", 0))
    id_cliente = int(msg.get("ID", -1))

    ops = []
    for entry in op_log:
        if entry["REVISION"] > rev_cliente:
            ops.append(entry)

    print(f"Las operaciones en el log antes de {rev_cliente} son {ops}")
    reply = {
        "TYPE": "LOG_RESTORAGE",
        "REVISION": revision,
        "OPERATIONS": ops
    }
    print(f"[Servidor] LOG_RESTORAGE -> cliente {id_cliente}, desde rev {rev_cliente}, envio {len(ops)} ops, server_rev={revision}")
    send_msg(sock, reply)

def handle_operator(sock, msg):
    global doc, revision, op_log

    time.sleep(10)          #Latencia

    op = msg.get("OP")
    base_revision = int(msg.get("REVISION", 0))

    # TODO: PODEMOS BORRAR ESTO CREO
    if op is None:
        send_ack(sock)
        return

    id_op = int(op.get("ID", 0))
    seq_num_op = int(op.get("SEQ_NUM", -1))
    prev_seq = last_num_seq.get(id_op, -1)

    if prev_seq < seq_num_op:
        last_num_seq[id_op] = seq_num_op
    else:
        print("[Servidor] Operacion duplicada, ACK para actualizar cliente")
        send_ack(sock)
        return

    print("[Cliente] Operacion:", op, "BASE_REVISION:", base_revision)

    # si la op ya es "None" entonces mandamos ack directamente
    if op_is_none(op):
        send_ack(sock)
        return

    # transform contra las operaciones en log con base_revision mayor
    for entry in op_log:
        if entry.get("REVISION", 0) > base_revision:
            op = transform(op, entry.get("OP"))

            # TODO: ver si borrarlo
            if op_is_none(op):
                send_ack(sock)
                return

    # aplicar
    new_doc = apply_op(doc, op)

    if new_doc != doc:
        doc = new_doc
        revision += 1
        op_log.append({"REVISION": revision, "OP": op})
        save_snapshot()

        print(f"[Servidor] Nuevo documento: {doc}")
        print(f"[Servidor] Nueva revisión: {revision}")

        operator_msg = make_json(type="OPERATOR", rev=revision, op=op)
        broadcast(operator_msg, sock)
    else:
        send_ack(sock)
        print("[Servidor] La operación no cambió el documento.")


def handle_client(sock):
    try:
        data = sock.recv(4096)
    except Exception as e:
        print(f"[Servidor] Error con cliente: {e}")
        close_connection(sock)
        return

    if not data:
        close_connection(sock)
        return
    msg = json.loads(data.decode("utf-8").strip())
    msg_type = msg.get("TYPE")
    if msg_type == "GET_DOC":
        send_initial_document(sock)
    elif msg_type == "OPERATOR":
        handle_operator(sock, msg)
    elif msg_type == "GET_LOG":
        handle_get_log(sock, msg)
    else:
        print(f"[Servidor] Tipo de mensaje invalido: {msg_type}")

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
        read_sockets, _, _ = select.select(connections, [], [])
        for s in read_sockets:
            if s == server_socket:
                handle_new_connection()
            else:
                handle_client(s)

if __name__ == "__main__":
    main()
