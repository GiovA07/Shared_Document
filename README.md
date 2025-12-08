# Shared_Document (Python + Operational Transformation)

Implementamos una aplicación distribuida de edición colaborativa:

- Un servidor central encargado del estado del documento, versiones y log de operaciones.
- Pueden conectarse multiples clientes para editar el documento.

- un algoritmo de Transformaciones Operacionales (Operational Transform) para resolver conflictos y asegurar la convergencia del documento.

La edicion soporta las operaciones:

- insert(c, p) – insertar carácter en posición p
- delete(p) – eliminar carácter en posición p

  

A su vez maneja revisiones (REVISION) y operaciones ocumuladas (OP).

  
# Protocolo de mensajes con TCP

1. Mensaje inicial, documento actual.

  
```json
	{
	"TYPE": "DOC_TYPE",
	"DOC": " ",
	"REVISION": 0
	}
```

  

2. Envio de operaciones

  
```json
{
"TYPE": "OPERATOR",
"REVISION": 0,
"OP": {
	"KIND": "insert",
	"POS": 3,
	"MSG": "X"
	}
}
```

  

3. Broadcast del servidor (operacion que se realizo)
```json
{
	"TYPE": "OPERATOR",
	"REVISION": 0,
	"OP": {
		"KIND": "delete",
		"POS": 2
		}
}
```
  

4. ACK al cliente origen (quien envio la operacion)
```json
{
	"TYPE": "ACK",
	"REVISION": 1
}
```

  

# Algoritmo de transformacion OT

Caso Acción OT

insert vs insert Ajustar posiciones según cuál va primero

insert vs delete La delete puede desplazar la posición del insert

delete vs insert Similar al anterior

delete vs delete Si ambas borran el mismo carácter → NoOp

  

# Como Ejecutar

1. Iniciar servidor
```python
python3 server.py
```
  
2. Iniciar uno o mas clientes
```python
python3 client.py
```
  

## Comandos diponibles

| Comando 			  | Operacion |
|---------------------|---------------------------------------------|
| insert pos caracter | Inserta el caracter en la posición indicada |
| insert pos 		  | Inserta un espacio							|
| delete pos		  | Elimina el carácter en la posición indicada	|
| exit				  | Cierra el cliente							|


