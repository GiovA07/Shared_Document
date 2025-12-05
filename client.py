from socket import*
import sys
import select
import json

HOST = ''
PORT = 7777
s = socket(AF_INET, SOCK_STREAM)
s.connect((HOST, PORT))

doc_copy = " "

exit = False

#  {
#    "type": "DOC_STATE | OPERATION"
#    "doc": doc}
#    "op": {"kind": "insert", "pos": "7", "msg": "hola"},
#     "revision": 1,
#     "cliente": PORT
#   }

while not exit:
    socket_list = [sys.stdin, s]

    # Get the list sockets which are readable
    read, write, error = select.select(socket_list, [], [])

    for sock in read:
        if sock == s:
            #incoming message from remote server
            data = sock.recv(1024)
            json_str = data.decode('utf-8')
            data_json = json.loads(json_str)

            doc_copy = data_json.get("doc")
            
            if data:
                print(doc_copy)
        else:
            #user entered data by stdin
            msg = sys.stdin.readline()
            s.send(bytes(msg, "utf-8"))
            if msg.strip() == "quit":
                exit = True

s.close()