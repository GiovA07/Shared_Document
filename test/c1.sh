#!/usr/bin/env bash
sleep 4
echo "insert 0 A"
echo "insert 1 B"
sleep 6             # Espera que lleguen los ack
echo "delete 0"
sleep 4.5
echo "insert 0 X"
sleep 20
echo "exit"

