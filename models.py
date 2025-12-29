# models.py
import sqlite3
import random
import openai
import hashlib
from datetime import datetime

# ==========================================
# 設定區
# ==========================================
DB_NAME = "quiz_system.db"
# 如果你有 OpenAI Key，請填入這裡；若無，程式會使用模擬回覆
OPENAI_API_KEY = ""  

# 題庫 (保留原本的)
WORDS = [
    {"en": "apple", "zh": "蘋果"},
    {"en": "abandon", "zh": "放棄"},
    {"en": "ability", "zh": "能力"},
    {"en": "accept", "zh": "接受"},
    {"en": "achievement", "zh": "成就"},
    {"en": "active", "zh": "活躍的"},
    {"en": "advice", "zh": "建議"},
    {"en": "airport", "zh": "機場"},
    {"en": "already", "zh": "已經"},
    {"en": "backyard", "zh": "後院"},
    {"en": "computer", "zh": "電腦"},
    {"en": "database", "zh": "資料庫"},
    {"en": "algorithm", "zh": "演算法"},
    {"en": "network", "zh": "網路"},
    {"en": "interface", "zh": "介面"},
]

# ==========================================
# 設計模式：Singleton (單例模式) 管理使用者狀態
# ==========================================
class UserSession:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserSession, cls).__new__(cls)
            cls._instance.current_user = None
        return cls._instance

    def login(self, username):
        self.current_user = username

    def logout(self):
        self.current_user = None
    
    def get_user(self):
        return self.current_user

# ==========================================
# 資料庫管理 (SQLite)
# ==========================================
class DBManager:
    @staticmethod
    def init_db():
        """初始化資料庫與資料表"""
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        # 使用者資料表
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (username TEXT PRIMARY KEY, password TEXT)''')
        # 成績資料表
        c.execute('''CREATE TABLE IF NOT EXISTS scores
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT, mode TEXT, score INTEGER, 
                      total INTEGER, percent REAL, time TEXT)''')
        conn.commit()
        conn.close()

    @staticmethod
    def verify_user(username, password):
        """驗證登入"""
        # 密碼簡單雜湊 (Hash) 處理，增加安全性
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, pwd_hash))
        result = c.fetchone()
        conn.close()
        return result is not None

    @staticmethod
    def register_user(username, password):
        """註冊新使用者"""
        if not username or not password:
            return False, "帳號密碼不能為空"
        
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, pwd_hash))
            conn.commit()
            conn.close()
            return True, "註冊成功"
        except sqlite3.IntegrityError:
            return False, "帳號已存在"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def save_score(mode, score, total):
        """儲存成績到 SQLite"""
        user = UserSession().get_user()
        if not user:
            return # 未登入不存檔
        
        percent = (score / total * 100) if total > 0 else 0
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO scores (username, mode, score, total, percent, time) VALUES (?, ?, ?, ?, ?, ?)",
                  (user, mode, score, total, percent, timestamp))
        conn.commit()
        conn.close()

    @staticmethod
    def get_top_scores(mode_filter=None, limit=20):
        """讀取排行榜"""
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        query = "SELECT username, mode, score, total, percent, time FROM scores"
        params = []
        
        if mode_filter:
            query += " WHERE mode=?"
            params.append(mode_filter)
            
        # 依正確率與分數排序
        query += " ORDER BY percent DESC, score DESC LIMIT ?"
        params.append(limit)
        
        c.execute(query, tuple(params))
        results = c.fetchall()
        conn.close()
        
        # 轉成字典列表格式以符合 UI 需求
        data = []
        for r in results:
            data.append({
                "name": r[0], "mode": r[1], "score": r[2], 
                "total": r[3], "percent": r[4], "time": r[5]
            })
        return data

# ==========================================
# 輔助功能 & AI API
# ==========================================
def get_quiz_questions(num_questions: int):
    words_copy = WORDS.copy()
    random.shuffle(words_copy)
    return words_copy[: min(num_questions, len(words_copy))]

def normalize(text: str) -> str:
    return text.strip().lower()

def get_ai_explanation(word: str):
    """呼叫 OpenAI API 解釋單字"""
    if not OPENAI_API_KEY:
        # 如果沒有 Key，回傳模擬訊息 (避免 Demo 失敗)
        return (f"【模擬 AI 回覆】\n\n單字：{word}\n"
                f"因為未設定 API Key，這是自動生成的範例。\n"
                f"例句：The {word} is very important for learning.")
    
    try:
        openai.api_key = OPENAI_API_KEY
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一位英文老師，請用繁體中文簡單解釋這個單字，並給一個英文例句。"},
                {"role": "user", "content": f"請解釋：{word}"}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 連線錯誤：{str(e)}"