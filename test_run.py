import time
import socket
import sys
import multiprocessing
from multiprocessing import Barrier

# Importamos tu cliente. 
# Al ser multiprocessing, cada proceso tendrá sus propias variables globales de 'client'.
import client 

HOST = "localhost"
PORT = 7777

def run_client_process(barrier, name, action, param1, param2=None):
    """
    Esta función corre en un PROCESO separado.
    Tiene su propia memoria y sus propias variables globales de 'client'.
    """
    # 1. Conexión manual usando las funciones de tu cliente
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((HOST, PORT))
    except:
        print(f"[{name}] Error al conectar con el servidor.")
        return

    # 2. Hilo de escucha (para que funcione el OT y los ACKs)
    # Necesitamos escuchar en segundo plano mientras preparamos el ataque
    def escuchar():
        while not client.exit_loop:
            try:
                # Usamos TU función de manejo de mensajes
                client.handle_server_message(s)
            except:
                break
    
    listener = multiprocessing.Process(target=escuchar) # Usamos thread o process interno? 
    # Mejor usamos un Thread simple dentro de este proceso para no complicar
    import threading

    t = threading.Thread(target=escuchar)
    t.daemon = True
    t.start()

    # Esperamos un poco para recibir el estado inicial (DOC_TYPE)
    time.sleep(0.5)
    print(f"[{name}] Listo. Doc inicial: '{client.doc_copy}'")

    # 3. SINCRONIZACIÓN (Esperar al otro proceso)
    if barrier:
        barrier.wait()
    
    # 4. EJECUTAR LA ACCIÓN (Usando TUS funciones)
    # Esto modificará el client.doc_copy de ESTE proceso
    if action == "insert":
        # operations(sock, cmd, pos, msg)
        client.operations(s, "insert", param1, param2)
        print(f"[{name}] Insertó '{param2}' en {param1}")
        
    elif action == "delete":
        client.operations(s, "delete", param1)
        print(f"[{name}] Borró en {param1}")

    # 5. Esperar para ver la convergencia
    #time.sleep(2)
    time.sleep(22)
    print(f"[{name}] DOCUMENTO FINAL: '{client.doc_copy}'")
    
    # Cerramos
    client.exit_loop = True
    s.close()

# --- DEFINICIÓN DE LOS 4 TESTS ---

def test_1_insert_vs_insert(pos1, pos2, msg1, msg2):
    print("\n" + "="*40)
    print(" TEST 1: INSERT VS INSERT (CONCURRENTE)")
    print("="*40)
    
    # Barrera para 2 procesos
    barrier = Barrier(2)
    
    # Lanzamos dos procesos independientes
    p1 = multiprocessing.Process(target=run_client_process, 
                                 args=(barrier, "Clinet_1", "insert", pos1, msg1))
    p2 = multiprocessing.Process(target=run_client_process,
                                 args=(barrier, "Client_2", "insert", pos2, msg2))

    p1.start()
    p2.start()
    
    p1.join()
    p2.join()

def test_2_delete_vs_delete(pos1, pos2):
    print("\n" + "="*40)
    print(" TEST 2: IDEMPOTENCIA (DELETE VS DELETE)")
    print("="*40)
    
    barrier = Barrier(2)
    
    # Asumimos que hay texto. Intentamos borrar la pos 0 al mismo tiempo.
    p1 = multiprocessing.Process(target=run_client_process, 
                                 args=(barrier, "Clinet_1", "delete", pos1))
    p2 = multiprocessing.Process(target=run_client_process, 
                                 args=(barrier, "Clinet_2", "delete", pos2))

    p1.start()
    p2.start()
    p1.join()
    p2.join()

def test_3_ghost_index():
    print("\n" + "="*40)
    print(" TEST 3: INSERT DESPLAZA DELETE")
    print("="*40)
    
    barrier = Barrier(2)
    
    # C1 inserta 'H' en 0. C2 intenta borrar lo que estaba en 0.
    p1 = multiprocessing.Process(target=run_client_process, 
                                 args=(barrier, "Clinet_1", "insert", 0, "H"))
    p2 = multiprocessing.Process(target=run_client_process, 
                                 args=(barrier, "Clinet_2", "delete", 0))

    p1.start()
    p2.start()
    p1.join()
    p2.join()

def test_4_queue_check():
    print("\n" + "="*40)
    print(" TEST 4: TRANSFORMACIÓN LOCAL (PENDIENTES)")
    print("="*40)
    # Este es truco: Lanzamos un solo proceso cliente que:
    # 1. Manda una operación (que queda pendiente un instante)
    # 2. Recibe una externa.
    # Para simular esto con multiprocessing sin cambiar tu código es difícil,
    # así que usaremos 2 procesos pero uno disparará más tarde para actuar como "externo".
    
    # No usamos barrera aquí, queremos secuencia controlada
    
    # P1 (Víctima): Inserta 'X'
    # P2 (Atacante): Inserta 'R' muy rápido
    
    # Para este test específico, tu código client.py necesitaría ser manipulado
    # para 'retrasar' el envío y dejarlo en pendiente. 
    # Como no queremos tocar client.py, este test es mejor hacerlo manual o 
    # confiando en que si pasan el 1, 2 y 3, tu lógica de pendientes funciona.
    print("Para probar la cola de pendientes, ejecuta manualmente:")
    print("1. Desconecta internet o pausa el server.")
    print("2. Escribe 'insert 0 X' en tu cliente.")
    print("3. Reactiva y que otro cliente escriba.")
    print("(Saltando test automático para no modificar client.py)")

if __name__ == "__main__":
    # IMPORTANTE: En Windows esto es obligatorio. En Linux es buena práctica.
    multiprocessing.set_start_method('spawn', force=True)
    
    try:
        test_1_insert_vs_insert(0, 0, "X", "Y")
        time.sleep(5)
        test_1_insert_vs_insert(0, 3, "W", "W")
        time.sleep(5)
        test_2_delete_vs_delete(0, 0)
        time.sleep(5)
        test_2_delete_vs_delete(1, 3)
        #test_2_delete_vs_delete()
        #test_3_ghost_index()
        # ... puedes descomentar los otros
    except KeyboardInterrupt:
        print("Test interrumpido.")