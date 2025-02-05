## channel.py - a simple message channel
##

from flask import Flask, request, render_template, jsonify
import json
import requests

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db

HUB_URL = 'http://localhost:5555'
HUB_AUTHKEY = '1234567890'
CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "EAC ETW Tree Species"
CHANNEL_ENDPOINT = "http://localhost:5001" # don't forget to adjust in the bottom of the file
CHANNEL_FILE = 'messages.json'
CHANNEL_TYPE_OF_SERVICE = 'aiweb24:chat'

@app.cli.command('register')
def register_command():
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT

    # send a POST request to server /channels
    response = requests.post(HUB_URL + '/channels', headers={'Authorization': 'authkey ' + HUB_AUTHKEY},
                             data=json.dumps({
                                "name": CHANNEL_NAME,
                                "endpoint": CHANNEL_ENDPOINT,
                                "authkey": CHANNEL_AUTHKEY,
                                "type_of_service": CHANNEL_TYPE_OF_SERVICE,
                             }))

    if response.status_code != 200:
        print("Error creating channel: "+str(response.status_code))
        print(response.text)
        return

def check_authorization(request):
    global CHANNEL_AUTHKEY
    # check if Authorization header is present
    if 'Authorization' not in request.headers:
        return False
    # check if authorization header is valid
    if request.headers['Authorization'] != 'authkey ' + CHANNEL_AUTHKEY:
        return False
    return True

@app.route('/health', methods=['GET'])
def health_check():
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({'name':CHANNEL_NAME}),  200

# GET: Return list of messages
@app.route('/', methods=['GET'])
def home_page():
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400

    messages = read_messages()
    
    # enforce limit for amount of messages
    limit_message_count(messages)

    # if messages empy or first message not welcome message
    # --> add welcome message in beginning
    # ensures that welcome message is always first message on server
    welcome_message = {
        'content': f"Welcome to {CHANNEL_NAME}. This channel aims to help you learn the botanical names of trees relevant in the examination for the European Tree Worker by the Europoean Arboricultural Council. Type in the common name of one of the 45 tree species (e.g. european beech) to get the botanical name as an answer.",
        'sender': "System Message",
        'timestamp': None,
        'extra': "system"
        }
    if not messages:
        messages.append(welcome_message) 
    elif (messages[0]['sender'] != "System Message" or messages[0]['timestamp'] != None):
        messages.insert(0, welcome_message)
    save_messages(messages)

    # fetch channels from server
    return jsonify(read_messages())

# POST: Send a message
@app.route('/', methods=['POST'])
def send_message():
    # fetch channels from server
    # check authorization header
    if not check_authorization(request):
        return "Invalid authorization", 400
    # check if message is present
    message = request.json
    if not message:
        return "No message", 400
    if not 'content' in message:
        return "No content", 400
    if not 'sender' in message:
        return "No sender", 400
    if not 'timestamp' in message:
        return "No timestamp", 400
    if not 'extra' in message:
        extra = None
    else:
        extra = message['extra']
    
    # add message to messages
    messages = read_messages()
    # enforce limit for amount of messages
    limit_message_count(messages)

    # check validity of message
    if valid_message(message):
        messages.append({'content': message['content'],
                     'sender': message['sender'],
                     'timestamp': message['timestamp'],
                     'extra': extra,
                     })
        # system answer for valid user message
        botanical_name = valid_message(message)
        messages.append({'content': f"The botanical name for {message['content']} is {botanical_name}.",
                        'sender': "Answer",
                        'timestamp': message['timestamp'],
                        'extra': None,
                        })
        save_messages(messages)
    else:
        messages.append({'content': "Your message has been filtered. Please only input one of the 45 common tree names relevant for the ETW.",
                        'sender': "System Message",
                        'timestamp': message['timestamp'],
                        'extra': None,
                        })
        save_messages(messages)

    return "OK", 200


# limit number of messages to 100
def limit_message_count(messages):
    while len(messages) > 3:
        del messages[1]
    return None

def read_messages():
    global CHANNEL_FILE
    try:
        f = open(CHANNEL_FILE, 'r')
    except FileNotFoundError:
        return []
    try:
        messages = json.load(f)
    except json.decoder.JSONDecodeError:
        messages = []
    f.close()
    return messages

def save_messages(messages):
    global CHANNEL_FILE

    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)




# filter messages for common names of trees
# and get botanical name for user input if available
def valid_message(message):
    botanical_names = {
        "field maple": "Acer campestre",
        "norway maple": "Acer platanoides",
        "sycamore": "Acer pseudoplatanoides",
        "silver maple": "Acer saccharinum",
        "horse chestnut": "Aesculus hippocastanum",
        "tree of heaven": "Ailanthus altissima",
        "black alder": "Alnus glutinosa",
        "silver birch": "Betula pendula",
        "hornbeam": "Carpinus betulus",
        "sweet chestnut": "Castanea sativa",
        "tree hazel": "Corylus colurna",
        "two-handled hawthorn": "Crataegus laevigata",
        "european beech": "Fagus sylvatica"
    }
    try:
        botanical_name = botanical_names[message['content'].lower()]
        return botanical_name
    except:
        return False

# Start development web server
# run flask --app channel.py register
# to register channel with hub

if __name__ == '__main__':
    app.run(port=5001, debug=True)
