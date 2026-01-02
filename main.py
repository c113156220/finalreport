import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QDialog
)
from PyQt5.QtCore import Qt

# 引用資料庫與使用者 Session 管理
from models import DBManager, UserSession

# 引用所有視窗介面 (包含連連看 MatchQuizWindow)
from windows_quiz import (
    LoginDialog, 
    FillQuizWindow, 
    ChoiceQuizWindow, 
    MatchQuizWindow, 
    RankingDialog
)

class MenuWindow(QWidget):
    """主選單視窗"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("英文單字學習系統 - 主選單")
        self.setFixedSize(450, 500)
        
        # 1. 取得目前登入的使用者名稱
        user_name = UserSession().get_user()
        
        # 2. 介面元件初始化
        label_title = QLabel("英文單字學習系統")
        label_title.setAlignment(Qt.AlignCenter)
        label_title.setStyleSheet("font-size: 22px; font-weight: bold; margin-bottom: 10px;")

        label_welcome = QLabel(f"歡迎回來，{user_name}！")
        label_welcome.setAlignment(Qt.AlignCenter)
        label_welcome.setStyleSheet("font-size: 16px; color: #1565c0;")
        
        self.btn_fill = QPushButton("填空模式（中文 → 英文）")
        self.btn_choice = QPushButton("選擇題模式（四選一）")
        self.btn_match = QPushButton("連連看模式（配對遊戲）") 
        self.btn_rank = QPushButton("查看排行榜")
        self.btn_exit = QPushButton("登出 / 離開")
        
        # 設定按鈕樣式與高度
        for btn in [self.btn_fill, self.btn_choice, self.btn_match, self.btn_rank, self.btn_exit]:
            btn.setMinimumHeight(45)
            btn.setStyleSheet("font-size: 20px;")
            
        # 特別將離開按鈕設為不同顏色
        self.btn_exit.setStyleSheet("background-color: #ffebee; color: #c62828; font-size: 20px;")

        # 3. 版面配置
        layout = QVBoxLayout()
        layout.addWidget(label_title)
        layout.addWidget(label_welcome)
        layout.addSpacing(20) # 增加一點間距
        layout.addWidget(self.btn_fill)
        layout.addWidget(self.btn_choice)
        layout.addWidget(self.btn_match)
        layout.addWidget(self.btn_rank)
        layout.addStretch() # 把按鈕往上頂，離開按鈕在最下
        layout.addWidget(self.btn_exit)

        self.setLayout(layout)

        # 4. 為了防止視窗被資源回收 (Garbage Collection)，建立變數保存子視窗參照
        self.current_window = None

        # 5. 連接按鈕訊號
        self.btn_fill.clicked.connect(self.open_fill_mode)
        self.btn_choice.clicked.connect(self.open_choice_mode)
        self.btn_match.clicked.connect(self.open_match_mode)
        self.btn_rank.clicked.connect(self.open_ranking)
        self.btn_exit.clicked.connect(self.close)

    def open_fill_mode(self):
        self.current_window = FillQuizWindow(num_questions=5)
        self.current_window.show()

    def open_choice_mode(self):
        self.current_window = ChoiceQuizWindow(num_questions=5)
        self.current_window.show()

    def open_match_mode(self):
        self.current_window = MatchQuizWindow(num_questions=5)
        self.current_window.show()

    def open_ranking(self):
        self.current_window = RankingDialog(self)
        self.current_window.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 步驟 1: 初始化資料庫 (若檔案不存在會自動建立)
    # 這符合專題報告加分項目：整合 SQLite
    DBManager.init_db()
    
    # 步驟 2: 顯示登入視窗
    # 必須先登入成功才能進入主選單
    login_window = LoginDialog()
    
    if login_window.exec_() == QDialog.Accepted:
        # 登入成功 (LoginDialog 內部驗證通過後會回傳 Accepted)
        menu_window = MenuWindow()
        menu_window.show()
        sys.exit(app.exec_())
    else:
        # 使用者關閉登入視窗或按下取消，則直接結束程式
        sys.exit()