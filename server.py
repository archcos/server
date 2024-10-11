import socket
import threading
import signal
import sys
from datetime import datetime

clients = {}
admin_socket = None
server_socket = None

# Subserver management
subservers = {}  # To keep track of active subservers

def handle_client(client_socket):
    global admin_socket
    addr = client_socket.getpeername()
    username = client_socket.recv(1024).decode('utf-8')

    if username == "IS Admin":
        if admin_socket is not None:
            client_socket.send("Admin is already connected. Please try again later.".encode('utf-8'))
            client_socket.close()
            return
        admin_socket = client_socket
        clients[client_socket] = (username, addr)
        broadcast(f"{username} has joined the chat", client_socket)
        print("Admin has connected.")
    else:
        clients[client_socket] = (username, addr)
        broadcast(f"{username} has joined the chat", client_socket)

    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if message:
                if message == "/users":
                    send_user_list(client_socket)
                elif message.startswith("/ismsg"):
                    if admin_socket:
                        admin_socket.send(f"{message}".encode('utf-8'))
                        print(f"ismsg {message}")
                elif message.startswith("/private"):
                    sender = message.split(":")[1]
                    for client in clients.keys():
                        if clients[client][0] == sender:
                            client.send(f"{username}: {message.split(':')[2]}".encode('utf-8'))
                else:
                    broadcast(message, client_socket)
            else:
                break
        except Exception as e:
            print(f"Error: {e}")
            break

    remove(client_socket)

def broadcast(message, client_socket):
    timestamped_message = add_timestamp(message)
    for client in clients.keys():
        if client != client_socket:
            try:
                client.send(timestamped_message.encode('utf-8'))
            except Exception as e:
                print(f"Error sending message: {e}")
                remove(client)

def add_timestamp(message):
    current_time = datetime.now().strftime("%H:%M:%S")
    return f"{current_time} {message}"

def send_user_list(client_socket):
    online_users = [username for username, _ in clients.values()]
    user_list_message = "\n".join(online_users)
    client_socket.send(("/users " + user_list_message).encode('utf-8'))

def remove(client_socket):
    global admin_socket
    if client_socket in clients:
        username, addr = clients.pop(client_socket)
        disconnection_message = f"{username} has left the chat"
        broadcast(disconnection_message, client_socket)
        print(f"{username} from {addr} has disconnected.")
        
        if client_socket == admin_socket:
            print("Admin has disconnected.")
            admin_socket = None

def cleanup():
    global server_socket
    if admin_socket:
        admin_socket.close()
    for client_socket in clients.keys():
        client_socket.close()
    if server_socket:
        server_socket.close()
    print("Server has shut down gracefully.")
    sys.exit(0)

def signal_handler(sig, frame):
    cleanup()

def start_server():
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 53214))
    server_socket.listen(5)
    print("Server started, waiting for connections...")

    while True:
        try:
            client_socket, addr = server_socket.accept()
            print(f"Connection from {addr} has been established!")
            threading.Thread(target=handle_client, args=(client_socket,)).start()
        except Exception as e:
            print(f"Error accepting connection: {e}")
            break

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    start_server()
