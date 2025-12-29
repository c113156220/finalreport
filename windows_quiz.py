# windows_quiz.py
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QDialog,
    QTableWidget, QTableWidgetItem, QComboBox,
    QListWidget, QListWidgetItem, QInputDialog, QFormLayout
)
from PyQt5.QtCore import Qt
import random

from models import (
    get_quiz_questions, normalize, WORDS,
    DBManager, UserSession, get_ai_explanation
)

# ========= 連連看模式 (新增 AI 與 資料庫支援) =========
class MatchQuizWindow(QWidget):
    def __init__(self, num_questions=5):
        super().__init__()
        self.num_questions = min(num_questions, len(WORDS))
        self.score = 0
        self.pairs = []          
        self.left_selected = None
        self.right_selected = None
        self.matched_count = 0

        self.init_data()
        self.init_ui()

    def init_data(self):
        all_words = WORDS.copy()
        random.shuffle(all_words)
        self.pairs = all_words[: self.num_questions]
        self.matched_count = 0
        self.score = 0
        self.left_selected = None
        self.right_selected = None

    def init_ui(self):
        self.setWindowTitle(f"連連看模式 - 玩家: {UserSession().get_user()}")
        self.setFixedSize(1000, 650)

        label_instruction = QLabel("請點選左側中文與右側英文進行配對：")
        label_instruction.setAlignment(Qt.AlignCenter)

        # 左右列表
        self.list_left = QListWidget()
        self.list_right = QListWidget()
        self.list_left.setSelectionMode(QListWidget.SingleSelection)
        self.list_right.setSelectionMode(QListWidget.SingleSelection)

        self.list_left.itemClicked.connect(self.on_left_clicked)
        self.list_right.itemClicked.connect(self.on_right_clicked)

        self.label_status = QLabel("請開始配對")
        self.label_status.setAlignment(Qt.AlignCenter)

        # AI 按鈕 (新功能：解釋選中的單字)
        self.btn_ai = QPushButton("💡 AI 解說選定單字")
        self.btn_ai.setStyleSheet("background-color: #e0f7fa; color: #006064;")
        self.btn_ai.clicked.connect(self.show_ai_help)

        self.btn_restart = QPushButton("重新開始")
        self.btn_restart.clicked.connect(self.restart_match)

        # 版面配置
        lists_layout = QHBoxLayout()
        lists_layout.addWidget(self.list_left)
        lists_layout.addWidget(self.list_right)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.btn_ai)
        bottom_layout.addWidget(self.btn_restart)

        main_layout = QVBoxLayout()
        main_layout.addWidget(label_instruction)
        main_layout.addLayout(lists_layout)
        main_layout.addWidget(self.label_status)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)
        self.load_lists()

    def load_lists(self):
        self.list_left.clear()
        self.list_right.clear()
        
        # 左邊放中文 (隱藏英文 data)
        for w in self.pairs:
            item = QListWidgetItem(w["zh"])
            item.setData(Qt.UserRole, w["en"])
            self.list_left.addItem(item)

        # 右邊放英文 (打亂)
        en_list = [w["en"] for w in self.pairs]
        random.shuffle(en_list)
        for en in en_list:
            item = QListWidgetItem(en)
            # 反查中文當 data
            zh = next(w["zh"] for w in self.pairs if w["en"] == en)
            item.setData(Qt.UserRole, zh)
            self.list_right.addItem(item)

    def on_left_clicked(self, item):
        self.left_selected = item
        self.check_pair()

    def on_right_clicked(self, item):
        self.right_selected = item
        self.check_pair()

    def check_pair(self):
        if not self.left_selected or not self.right_selected:
            return

        zh_text = self.left_selected.text()
        en_text = self.right_selected.text()

        # 檢查是否匹配
        is_correct = any((w["zh"] == zh_text and w["en"] == en_text) for w in self.pairs)

        if is_correct:
            self.matched_count += 1
            self.score += 1
            self.label_status.setText(f"配對成功！目前進度：{self.matched_count}/{self.num_questions}")
            
            # 鎖定已配對項目
            for item in [self.left_selected, self.right_selected]:
                item.setFlags(Qt.NoItemFlags) # 禁止再選
                item.setForeground(Qt.gray)   # 變灰色
                item.setSelected(False)       # 取消選取狀態
        else:
            self.label_status.setText("配對錯誤，請再試一次")
            # 取消選取讓使用者重選
            self.list_left.clearSelection()
            self.list_right.clearSelection()

        self.left_selected = None
        self.right_selected = None

        if self.matched_count >= self.num_questions:
            self.show_final_result()

    def show_ai_help(self):
        """解釋目前選取的單字 (左邊或右邊)"""
        target_word = None
        
        # 優先看右邊選了哪個英文
        if self.list_right.currentItem() and self.list_right.currentItem().isSelected():
            target_word = self.list_right.currentItem().text()
        # 其次看左邊選了哪個中文 (取出隱藏的英文 data)
        elif self.list_left.currentItem() and self.list_left.currentItem().isSelected():
            target_word = self.list_left.currentItem().data(Qt.UserRole)
            
        if target_word:
            self.label_status.setText("AI 正在查詢中...")
            self.repaint()
            explanation = get_ai_explanation(target_word)
            QMessageBox.information(self, "AI 解說", explanation)
            self.label_status.setText("")
        else:
            QMessageBox.warning(self, "提示", "請先點選一個單字，再按 AI 解說")

    def show_final_result(self):
        # 改用 DBManager 存檔
        DBManager.save_score("連連看", self.score, self.num_questions)
        QMessageBox.information(self, "完成", 
            f"恭喜！完成所有配對。\n得分：{self.score}/{self.num_questions}")
        self.close()

    def restart_match(self):
        self.init_data()
        self.load_lists()

