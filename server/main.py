import pathlib
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import mimetypes
import json
import socket
import threading
from datetime import datetime


BASE_DIR = pathlib.Path()
STORAGE_DIR = BASE_DIR / 'storage'
STORAGE_DIR.mkdir(exist_ok=True)

data_file = STORAGE_DIR / 'data.json'
if not data_file.exists():
    with open(data_file, 'w', encoding='utf-8') as fd:
        json.dump({}, fd)

IP = '127.0.0.1'
SERVER_PORT = 3000
SOKET_PORT = 5000


# HTTP Handler
class HttpGetHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.data = None

    def do_POST(self):
        self.data = self.rfile.read(int(self.headers['Content-Length']))
        self.send_to_socket()  # send data to socket
        self.send_response(302)
        self.send_header('Location', '/message')
        self.end_headers()

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)

        match pr_url.path:
            case '/':
                self.send_html_file('index.html')
            case '/message':
                self.send_html_file('message.html')
            case _:
                file = BASE_DIR.joinpath(pr_url.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html_file('error.html', 404)

    def send_static(self, file):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header('Content-type', mt[0])
        else:
            self.send_header('Content-type', 'text/plain')
        self.end_headers()
        with open(file, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_to_socket(self):
        # data parsing
        data_parse = urllib.parse.unquote_plus(self.data.decode())
        data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}
        if data_dict['username'] and data_dict['message']:
            message = json.dumps(data_dict)
            # Send parsed data to socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(message.encode(), (IP, SOKET_PORT))


# Socket-server
def socket_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP, SOKET_PORT))
    print("Socket run with port: {}".format(SOKET_PORT))

    while True:
        data, addr = sock.recvfrom(1024)
        message = data.decode()
        message_dict = json.loads(message)

        # Add time as a key
        current_time = str(datetime.now())
        full_message = {current_time: message_dict}

        # Write msgs history to JSON
        file_path = STORAGE_DIR / 'data.json'
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as fd:
                existing_data = json.load(fd)
        else:
            existing_data = {}

        existing_data.update(full_message)

        with open(file_path, 'w', encoding='utf-8') as fd:
            json.dump(existing_data, fd, ensure_ascii=False, indent=4)
        print(f"Added message: {full_message}")


# Run HTTP-server
def run_http_server():
    server_address = (IP, SERVER_PORT)
    http = HTTPServer(server_address, HttpGetHandler)
    print("HTTP run with port: {}".format(SERVER_PORT))
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


if __name__ == '__main__':
    http_thread = threading.Thread(target=run_http_server)
    socket_thread = threading.Thread(target=socket_server)

    http_thread.start()
    socket_thread.start()

    http_thread.join()
    socket_thread.join()
