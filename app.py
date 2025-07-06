from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Storage
users = {}
waiting_users = []
active_rooms = {}

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('connect')
def handle_connect():
    user_id = str(uuid.uuid4())[:8]
    users[request.sid] = {
        'id': user_id,
        'room': None,
        'partner': None
    }
    print(f"User {user_id} connected")

@socketio.on('find_stranger')
def handle_find_stranger():
    current_user = users.get(request.sid)
    if not current_user:
        return
    
    if waiting_users:
        # Match với user đang đợi
        partner_sid = waiting_users.pop(0)
        partner = users.get(partner_sid)
        
        if partner:
            room_id = str(uuid.uuid4())[:8]
            
            # Update user info
            current_user['room'] = room_id
            current_user['partner'] = partner_sid
            partner['room'] = room_id
            partner['partner'] = request.sid
            
            # Join room
            join_room(room_id, sid=request.sid)
            join_room(room_id, sid=partner_sid)
            
            # Store room info
            active_rooms[room_id] = [request.sid, partner_sid]
            
            # Notify both users
            emit('stranger_found', {
                'room_id': room_id,
                'your_id': current_user['id'],
                'is_initiator': True
            }, room=request.sid)
            
            emit('stranger_found', {
                'room_id': room_id,
                'your_id': partner['id'],
                'is_initiator': False
            }, room=partner_sid)
            
            print(f"Matched: {current_user['id']} <-> {partner['id']} in room {room_id}")
    else:
        # Thêm vào waiting list
        waiting_users.append(request.sid)
        emit('waiting_for_stranger')

@socketio.on('send_message')
def handle_message(data):
    current_user = users.get(request.sid)
    if not current_user or not current_user['room']:
        return
    
    message_data = {
        'message': data['message'],
        'sender_id': current_user['id'],
        'sender_sid': request.sid,  # Thêm sender_sid để phân biệt
        'timestamp': datetime.now().strftime('%H:%M'),
        'room_id': current_user['room']
    }
    
    # Gửi tin nhắn đến tất cả trong room
    emit('receive_message', message_data, room=current_user['room'])
    print(f"Message from {current_user['id']}: {data['message']}")

@socketio.on('typing')
def handle_typing():
    current_user = users.get(request.sid)
    if current_user and current_user['room'] and current_user['partner']:
        emit('user_typing', {'user_id': current_user['id']}, room=current_user['partner'])

@socketio.on('stop_typing')
def handle_stop_typing():
    current_user = users.get(request.sid)
    if current_user and current_user['room'] and current_user['partner']:
        emit('user_stop_typing', room=current_user['partner'])

@socketio.on('next_stranger')
def handle_next_stranger():
    current_user = users.get(request.sid)
    if not current_user:
        return
    
    # Leave current room
    if current_user['room']:
        leave_room(current_user['room'])
        
        # Notify partner
        if current_user['partner']:
            partner = users.get(current_user['partner'])
            if partner:
                partner['room'] = None
                partner['partner'] = None
                emit('stranger_disconnected', room=current_user['partner'])
        
        # Clean up room
        if current_user['room'] in active_rooms:
            del active_rooms[current_user['room']]
    
    # Reset user
    current_user['room'] = None
    current_user['partner'] = None
    
    # Find new stranger
    handle_find_stranger()

@socketio.on('disconnect')
def handle_disconnect():
    current_user = users.get(request.sid)
    if current_user:
        # Remove from waiting list
        if request.sid in waiting_users:
            waiting_users.remove(request.sid)
        
        # Notify partner
        if current_user['partner']:
            partner = users.get(current_user['partner'])
            if partner:
                partner['room'] = None
                partner['partner'] = None
                emit('stranger_disconnected', room=current_user['partner'])
        
        # Clean up room
        if current_user['room'] and current_user['room'] in active_rooms:
            del active_rooms[current_user['room']]
        
        # Remove user
        del users[request.sid]
        print(f"User {current_user['id']} disconnected")

