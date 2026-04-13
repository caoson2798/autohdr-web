from flask import Flask, request, render_template_string, send_file, session, redirect, url_for, jsonify
import requests, zipfile, io, re, time, uuid, threading, os
from urllib.parse import unquote

app = Flask(__name__)
# Khóa bảo mật để tạo Session
app.secret_key = 'Soca_Studio_AutoHDR_Super_Secret_Key_2026'

# ĐỊA CHỈ MÁY CHỦ QUẢN LÝ KEY CỦA ĐẠI CA
ADMIN_SERVER_URL = "https://caoson.pythonanywhere.com"

# Thư mục lưu tạm file ZIP trên Server
TEMP_DIR = "temp_zips"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

TASKS = {}

# =========================================================================
# GIAO DIỆN 1: MÀN HÌNH ĐĂNG NHẬP (LOGIN)
# =========================================================================
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔑 ĐĂNG NHẬP - AUTOHDR VIP</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700;900&display=swap');
        body { font-family: 'Roboto', sans-serif; background-color: #0f172a; color: white; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background-image: radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 70%); }
        .container { background-color: #1e293b; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid #334155; width: 100%; max-width: 450px; text-align: center; }
        h1 { color: #38bdf8; font-size: 32px; font-weight: 900; margin-bottom: 5px; }
        .subtitle { color: #94a3b8; font-size: 15px; margin-bottom: 30px; }
        input[type="text"] { width: 100%; padding: 18px; font-size: 16px; background-color: #0f172a; border: 2px solid #3b82f6; border-radius: 12px; color: white; box-sizing: border-box; text-align: center; font-weight: bold; letter-spacing: 2px; margin-bottom: 20px; }
        input[type="text"]:focus { outline: none; border-color: #fbbf24; box-shadow: 0 0 15px rgba(245, 158, 11, 0.2); }
        button { width: 100%; padding: 18px; font-size: 18px; font-weight: bold; background-color: #2563eb; color: white; border: none; border-radius: 12px; cursor: pointer; transition: 0.3s; }
        button:hover { background-color: #1d4ed8; }
        .error-msg { color: #ef4444; background-color: rgba(239, 68, 68, 0.1); padding: 15px; border-radius: 8px; border: 1px solid #ef4444; margin-bottom: 20px; font-weight: bold; {% if not error %}display: none;{% endif %} }
        .footer-text { margin-top: 25px; font-size: 13px; color: #64748b; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AUTOHDR LOGIN</h1>
        <div class="subtitle">Xác thực bản quyền hệ thống</div>
        <div class="error-msg">{{ error }}</div>
        <form action="/login" method="POST">
            <input type="text" name="user_key" placeholder="SON-XXXXX-XXXXX" required value="{{ last_key }}">
            <button type="submit" id="loginBtn">🔓 ĐĂNG NHẬP VÀO HỆ THỐNG</button>
        </form>
        <div class="footer-text">IP của bạn đã được ghi nhận: <b>{{ client_ip }}</b></div>
    </div>
    <script> document.querySelector('form').onsubmit = function() { document.getElementById('loginBtn').innerHTML = '⏳ ĐANG KIỂM TRA...'; } </script>
</body>
</html>
"""

# =========================================================================
# GIAO DIỆN 2: MÀN HÌNH TẢI ẢNH (ĐÃ THÊM NÚT UPLOAD VÀ HIỆN TÊN USER)
# =========================================================================
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ AUTOHDR DASHBOARD ⚡</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700;900&display=swap');
        body { font-family: 'Roboto', sans-serif; background-color: #0f172a; color: white; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background-image: radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 70%); }
        .container { background-color: #1e293b; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid #334155; width: 100%; max-width: 500px; text-align: center; }
        
        .header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #334155; }
        .header-bar span { color: #e2e8f0; font-size: 14px; }
        .username-hl { color: #fbbf24; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;}
        
        .logout-btn { background-color: #ef4444; color: white; text-decoration: none; padding: 8px 15px; border-radius: 8px; font-size: 13px; font-weight: bold; transition: 0.3s; }
        .logout-btn:hover { background-color: #be123c; }
        
        h1 { color: #38bdf8; font-size: 28px; font-weight: 900; margin: 0 0 5px 0; }
        .subtitle { color: #94a3b8; font-size: 14px; margin-bottom: 25px; }
        
        /* Nút Upload Sang Trang Chủ */
        .upload-btn { display: block; width: 100%; padding: 15px; font-size: 15px; font-weight: bold; color: #10b981; border: 2px dashed #10b981; border-radius: 12px; text-decoration: none; margin-bottom: 25px; transition: 0.3s; box-sizing: border-box;}
        .upload-btn:hover { background-color: rgba(16, 185, 129, 0.1); color: #34d399; border-color: #34d399;}

        label { display: block; text-align: left; font-weight: bold; font-size: 14px; color: #e2e8f0; margin-bottom: 10px; }
        input[type="text"] { width: 100%; padding: 16px; font-size: 15px; background-color: #0f172a; border: 2px solid #475569; border-radius: 12px; color: white; box-sizing: border-box; margin-bottom: 20px; }
        input[type="text"]:focus { outline: none; border-color: #8b5cf6; }
        
        button.action-btn { width: 100%; padding: 18px; font-size: 18px; font-weight: bold; background-color: #8b5cf6; color: white; border: none; border-radius: 12px; cursor: pointer; transition: 0.3s; text-transform: uppercase; }
        button.action-btn:hover { background-color: #7c3aed; }
        
        .error-msg { color: #ef4444; background-color: rgba(239, 68, 68, 0.1); padding: 15px; border-radius: 8px; border: 1px solid #ef4444; margin-bottom: 20px; font-weight: bold; display: none; }
        
        .progress-container { margin-top: 25px; display: none; }
        .progress-bg { width: 100%; background-color: #334155; border-radius: 10px; overflow: hidden; height: 22px; position: relative; }
        .progress-bar { width: 0%; height: 100%; background-color: #10b981; transition: width 0.3s ease; }
        .progress-text { margin-top: 10px; font-family: 'Consolas', monospace; font-size: 14px; color: #fbbf24; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header-bar">
            <span>👤 Chào đại ca: <span class="username-hl">{{ user_name }}</span></span>
            <a href="/logout" class="logout-btn">ĐĂNG XUẤT</a>
        </div>
        
        <h1>AUTOHDR DASHBOARD</h1>
        <div class="subtitle">Dán link dự án để tiến hành tải ảnh ngay</div>
        
        <a href="https://www.autohdr.com" target="_blank" class="upload-btn">☁️ MỞ WEB AUTOHDR ĐỂ UP ẢNH TRƯỚC</a>

        <div class="error-msg" id="errorBox"></div>

        <div id="dlForm">
            <label>🔗 SAU ĐÓ DÁN LINK DỰ ÁN VÀO ĐÂY ĐỂ TẢI:</label>
            <input type="text" id="uuidInput" placeholder="Ví dụ: https://www.autohdr.com/... hoặc mã d8b2..." required>
            <button class="action-btn" onclick="startDownload()" id="downloadBtn">⚡ BẮT ĐẦU TẢI VỀ MÁY</button>
        </div>

        <div class="progress-container" id="progressContainer">
            <div class="progress-bg">
                <div class="progress-bar" id="progressBar"></div>
            </div>
            <div class="progress-text" id="progressText">🚀 Đang kết nối máy chủ...</div>
        </div>
    </div>

    <script>
        let pollInterval;

        function startDownload() {
            const uuidVal = document.getElementById('uuidInput').value.trim();
            if(!uuidVal) {
                showError("❌ Vui lòng nhập link dự án hoặc UUID!");
                return;
            }

            document.getElementById('errorBox').style.display = 'none';
            document.getElementById('downloadBtn').innerHTML = '⏳ ĐANG KHỞI ĐỘNG...';
            document.getElementById('downloadBtn').style.backgroundColor = '#475569';
            document.getElementById('downloadBtn').style.pointerEvents = 'none';
            document.getElementById('progressContainer').style.display = 'block';
            document.getElementById('progressBar').style.width = '2%';
            document.getElementById('progressText').innerText = '🚀 Đang phân tích đường dẫn...';

            fetch('/api/start_download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'uuid=' + encodeURIComponent(uuidVal)
            })
            .then(res => res.json())
            .then(data => {
                if(data.error) {
                    resetUI();
                    showError(data.error);
                } else if(data.task_id) {
                    pollProgress(data.task_id);
                }
            })
            .catch(err => {
                resetUI();
                showError("❌ Lỗi mất kết nối mạng cục bộ!");
            });
        }

        function pollProgress(taskId) {
            pollInterval = setInterval(() => {
                fetch('/api/progress/' + taskId)
                .then(res => res.json())
                .then(data => {
                    if(data.error) {
                        clearInterval(pollInterval);
                        resetUI();
                        showError(data.error);
                    } else {
                        document.getElementById('progressBar').style.width = data.progress + '%';
                        document.getElementById('progressText').innerText = data.status + ' (' + data.progress + '%)';
                        
                        if(data.done) {
                            clearInterval(pollInterval);
                            document.getElementById('progressText').innerText = '✅ HOÀN TẤT! ĐANG LƯU FILE...';
                            document.getElementById('progressBar').style.backgroundColor = '#3b82f6';
                            setTimeout(() => {
                                window.location.href = '/api/download_zip/' + taskId;
                                setTimeout(resetUI, 2000); 
                            }, 500);
                        }
                    }
                })
                .catch(err => console.log(err));
            }, 1000);
        }

        function showError(msg) {
            const errBox = document.getElementById('errorBox');
            errBox.innerText = msg;
            errBox.style.display = 'block';
        }

        function resetUI() {
            document.getElementById('downloadBtn').innerHTML = '⚡ BẮT ĐẦU TẢI VỀ MÁY';
            document.getElementById('downloadBtn').style.backgroundColor = '#8b5cf6';
            document.getElementById('downloadBtn').style.pointerEvents = 'auto';
            document.getElementById('progressContainer').style.display = 'none';
            document.getElementById('progressBar').style.width = '0%';
            document.getElementById('progressBar').style.backgroundColor = '#10b981';
        }
    </script>
</body>
</html>
"""

def get_client_ip():
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    return request.remote_addr

@app.route('/')
def index():
    if 'user_key' in session: return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_HTML, error="", last_key="", client_ip=get_client_ip())

@app.route('/login', methods=['POST'])
def login():
    user_key = request.form.get('user_key', '').strip()
    client_ip = get_client_ip()
    if not user_key: return render_template_string(LOGIN_HTML, error="❌ Vui lòng nhập Key Bản Quyền!", last_key="", client_ip=client_ip)

    try:
        verify_res = requests.post(f"{ADMIN_SERVER_URL}/api/verify", json={"key": user_key, "ip": client_ip}, timeout=10)
        v_data = verify_res.json()
        if verify_res.status_code != 200 or not (v_data.get("valid") or v_data.get("status") == "ok"):
            return render_template_string(LOGIN_HTML, error=f"❌ {v_data.get('message', 'Key sai, hết hạn hoặc sai IP!')}", last_key=user_key, client_ip=client_ip)
        
        # Nhét Key và Tên khách hàng vào Session
        session['user_key'] = user_key
        session['user_name'] = v_data.get("user_name", "VIP Tương Lai")
        return redirect(url_for('dashboard'))
    except Exception as e:
        return render_template_string(LOGIN_HTML, error=f"⚠️ Lỗi kết nối Máy chủ Key: {str(e)}", last_key=user_key, client_ip=client_ip)

@app.route('/dashboard')
def dashboard():
    if 'user_key' not in session: return redirect(url_for('index'))
    # Lấy tên ra hiển thị
    current_user = session.get('user_name', 'VIP')
    return render_template_string(DASHBOARD_HTML, user_name=current_user)

@app.route('/logout')
def logout():
    session.pop('user_key', None)
    session.pop('user_name', None)
    return redirect(url_for('index'))

# =========================================================================
# LÕI ĐỘNG CƠ TẢI NGẦM TRONG BACKGROUND
# =========================================================================
def background_download_task(task_id, target_uuid, user_key):
    try:
        TASKS[task_id]['progress'] = 5
        TASKS[task_id]['status'] = 'Đang quét máy chủ AutoHDR...'
        
        check_url = f"https://www.autohdr.com/api/proxy/photoshoots/uuid/{target_uuid}/processed_photos?page=1&page_size=100&_t={int(time.time())}"
        headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }
        
        res = requests.get(check_url, headers=headers, timeout=15)
        if res.status_code != 200:
            TASKS[task_id]['error'] = f"❌ AUTOHDR TỪ CHỐI! Lỗi {res.status_code}."
            return
            
        data = res.json()
        photos = data if isinstance(data, list) else data.get('processed_photos', [])
        
        if not photos:
            TASKS[task_id]['error'] = "⏳ DỰ ÁN ĐANG XỬ LÝ! Ảnh chưa trộn xong, vui lòng đợi 5 phút rồi tải lại."
            return

        total_photos = len(photos)
        TASKS[task_id]['progress'] = 10
        TASKS[task_id]['status'] = f'Tìm thấy {total_photos} ảnh. Bắt đầu tải...'

        zip_filename = f'Job_{target_uuid[:8]}.zip'
        zip_path = os.path.join(TEMP_DIR, zip_filename)
        success_count = 0
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, photo in enumerate(photos):
                img_url = photo.get('url')
                if not img_url: continue
                
                original_name = photo.get('name') or photo.get('original_name') or f"AutoHDR_Photo_{i+1}.jpg"
                original_name = unquote(original_name)
                
                TASKS[task_id]['status'] = f'Đang kéo ảnh {i+1}/{total_photos}...'
                
                img_res = requests.get(img_url, timeout=30)
                if img_res.status_code == 200:
                    zf.writestr(original_name, img_res.content)
                    success_count += 1
                
                current_percent = 10 + int(85 * ((i + 1) / total_photos))
                TASKS[task_id]['progress'] = current_percent

        TASKS[task_id]['status'] = 'Đang đóng gói file ZIP...'
        TASKS[task_id]['progress'] = 98

        if success_count > 0:
            try: requests.post(f"{ADMIN_SERVER_URL}/api/consume", json={"key": user_key, "img_count": success_count, "count": success_count}, timeout=5)
            except: pass 
        
        TASKS[task_id]['progress'] = 100
        TASKS[task_id]['status'] = 'Đã xong!'
        TASKS[task_id]['done'] = True
        TASKS[task_id]['file_path'] = zip_path
        TASKS[task_id]['filename'] = zip_filename

    except Exception as e:
        TASKS[task_id]['error'] = f"❌ LỖI TRONG QUÁ TRÌNH TẢI: {str(e)}"

# =========================================================================
# CÁC API GIAO TIẾP VỚI AJAX CỦA TRÌNH DUYỆT
# =========================================================================
@app.route('/api/start_download', methods=['POST'])
def api_start():
    if 'user_key' not in session: return jsonify({'error': '❌ Hết phiên đăng nhập!'})
    
    raw_uuid = request.form.get('uuid', '').strip()
    match = re.search(r'([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})', raw_uuid)
    if not match: return jsonify({'error': '❌ Mã UUID không hợp lệ!'})
    target_uuid = match.group(1)

    task_id = str(uuid.uuid4())
    TASKS[task_id] = {'progress': 0, 'status': 'Khởi tạo...', 'done': False, 'error': None}

    thread = threading.Thread(target=background_download_task, args=(task_id, target_uuid, session['user_key']))
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id})

@app.route('/api/progress/<task_id>', methods=['GET'])
def api_progress(task_id):
    if task_id in TASKS:
        return jsonify(TASKS[task_id])
    return jsonify({'error': '❌ Không tìm thấy tiến trình này!'})

@app.route('/api/download_zip/<task_id>', methods=['GET'])
def api_download_zip(task_id):
    if task_id in TASKS and TASKS[task_id].get('done'):
        file_path = TASKS[task_id]['file_path']
        filename = TASKS[task_id]['filename']
        return send_file(file_path, mimetype='application/zip', as_attachment=True, download_name=filename)
    return "File chưa sẵn sàng hoặc đã bị lỗi!", 404