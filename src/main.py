import re
from dataclasses import dataclass
from socket import AF_INET, SHUT_WR, SO_REUSEADDR, SOCK_STREAM, SOL_SOCKET, socket
from typing import Dict


@dataclass
class Request:
    method: str
    headers: Dict[str, str]
    path: str
    body: str


@dataclass
class Response:
    body: str = ""
    status_code: int = 200
    content_type: str = "text/html"


class PicoFlask:
    routes = []

    def route(self, path):
        def decorator(func):
            self.routes.append((re.compile(path + "$"), func))
            return func

        return decorator

    def get_route(self, request_path):
        for path, route_func in self.routes:
            if path.match(request_path):
                return route_func
        raise Exception("no matching path")

    def parse_request(self, request):
        first_line, request = request.split("\r\n", maxsplit=1)
        method, path, _ = first_line.split(" ")
        headers_str, body = request.split("\r\n\r\n")
        headers = {}
        for line in headers_str.split("\r\n"):
            header, value = line.split(": ")
            headers[header] = value
        return Request(method, headers, path, body)

    def build_response(self, request):
        return f"""HTTP/1.1 {request.status_code}\r
        Content-Type: {request.content_type}; chartset=utf-8\r
        Content-Length: {len(request.body)}\r
        Connection: close\r\n\r
        {request.body}"""

    def run(self, addr, port):
        with socket(AF_INET, SOCK_STREAM) as s:
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.bind((addr, port))
            s.listen(5)
            while True:
                client, _ = s.accept()
                request = client.recv(4096).decode()
                try:
                    parsed_req = self.parse_request(request)
                    print("[REQUEST]\t", parsed_req.method, parsed_req.path)
                    route = self.get_route(parsed_req.path)
                    response = route(parsed_req)
                except:
                    response = Response("server error", 500)
                print("[RESPONSE]\t", response.status_code, response.body)
                client.sendall(self.build_response(response).encode())
                client.shutdown(SHUT_WR)


if __name__ == "__main__":
    app = PicoFlask()

    @app.route("/page1")
    def page1(request):
        return Response("you're on page 1")

    @app.route("/page2")
    def page1(request):
        return Response("you're on page 2")

    @app.route("/test")
    def test(request):
        return Response("cool framework")

    @app.route("/")
    def test(request):
        return Response("main")

    app.run("0.0.0.0", 8000)
