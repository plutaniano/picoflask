import re
from dataclasses import dataclass
from socket import AF_INET, SHUT_WR, SO_REUSEADDR, SOCK_STREAM, SOL_SOCKET, socket
from typing import Callable, NoReturn


@dataclass
class Request:
    method: str
    headers: dict[str, str]
    path: str
    body: str


@dataclass
class Response:
    body: str = ""
    status_code: int = 200
    content_type: str = "text/html"


View = Callable[[Request], Response]


class PicoFlask:
    routes: list[tuple[re.Pattern, View]] = []

    def route(self, path: str) -> Callable[[View], View]:
        def decorator(func: View) -> View:
            self.routes.append((re.compile(path + "$"), func))
            return func

        return decorator

    def get_route(self, req_path: str) -> View:
        for path, route_func in self.routes:
            if path.match(req_path):
                return route_func
        raise Exception("no matching path")

    def parse_request(self, request: str) -> Request:
        first_line, request = request.split("\r\n", maxsplit=1)
        method, path, _ = first_line.split(" ")
        headers_str, body = request.split("\r\n\r\n")
        headers = {}
        for line in headers_str.split("\r\n"):
            header, value = line.split(": ")
            headers[header] = value
        return Request(method, headers, path, body)

    def build_response(self, response: Response) -> str:
        return (
            f"HTTP/1.1 {response.status_code}\r\n"
            f"Content-Type: {response.content_type}; chartset=utf-8\r\n"
            f"Content-Length: {len(response.body)}\r\n"
            f"Connection: close\r\n\r\n"
            f"{response.body}"
        )

    def run(self, addr: str = "0.0.0.0", port: int = 8000) -> NoReturn:
        print(f"Running on {addr}:{port}")
        with socket(AF_INET, SOCK_STREAM) as s:
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.bind((addr, port))
            s.listen(5)
            while True:
                client, _ = s.accept()
                raw_req = client.recv(4096).decode()
                try:
                    req = self.parse_request(raw_req)
                    print(f"[REQUEST]\t {req.method} '{req.path}'")
                    route = self.get_route(req.path)
                    resp = route(req)
                except Exception as e:
                    resp = Response(f"server error: {e}", 500)
                print(f"[RESPONSE]\t {resp.status_code} {resp.body}")
                client.sendall(self.build_response(resp).encode())
                client.shutdown(SHUT_WR)


if __name__ == "__main__":
    app = PicoFlask()

    @app.route("/")
    def index(request: Request) -> Response:
        return Response("<b>It works</b>")

    app.run()
