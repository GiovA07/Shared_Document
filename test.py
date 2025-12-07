import socket
import json
import time

HOST = "127.0.0.1"
PORT = 7777


def receive_full_json(sock):
    """Ayuda a recibir la respuesta completa del servidor"""
    try:

        data = sock.recv(4096)
        if not data: return None
        return json.loads(data.decode('utf-8'))
    except Exception as e:
        print(f"Error recibiendo: {e}")
        return None

def run_test():
    print("--- INICIANDO TEST DE CONFLICTO OT ---")

    # 1. Conectar Cliente A y Cliente B
    client_a = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_a.connect((HOST, PORT))
    init_a = receive_full_json(client_a)
    print(f"[Cliente A] Conectado. Doc actual: '{init_a['DOC']}' (Rev: {init_a['REVISION']})")

    client_b = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_b.connect((HOST, PORT))
    init_b = receive_full_json(client_b)
    print(f"[Cliente B] Conectado. Doc actual: '{init_b['DOC']}' (Rev: {init_b['REVISION']})")

    base_revision = init_a['REVISION'] # Debería ser 0

    # ---------------------------------------------------------
    # ESCENARIO DE CONFLICTO (Insert vs Insert)
    # Doc original: "Bienvenidos"
    # Cliente A: Quiere insertar "HOLA " al principio (pos 0).
    # Cliente B: Quiere insertar "CHAU " al principio (pos 0).
    # ---------------------------------------------------------

    # 2. Cliente A envía su operación primero
    op_a = {
        "TYPE": "OPERATOR",
        "REVISION": base_revision, # Rev 0
        "OP": {"KIND": "delete", "POS": 2}
    }
    print(f"\n[Cliente A] Enviando: Insertar 'HOLA ' en 0 (Basado en Rev {base_revision})")
    client_a.send(json.dumps(op_a).encode('utf-8'))
    
    # Damos un pequeño respiro para asegurar que el servidor procese a A primero
    # y aumente su revisión interna a 1.
    time.sleep(0.1) 

    # 3. Cliente B envía su operación AHORA (pero con REVISIÓN VIEJA)
    # Esto forzará al servidor a usar tii()
    op_b = {
        "TYPE": "OPERATOR",
        "REVISION": base_revision, # SIGUE ENVIANDO 0 (STALE)
        "OP": {"KIND": "delete", "POS": 2}
    }
    print(f"[Cliente B] Enviando: Insertar 'CHAU ' en 0 (Basado en Rev {base_revision})")
    print(f"[Cliente B] (!) Esto debe causar conflicto porque el servidor ya debería ir por Rev {base_revision + 1}")
    client_b.send(json.dumps(op_b).encode('utf-8'))

    # 4. Verificamos el resultado final esperando el broadcast en Cliente A
    # El servidor debería mandar el ACK de B transformado
    
    print("\n--- Esperando respuesta del servidor... ---")
    
    # Leemos lo que llega a A (debería ser el update de B transformado)
    # Nota: A recibió primero su propio ACK, y luego recibirá el de B.
    # Vamos a leer un par de veces para limpiar el buffer
    try:
        response_1 = receive_full_json(client_a) # ACK de A
        print("Recive A")
        response_2 = receive_full_json(client_b) # ACK de B (Transformado)
        print("Recive B")
        
        print(f"Respuesta final recibida en A: {response_2}")
        
        if response_2 and response_2.get("TYPE") == "OPERATOR":
            op_final = response_2.get("OP")
            print(f"\n[RESULTADO] La operación de B fue transformada a: {op_final}")
            
            if op_final["POS"] == 0:
                print("Lógica TII aplicada: Se mantuvo en 0 (o ganó prioridad).")
                print("Documento final esperado: 'CHAU HOLA Bienvenidos'")
            elif op_final["POS"] > 0:
                print(f"Lógica TII aplicada: Se movió a {op_final['POS']}.")
                print("Documento final esperado: 'HOLA CHAU Bienvenidos'")
    except:
        print("No se pudo leer la respuesta final o timeout.")

    client_a.close()
    print("cliente cerrado")
    client_b.close()
    print("cliente cerrado B")
    

if __name__ == "__main__":
    run_test()