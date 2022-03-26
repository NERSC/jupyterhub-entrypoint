
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler

class ExampleImageHandler(RequestHandler):

    async def get(self, username):
        self.write({"images" : [
            {"tag": ["ubuntu:latest"]},
            {"tag": ["centos:latest"]},
            {"tag": ["nginx:latest"]},
            {"tag": ["redis:latest"]},
            {"tag": ["node:latest"]},
            {"tag": ["postgres:latest"]},
            {"tag": ["mysql:latest"]},
            {"tag": ["mongo:latest"]},
            {"tag": ["debian:latest"]},
            {"tag": ["jenkins:latest"]},
        ]})

def main():
    app = Application([
        ("/services/images/list/(.+)", ExampleImageHandler)
    ])
    app.listen(8890, address="127.0.0.1")
    IOLoop.current().start()

if __name__ == "__main__":
    main()