# ========= 登入視窗 (頂部顯示圖片) =========
class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("英文學習系統 - 使用者登入")
        self.setFixedSize(500, 400)

        main_layout = QVBoxLayout()

        # 1. 最上方圖片
        icon_label = QLabel()
        pix = QPixmap("ABC.png")   # 換成你的圖檔名稱
        if not pix.isNull():
            pix = pix.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pix)
            icon_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(icon_label)

        # 2. 帳號 / 密碼表單
        self.edit_user = QLineEdit()
        self.edit_pwd = QLineEdit()
        self.edit_pwd.setEchoMode(QLineEdit.Password)

        form_layout = QFormLayout()
        form_layout.addRow("帳號：", self.edit_user)
        form_layout.addRow("密碼：", self.edit_pwd)

        main_layout.addLayout(form_layout)

        # 3. 按鈕區
        btn_layout = QHBoxLayout()
        self.btn_login = QPushButton("登入")
        self.btn_register = QPushButton("註冊新帳號")
        btn_layout.addWidget(self.btn_login)
        btn_layout.addWidget(self.btn_register)

        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        self.btn_login.clicked.connect(self.handle_login)
        self.btn_register.clicked.connect(self.handle_register)

    def handle_login(self):
        user = self.edit_user.text().strip()
        pwd = self.edit_pwd.text().strip()
        if DBManager.verify_user(user, pwd):
            UserSession().login(user)
            self.accept()
        else:
            QMessageBox.warning(self, "錯誤", "帳號或密碼錯誤")

    def handle_register(self):
        user = self.edit_user.text().strip()
        pwd = self.edit_pwd.text().strip()
        success, msg = DBManager.register_user(user, pwd)
        if success:
            QMessageBox.information(self, "成功", "註冊成功，請登入")
        else:
            QMessageBox.warning(self, "失敗", msg)


# ========= 填空模式 =========
class FillQuizWindow(QWidget):
    def __init__(self, num_questions=5):
        super().__init__()
        self.num_questions = num_questions
        self.current_index = 0
        self.score = 0
        self.question_list = []
        self.init_data()
        self.init_ui()
        self.load_question()

    def init_data(self):
        self.question_list = get_quiz_questions(self.num_questions)

    def init_ui(self):
        self.setWindowTitle(f"填空模式 - 玩家: {UserSession().get_user()}")
        self.setFixedSize(550, 400) # 加大一點給 AI 文字

        self.label_word = QLabel("")
        self.label_word.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.label_word.setAlignment(Qt.AlignCenter)
        
        self.edit_answer = QLineEdit()
        self.edit_answer.setPlaceholderText("輸入英文答案")
        self.edit_answer.returnPressed.connect(self.check_answer)

        self.label_feedback = QLabel("")
        self.label_feedback.setAlignment(Qt.AlignCenter)
        
        # AI 按鈕
        self.btn_ai = QPushButton("💡 AI 老師解說")
        self.btn_ai.setStyleSheet("background-color: #e0f7fa; color: #006064;")
        self.btn_ai.clicked.connect(self.show_ai_help)

        self.btn_check = QPushButton("確認")
        self.btn_next = QPushButton("下一題")
        self.btn_check.clicked.connect(self.check_answer)
        self.btn_next.clicked.connect(self.next_question)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("請輸入對應的英文："))
        layout.addWidget(self.label_word)
        layout.addWidget(self.edit_answer)
        layout.addWidget(self.btn_ai) # 加入介面
        layout.addWidget(self.label_feedback)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_check)
        btn_layout.addWidget(self.btn_next)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def load_question(self):
        if self.current_index >= self.num_questions:
            self.show_final_result()
            return
        word = self.question_list[self.current_index]
        self.label_word.setText(word["zh"])
        self.label_feedback.setText("")
        self.edit_answer.clear()

    def show_ai_help(self):
        """呼叫 AI API"""
        if self.current_index >= len(self.question_list): return
        
        current_word_en = self.question_list[self.current_index]["en"]
        self.label_feedback.setText("🤖 AI 正在思考中...")
        self.repaint() # 強制刷新介面
        
        explanation = get_ai_explanation(current_word_en)
        QMessageBox.information(self, f"{current_word_en} - AI 解說", explanation)
        self.label_feedback.setText("")

    def check_answer(self):
        user_input = normalize(self.edit_answer.text())
        correct = normalize(self.question_list[self.current_index]["en"])
        
        if user_input == correct:
            self.score += 1
            self.label_feedback.setText("✔ 正確！")
            self.label_feedback.setStyleSheet("color: green;")
        else:
            self.label_feedback.setText(f"✘ 錯誤，答案是: {correct}")
            self.label_feedback.setStyleSheet("color: red;")

    def next_question(self):
        self.current_index += 1
        self.load_question()

    def show_final_result(self):
        # 自動存入資料庫，不需要再手動輸入名字
        DBManager.save_score("填空", self.score, self.num_questions)
        QMessageBox.information(self, "結果", f"得分：{self.score}/{self.num_questions}")
        self.close()

