import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from modules import shared
from modules.text_generation import summary_encoder, merge_sum, merge_topic#,generate_tweet #encode, generate_reply,



class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/v1/model':
            self.send_response(200)
            self.end_headers()
            response = json.dumps({
                'result': shared.model_name
            })

            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(content_length).decode('utf-8'))

        if self.path == '/api/v1/summary':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            # prompt_type = body['prompt_type']
            conv = body['conv']
            generator = summary_encoder(conv)
                #     break
                # except Exception as e:
                #     print('error:', e)
                #     retry_time+=1
                #     print('retry_time:', retry_time)
            answer = ''
            for a in generator:
                answer += a

            response = json.dumps({
                'results': [{
                    'text': answer
                }]
            })

            self.wfile.write(response.encode('utf-8'))
        
        elif self.path == '/api/v1/merge_sum':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            # prompt_type = body['prompt_type']
            sum_ls = body['sum_ls']
            generator = merge_sum(sum_ls)
                #     break
                # except Exception as e:
                #     print('error:', e)
                #     retry_time+=1
                #     print('retry_time:', retry_time)
            answer = ''
            for a in generator:
                answer += a

            response = json.dumps({
                'results': [{
                    'text': answer
                }]
            })

            self.wfile.write(response.encode('utf-8'))
        

        elif self.path == '/api/v1/merge_topic':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            # prompt_type = body['prompt_type']
            topic_ls = body['topic_ls']
            generator = merge_topic(topic_ls)
                #     break
                # except Exception as e:
                #     print('error:', e)
                #     retry_time+=1
                #     print('retry_time:', retry_time)
            answer = ''
            for a in generator:
                answer += a

            response = json.dumps({
                'results': [{
                    'text': answer
                }]
            })

            self.wfile.write(response.encode('utf-8'))

        
        else:
            self.send_error(404)


def _run_server(port: int, share: bool = False):
    address = '0.0.0.0' if shared.args.listen else '127.0.0.1'
    server = ThreadingHTTPServer((address, port), Handler)

    def on_start(public_url: str):
        print(f'Starting non-streaming server at public url {public_url}/api')

        print(
            f'Starting API at http://{address}:{port}/api')

    server.serve_forever()


def start_server(port: int, share: bool = False):
    Thread(target=_run_server, args=[port, share], daemon=True).start()
