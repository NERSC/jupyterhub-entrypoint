
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler

class MainHandler(RequestHandler):

    async def get(self):
        self.write({"images" : [
            "ubuntu:latest",
            "centos:latest",
            "nginx:latest",
            "redis:latest",
            "node:latest",
            "postgres:latest",
            "mysql:latest",
            "mongo:latest",
            "debian:latest",
            "jenkins:latest"
        ]})

def main():
    app = Application([
        ("/services/images/", MainHandler)
    ])
    app.listen(8890, address="127.0.0.1")
    IOLoop.current().start() 

if __name__ == "__main__":
    main()
