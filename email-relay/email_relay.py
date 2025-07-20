from flask import Flask, request, jsonify
from tasks import send_email_task

app = Flask(__name__)

@app.route('/send-email', methods=['POST'])
def send_email():
    """
    Handles incoming email sending requests by extracting JSON data from the request,
    queuing the email sending task asynchronously, and returning a JSON response indicating
    the request has been queued.
    Returns:
        Response: A JSON response with a status indicating the email has been queued.
    """
    data = request.json
    send_email_task.delay(data)
    return jsonify({'status': 'queued'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