# ========= 選擇題模式 =========
class ChoiceQuizWindow(QWidget):
    def __init__(self, num_questions=5):
        super().__init__()
        self.num_questions = num_questions
        self.current_index = 0
        self.score = 0
        self.question_list = []
        self.btn_options = []
        self.init_data()
        self.init_ui()
        self.load_question()

    def init_data(self):
        self.question_list = get_quiz_questions(self.num_questions)

    def init_ui(self):
        self.setWindowTitle(f"選擇題模式 - 玩家: {UserSession().get_user()}")
        self.setFixedSize(500, 450)

        self.label_word = QLabel("")
        self.label_word.setAlignment(Qt.AlignCenter)
        self.label_word.setStyleSheet("font-size: 24px; font-weight: bold;")

        self.label_feedback = QLabel("")
        self.label_feedback.setAlignment(Qt.AlignCenter)

        # AI 按鈕
        self.btn_ai = QPushButton("💡 AI 老師解說")
        self.btn_ai.setStyleSheet("background-color: #e0f7fa; color: #006064;")
        self.btn_ai.clicked.connect(self.show_ai_help)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("請選擇正確的英文單字："))
        layout.addWidget(self.label_word)
        layout.addWidget(self.btn_ai)

        for i in range(4):
            btn = QPushButton(f"選項 {i+1}")
            btn.clicked.connect(self.on_option_clicked)
            self.btn_options.append(btn)
            layout.addWidget(btn)

        layout.addWidget(self.label_feedback)
        
        self.btn_next = QPushButton("下一題")
        self.btn_next.clicked.connect(self.next_question)
        layout.addWidget(self.btn_next)

        self.setLayout(layout)

    def load_question(self):
        if self.current_index >= self.num_questions:
            self.show_final_result()
            return
        
        word = self.question_list[self.current_index]
        self.correct_answer = word["en"]
        self.label_word.setText(word["zh"])
        self.label_feedback.setText("")
        
        # 產生選項
        options = [word["en"]]
        while len(options) < 4:
            w = random.choice(WORDS)["en"]
            if w not in options:
                options.append(w)
        random.shuffle(options)
        
        for i, btn in enumerate(self.btn_options):
            btn.setText(options[i])
            btn.setEnabled(True)
            btn.setStyleSheet("")

    def show_ai_help(self):
        if self.current_index >= len(self.question_list): return
        current_word_en = self.question_list[self.current_index]["en"]
        self.label_feedback.setText("🤖 AI 正在思考中...")
        self.repaint()
        explanation = get_ai_explanation(current_word_en)
        QMessageBox.information(self, "AI 解說", explanation)
        self.label_feedback.setText("")

    def on_option_clicked(self):
        sender = self.sender()
        if sender.text() == self.correct_answer:
            self.score += 1
            self.label_feedback.setText("✔ 正確！")
            sender.setStyleSheet("background-color: #a5d6a7;") # 綠色
        else:
            self.label_feedback.setText(f"✘ 錯誤，答案是 {self.correct_answer}")
            sender.setStyleSheet("background-color: #ef9a9a;") # 紅色
        
        for btn in self.btn_options:
            btn.setEnabled(False)

    def next_question(self):
        self.current_index += 1
        self.load_question()

    def show_final_result(self):
        DBManager.save_score("選擇題", self.score, self.num_questions)
        QMessageBox.information(self, "結果", f"得分：{self.score}/{self.num_questions}")
        self.close()

# ========= 排行榜 (資料庫版) =========
class RankingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("排行榜 (Top 20)")
        self.resize(600, 400)
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["全部", "填空", "選擇題"])
        self.combo_mode.currentIndexChanged.connect(self.refresh_table)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["排名", "玩家", "模式", "分數", "正確率"])
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("篩選模式："))
        layout.addWidget(self.combo_mode)
        layout.addWidget(self.table)
        self.setLayout(layout)
        
        self.refresh_table()

    def refresh_table(self):
        mode = self.combo_mode.currentText()
        if mode == "全部": mode = None
        
        records = DBManager.get_top_scores(mode)
        self.table.setRowCount(len(records))
        
        for i, r in enumerate(records):
            self.table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            self.table.setItem(i, 1, QTableWidgetItem(r['name']))
            self.table.setItem(i, 2, QTableWidgetItem(r['mode']))
            self.table.setItem(i, 3, QTableWidgetItem(f"{r['score']}/{r['total']}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{r['percent']:.1f}%"))