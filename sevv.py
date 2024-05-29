import socket
import threading
import sys
from prometheus_client import start_http_server, Gauge
import psutil

class Server:
    cpu_usage = Gauge("cpu_usage", "this measures the cpu usage")
    def __init__(self):
        start_http_server(8000)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connections = {}
        self.lock = threading.Lock()
    def handle_client(self, client_socket, client_name):
        try:
            while True:
                self.cpu_usage.set(psutil.cpu_percent(interval=1))
                data = client_socket.recv(1024)
                if not data:
                    break
                recipient, message = data.decode('utf-8').split(':', 1)
                with self.lock:
                    recipient_socket = self.connections.get(recipient)
                if recipient_socket:
                    recipient_socket.send(bytes(f"{client_name}: {message}", 'utf-8'))
        except Exception as e:
            print("Error:", e)
        finally:
            with self.lock:
                del self.connections[client_name]
            client_socket.close()
            self.broadcast_active_clients()

    def broadcast_active_clients(self):
        with self.lock:
            active_clients = list(self.connections.keys())
        message = "Active Clients: " + ", ".join(active_clients)
        for connection in self.connections.values():
            connection.send(bytes( message, 'utf-8'))

    def run(self):
        self.sock.bind(('0.0.0.0', 62561))
        self.sock.listen(5)
        print('Server running ...')
        while True:
            client_socket, _ = self.sock.accept()
            client_name = client_socket.recv(1024).decode('utf-8')
            with self.lock:
                self.connections[client_name] = client_socket
            print(f"{client_name} connected")
            self.broadcast_active_clients()
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_name))
            client_thread.daemon = True
            client_thread.start()


class Client:
    def __init__(self, address):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((address, 62561))
            self.name = input("Enter your name: ")
            self.sock.send(bytes(self.name, 'utf-8'))
            input_thread = threading.Thread(target=self.send_msg)
            input_thread.daemon = True
            input_thread.start()
            while True:
                data = self.sock.recv(1024)
                if not data:
                    break
                print(str(data, 'utf-8'))
        except Exception as e:
            print("Error:", e)

    def send_msg(self):
        try:
            while True:
                recipient = input("Enter recipient's name: ")
                message = input("Enter message: ")
                data = f"{recipient}:{message}"
                self.sock.send(bytes(data, 'utf-8'))
        except Exception as e:
            print("Error:", e)

if len(sys.argv) > 1:
    client = Client(sys.argv[1])
else:
    server = Server()
    server.run()

