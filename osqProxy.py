#!/usr/bin/python
import SimpleHTTPServer
import SocketServer
import argparse
import pip
import json
import sys
import os

'''
[Osquery-Proxy]
Usage:  python dbaOsqServer.py --port 8161
'''

class OsqueryRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.osqserver = OsqProxyServer()
        if self.path == '/':
            self.osqResponse = self.osqserver.list_tables()
            for tab in self.osqResponse:
                table_link = "<a href='select+*+from+%s'>%s<a><br/>" % (tab, tab)
                self.wfile.write(table_link)
        else:
            self.osqResponse = self.osqserver.execute_query(self.path.strip('/'))
            self.wfile.write(self.osqResponse)
        return

class OsqTCPServer(SocketServer.TCPServer):
    allow_reuse_address = True

class OsqProxyServer():
    def __init__(self, listen_addr = '0.0.0.0', listen_port = 8161):
        self.listen_addr = listen_addr
        self.listen_port = listen_port

    def __close__(self):
        pass

    def list_tables(self):
        cmd = 'echo .tables | osqueryi|cut -d ">" -f2 | xargs'
        try:
            table = os.popen(cmd).read().split()
            return table
        except KeyboardInterrupt:
            print "exit"

    def execute_query(self, query):
        query = query.replace('+',' ')
        self.instance = osquery.SpawnInstance()
        self.instance.open()
        self.queryResult = self.instance.client.query(query)

        self.instance.connection.close()
        self.instance.instance.kill()

        os.close(self.instance._pidfile[0])
        os.remove(self.instance._pidfile[1])
        os.close(self.instance._socket[0])
        os.remove(self.instance._socket[1])

        if self.queryResult.status.code != 0:
            self.resultMsg = self.queryResult.status.message
            self.rc = 1
        else:
            self.resultMsg = self.queryResult.response
            self.rc = 0
        return json.dumps({"result":self.resultMsg, "rc":self.rc})

    def run(self):
        print 'osquery proxy is listening on 0.0.0.0:%s ...' % str(self.listen_port)
        self.osqHandler = OsqueryRequestHandler
        try:
            self.server = OsqTCPServer((self.listen_addr, self.listen_port),self.osqHandler)
        except KeyboardInterrupt:
            print 'osquery proxy has stopped...'
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.server.socket.close()
            self.server.shutdown()
            print 'osquery proxy has stopped...'
            sys.exit(0)

if __name__ == '__main__':
    try:
        import osquery
    except:
        pip.main(['install', 'osquery'])

    parser = argparse.ArgumentParser(description=('osquery simplte HTTP server'))
    parser.add_argument('--port', metavar='PORT',
                         type=int, default=8161, help='listen TCP port.')
    args = parser.parse_args()

    testserver = OsqProxyServer('0.0.0.0',args.port)
    testserver.run()
