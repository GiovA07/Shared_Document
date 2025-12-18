#!/usr/bin/env bash
# Cliente 3: se cae, hace operaciones offline, espera, reconecta
sleep 4
echo "insert 0 Q"
echo "crash"

# ahora offline: hacemos un par de comandos (quedan en pending local)
sleep 0.3
echo "insert 1 W"
sleep 0.3
echo "delete 0"

# esperar para que otros clientes avancen y el server acumule log
sleep 15

# reconectar y dejar tiempo para GET_LOG + transforms + enviar pendientes (latencia 3s)
echo "reconnect"
sleep 5
echo "insert 0 R"
sleep 30

echo "exit"
