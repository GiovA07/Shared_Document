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

| Comando 			   | Operacion                                   |
|----------------------|---------------------------------------------|
| `insert pos caracter`| Inserta el caracter en la posición indicada |
| `insert pos` 		   | Inserta un espacio							 |
| `delete pos`		   | Elimina el carácter en la posición indicada |
| `exit`			   | Cierra el cliente							 |

Cada operación enviada por un cliente incluye un numero `REVISION` base, que indica
la última revisión del documento conocida por dicho cliente al momento de
generar la operación.

El servidor utiliza este valor para poder determinar con que operaciones del log
debera transformar la operación entrante antes de aplicarla al documento.

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

1. Al conectarse un cliente nuevo le envia al servidor un mensaje solcitandole el documento actual:
```json
{
  "TYPE": "GET_DOC"
}
```

3. Mensaje inicial, documento actual.
El servidor le respone con el numero de revision hasta el momento y el documento actual.  
```json
{
 "TYPE": "DOC_TYPE",
 "DOC": "Bienvenidos",
 "REVISION": 0
}
```
Este mensaje actúa como una "snapshot" del documento indicando el numero de revisión hasta el momento.
  

4. Envío de una operación desde el cliente

```json
{
 "TYPE": "OPERATOR",
 "REVISION": 0,
 "OP": {
	 "KIND": "insert",
	 "POS": 3,
	 "MSG": "X",
	 "ID": 70133,
   "SEQ_NUM": 1
	}
}

```
- REVISION indica la revisión base sobre la cual se generó la operación.
- ID identifica al cliente y se utiliza para desempatar inserciones concurrentes.


5. Broadcast de una operación desde el servidor
El servidor aplica la operación (luego de transformarla) y la reenvía a todos los clientes:
```json
{
 "TYPE": "OPERATOR",
 "REVISION": 0,
 "OP": {
      "KIND": "delete",
	    "POS": 2,
      "ID": 70133,
      "SEQ_NUM": 7
	}
}
```
  

6. ACK al cliente origen (quien envio la operacion)
El servidor responde al cliente que originó la operación.
El ACK confirma que la operación fue agregada con exito al documento global.
```json
{
 "TYPE": "ACK",
 "REVISION": 1,
 "ID": 70133,
 "SEQ_NUM": 1
}
```

7. Solicitud de sincronizacion / reconexion

Cuando un cliente el cual perdio la conexion se reconecta, solicita al servidor las operaciones que ocurrieron mientras estuvo offline:

```json
{
 "TYPE": "GET_LOG",
 "REVISION": 3,
 "ID": 70133
}
```
El campo `REVISION` le informa al servidor cuales deberian ser las operaciones a mandarle para que el cliente pueda aplicarlas y el documento quede consistente con el original.

El servidor entonces, le respondera con todas las operaciones las cuales su revisión sea mayor a la indicada:
```json
{
 "TYPE": "LOG_RESTORAGE",
 "REVISION": 6,
 "OPERATIONS": [
   { "REVISION": 4, "OP": {...} },
   { "REVISION": 5, "OP": {...} }
 ]
}
```
  

# Algoritmo de transformación OT
En est sistema implementamos un algoritmo de Operational Transformation para resolver conflictos entre operaciones concurrentes.


## Reglas de transformación

**Insert vs Insert**

- Si `pos_1 < pos_2` 		-> no se modifica op1.
- Si `pos_1 > pos_2` 		-> pos_1 := pos_1 + 1.
- Si `pos_1 == pos_2` -> se desempata usando el ID del cliente, garantizando un orden para aplicarse al documento.


**Insert vs Delete**

- Si `pos_1 <= pos_2` 	    -> no se modifica op1.
- Si `pos_1 > pos_2` 		-> `pos_1 := pos_1 - 1`.

**Delete vs Insert**

- Si `pos_1 < pos_2` 		-> no se modifica op1.
- Si `pos_1 >= pos_2` 	    -> `pos_1 := pos_1 + 1`.

**Delete vs Delete**

- Si `pos_1 < pos_2` 		-> no se modifica op1.
- Si `pos_1 > pos_2` 		-> `pos_1 := pos_1 - 1`.
- Si `pos_1 == pos_2` 	    -> la operación se anula (None).


## Aplicamos las operaciones
Luego de la transformación, las operaciones se aplican secuencialmente al documento mediante la función apply_op(doc, op).


# Tolerancia a fallas

El sistema contempla fallas tanto del lado del cliente como del servidor.

## Detección de duplicados (ID + SEQ_NUM)

Cada operación local se numera con `SEQ_NUM` creciente por cliente.
El servidor mantiene `LAST_NUM_SEQ[client_id]` y descarta operaciones duplicadas
(o reenvíos) respondiendo con `ACK` para que el cliente pueda avanzar.

Esto evita aplicar dos veces la misma operación ante retransmisiones o reconexiones.

## Persistencia del servidor (snapshot)

El servidor guarda el estado en `snapshot.json` con:

- `DOC`: documento actual
- `REVISION`: revisión global
- `LOG`: log de operaciones aplicadas con su revisión
- `LAST_NUM_SEQ`: último `SEQ_NUM` visto por cliente (deduplicación)

Al reiniciar, el servidor carga este snapshot y continúa desde ese estado.

## Fallas de clientes (offline work)

Si un cliente pierde la conexión con el servidor:
- El cliente puede continuar editando el documento localmente.
- Las operaciones se almacenan en una cola de operaciones pendientes.
- No se envían operaciones al servidor mientras el cliente esté offline.

Al reconectarse:
1. El cliente solicita al servidor las operaciones realizadas durante su ausencia
   mediante el mensaje `GET_LOG`.
2. El servidor responde con las operaciones faltantes.
3. El cliente transforma dichas operaciones contra sus operaciones locales pendientes.
4. Finalmente, el cliente envía sus operaciones locales al servidor.

## Fallas del servidor

El servidor implementa un mecanismo de persistencia mediante snapshots periódicos,
almacenando:
- El documento actual.
- El número de revisión.
- El log de operaciones aplicadas.

Ante una caída del servidor, el sistema puede restaurar el último estado del documento y continuar aceptando conexiones de clientes.