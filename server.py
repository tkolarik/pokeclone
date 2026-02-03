import http.server
import socketserver
import json
import os

PORT = 8001
DATA_FILE = os.path.join(os.path.dirname(__file__), 'tasks.json')

class KanbanHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/tasks':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r') as f:
                    self.wfile.write(f.read().encode())
            else:
                self.wfile.write(b'[]')
        elif self.path == '/':
            self.path = '/index.html'
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/tasks':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            new_task = json.loads(post_data)
            
            tasks = self._load_tasks()
            
            # Simple ID generation if not present
            if 'id' not in new_task or not new_task['id']:
                new_task['id'] = f"TASK-{len(tasks)+1}"
            
            tasks.append(new_task)
            self._save_tasks(tasks)
                
            self.send_response(201)
            self.end_headers()
            self.wfile.write(json.dumps(new_task).encode())

    def do_PUT(self):
        if self.path.startswith('/api/tasks/'):
            task_id = self.path.split('/')[-1]
            content_length = int(self.headers['Content-Length'])
            put_data = self.rfile.read(content_length)
            updated_data = json.loads(put_data)
            
            tasks = self._load_tasks()
            found = False
            for task in tasks:
                if task['id'] == task_id:
                    task.update(updated_data)
                    found = True
                    break
            
            if found:
                self._save_tasks(tasks)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"status": "updated"}')
            else:
                self.send_response(404)
                self.end_headers()

    def _load_tasks(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        return []

    def _save_tasks(self, tasks):
        with open(DATA_FILE, 'w') as f:
            json.dump(tasks, f, indent=2)

if __name__ == "__main__":
    # Ensure we serve from the directory containing this script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Create tasks.json if it doesn't exist
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump([], f)
            
    with socketserver.TCPServer(("", PORT), KanbanHandler) as httpd:
        print(f"Serving Kanban Board at http://localhost:{PORT}")
        print("Press Ctrl+C to stop.")
        httpd.serve_forever()