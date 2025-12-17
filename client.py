from socket import *
import sys
import select
import json
import time
from utils import send_msg, make_json, apply_op, op_is_none
from ot import transform


HOST = "localhost"
PORT = 7777

class Pending:
    base_rev: int
    op: dict      # {"KIND","POS","MSG","ID","SEQ_NUM"}

    def __init__(self, base_rev, op):
        self.base_rev = base_rev
        self.op = op

class Client:
    def __init__(self):
        self.sock = None
        self.client_buffer = "" 

        self.client_id = -1
        self.server_rev = 0
        self.doc = ""

        self.pending = []
        self.next_seq = 0
        self.waitting_ack = False
        self.offline = False

        self.exit_loop = False


    def connect(self):
        s = socket(AF_INET, SOCK_STREAM)
        s.connect((HOST, PORT))

        # id del cliente
        self.client_id = s.getsockname()[1]
        
        self.sock = s
        self.offline = False
        
        send_msg(self.sock, {"TYPE": "GET_DOC"})


    def disconnect(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except:
                pass
        self.sock = None
        self.offline = True
        self.waitting_ack = False
        print("[Cliente] Desconectado.")

    def reconnect_to_server(self):
        try:
            s = socket(AF_INET, SOCK_STREAM)
            s.settimeout(2.0)
            s.connect((HOST, PORT))
            s.settimeout(None)

            self.sock = s
            self.offline = False
            self.waitting_ack = False

            msg = {
                "TYPE": "GET_LOG",
                "REVISION": self.server_rev,
                "ID": self.client_id
            }
            
            send_msg(self.sock, msg)
            print("[Cliente] Reconexion exitosa. Sincronizando...")
        except Exception:
            print("[Cliente] No se pudo reconectar al servidor")
    
    def send_next_operation(self):
        if self.offline or self.sock is None:
            return
        if self.waitting_ack:
            return
        if not self.pending:
            return

        msg = make_json(type="OPERATOR", rev=self.server_rev, op=self.pending[0].op)
        try:
            send_msg(self.sock, msg)
            self.waitting_ack = True
            print(f"\n[Cliente] Enviando operacion: {self.pending[0].op}")
        except Exception:
            print("[Cliente] Error al enviar operacion.")
            self.disconnect()

    def handle_server_message(self):
        try:
            data = self.sock.recv(4096)
        except:
            data = None

        if not data:
            print("[Cliente] Servidor desconectado")
            self.disconnect()
            return

        self.client_buffer += data.decode("utf-8")

        while "\n" in self.client_buffer:
            msg_str, resto = self.client_buffer.split("\n", 1)
            self.client_buffer = resto
            msg_str = msg_str.strip()
            if not msg_str:
                continue
            try:
                data_json = json.loads(msg_str)
                self.process_server_msg(data_json)
            except:
                print("[Cliente] Invalid JSON")

    def process_server_msg(self, data_json):
        msg_type = data_json.get("TYPE")

        if msg_type == "DOC_TYPE":
            self.doc = data_json.get("DOC", "")
            self.server_rev = data_json.get("REVISION", 0)

            print("[Servidor] Documento compartido inicial:")
            print(f"  {self.doc}")
            print(f"Revision: {self.server_rev}")

        elif msg_type == "LOG_RESTORAGE":
            self.handle_log_restorage(data_json)

        elif msg_type == "OPERATOR":
            self.handle_remote_operation(data_json)

        elif msg_type == "ACK":
            self.handle_ack(data_json)

        else:
            print("[Cliente] Mensaje no valido enviado desde el servidor:", data_json)

    def transform_remote_against_pending(self, remote_op):
        remote_op = remote_op.copy()
        for p in self.pending:
            local_op = p.op
            if op_is_none(remote_op):
                break
            if op_is_none(local_op):
                continue
            p.op = transform(local_op.copy(), remote_op)
            remote_op = transform(remote_op.copy(), local_op)
        return remote_op
    
    def handle_log_restorage(self, data_json):
        operations_entry = data_json.get("OPERATIONS", [])
        server_final_rev = data_json.get("REVISION", self.server_rev)

        print("[Cliente] Sincronizando con operaciones del servidor...")

        # filtra ops realmente nuevas
        ops_to_apply = []
        for entry in operations_entry:
            entry_op = entry.get("OP")
            if self.pending and entry_op.get("ID") == self.client_id and entry_op.get("SEQ_NUM") == self.pending[0].op["SEQ_NUM"]:
                self.pending.pop(0)

            if  entry_op.get("ID") != self.client_id:
                ops_to_apply.append(entry)

        # aplico una por una, haciendo OT contra las operaciones pendientes
        for entry in ops_to_apply:
            remote_op = entry.get("OP")
            if op_is_none(remote_op):
                continue
            
            remote_op = self.transform_remote_against_pending(remote_op)
            #TODO: puede cambiarse
            if not op_is_none(remote_op):
                self.doc = apply_op(self.doc, remote_op)

        self.server_rev = server_final_rev
        print(f"[Cliente] Sincronización completa. Documento:\n  '{self.doc}'")
        print(f"[Cliente] Revisión actual: {self.server_rev}\n")

        self.waitting_ack = False
        self.send_next_operation()



    def handle_remote_operation(self, data_json):
        remote_op = data_json.get("OP")
        self.server_rev = data_json.get("REVISION", self.server_rev)

        print(f"\n[Servidor] Operacion remota: {remote_op} Revision: {self.server_rev}\n")

        # transformar operacion remota con las op pendientes
        remote_op = self.transform_remote_against_pending(remote_op)

        # aplico remota si no es None
        if not op_is_none(remote_op):
            self.doc = apply_op(self.doc, remote_op)
            print(f"[Cliente] Documento actualizado:\n {self.doc}")
        else:
            print("[Cliente] Operacion remota anulada (KIND='None'), no se aplica.")


    def handle_ack(self, data_json):
        if not self.pending:
            print("[Cliente] ACK inesperado (no hay operaciones pendientes)")
            self.waitting_ack = False
            return

        self.server_rev = data_json.get("REVISION", self.server_rev)
        id_c = data_json.get("ID")
        seq_num_r = data_json.get("SEQ_NUM")
        expected = self.pending[0]
        if (id_c == self.client_id and seq_num_r == expected.op.get("SEQ_NUM")):
            confirmed = self.pending.pop(0)
            print(f"[Cliente] ACK recibido para: {confirmed.op}")
    
            self.waitting_ack = False
            self.send_next_operation()
        
        print("[Cliente] ACK invalido: lo ignoro y reintento enviar la operacion.")
        self.waitting_ack = False
        self.send_next_operation()


    def execute_operation(self, kind, pos, msg=None):
        
        op = {"KIND": kind, "POS": pos, "ID": self.client_id, "SEQ_NUM": self.next_seq}
        self.next_seq += 1
        if msg is not None:
            op["MSG"] = msg

        # aplico localmente
        self.doc = apply_op(self.doc, op)
        print(f"\n[Cliente] Documento local:\n {self.doc}")

        self.pending.append(Pending(self.server_rev, op))

        if not self.offline:
            self.send_next_operation()


    def handle_client_input(self):
        user_input = sys.stdin.readline().strip()

        if user_input == "exit":
            self.exit_loop = True
            return

        if user_input == "crash":
            print("\n[Cliente] Simulando desconexion forzada...")
            self.disconnect()
            print("[Cliente] Desconectado. Usa 'reconnect' para reconectar.\n")
            return

        if user_input == "reconnect":
            if not self.offline:
                print("[Cliente] Ya estas conectado")
            else:
                self.reconnect_to_server()
            return

        parts = user_input.split(" ")
        if not parts or not parts[0]:
            print("[Cliente] Comando vacio")
            return

        cmd = parts[0]
        if cmd == "insert" and len(parts) >= 2 and parts[1].isdigit():
            pos = int(parts[1])
            msg_text = " " if len(parts) == 2 else parts[2]
            self.execute_operation("insert", pos, msg_text)
            return

        if cmd == "delete" and len(parts) == 2 and parts[1].isdigit():
            pos = int(parts[1])
            self.execute_operation("delete", pos)
            return

        print("[Cliente] Comando invalido.")
        self.print_help()


    def print_help(self):
        print("\nComandos disponibles:")
        print("  insert <pos> <texto>  - Insertar texto en posicion")
        print("  insert <pos>          - Insertar espacio en posicion")
        print("  delete <pos>          - Eliminar caracter en posicion")
        print("  crash                 - Simular desconexion")
        print("  reconnect             - Reconectar al servidor")
        print("  exit                  - Salir del programa\n")

    def run(self):
        self.connect()
        self.print_help()

        while not self.exit_loop:
            readers = [sys.stdin]
            if not self.offline and self.sock is not None and self.sock.fileno() >= 0:
                readers.append(self.sock)

            read, _, _ = select.select(readers, [], [], 1.0)

            for r in read:
                if self.sock is not None and r == self.sock:
                    self.handle_server_message()
                else:
                    self.handle_client_input()

        self.disconnect()
        print("[Cliente] Cliente desconectado.")


if __name__ == "__main__":
    Client().run()