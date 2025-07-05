from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hubchat_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Lưu trữ người dùng và phòng chat
users = {}
waiting_users = []
active_rooms = {}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HUBchat - Anonymous Chat</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .chat-container {
            width: 450px;
            height: 600px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .chat-header {
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header-left h1 {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 5px;
        }

        .online-status {
            display: flex;
            align-items: center;
            font-size: 14px;
            opacity: 0.8;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background: #2ecc71;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        .header-right {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .connection-status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
        }

        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }

        .status-indicator.connected {
            background: #2ecc71;
        }

        .status-indicator.disconnected {
            background: #e74c3c;
        }

        .status-indicator.connecting {
            background: #f39c12;
        }

        .chat-body {
            flex: 1;
            display: flex;
            flex-direction: column;
            position: relative;
        }

        .welcome-screen {
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 40px;
        }

        .welcome-content {
            text-align: center;
        }

        .welcome-content {
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .welcome-content h2 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-weight: 500;
        }

        .welcome-content p {
            color: #7f8c8d;
            margin-bottom: 30px;
        }

        .messages-container {
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        .messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            scroll-behavior: smooth;
        }

        .message {
            margin-bottom: 15px;
            animation: fadeIn 0.3s ease-in;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.system {
            text-align: center;
            color: #7f8c8d;
            font-style: italic;
            font-size: 14px;
        }

        .message.user {
            display: flex;
            justify-content: flex-end;
        }

        .message.stranger {
            display: flex;
            justify-content: flex-start;
        }

        .message-bubble {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
            position: relative;
        }

        .message.user .message-bubble {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border-bottom-right-radius: 4px;
        }

        .message.stranger .message-bubble {
            background: #f1f3f4;
            color: #2c3e50;
            border-bottom-left-radius: 4px;
        }

        .message-time {
            font-size: 11px;
            opacity: 0.6;
            margin-top: 5px;
        }

        .typing-indicator {
            padding: 10px 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #7f8c8d;
            font-size: 14px;
        }

        .typing-dots {
            display: flex;
            gap: 4px;
        }

        .typing-dots span {
            width: 6px;
            height: 6px;
            background: #bdc3c7;
            border-radius: 50%;
            animation: typing 1.4s infinite ease-in-out;
        }

        .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
        .typing-dots span:nth-child(2) { animation-delay: -0.16s; }

        @keyframes typing {
            0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
            40% { transform: scale(1); opacity: 1; }
        }

        .chat-footer {
            padding: 20px;
            background: #f8f9fa;
            border-top: 1px solid #e9ecef;
        }

        .message-input-container {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        #message-input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e9ecef;
            border-radius: 25px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s ease;
        }

        #message-input:focus {
            border-color: #667eea;
        }

        #message-input:disabled {
            background: #f8f9fa;
            cursor: not-allowed;
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }

        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }

        .btn-secondary:hover:not(:disabled) {
            background: rgba(255, 255, 255, 0.3);
        }

        #send-btn {
            width: 45px;
            height: 45px;
            border-radius: 50%;
            padding: 0;
            justify-content: center;
        }

        /* Responsive */
        @media (max-width: 480px) {
            .chat-container {
                width: 100%;
                height: 100vh;
                border-radius: 0;
            }
            
            .chat-header {
                padding: 15px;
            }
            
            .header-left h1 {
                font-size: 20px;
            }
            
            .messages {
                padding: 15px;
            }
            
            .chat-footer {
                padding: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <div class="header-left">
                <h1>🌐 HUBchat</h1>
                <div class="online-status">
                    <span class="status-dot"></span>
                    <span id="online-count">0</span> online
                </div>
            </div>
            <div class="header-right">
                <button id="next-btn" class="btn btn-secondary" disabled>Next</button>
                <div class="connection-status" id="connection-status">
                    <span class="status-indicator disconnected"></span>
                    <span class="status-text">Disconnected</span>
                </div>
            </div>
        </div>

        <div class="chat-body" id="chat-body">
            <div class="welcome-screen" id="welcome-screen">
                <div class="welcome-content">
                    <h2>🎭 Chào mừng đến HUBchat</h2>
                    <p>Kết nối với những người lạ từ khắp nơi trên thế giới</p>
                    <button id="start-chat-btn" class="btn btn-primary">Bắt đầu trò chuyện</button>
                </div>
            </div>
            
            <div class="messages-container" id="messages-container" style="display: none;">
                <div class="messages" id="messages"></div>
                <div class="typing-indicator" id="typing-indicator" style="display: none;">
                    <span>Stranger đang gõ</span>
                    <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        </div>

        <div class="chat-footer" id="chat-footer" style="display: none;">
            <div class="message-input-container">
                <input type="text" id="message-input" placeholder="Nhập tin nhắn..." disabled>
                <button id="send-btn" class="btn btn-primary" disabled>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22,2 15,22 11,13 2,9"></polygon>
                    </svg>
                </button>
            </div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        class HUBChat {
            constructor() {
                this.socket = io();
                this.isConnected = false;
                this.isTyping = false;
                this.typingTimeout = null;
                
                this.initializeElements();
                this.bindEvents();
                this.setupSocketListeners();
            }
            
            initializeElements() {
                this.elements = {
                    welcomeScreen: document.getElementById('welcome-screen'),
                    messagesContainer: document.getElementById('messages-container'),
                    chatFooter: document.getElementById('chat-footer'),
                    messages: document.getElementById('messages'),
                    messageInput: document.getElementById('message-input'),
                    sendBtn: document.getElementById('send-btn'),
                    startChatBtn: document.getElementById('start-chat-btn'),
                    nextBtn: document.getElementById('next-btn'),
                    onlineCount: document.getElementById('online-count'),
                    connectionStatus: document.getElementById('connection-status'),
                    typingIndicator: document.getElementById('typing-indicator')
                };
            }
            
            bindEvents() {
                // Start chat
                this.elements.startChatBtn.addEventListener('click', () => {
                    this.findStranger();
                });
                
                // Send message
                this.elements.sendBtn.addEventListener('click', () => {
                    this.sendMessage();
                });
                
                // Enter key to send
                this.elements.messageInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        this.sendMessage();
                    }
                });
                
                // Typing indicator
                this.elements.messageInput.addEventListener('input', () => {
                    this.handleTyping();
                });
                
                // Next stranger
                this.elements.nextBtn.addEventListener('click', () => {
                    this.nextStranger();
                });
            }
            
            setupSocketListeners() {
                this.socket.on('connect', () => {
                    console.log('Đã kết nối tới server');
                });
                
                this.socket.on('online_count', (data) => {
                    this.elements.onlineCount.textContent = data.count;
                });
                
                this.socket.on('waiting_for_stranger', () => {
                    this.updateConnectionStatus('Tìm kiếm người lạ...', 'connecting');
                    this.addSystemMessage('Đang tìm kiếm người lạ...');
                });
                
                this.socket.on('stranger_found', () => {
                    this.isConnected = true;
                    this.updateConnectionStatus('Đã kết nối', 'connected');
                    this.enableChat();
                });
                
                this.socket.on('system_message', (data) => {
                    this.addSystemMessage(data.message);
                });
                
                this.socket.on('receive_message', (data) => {
                    this.addMessage(data.message, data.sender === 'you' ? 'user' : 'stranger', data.timestamp);
                });
                
                this.socket.on('partner_typing', (data) => {
                    if (data.typing) {
                        this.showTypingIndicator();
                    } else {
                        this.hideTypingIndicator();
                    }
                });
                
                this.socket.on('partner_disconnected', () => {
                    this.isConnected = false;
                    this.updateConnectionStatus('Đã ngắt kết nối', 'disconnected');
                    this.disableChat();
                    this.addSystemMessage('Người lạ đã ngắt kết nối');
                    this.hideTypingIndicator();
                });
            }
            
            findStranger() {
                this.elements.welcomeScreen.style.display = 'none';
                this.elements.messagesContainer.style.display = 'flex';
                this.elements.chatFooter.style.display = 'block';
                
                this.socket.emit('find_stranger');
            }
            
            sendMessage() {
                const message = this.elements.messageInput.value.trim();
                if (!message || !this.isConnected) return;
                
                const timestamp = new Date().toLocaleTimeString('vi-VN', {
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                this.socket.emit('send_message', {
                    message: message,
                    timestamp: timestamp
                });
                
                this.elements.messageInput.value = '';
                this.stopTyping();
            }
            
            addMessage(text, sender, timestamp) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${sender}`;
                
                if (sender === 'system') {
                    messageDiv.innerHTML = `<div class="system-message">${text}</div>`;
                } else {
                    messageDiv.innerHTML = `
                        <div class="message-bubble">
                            ${text}
                            ${timestamp ? `<div class="message-time">${timestamp}</div>` : ''}
                        </div>
                    `;
                }
                
                this.elements.messages.appendChild(messageDiv);
                this.scrollToBottom();
            }
            
            addSystemMessage(text) {
                this.addMessage(text, 'system');
            }
            
            handleTyping() {
                if (!this.isConnected) return;
                
                if (!this.isTyping) {
                    this.isTyping = true;
                    this.socket.emit('typing', { typing: true });
                }
                
                clearTimeout(this.typingTimeout);
                this.typingTimeout = setTimeout(() => {
                    this.stopTyping();
                }, 1000);
            }
            
            stopTyping() {
                if (this.isTyping) {
                    this.isTyping = false;
                    this.socket.emit('typing', { typing: false });
                }
            }
            
            showTypingIndicator() {
                this.elements.typingIndicator.style.display = 'flex';
                this.scrollToBottom();
            }
            
            hideTypingIndicator() {
                this.elements.typingIndicator.style.display = 'none';
            }
            
            enableChat() {
                this.elements.messageInput.disabled = false;
                this.elements.sendBtn.disabled = false;
                this.elements.nextBtn.disabled = false;
                this.elements.messageInput.focus();
            }
            
            disableChat() {
                this.elements.messageInput.disabled = true;
                this.elements.sendBtn.disabled = true;
                this.elements.nextBtn.disabled = false;
            }
            
            updateConnectionStatus(text, status) {
                const statusElement = this.elements.connectionStatus;
                const indicator = statusElement.querySelector('.status-indicator');
                const textElement = statusElement.querySelector('.status-text');
                
                textElement.textContent = text;
                indicator.className = `status-indicator ${status}`;
            }
            
            nextStranger() {
                this.socket.emit('next_stranger');
                this.elements.messages.innerHTML = '';
                this.hideTypingIndicator();
                this.updateConnectionStatus('Tìm kiếm...', 'connecting');
            }
            
            scrollToBottom() {
                setTimeout(() => {
                    this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
                }, 100);
            }
        }

        // Khởi tạo ứng dụng
        document.addEventListener('DOMContentLoaded', () => {
            new HUBChat();
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('connect')
def on_connect():
    user_id = str(uuid.uuid4())
    users[request.sid] = {
        'id': user_id,
        'room': None,
        'partner': None
    }
    emit('user_connected', {'user_id': user_id})
    emit('online_count', {'count': len(users)}, broadcast=True)

@socketio.on('disconnect')
def on_disconnect():
    if request.sid in users:
        user = users[request.sid]
        
        # Thông báo cho partner nếu có
        if user['partner']:
            emit('partner_disconnected', room=user['partner'])
        
        # Xóa khỏi waiting list
        if request.sid in waiting_users:
            waiting_users.remove(request.sid)
        
        # Xóa room nếu có
        if user['room']:
            if user['room'] in active_rooms:
                del active_rooms[user['room']]
        
        del users[request.sid]
        emit('online_count', {'count': len(users)}, broadcast=True)

@socketio.on('find_stranger')
def find_stranger():
    current_user = request.sid
    
    if current_user in waiting_users:
        return
    
    if waiting_users:
        # Ghép với người đang chờ
        partner = waiting_users.pop(0)
        room_id = str(uuid.uuid4())
        
        # Cập nhật thông tin người dùng
        users[current_user]['room'] = room_id
        users[current_user]['partner'] = partner
        users[partner]['room'] = room_id
        users[partner]['partner'] = current_user
        
        # Tạo phòng chat
        active_rooms[room_id] = [current_user, partner]
        
        # Thêm vào room
        join_room(room_id, sid=current_user)
        join_room(room_id, sid=partner)
        
        # Thông báo kết nối thành công
        emit('stranger_found', room=room_id)
        emit('system_message', {'message': 'Đã kết nối với một người lạ! 🎉'}, room=room_id)
        
    else:
        # Thêm vào danh sách chờ
        waiting_users.append(current_user)
        emit('waiting_for_stranger')

@socketio.on('send_message')
def handle_message(data):
    user = users.get(request.sid)
    if user and user['room']:
        message_data = {
            'message': data['message'],
            'sender': 'stranger' if request.sid != user['partner'] else 'you',
            'timestamp': data.get('timestamp')
        }
        emit('receive_message', message_data, room=user['room'])

@socketio.on('typing')
def handle_typing(data):
    user = users.get(request.sid)
    if user and user['partner']:
        emit('partner_typing', data, room=user['partner'])

@socketio.on('next_stranger')
def next_stranger():
    user = users.get(request.sid)
    if user:
        # Thông báo cho partner
        if user['partner']:
            emit('partner_disconnected', room=user['partner'])
            users[user['partner']]['room'] = None
            users[user['partner']]['partner'] = None
        
        # Reset user
        if user['room'] and user['room'] in active_rooms:
            del active_rooms[user['room']]
        
        users[request.sid]['room'] = None
        users[request.sid]['partner'] = None
        
        # Tìm stranger mới
        find_stranger()

if __name__ == '__main__':
    import os
    # Lấy PORT từ environment variable (Railway sẽ cung cấp)
    port = int(os.environ.get('PORT', 5000))
    # Chạy với production settings
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
