# Shared_Document (Python + Operational Transformation)

Este proyecto implementa una aplicación distribuida de "edición colaborativa de documentos" utilizando un modelo cliente–servidor y el algoritmo de Transformaciones Operacionales (OT) para resolver conflictos de edición concurrente.

## Descripción general

La arquitectura del sistema se compone de:

- Un **servidor central**, responsable de:
  - Mantener el estado actual del documento.
  - Llevar un número de revisión (`REVISION`).
  - Almacenar un log de operaciones aplicadas.

- Múltiples **clientes**, que pueden conectarse concurrentemente y editar el documento compartido.

- Un algoritmo de **Operational Transformation** el cual garantiza:
  - Convergencia del documento en todos los nodos (**clientes**).
  - Preservación de las posiciones de las operaciones.
  - Resolución de conflictos.

### Operaciones soportadas

| Comando 			  | Operacion |
|---------------------|---------------------------------------------|
| insert pos caracter | Inserta el caracter en la posición indicada |
| insert pos 		  | Inserta un espacio							|
| delete pos		  | Elimina el carácter en la posición indicada	|
| exit				  | Cierra el cliente							|

Cada operación realizada en un cliente se envía junto con una **revisión base**, que indica el estado del documento sobre el cual fue generada.


## Ejecución del sistema

1. Iniciar servidor
```python
python3 server.py
```
  
2. Iniciar uno o mas clientes
```python
python3 client.py
```

# Protocolo de mensajes con TCP

1. Mensaje inicial, documento actual.
Al conectarse, el servidor envía al cliente el estado actual del documento:
  
```json
	{
	"TYPE": "DOC_TYPE",
	"DOC": "Bienvenidos",
	"REVISION": 0
	}
```
Este mensaje actúa como una "snapshot" del documento indicando el numero de revisión hasta el momento.
  

2. Envío de una operación desde el cliente

```json
{
"TYPE": "OPERATOR",
"REVISION": 0,
"OP": {
	"KIND": "insert",
	"POS": 3,
	"MSG": "X",
	"ID": 70133
	}
}
```
- REVISION indica la revisión base sobre la cual se generó la operación.
- ID identifica al cliente y se utiliza para desempatar inserciones concurrentes.

  

3. Broadcast de una operación desde el servidor
El servidor aplica la operación (luego de transformarla) y la reenvía a todos los clientes:
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
El servidor responde al cliente que originó la operación.
El ACK confirma que la operación fue agregada con exito al documento global.
```json
{
	"TYPE": "ACK",
	"REVISION": 1
}
```

  

# Algoritmo de transformación OT
En est sistema implementamos un algoritmo de Operational Transformation para resolver conflictos entre operaciones concurrentes.


## Reglas de transformación

**Insert vs Insert**

	- Si pos_1 < pos_2 		-> no se modifica op1.
	- Si pos_1 > pos_2 		-> pos_1 := pos_1 + 1.
	- Si pos_1 == pos_2 	-> se desempata usando el ID del cliente  (ESTO DEBERIAMOS REVISARLO BIEN)

**Insert vs Delete**

	- Si pos_1 <= pos_2 	-> no se modifica op1.
	- Si pos_1 > pos_2 		-> pos_1 := pos_1 - 1.

**Delete vs Insert**

	- Si pos_1 < pos_2 		-> no se modifica op1.
	- Si pos_1 >= pos_2 	-> pos_1 := pos_1 + 1.

**Delete vs Delete**

	- Si pos_1 < pos_2 		-> no se modifica op1.
	- Si pos_1 > pos_2 		-> pos_1 := pos_1 - 1.
	- Si pos_1 == pos_2 	-> la operación se anula (None).


## Aplicamos las operaciones
Luego de la transformación, las operaciones se aplican secuencialmente al documento mediante la función apply_op(doc, op).


# Tolerancia a fallas
