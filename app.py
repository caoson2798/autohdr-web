from flask import Flask, request, render_template_string, send_file, session, redirect, url_for
import requests, zipfile, io, re, time

app = Flask(__name__)
# Khóa bảo mật để tạo Session lưu trạng thái đăng nhập (bắt buộc phải có)
app.secret_key = 'Soca_Studio_AutoHDR_Super_Secret_Key_2026'

# ĐỊA CHỈ MÁY CHỦ QUẢN LÝ KEY CỦA ĐẠI CA
ADMIN_SERVER_URL = "https://caoson.pythonanywhere.com"

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
# GIAO DIỆN 2: MÀN HÌNH TẢI ẢNH (DASHBOARD)
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
        .header-bar span { color: #10b981; font-weight: bold; font-size: 14px; }
        .logout-btn { background-color: #ef4444; color: white; text-decoration: none; padding: 8px 15px; border-radius: 8px; font-size: 13px; font-weight: bold; transition: 0.3s; }
        .logout-btn:hover { background-color: #be123c; }
        h1 { color: #38bdf8; font-size: 28px; font-weight: 900; margin: 0 0 5px 0; }
        .subtitle { color: #94a3b8; font-size: 14px; margin-bottom: 25px; }
        label { display: block; text-align: left; font-weight: bold; font-size: 14px; color: #e2e8f0; margin-bottom: 10px; }
        input[type="text"] { width: 100%; padding: 16px; font-size: 15px; background-color: #0f172a; border: 2px solid #475569; border-radius: 12px; color: white; box-sizing: border-box; margin-bottom: 20px; }
        input[type="text"]:focus { outline: none; border-color: #8b5cf6; }
        button { width: 100%; padding: 18px; font-size: 18px; font-weight: bold; background-color: #8b5cf6; color: white; border: none; border-radius: 12px; cursor: pointer; transition: 0.3s; text-transform: uppercase; }
        button:hover { background-color: #7c3aed; }
        .error-msg { color: #ef4444; background-color: rgba(239, 68, 68, 0.1); padding: 15px; border-radius: 8px; border: 1px solid #ef4444; margin-bottom: 20px; font-weight: bold; {% if not error %}display: none;{% endif %} }
        .status-box { margin-top: 20px; padding: 15px; border-radius: 8px; background-color: #000; border: 1px solid #334155; color: #f59e0b; font-family: 'Consolas', monospace; font-size: 13px; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header-bar">
            <span>✅ Trạng thái VIP</span>
            <a href="/logout" class="logout-btn">ĐĂNG XUẤT</a>
        </div>
        <h1>AUTOHDR DASHBOARD</h1>
        <div class="subtitle">Dán link dự án để tiến hành tải ảnh ngay</div>
        <div class="error-msg">{{ error }}</div>

        <form action="/download" method="POST" id="dlForm" onsubmit="showLoading()">
            <label>🔗 MÃ UUID HOẶC ĐƯỜNG DẪN DỰ ÁN:</label>
            <input type="text" name="uuid" placeholder="Ví dụ: https://www.autohdr.com/... hoặc mã d8b2..." required>
            <button type="submit" id="downloadBtn">⚡ BẮT ĐẦU TẢI DỰ ÁN</button>
        </form>

        <div class="status-box" id="logBox">
            🚀 Đang kết nối máy chủ AutoHDR...<br>
            ⏳ Xin vui lòng chờ, tải xong sẽ tự động ra file ZIP!
        </div>
    </div>
    <script> function showLoading() { document.getElementById('downloadBtn').innerHTML = '⏳ ĐANG XỬ LÝ... ĐỪNG TẮT TRANG NÀY!'; document.getElementById('downloadBtn').style.backgroundColor = '#475569'; document.getElementById('downloadBtn').style.pointerEvents = 'none'; document.getElementById('logBox').style.display = 'block'; document.querySelector('.error-msg').style.display = 'none'; } </script>
</body>
</html>
"""

# =========================================================================
# HÀM LẤY IP CỦA KHÁCH HÀNG (Chuẩn cho PythonAnywhere)
# =========================================================================
def get_client_ip():
    if request.headers.getlist("X-Forwarded-For"):
        # PA dùng proxy nên phải móc trong header ra
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    else:
        ip = request.remote_addr
    return ip

# =========================================================================
# XỬ LÝ CÁC TRANG WEB
# =========================================================================

# Trang chủ: Nếu chưa có Session thì quăng ra Login, có rồi thì vào Dashboard
@app.route('/')
def index():
    if 'user_key' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_HTML, error="", last_key="", client_ip=get_client_ip())

# Nơi hứng thông tin Đăng Nhập
@app.route('/login', methods=['POST'])
def login():
    user_key = request.form.get('user_key', '').strip()
    client_ip = get_client_ip()

    if not user_key:
        return render_template_string(LOGIN_HTML, error="❌ Vui lòng nhập Key Bản Quyền!", last_key="", client_ip=client_ip)

    try:
        # ĐẠI CA CHÚ Ý: ĐÃ NHÉT CẢ 'ip' VÀO TRONG GÓI TIN GỬI SANG ADMIN
        verify_res = requests.post(f"{ADMIN_SERVER_URL}/api/verify", json={"key": user_key, "ip": client_ip}, timeout=10)
        v_data = verify_res.json()
        
        if verify_res.status_code != 200 or not (v_data.get("valid") or v_data.get("status") == "ok"):
            return render_template_string(LOGIN_HTML, error=f"❌ {v_data.get('message', 'Key sai, hết hạn hoặc sai IP!')}", last_key=user_key, client_ip=client_ip)
            
        # Nếu OK, lưu vào Session của trình duyệt khách
        session['user_key'] = user_key
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        return render_template_string(LOGIN_HTML, error=f"⚠️ Lỗi kết nối Máy chủ Key: {str(e)}", last_key=user_key, client_ip=client_ip)

# Trang Dashboard tải ảnh
@app.route('/dashboard')
def dashboard():
    if 'user_key' not in session:
        return redirect(url_for('index'))
    return render_template_string(DASHBOARD_HTML, error="")

# Nút Đăng xuất
@app.route('/logout')
def logout():
    session.pop('user_key', None)
    return redirect(url_for('index'))

# Xử lý nút Tải Ảnh
@app.route('/download', methods=['POST'])
def download_job():
    if 'user_key' not in session:
        return redirect(url_for('index'))

    user_key = session['user_key']
    client_ip = get_client_ip()
    raw_uuid = request.form.get('uuid', '').strip()
    
    if not raw_uuid:
        return render_template_string(DASHBOARD_HTML, error="❌ Vui lòng nhập Mã dự án!")

    # CHECK KEY LẠI 1 LẦN NỮA TRƯỚC KHI CHO TẢI ĐỂ ĐỀ PHÒNG KEY VỪA HẾT HẠN
    try:
        verify_res = requests.post(f"{ADMIN_SERVER_URL}/api/verify", json={"key": user_key, "ip": client_ip}, timeout=10)
        v_data = verify_res.json()
        if verify_res.status_code != 200 or not (v_data.get("valid") or v_data.get("status") == "ok"):
            session.pop('user_key', None) # Sút mẹ ra
            return render_template_string(LOGIN_HTML, error=f"❌ Key vừa hết hạn hoặc bị khóa: {v_data.get('message')}", last_key="", client_ip=client_ip)
    except: pass # Nếu check lỗi mạng thì tạm cho qua

    # ================= BẮT ĐẦU TẢI ẢNH =================
    match = re.search(r'([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})', raw_uuid)
    if not match:
        return render_template_string(DASHBOARD_HTML, error="❌ LỖI: Mã UUID không hợp lệ!")
    target_uuid = match.group(1)

    check_url = f"https://www.autohdr.com/api/proxy/photoshoots/uuid/{target_uuid}/processed_photos?page=1&page_size=100&_t={int(time.time())}"
    headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }
    
    try:
        res = requests.get(check_url, headers=headers, timeout=15)
        if res.status_code != 200:
            return render_template_string(DASHBOARD_HTML, error=f"❌ AUTOHDR TỪ CHỐI! Lỗi {res.status_code}. (Cần login hoặc sai mã)")
            
        data = res.json()
        photos = data if isinstance(data, list) else data.get('processed_photos', [])
        
        if not photos:
            return render_template_string(DASHBOARD_HTML, error="⏳ DỰ ÁN CHƯA XONG! Vui lòng đợi 5 phút rồi tải lại.")

        success_count = 0
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, photo in enumerate(photos):
                img_url = photo.get('url')
                if not img_url: continue
                
                from urllib.parse import unquote
                original_name = photo.get('name') or photo.get('original_name') or f"AutoHDR_Photo_{i+1}.jpg"
                original_name = unquote(original_name)
                
                img_res = requests.get(img_url, timeout=30)
                if img_res.status_code == 200:
                    zf.writestr(original_name, img_res.content)
                    success_count += 1
                    
        memory_file.seek(0)
        
        # Báo trừ lượt
        if success_count > 0:
            try: requests.post(f"{ADMIN_SERVER_URL}/api/consume", json={"key": user_key, "img_count": success_count, "count": success_count}, timeout=5)
            except: pass 
        
        safe_filename = f'Job_{target_uuid[:8]}.zip'
        return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name=safe_filename)

    except Exception as e:
        return render_template_string(DASHBOARD_HTML, error=f"❌ LỖI MÁY CHỦ WEB: {str(e)}")