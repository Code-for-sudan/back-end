from flask import Flask, request, jsonify
from tasks import send_email_task

app = Flask(__name__)

@app.route('/send-email', methods=['POST'])
def send_email():
    data = request.json
    send_email_task.delay(data)
    return jsonify({'status': 'queued'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)