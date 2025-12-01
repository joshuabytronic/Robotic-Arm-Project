import socket

host = "192.168.125.1"
port = 8000                   # The same port as used by the server
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))
data = s.recv(1024)
print('Received', repr(data))
#Transmit to 3dinspect through modbus

s.sendall(1)

s.close()
