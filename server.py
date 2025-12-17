import socket, select
import json
import time
from utils import send_msg, make_json, apply_op, op_is_none
from ot import transform

class Server:
    def __init__(self, host="localhost", port= 7777):
        self.host = host
        self.port = port
        self.server_socket = None
        self.connections = []
        self.buffers = {} 

        self.doc = "Bienvenidos"
        self.revision = 0
        self.op_log = []
        self.last_num_seq = {} # {client_id: last_seq_num}
        self.snapshot_file = "snapshot.json"
        
        self.load_snapshot()

    # ===== snapshot =====
    def save_snapshot(self):
        with open(self.snapshot_file, "w", encoding="utf-8") as f:
            json_data = {
                "DOC": self.doc,
                "REVISION": self.revision,
                "LOG": self.op_log,
                "LAST_NUM_SEQ": self.last_num_seq,
            }
            json.dump(json_data, f)

    def load_snapshot(self):
        try:
            with open(self.snapshot_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            self.doc = state.get("DOC", "")
            self.revision = int(state.get("REVISION", 0))
            self.op_log = state.get("LOG", [])
            str_last_seq = state.get("LAST_NUM_SEQ", {})
            self.last_num_seq = {int(k): int(v) for k, v in str_last_seq.items()}

            print(f"[Servidor] Snapshot cargado: rev={self.revision}, len(doc)={len(self.doc)}")
        except FileNotFoundError:
            print("[Servidor] No hay snapshot previo.")
        except Exception as e:
            print(f"[Servidor] Error cargando snapshot: {e}")

    # ===== helpers =====
    def send_initial_document(self, sock):
        json_data = make_json(type="DOC_TYPE", rev=self.revision, doc=self.doc)
        send_msg(sock, json_data)
        print("[Servidor] Documento inicial enviado a cliente")

    def send_ack(self, sock, op):
        try:
            data = make_json(type="ACK", rev=self.revision)
            data["ID"] = op.get("ID")
            data["SEQ_NUM"] = op.get("SEQ_NUM")
            send_msg(sock, data)
        except Exception as e:
            print(f"[Servidor] Error al enviar ACK: {e}")
            self.close_connection(sock)

    def close_connection(self, client_socket):
        if client_socket not in self.connections:
            return

        self.connections.remove(client_socket)
        try:
            client_socket.close()
        except:
            pass
        print("[Servidor] Cliente desconectado")

    def broadcast(self, msg, origin_sock, op):
        for s in list(self.connections):
            if s == self.server_socket:
                continue
            if s == origin_sock:
                self.send_ack(s, op)
                continue
            try:
                send_msg(s, msg)
            except:
                print("[Servidor] Error al enviar a cliente.")
                self.close_connection(s)

    # ===== eventos =====
    def handle_new_connection(self):
        sockfd, addr = self.server_socket.accept()
        self.connections.append(sockfd)
        print(f"[Servidor] Nueva Conexion desde {addr}")

    def handle_get_log(self, sock, msg):
        rev_cliente = int(msg.get("REVISION", 0))
        id_cliente = int(msg.get("ID", -1))

        ops = []
        for entry in self.op_log:
            if entry["REVISION"] > rev_cliente:
                ops.append(entry)

        print(f"Las operaciones en el log antes de {rev_cliente} son {ops}")
        reply = {
            "TYPE": "LOG_RESTORAGE",
            "REVISION": self.revision,
            "OPERATIONS": ops
        }
        print(f"[Servidor] LOG_RESTORAGE -> cliente {id_cliente}, desde rev {rev_cliente}, envio {len(ops)} ops, server_rev={self.revision}")
        send_msg(sock, reply)

    def handle_operator(self, sock, msg):
        time.sleep(10)          #Latencia
        op = msg.get("OP")
        base_revision = int(msg.get("REVISION", 0))

        # TODO: PODEMOS BORRAR ESTO CREO
        if op_is_none(op):
            self.send_ack(sock, op)
            return

        id_op = int(op.get("ID", 0))
        seq_num_op = int(op.get("SEQ_NUM", -1))
        prev_seq = self.last_num_seq.get(id_op, -1)

        if prev_seq < seq_num_op:
            self.last_num_seq[id_op] = seq_num_op
        else:
            print("[Servidor] Operacion duplicada, ACK para actualizar cliente")
            self.send_ack(sock, op)
            return

        print("[Cliente] Operacion:", op, "BASE_REVISION:", base_revision)

        # si la op ya es "None" entonces mandamos ack directamente
        if op_is_none(op):
            self.send_ack(sock, op)
            return

        # transform contra las operaciones en log con base_revision mayor
        for entry in self.op_log:
            if entry.get("REVISION", 0) > base_revision:
                op = transform(op, entry.get("OP"))

                # TODO: ver si borrarlo
                if op_is_none(op):
                    self.send_ack(sock, op)
                    return

        # aplicar
        new_doc = apply_op(self.doc, op)

        if new_doc != self.doc:
            self.doc = new_doc
            self.revision += 1
            self.op_log.append({"REVISION": self.revision, "OP": op})
            self.save_snapshot()

            print(f"[Servidor] Nuevo documento: {self.doc}")
            print(f"[Servidor] Nueva revisión: {self.revision}")

            operator_msg = make_json(type="OPERATOR", rev=self.revision, op=op)
            self.broadcast(operator_msg, sock, op)
        else:
            self.send_ack(sock, op)
            print("[Servidor] La operación no cambió el documento.")


    def handle_client(self,sock):
        try:
            data = sock.recv(4096)
        except Exception as e:
            print(f"[Servidor] Error con cliente: {e}")
            self.close_connection(sock)
            return

        if not data:
            self.close_connection(sock)
            return
        msg = json.loads(data.decode("utf-8").strip())
        msg_type = msg.get("TYPE")
        if msg_type == "GET_DOC":
            self.send_initial_document(sock)
        elif msg_type == "OPERATOR":
            self.handle_operator(sock, msg)
        elif msg_type == "GET_LOG":
            self.handle_get_log(sock, msg)
        else:
            print(f"[Servidor] Tipo de mensaje invalido: {msg_type}")

    def run(self):

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.connections.append(self.server_socket)

        print(f"[Servidor] Escuchando en {self.host}:{self.port}")
        print(f"[Servidor] Documento inicial: '{self.doc}' (rev={self.revision})")

        while True:
            read_sockets, _, _ = select.select(self.connections, [], [])
            for s in read_sockets:
                if s == self.server_socket:
                    self.handle_new_connection()
                else:
                    self.handle_client(s)

if __name__ == "__main__":
    Server().run()
