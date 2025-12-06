import socket
import json
import threading
import time

HOST = 'localhost'
PORT = 7777

# Definimos una barrera para 2 hilos. 
# Los hilos se quedarán bloqueados hasta que los 2 lleguen a este punto.
start_gate = threading.Barrier(2)

def attack_client(client_id, char_to_insert, position, operation):
    
    doc_copy = ""
    ## hago la conexion
    try:
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        print(f"[{client_id}] Conectado y listo.")
    except Exception as e:
        print(f"[{client_id}] Error conexión: {e}")
        return

    # Preparamos el mensaje pero NO lo enviamos todavía
    json_data = {
        "TYPE": "OPERATOR",
        "OP": {
            "KIND": operation,
            "POS": position,  # CONFLICTO: Ambos pelean por el inicio
            "MSG": char_to_insert
        }
    }

    payload = bytes(json.dumps(json_data), "utf-8")

    # --- PUNTO DE SINCRONIZACIÓN ---
    # El hilo espera aquí. No pasará hasta que el otro hilo también llegue aquí.
    start_gate.wait()
    # -------------------------------

    #Envío simultáneo
    s.send(payload)

    print(f"[{client_id}] ---> ENVIADO '{operation} {position} {char_to_insert}'")

    # Escuchamos qué responde el servidor para ver cómo quedó el documento
    # Leemos un par de veces para ver nuestra operación y la del otro
    s.settimeout(2) # Esperar máximo 2 segundos, salir del ciclo
    
    try:
        while True:
            data = s.recv(4096)
            if not data: break
            
            json_str = data.decode('utf-8')
            data_json = json.loads(json_str)
            msg_type = data_json.get("TYPE")    
           
            if msg_type == "DOC_TYPE":
                doc_copy = data_json.get("DOC")
                print(f"---- Document {client_id} ------ \n {doc_copy}")
                
                
                # aplico la operacion localmente 
                if operation == "delete":
                    doc_copy = doc_copy[:position] + doc_copy[position + 1:]
                else:
                    doc_copy = doc_copy[:position] + char_to_insert + doc_copy[position:]

                
                print(f"---- El {client_id}, aplico localmente {operation} en la pos {position} ------ \n {doc_copy}")  

            ## recibo operacion del servidor indica que otro cliente modifico 
            
            
            elif msg_type == "OPERATOR": 
                op_msg = data_json.get("OP")
                pos = int(op_msg.get("POS"))
                if(op_msg.get("KIND") == "insert"):
                    msg = op_msg.get("MSG")
                    doc_copy = doc_copy[:pos] + msg + doc_copy[pos:]
                else:
                    doc_copy = doc_copy[:pos] + doc_copy[pos+1:]
            else:
                print("ERROR")
              
    except socket.timeout:
        pass # Se acabó el tiempo de espera
    
    print(f"\n--- DOCUMENT {client_id} --- \n{doc_copy}")
    
    s.close()

if __name__ == "__main__":
    print("--- INICIANDO PRUEBA DE CONFLICTO SIMULTÁNEO ---")
    operation = "insert"
    pos_A     = 0
    pos_B     = 0
    print(f"Objetivo: {operation} en 'A' pos: {pos_A} y en 'B' {pos_B} al mismo tiempo.")
    
    # Creamos dos hilos
    t1 = threading.Thread(target=attack_client, args=("CLIENTE_A", "X", pos_A, operation))
    t2 = threading.Thread(target=attack_client, args=("CLIENTE_B", "S", pos_B , operation))

    t1.start()
    t2.start()

    ## Espera a que termine los procesos
    t1.join()
    t2.join()

    print("\nPrueba terminada.")