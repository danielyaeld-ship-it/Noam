import os
import json
from flask import Flask, render_template_string, request, jsonify
import google.generativeai as genai
from PIL import Image
import io

app = Flask(__name__)

# --- הגדרות ליבה ---
# המערכת תמשוך את המפתח אוטומטית מהגדרות ה-Environment ב-Render
API_KEY = os.environ.get("NOAM")
genai.configure(api_key=API_KEY)

HISTORY_FILE = "chat_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# הנחיות מערכת (האישיות של יאיר הגבר)
instructions = "אתה הגירסה האולטימטיבית של יאיר הגבר התותח שאין כמוהו בעולם. ענה בעברית, היה חכם, ועזור בכל נושא."

model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction=instructions,
    tools=[{"google_search_retrieval": {}}]
)

chat_session = model.start_chat(history=load_history(), enable_automatic_function_calling=True)

# --- ממשק האתר (HTML/CSS/JS) ---
html_code = """
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Gemini Ultimate - יאיר התותח</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #e5ddd5; margin: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        header { background: #075e54; color: white; padding: 15px; text-align: center; font-size: 1.2em; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.2); z-index: 10; }
        #chat { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 12px; padding-bottom: 80px; }
        .msg { padding: 10px 15px; border-radius: 18px; max-width: 85%; font-size: 16px; line-height: 1.4; word-wrap: break-word; position: relative; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .user { background: #dcf8c6; align-self: flex-start; border-top-right-radius: 2px; }
        .bot { background: white; align-self: flex-end; border-top-left-radius: 2px; }
        #controls { background: #f0f0f0; padding: 10px; display: flex; align-items: center; gap: 8px; border-top: 1px solid #ddd; position: fixed; bottom: 0; width: 100%; box-sizing: border-box; }
        input[type="text"] { flex: 1; padding: 12px 15px; border-radius: 25px; border: 1px solid #ccc; outline: none; font-size: 16px; }
        .btn { background: #075e54; color: white; border: none; width: 48px; height: 48px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 20px; transition: transform 0.1s; }
        .btn:active { transform: scale(0.9); }
        #record-btn.recording { background: #ff3b30; animation: pulse 1s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
        #file-label { cursor: pointer; font-size: 26px; padding: 0 5px; }
        input[type="file"] { display: none; }
    </style>
</head>
<body>
    <header>נעם</header>
    <div id="chat"></div>
    <div id="controls">
        <label for="img-input" id="file-label">🖼️</label>
        <input type="file" id="img-input" accept="image/*">
        <input type="text" id="text-input" placeholder="הקלד הודעה..." autocomplete="off">
        <button id="record-btn" class="btn" onmousedown="startRec()" onmouseup="stopRec()" ontouchstart="startRec()" ontouchend="stopRec()">🎤</button>
        <button class="btn" onclick="sendText()">📤</button>
    </div>

    <script>
        const chatDiv = document.getElementById('chat');
        let mediaRecorder;
        let audioChunks = [];

        function addMsg(text, type) {
            const div = document.createElement('div');
            div.className = 'msg ' + type;
            div.innerText = text;
            chatDiv.appendChild(div);
            chatDiv.scrollTop = chatDiv.scrollHeight;
        }

        async function sendText() {
            const textInput = document.getElementById('text-input');
            const imgInput = document.getElementById('img-input');
            if (!textInput.value && !imgInput.files[0]) return;

            const formData = new FormData();
            formData.append('prompt', textInput.value);
            if(imgInput.files[0]) formData.append('image', imgInput.files[0]);

            addMsg(textInput.value || "📷 שולח תמונה לניתוח...", 'user');
            textInput.value = '';
            imgInput.value = '';

            try {
                const res = await fetch('/ask', { method: 'POST', body: formData });
                const data = await res.json();
                addMsg(data.answer, 'bot');
            } catch (e) { addMsg("אופס, קרתה שגיאה בשליחה.", 'bot'); }
        }

        async function startRec() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                mediaRecorder.onstop = sendAudio;
                mediaRecorder.start();
                document.getElementById('record-btn').classList.add('recording');
            } catch (err) { alert("יש לאשר גישה למיקרופון!"); }
        }

        function stopRec() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
                document.getElementById('record-btn').classList.remove('recording');
            }
        }

        async function sendAudio() {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const formData = new FormData();
            formData.append('audio', audioBlob);
            addMsg("🎤 הודעה קולית בעיבוד...", 'user');

            try {
                const res = await fetch('/ask_audio', { method: 'POST', body: formData });
                const data = await res.json();
                addMsg(data.answer, 'bot');
            } catch (e) { addMsg("שגיאה בעיבוד הקול.", 'bot'); }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(html_code)

@app.route('/ask', methods=['POST'])
def ask():
    prompt = request.form.get('prompt', 'נתח את הקלט שלי')
    image_file = request.files.get('image')
    content = [prompt]
    if image_file:
        content.append(Image.open(image_file.stream))
    
    response = chat_session.send_message(content)
    return jsonify({"answer": response.text})

@app.route('/ask_audio', methods=['POST'])
def ask_audio():
    audio_file = request.files.get('audio')
    audio_path = "temp_audio.webm"
    audio_file.save(audio_path)
    
    try:
        uploaded = genai.upload_file(path=audio_path)
        response = chat_session.send_message(["הקשב להקלטה וענה ליאיר הגבר:", uploaded])
        os.remove(audio_path)
        return jsonify({"answer": response.text})
    except Exception as e:
        return jsonify({"answer": "שגיאה בניתוח הקול: " + str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