# HTML Template với JavaScript đã fix
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HUBchat - Chat ẩn danh</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            width: 100%;
            max-width: 800px;
            height: 600px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .header {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            text-align: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .header h1 {
            color: white;
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .header p {
            color: rgba(255, 255, 255, 0.8);
            font-size: 14px;
        }
        
        .status {
            background: rgba(255, 255, 255, 0.05);
            padding: 15px 20px;
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
        }
        
        .chat-area {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .message {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
            animation: fadeIn 0.3s ease;
            position: relative;
        }
        
        /* TIN NHẮN CỦA TÔI - BÊN PHẢI */
        .message.my-message {
            align-self: flex-end;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border-bottom-right-radius: 5px;
        }
        
        /* TIN NHẮN CỦA ĐỐI PHƯƠNG - BÊN TRÁI */
        .message.their-message {
            align-self: flex-start;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            border-bottom-left-radius: 5px;
        }
        
        .message-time {
            font-size: 11px;
            opacity: 0.7;
            margin-top: 4px;
            display: block;
        }
        
        .typing-indicator {
            align-self: flex-start;
            background: rgba(255, 255, 255, 0.9);
            color: #666;
            padding: 12px 16px;
            border-radius: 18px;
            border-bottom-left-radius: 5px;
            font-style: italic;
            animation: pulse 1.5s infinite;
        }
        
        .input-area {
            padding: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .message-input {
            flex: 1;
            padding: 12px 16px;
            border: none;
            border-radius: 25px;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            font-size: 14px;
            outline: none;
            transition: all 0.3s ease;
        }
        
        .message-input:focus {
            background: white;
            box-shadow: 0 0 0 2px rgba(79, 172, 254, 0.3);
        }
        
        .send-button, .next-button {
            padding: 12px 20px;
            border: none;
            border-radius: 25px;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s ease;
            font-size: 14px;
        }
        
        .send-button:hover, .next-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(79, 172, 254, 0.4);
        }
        
        .send-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .start-button {
            padding: 15px 30px;
            border: none;
            border-radius: 25px;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            cursor: pointer;
            font-weight: 600;
            font-size: 16px;
            margin: 20px auto;
            display: block;
            transition: all 0.3s ease;
        }
        
        .start-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(79, 172, 254, 0.4);
        }
        
        .controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .chat-area::-webkit-scrollbar {
            width: 6px;
        }
        
        .chat-area::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }
        
        .chat-area::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.3);
            border-radius: 10px;
        }
        
        .chat-area::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.5);
        }
        
        @media (max-width: 480px) {
            .container {
                height: 100vh;
                border-radius: 0;
                max-width: 100%;
            }
            
            .message {
                max-width: 85%;
            }
            
            .controls {
                flex-direction: column;
                gap: 10px;
            }
            
            .message-input {
                margin-bottom: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌟 HUBchat</h1>
            <p>Chat ẩn danh với người lạ trên toàn thế giới</p>
        </div>
        
        <div class="status" id="status">
            Nhấn "Bắt đầu trò chuyện" để tìm người lạ
        </div>
        
        <div class="chat-area" id="chatArea">
            <button class="start-button" id="startButton" onclick="hubChat.findStranger()">
                🚀 Bắt đầu trò chuyện
            </button>
        </div>
        
        <div class="input-area" id="inputArea" style="display: none;">
            <input type="text" class="message-input" id="messageInput" 
                   placeholder="Nhập tin nhắn..." maxlength="500">
            <div class="controls">
                <button class="send-button" id="sendButton" onclick="hubChat.sendMessage()">Gửi</button>
                <button class="next-button" onclick="hubChat.nextStranger()">Tiếp theo</button>
            </div>
        </div>
    </div>

    <script>
        class HUBChat {
            constructor() {
                this.socket = io();
                this.currentUserId = null;  // ID của user hiện tại
                this.isConnected = false;
                this.isAtBottom = true;
                this.typingTimeout = null;
                
                this.initializeSocketEvents();
                this.initializeUI();
            }
            
            initializeSocketEvents() {
                this.socket.on('connect', () => {
                    console.log('Đã kết nối server');
                });
                
                this.socket.on('stranger_found', (data) => {
                    this.currentUserId = data.your_id;  // Lưu ID của mình
                    this.isConnected = true;
                    this.updateStatus('🎉 Đã tìm thấy người lạ! Bắt đầu trò chuyện...');
                    this.showChatInterface();
                    this.clearMessages();
                });
                
                this.socket.on('waiting_for_stranger', () => {
                    this.updateStatus('🔍 Đang tìm người lạ...');
                });
                
                this.socket.on('receive_message', (data) => {
                    // Phân biệt tin nhắn của mình và đối phương
                    const isMyMessage = (data.sender_sid === this.socket.id);
                    this.addMessage(data.message, data.timestamp, isMyMessage);
                });
                
                this.socket.on('user_typing', (data) => {
                    this.showTypingIndicator();
                });
                
                this.socket.on('user_stop_typing', () => {
                    this.hideTypingIndicator();
                });
                
                this.socket.on('stranger_disconnected', () => {
                    this.isConnected = false;
                    this.updateStatus('😢 Người lạ đã ngắt kết nối');
                    this.hideChatInterface();
                    this.addSystemMessage('Người lạ đã rời khỏi cuộc trò chuyện');
                });
                
                this.socket.on('disconnect', () => {
                    this.isConnected = false;
                    this.updateStatus('❌ Mất kết nối server');
                });
            }
            
            initializeUI() {
                const messageInput = document.getElementById('messageInput');
                const sendButton = document.getElementById('sendButton');
                
                messageInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        this.sendMessage();
                    }
                });
                
                messageInput.addEventListener('input', () => {
                    if (this.isConnected) {
                        this.handleTyping();
                    }
                });
                
                const chatArea = document.getElementById('chatArea');
                chatArea.addEventListener('scroll', () => {
                    const { scrollTop, scrollHeight, clientHeight } = chatArea;
                    this.isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
                });
            }
            
            findStranger() {
                this.socket.emit('find_stranger');
                this.updateStatus('🔍 Đang tìm người lạ...');
                document.getElementById('startButton').style.display = 'none';
            }
            
            sendMessage() {
                const messageInput = document.getElementById('messageInput');
                const message = messageInput.value.trim();
                
                if (message && this.isConnected) {
                    this.socket.emit('send_message', { message: message });
                    messageInput.value = '';
                    this.stopTyping();
                }
            }
            
            addMessage(message, timestamp, isMyMessage) {
                const chatArea = document.getElementById('chatArea');
                const messageDiv = document.createElement('div');
                
                // Phân biệt class dựa trên isMyMessage
                messageDiv.className = `message ${isMyMessage ? 'my-message' : 'their-message'}`;
                
                messageDiv.innerHTML = `
                    ${this.escapeHtml(message)}
                    <span class="message-time">${timestamp}</span>
                `;
                
                chatArea.appendChild(messageDiv);
                
                if (this.isAtBottom) {
                    this.scrollToBottom();
                }
            }
            
            addSystemMessage(message) {
                const chatArea = document.getElementById('chatArea');
                const messageDiv = document.createElement('div');
                messageDiv.style.cssText = `
                    text-align: center;
                    color: rgba(255, 255, 255, 0.7);
                    font-size: 12px;
                    padding: 10px;
                    font-style: italic;
                `;
                messageDiv.textContent = message;
                chatArea.appendChild(messageDiv);
                this.scrollToBottom();
            }
            
            handleTyping() {
                if (this.isConnected) {
                    this.socket.emit('typing');
                    
                    clearTimeout(this.typingTimeout);
                    this.typingTimeout = setTimeout(() => {
                        this.stopTyping();
                    }, 1000);
                }
            }
            
            stopTyping() {
                if (this.isConnected) {
                    this.socket.emit('stop_typing');
                }
            }
            
            showTypingIndicator() {
                this.hideTypingIndicator();
                
                const chatArea = document.getElementById('chatArea');
                const typingDiv = document.createElement('div');
                typingDiv.className = 'typing-indicator';
                typingDiv.id = 'typingIndicator';
                typingDiv.textContent = 'Đang nhập...';
                
                chatArea.appendChild(typingDiv);
                this.scrollToBottom();
            }
            
            hideTypingIndicator() {
                const typingIndicator = document.getElementById('typingIndicator');
                if (typingIndicator) {
                    typingIndicator.remove();
                }
            }
            
            nextStranger() {
                this.socket.emit('next_stranger');
                this.isConnected = false;
                this.updateStatus('🔍 Đang tìm người lạ mới...');
                this.hideTypingIndicator();
            }
            
            updateStatus(message) {
                document.getElementById('status').textContent = message;
            }
            
            showChatInterface() {
                document.getElementById('inputArea').style.display = 'flex';
                document.getElementById('messageInput').focus();
            }
            
            hideChatInterface() {
                document.getElementById('inputArea').style.display = 'none';
                document.getElementById('startButton').style.display = 'block';
            }
            
            clearMessages() {
                const chatArea = document.getElementById('chatArea');
                const messages = chatArea.querySelectorAll('.message, .typing-indicator');
                messages.forEach(msg => msg.remove());
            }
            
            scrollToBottom() {
                const chatArea = document.getElementById('chatArea');
                setTimeout(() => {
                    chatArea.scrollTop = chatArea.scrollHeight;
                }, 10);
            }
            
            escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
        }
        
        // Khởi tạo ứng dụng
        const hubChat = new HUBChat();
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, debug=False, host='0.0.0.0', port=port)
