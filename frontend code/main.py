import sys
import requests
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QStackedWidget, 
                             QMessageBox, QHBoxLayout, QFrame, QTabWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, 
                             QListWidgetItem)
from PyQt6.QtCore import Qt
import pyqtgraph as pg
from PyQt6.QtGui import QPainter, QPicture

#FastAPI server address
API_URL = "https://turing.cs.olemiss.edu/~mhnguye5/SeniorProject"


class CandlestickItem(pg.GraphicsObject):
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data  # List of (time, open, close, low, high)
        self.generatePicture()

    def generatePicture(self):
        self.picture = QPicture()
        p = QPainter(self.picture)
        # Use a width of 0.6 for the candles
        w = 0.6
        for (t, open, close, low, high) in self.data:
            # Green if close > open, Red if close < open
            p.setPen(pg.mkPen('w'))
            p.setBrush(pg.mkBrush('g' if open < close else 'r'))
            
            # Draw the wick (high to low)
            p.drawLine(pg.QtCore.QPointF(t, low), pg.QtCore.QPointF(t, high))
            # Draw the body (open to close)
            p.drawRect(pg.QtCore.QRectF(t - w/2, open, w, close - open))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return pg.QtCore.QRectF(self.picture.boundingRect())
    
class TimeAxisItem(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x_labels = {} # Dictionary mapping index (0, 1, 2) to Date strings

    def tickStrings(self, values, scale, spacing):
        # pyqtgraph passes in the x-coordinates currently visible on screen.
        # We look up the date string for each coordinate.
        return [self.x_labels.get(int(value), "") for value in values]
    

class LoginScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Centered container for inputs so they don't stretch across the giant screen
        container = QVBoxLayout()
        container.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Trading Simulator")
        title.setStyleSheet("font-size: 36px; font-weight: bold; margin-bottom: 5px; color: #f8fafc;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Log In to Your Account")
        subtitle.setStyleSheet("font-size: 16px; margin-bottom: 30px; color: #94a3b8;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setMaximumWidth(400)
        self.username_input.returnPressed.connect(self.attempt_login)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMaximumWidth(400)
        self.password_input.returnPressed.connect(self.attempt_login)
        
        login_btn = QPushButton("Log In")
        login_btn.setObjectName("AuthBtn")
        login_btn.setMaximumWidth(400)
        login_btn.clicked.connect(self.attempt_login)
        
        switch_to_signup_btn = QPushButton("Don't have an account? Sign Up")
        switch_to_signup_btn.setProperty("flat", True) # Triggers the transparent QSS style
        switch_to_signup_btn.setMaximumWidth(400)
        switch_to_signup_btn.clicked.connect(lambda: self.main_window.switch_screen(1))

        container.addWidget(title)
        container.addWidget(subtitle)
        container.addWidget(self.username_input)
        container.addWidget(self.password_input)
        container.addWidget(login_btn)
        container.addWidget(switch_to_signup_btn)
        
        layout.addLayout(container)
        self.setLayout(layout)

    def attempt_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please fill in all fields.")
            return

        try:
            response = requests.post(f"{API_URL}/login", json={"username": username, "password": password})
            
            if response.status_code == 200:
                data = response.json()
                self.main_window.current_user_id = data.get("user_id") 
                self.main_window.switch_screen(2)
            else:
                error_msg = response.json().get("detail", "Login failed")
                QMessageBox.warning(self, "Error", error_msg)
                
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Connection Error", "Could not connect to the server. Is FastAPI running?")

class SignupScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        container = QVBoxLayout()
        container.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Trading Simulator")
        title.setStyleSheet("font-size: 36px; font-weight: bold; margin-bottom: 5px; color: #f8fafc;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Create a New Account")
        subtitle.setStyleSheet("font-size: 16px; margin-bottom: 30px; color: #94a3b8;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Choose a Username")
        self.username_input.setMaximumWidth(400)
        self.username_input.returnPressed.connect(self.attempt_signup)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Choose a Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMaximumWidth(400)
        self.password_input.returnPressed.connect(self.attempt_signup)
        
        signup_btn = QPushButton("Sign Up")
        signup_btn.setObjectName("AuthBtn")
        signup_btn.setMaximumWidth(400)
        signup_btn.clicked.connect(self.attempt_signup)
        
        switch_to_login_btn = QPushButton("Already have an account? Log In")
        switch_to_login_btn.setProperty("flat", True)
        switch_to_login_btn.setMaximumWidth(400)
        switch_to_login_btn.clicked.connect(lambda: self.main_window.switch_screen(0))

        container.addWidget(title)
        container.addWidget(subtitle)
        container.addWidget(self.username_input)
        container.addWidget(self.password_input)
        container.addWidget(signup_btn)
        container.addWidget(switch_to_login_btn)
        
        layout.addLayout(container)
        self.setLayout(layout)

    def attempt_signup(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please fill in all fields.")
            return

        try:
            response = requests.post(f"{API_URL}/signup", json={"username": username, "password": password})
            
            if response.status_code == 200:
                QMessageBox.information(self, "Success", "Account created! You can now log in.")
                self.main_window.switch_screen(0)
            else:
                error_msg = response.json().get("detail", "Signup failed")
                QMessageBox.warning(self, "Error", error_msg)
                
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Connection Error", "Could not connect to the server.")

class HomeScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.current_timeframe = "1W" # defaulted 1W for portfolio chart
        self.main_window = main_window
        self.init_ui()
    
    def init_ui(self):
        # 1. Main Window Layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 0, 0, 0) # Remove outer margins for edge-to-edge look

    


        # --- Top Bar (Header) ---
        top_bar_container = QWidget()
        top_bar_container.setStyleSheet("background-color: #161720; border-bottom: 2px solid #2C2F3F;")
        top_bar = QHBoxLayout(top_bar_container)
        top_bar.setContentsMargins(20, 15, 20, 15)
        
        title = QLabel("Trading Simulator")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #f8fafc; border: none;")
        
        self.balance_label = QLabel("Cash Balance: $0.00")
        self.balance_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #1DD3B0; border: none;") 
        self.balance_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        top_bar.addWidget(title)
        top_bar.addWidget(self.balance_label)
        layout.addWidget(top_bar_container)

        # --- Main Split (Sidebar Left, Content Right) ---
        main_split = QHBoxLayout()
        main_split.setContentsMargins(0, 0, 0, 0)
        main_split.setSpacing(0)

        # === LEFT SIDEBAR ===
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(10)

        # Sidebar Navigation Buttons
        self.btn_dash = QPushButton("My Portfolio")
        self.btn_trade = QPushButton("Trade")
        self.btn_community = QPushButton("Community")
        self.btn_leader = QPushButton("Leaderboard")
        
        nav_buttons = [self.btn_dash, self.btn_trade, self.btn_community, self.btn_leader]
        for btn in nav_buttons:
            btn.setObjectName("NavBtn")
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        logout_btn = QPushButton("Log Out")
        logout_btn.setObjectName("NavBtn")
        logout_btn.setStyleSheet("color: #ef4444;") # Make it red
        logout_btn.clicked.connect(self.logout)
        sidebar_layout.addWidget(logout_btn)

        # === RIGHT CONTENT AREA ===
        self.pages = QStackedWidget()
        
        # --- PAGE 0: Dashboard (My Portfolio) ---
        self.page_dash = QWidget()
        dash_layout = QVBoxLayout(self.page_dash)
        dash_layout.setContentsMargins(30, 30, 30, 30)
        dash_layout.setSpacing(20)
        
        # 1. Total Value Header
        value_layout = QHBoxLayout()
        self.total_value_label = QLabel("$100,000.00")
        self.total_value_label.setStyleSheet("font-size: 36px; font-weight: bold; color: white;")
        
        self.percent_change_label = QLabel("+0.00 (0.00%)")
        self.percent_change_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #10b981; margin-left: 10px;")
        
        value_layout.addWidget(self.total_value_label)
        value_layout.addWidget(self.percent_change_label)
        value_layout.addStretch()
        
        # 2. Timeframe Buttons
        timeframe_layout = QHBoxLayout()
        timeframe_layout.setSpacing(8) # Adds a little breathing room between buttons
        
        for tf in ["1D", "1W", "1M", "1Y"]:
            btn = QPushButton(tf)
            btn.setFixedSize(50, 35) 
            btn.setStyleSheet("""
                QPushButton { background-color: #2C2F3F; color: white; border-radius: 6px; font-weight: bold; }
                QPushButton:hover { background-color: #53298a; }
            """)
            
            btn.clicked.connect(lambda checked, t=tf: self.change_timeframe(t))
            
            timeframe_layout.addWidget(btn)
        timeframe_layout.addStretch()

        dash_layout.addLayout(value_layout)
        dash_layout.addLayout(timeframe_layout)

        # 3. The Account Balance Chart
        self.portfolio_chart = pg.PlotWidget()
        self.portfolio_chart.setBackground('#1c1426')
        self.portfolio_chart.setFixedHeight(250)
        
        # Turn the grid back on (faint lines)
        self.portfolio_chart.showGrid(x=True, y=True, alpha=0.2)
        
        # Keep axes active so the grid draws, but hide numbers and little tick lines
        self.portfolio_chart.getAxis('left').setStyle(showValues=False)
        self.portfolio_chart.getAxis('left').setTicks([])
        self.portfolio_chart.getAxis('bottom').setStyle(showValues=False)
        self.portfolio_chart.getAxis('bottom').setTicks([])
        
        # Hide the little [A] button in the bottom left corner
        self.portfolio_chart.hideButtons()
        
        self.portfolio_chart.setMouseEnabled(x=False, y=False)
        dash_layout.addWidget(self.portfolio_chart)

        # 4. The Holdings Table
        holdings_label = QLabel("Current Holdings")
        holdings_label.setStyleSheet("font-size: 20px; font-weight: bold; color: white; margin-top: 10px;")
        dash_layout.addWidget(holdings_label)

        self.holdings_table = QTableWidget()
        self.holdings_table.setColumnCount(6)
        self.holdings_table.setHorizontalHeaderLabels(["Ticker", "Shares", "Avg Cost", "Current Price", "Total Value", "Return %"])
        
        # Stretch columns to fill screen
        self.holdings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Styling
        self.holdings_table.setStyleSheet("""
            QTableWidget {
                background-color: #1c1426;
                color: white;
                border: 1px solid #2C2F3F;
                border-radius: 8px;
                gridline-color: #2C2F3F;
            }
            QHeaderView::section {
                background-color: #2C2F3F;
                color: #94a3b8;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
        """)
        dash_layout.addWidget(self.holdings_table)

        # --- PAGE 1: Trade ---
        self.page_trade = QWidget()
        trade_layout = QHBoxLayout(self.page_trade) # Split Trade screen into Left (Candles) and Right (Execution)
        trade_layout.setContentsMargins(30, 30, 30, 30)
        
       # Left side of Trade: Charting Area
        candles_frame = QFrame()
        candles_frame.setStyleSheet("background-color: #1c1426; border-radius: 12px;")
        candles_layout = QVBoxLayout(candles_frame)

        # --- NEW: Trade Timeframe Buttons ---
        trade_tf_layout = QHBoxLayout()
        for tf in ["1D", "1W", "1M"]:
            btn = QPushButton(tf)
            btn.setFixedSize(50, 35)
            btn.setStyleSheet("""
                QPushButton { background-color: #2C2F3F; color: white; border-radius: 6px; font-weight: bold; }
                QPushButton:hover { background-color: #53298a; }
            """)
            btn.clicked.connect(lambda checked, t=tf: self.change_trade_timeframe(t))
            trade_tf_layout.addWidget(btn)
        trade_tf_layout.addStretch()
        candles_layout.addLayout(trade_tf_layout)

        
        # --- Create the actual PlotWidget WITH CUSTOM AXIS ---
        self.trade_time_axis = TimeAxisItem(orientation='bottom')
        self.trade_chart = pg.PlotWidget(axisItems={'bottom': self.trade_time_axis})
        self.trade_chart.setBackground('#1c1426')
        self.trade_chart.showGrid(x=True, y=True, alpha=0.3)
        candles_layout.addWidget(self.trade_chart)
        
        # --- Crosshairs & Hover Text ---
        self.trade_vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#94a3b8', width=1, style=Qt.PenStyle.DashLine))
        self.trade_hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#94a3b8', width=1, style=Qt.PenStyle.DashLine))
        self.trade_hover_label = pg.TextItem(color='#f8fafc', fill=(28, 30, 40, 200))
        
        # We will add these to the chart dynamically in get_quote!
        
        self.trade_chart.scene().sigMouseMoved.connect(self.trade_mouse_moved)
        self.trade_timeframe = "1M" 
        self.trade_history_data = []
        
        # Hide them initially
        self.trade_vLine.hide()
        self.trade_hLine.hide()
        self.trade_hover_label.hide()
        
        # Connect mouse movement to our new function
        self.trade_chart.scene().sigMouseMoved.connect(self.trade_mouse_moved)
        
        # State variables for the trade chart
        self.trade_timeframe = "1M" 
        self.trade_history_data = [] # Stores raw API data for hovering
        
        # Right side of Trade: Execution Panel
        trade_frame = QFrame()
        trade_frame.setFixedWidth(350)
        trade_frame.setStyleSheet("background-color: #1c1426; border-radius: 12px;")
        trade_desk = QVBoxLayout(trade_frame)
        trade_desk.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        desk_title = QLabel("Execute Trade")
        desk_title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px; color: white;")
        
        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("Enter Ticker (e.g., AAPL)")
        self.ticker_input.returnPressed.connect(self.get_quote)
        
        self.quote_btn = QPushButton("Fetch Price")
        self.quote_btn.setMinimumHeight(40)
        self.quote_btn.setStyleSheet("background-color: #0a050f; color: white;")
        self.quote_btn.clicked.connect(self.get_quote)
        
        self.price_label = QLabel("Current Price: ---")
        self.price_label.setStyleSheet("font-size: 16px; color: #38bdf8; margin: 15px 0px;")
        
        self.qty_input = QLineEdit()
        self.qty_input.setPlaceholderText("Quantity")
        
        btn_layout = QHBoxLayout()
        self.buy_btn = QPushButton("BUY")
        self.buy_btn.setStyleSheet("background-color: #10b981; color: white;")
        self.buy_btn.clicked.connect(self.buy_stock)
        
        self.sell_btn = QPushButton("SELL")
        self.sell_btn.setStyleSheet("background-color: #ef4444; color: white;")
        self.sell_btn.clicked.connect(self.sell_stock)
        
        btn_layout.addWidget(self.buy_btn)
        btn_layout.addWidget(self.sell_btn)

        trade_desk.addWidget(desk_title)
        trade_desk.addWidget(self.ticker_input)
        trade_desk.addWidget(self.quote_btn)
        trade_desk.addWidget(self.price_label)
        trade_desk.addWidget(self.qty_input)
        trade_desk.addLayout(btn_layout)
        trade_desk.addStretch()

        trade_layout.addWidget(candles_frame)
        trade_layout.addWidget(trade_frame)

# --- PAGE 2: Community ---
        self.page_community = QWidget()
        
        # Main layout is top-to-bottom (Top Bar over the Left/Right split)
        comm_main_layout = QVBoxLayout(self.page_community)
        comm_main_layout.setContentsMargins(30, 30, 30, 30)
        comm_main_layout.setSpacing(20)

        # === TOP PANEL: Search & Privacy Toggle ===
        top_bar_layout = QHBoxLayout()
        
        self.user_search_input = QLineEdit()
        self.user_search_input.setPlaceholderText("🔍 Search users and press Enter...")
        self.user_search_input.setFixedWidth(350)
        self.user_search_input.returnPressed.connect(self.search_users) # Trigger on Enter
        
        # Button to quickly return to your "Following" list after searching
        self.clear_search_btn = QPushButton("✖ Clear")
        self.clear_search_btn.setStyleSheet("background-color: #475569; color: white;")
        self.clear_search_btn.setFixedWidth(80)
        self.clear_search_btn.hide() # Hidden until a search happens
        self.clear_search_btn.clicked.connect(self.load_following_list)
        
        self.privacy_btn = QPushButton("Portfolio: PRIVATE")
        self.privacy_btn.setCheckable(True)
        self.privacy_btn.setFixedWidth(180)
        self.privacy_btn.setStyleSheet("""
            QPushButton { background-color: #ef4444; color: white; border-radius: 6px; font-weight: bold; }
            QPushButton:checked { background-color: #10b981; }
        """)
        self.privacy_btn.clicked.connect(self.toggle_privacy)

        top_bar_layout.addWidget(self.user_search_input)
        top_bar_layout.addWidget(self.clear_search_btn)
        top_bar_layout.addStretch() # Pushes the privacy toggle to the far right
        top_bar_layout.addWidget(self.privacy_btn)
        
        comm_main_layout.addLayout(top_bar_layout)

        # === BOTTOM PANEL: Left (List) & Right (Portfolio) ===
        comm_split_layout = QHBoxLayout()
        comm_split_layout.setSpacing(20)

        # -- LEFT SIDE: The User List --
        comm_left_frame = QFrame()
        comm_left_frame.setFixedWidth(250)
        comm_left_frame.setStyleSheet("background-color: #1c1426; border-radius: 12px;")
        comm_left_layout = QVBoxLayout(comm_left_frame)
        
        # Dynamic label to show what list we are looking at
        self.list_title_label = QLabel("Following")
        self.list_title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white; margin-bottom: 5px;")
        comm_left_layout.addWidget(self.list_title_label)
        
        self.community_list = QListWidget()
        self.community_list.setStyleSheet("""
            QListWidget { background-color: #110e14; color: white; border-radius: 6px; padding: 5px; outline: none; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #2C2F3F; border-radius: 4px; }
            QListWidget::item:selected { background-color: #3b82f6; color: white; font-weight: bold; }
            QListWidget::item:hover { background-color: #2C2F3F; }
        """)
        self.community_list.itemClicked.connect(self.load_spy_portfolio)
        comm_left_layout.addWidget(self.community_list)

        # -- RIGHT SIDE: The Spy Portfolio View --
        comm_right_frame = QFrame()
        comm_right_frame.setStyleSheet("background-color: #1c1426; border-radius: 12px;")
        comm_right_layout = QVBoxLayout(comm_right_frame)
        
        self.spy_username_label = QLabel("Select a user to view their portfolio")
        self.spy_username_label.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        
        self.follow_btn = QPushButton("Follow User")
        self.follow_btn.clicked.connect(self.toggle_follow_user)
        self.follow_btn.setStyleSheet("background-color: #10b981; color: white; font-weight: bold;")
        self.follow_btn.setFixedWidth(150)
        self.follow_btn.hide()
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(self.spy_username_label)
        header_layout.addWidget(self.follow_btn)
        header_layout.addStretch()
        comm_right_layout.addLayout(header_layout)
        
        self.spy_time_axis = TimeAxisItem(orientation='bottom')
        self.spy_chart = pg.PlotWidget(axisItems={'bottom': self.spy_time_axis})
        self.spy_chart.setBackground('#1c1426') # This will now stick!
        self.spy_chart.setFixedHeight(250)
        self.spy_chart.showGrid(x=True, y=True, alpha=0.2)
        comm_right_layout.addWidget(self.spy_chart)
        
        self.spy_table = QTableWidget()
        self.spy_table.setColumnCount(6)
        self.spy_table.setHorizontalHeaderLabels(["Ticker", "Shares", "Avg Cost", "Current Price", "Total Value", "Return %"])
        self.spy_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.spy_table.setStyleSheet(self.holdings_table.styleSheet())
        comm_right_layout.addWidget(self.spy_table)

        # Assemble the split layout
        comm_split_layout.addWidget(comm_left_frame)
        comm_split_layout.addWidget(comm_right_frame)
        
        comm_main_layout.addLayout(comm_split_layout)

        # --- PAGE 3: Leaderboard ---
        self.leaderboard_widget = QWidget()
        self.lb_layout = QVBoxLayout(self.leaderboard_widget)
        # 1. Timeframe Buttons
        self.lb_btn_layout = QHBoxLayout()
        self.btn_1w = QPushButton("Weekly")
        self.btn_1m = QPushButton("Monthly")
        self.btn_all = QPushButton("All-Time")
        
        self.lb_btn_layout.addWidget(self.btn_1w)
        self.lb_btn_layout.addWidget(self.btn_1m)
        self.lb_btn_layout.addWidget(self.btn_all)
        self.lb_layout.addLayout(self.lb_btn_layout)

        # 2. Top 10 List Widget
        self.leaderboard_list = QListWidget()
        self.leaderboard_list.setStyleSheet("font-size: 14px; padding: 5px;")
        self.lb_layout.addWidget(self.leaderboard_list)

        # 3. Pinned "My Rank" Label at the bottom
        self.my_rank_label = QLabel("Your Rank: Loading...")
        self.my_rank_label.setStyleSheet("""
            font-weight: bold; 
            padding: 12px; 
            background-color: #1e293b; 
            color: white; 
            border-radius: 6px;
            font-size: 14px;
        """)
        self.my_rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb_layout.addWidget(self.my_rank_label)
        
        self.page_leader = QWidget()
        self.page_leader_layout = QVBoxLayout(self.page_leader)
        self.page_leader_layout.addWidget(self.leaderboard_widget)

        # --- WIRE UP THE BUTTONS ---
        self.btn_1w.clicked.connect(lambda: self.load_leaderboard("1W"))
        self.btn_1m.clicked.connect(lambda: self.load_leaderboard("1M"))
        self.btn_all.clicked.connect(lambda: self.load_leaderboard("ALL"))
        
        # The Magic Trick: Connect clicks directly to your existing Spy method!
        self.leaderboard_list.itemClicked.connect(self.load_spy_portfolio)

        # Add all pages to the stack
        self.pages.addWidget(self.page_dash)      # Index 0
        self.pages.addWidget(self.page_trade)     # Index 1
        self.pages.addWidget(self.page_community) # Index 2
        self.pages.addWidget(self.page_leader)    # Index 3

        # Assemble the main split
        main_split.addWidget(sidebar)
        main_split.addWidget(self.pages)
        layout.addLayout(main_split)
        
        self.setLayout(layout)

        # --- Navigation Wiring ---
        self.btn_dash.clicked.connect(lambda: self.switch_tab(0))
        self.btn_trade.clicked.connect(lambda: self.switch_tab(1))
        self.btn_community.clicked.connect(lambda: self.switch_tab(2))
        self.btn_leader.clicked.connect(lambda: self.switch_tab(3))

    def change_trade_timeframe(self, tf):
        self.trade_timeframe = tf
        # Re-fetch the quote/chart with the new timeframe if a ticker is already entered
        if self.ticker_input.text():
            self.get_quote()

    def trade_mouse_moved(self, evt):
        if self.trade_chart.sceneBoundingRect().contains(evt):
            mousePoint = self.trade_chart.plotItem.vb.mapSceneToView(evt)
            idx = int(round(mousePoint.x()))
            
            if 0 <= idx < len(self.trade_history_data):
                candle = self.trade_history_data[idx]
                date_str = candle.get("Date", candle.get("Datetime", "Unknown Time"))
                
                o = float(candle.get("Open", candle.get("open", 0)))
                c = float(candle.get("Close", candle.get("close", 0)))
                h = float(candle.get("High", candle.get("high", 0)))
                l = float(candle.get("Low", candle.get("low", 0)))
                
                text = f"{date_str}\nO: {o:,.2f}  C: {c:,.2f}\nH: {h:,.2f}  L: {l:,.2f}"
                self.trade_hover_label.setText(text)
                
                self.trade_vLine.setPos(idx) 
                self.trade_hLine.setPos(mousePoint.y())
                
                # Prevent tooltip from clipping off the right side of the screen
                if idx > len(self.trade_history_data) - 10:
                    self.trade_hover_label.setAnchor((1.1, 0)) # Push text to the left
                else:
                    self.trade_hover_label.setAnchor((-0.1, 0)) # Push text to the right
                    
                self.trade_hover_label.setPos(idx, mousePoint.y())
                
                self.trade_vLine.show()
                self.trade_hLine.show()
                self.trade_hover_label.show()
        else:
            self.trade_vLine.hide()
            self.trade_hLine.hide()
            self.trade_hover_label.hide()
    
    def change_timeframe(self, tf):
        self.current_timeframe = tf
        self.update_portfolio()

    
    def update_portfolio(self):
        user_id = self.main_window.current_user_id
        if not user_id:
            return

        try:
            # 1. We hit the main portfolio endpoint which has everything
            response = requests.get(f"{API_URL}/portfolio/{user_id}", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                # Update Headers
                total_val = data.get("total_account_value", 100000.0)
                self.total_value_label.setText(f"${total_val:,.2f}")
                
                # Update Sidebar/Top Balance Label
                cash = data.get("cash_balance", 0.0)
                self.balance_label.setText(f"Cash Balance: ${cash:,.2f}")
                
                # Handle Portfolio Profit/Loss Colors
                diff = total_val - 100000.0
                perc = (diff / 100000.0) * 100
                self.percent_change_label.setText(f"{diff:+,.2f} ({perc:+.2f}%)")
                color = "#10b981" if diff >= 0 else "#ef4444"
                self.percent_change_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")

                # Update the Table
                positions = data.get("positions", [])
                self.holdings_table.setRowCount(0)
                for i, stock in enumerate(positions):
                    self.holdings_table.insertRow(i)
                    self.holdings_table.setItem(i, 0, QTableWidgetItem(stock.get("ticker", "")))
                    self.holdings_table.setItem(i, 1, QTableWidgetItem(str(stock.get("quantity", 0))))
                    self.holdings_table.setItem(i, 2, QTableWidgetItem(f"${stock.get('average_price', 0):,.2f}"))
                    self.holdings_table.setItem(i, 3, QTableWidgetItem(f"${stock.get('current_price', 0):,.2f}"))
                    self.holdings_table.setItem(i, 4, QTableWidgetItem(f"${stock.get('current_value', 0):,.2f}"))
                    
                    pnl_p = stock.get("pnl_percentage", 0.0)
                    pnl_item = QTableWidgetItem(f"{pnl_p:+.2f}%")
                    pnl_item.setForeground(Qt.GlobalColor.green if pnl_p >= 0 else Qt.GlobalColor.red)
                    self.holdings_table.setItem(i, 5, pnl_item)
                
                self.holdings_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

            # 2. --- FETCH REAL HISTORY DATA ---
            # (Notice how this aligns perfectly inside the 'try' block)
            hist_res = requests.get(f"{API_URL}/portfolio/history/{user_id}?timeframe={self.current_timeframe}", timeout=5)
            
            if hist_res.status_code == 200:
                hist_data = hist_res.json()
                if len(hist_data) > 0:
                    print(f"DEBUG DATA SAMPLES: X={hist_data[0]['x']}, Y={hist_data[0]['y']}")
                if len(hist_data) > 0:
                    # Extract the timestamps and values from the JSON
                    x_data = [point['x'] for point in hist_data]
                    y_data = [point['y'] for point in hist_data]
                    
                    # Send it to our polished charting function!
                    self.update_portfolio_chart(x_data, y_data)
                else:
                    # Fallback if the database is empty: Draw a flat $100k line
                    import time
                    now = time.time()
                    self.update_portfolio_chart([now - 86400, now], [100000.0, 100000.0])
            else:
                print(f"Failed to fetch history: {hist_res.status_code}")

        except Exception as e:
            print(f"Error in update_portfolio: {e}")

    def update_portfolio_chart(self, x_data, y_data):
        self.portfolio_chart.clear()
        
        self.portfolio_chart.setMouseEnabled(x=False, y=False) 
        self.portfolio_chart.getPlotItem().setMenuEnabled(False) 

        # --- FORCE ZERO PADDING ---
        min_x, max_x = min(x_data), max(x_data)
        min_y, max_y = min(y_data), max(y_data)
        
        # Give a little space above the peak, but set the bottom flush
        y_range = max_y - min_y if max_y != min_y else max_y * 0.1
        bottom_y = min_y - (y_range * 0.1)
        top_y = max_y + (y_range * 0.1)

        # Apply strict ranges (padding=0 removes the gaps on the sides!)
        self.portfolio_chart.setXRange(min_x, max_x, padding=0)
        self.portfolio_chart.setYRange(bottom_y, top_y, padding=0)
        # --------------------------

       # --- DRAW THE LINE ---
        pen = pg.mkPen(color='#8B5CF6', width=3) 
        
        # Removed fillLevel/brush. Added symbol (dot), size, and color!
        self.chart_line = self.portfolio_chart.plot(
            x_data, y_data, 
            pen=pen, 
            antialias=True,
            symbol='o', 
            symbolSize=8, 
            symbolBrush='#8B5CF6', # Same purple as the line
            symbolPen=None         # Removes the default border around the dot
        )
        
        self.hover_label = pg.TextItem(color='#1DD3B0', fill=(28, 30, 40, 200))
        self.portfolio_chart.addItem(self.hover_label)
        self.hover_label.hide()

        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#94a3b8', width=1, style=Qt.PenStyle.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#94a3b8', width=1, style=Qt.PenStyle.DashLine))
        self.portfolio_chart.addItem(self.vLine, ignoreBounds=True)
        self.portfolio_chart.addItem(self.hLine, ignoreBounds=True)
        self.vLine.hide()
        self.hLine.hide()

        self.portfolio_chart.scene().sigMouseMoved.connect(self.mouse_moved)
        self.chart_x_data = x_data
        self.chart_y_data = y_data

    def mouse_moved(self, evt):
        if self.portfolio_chart.sceneBoundingRect().contains(evt):
            mousePoint = self.portfolio_chart.plotItem.vb.mapSceneToView(evt)
            pos_x = mousePoint.x()
            
            if not hasattr(self, 'chart_x_data') or not self.chart_x_data:
                return

            import numpy as np
            x_array = np.array(self.chart_x_data)
            idx = (np.abs(x_array - pos_x)).argmin()
            
            if 0 <= idx < len(self.chart_y_data):
                val_x = self.chart_x_data[idx]
                val_y = self.chart_y_data[idx]
                
                from datetime import datetime
                date_str = datetime.fromtimestamp(val_x).strftime('%b %d, %I:%M %p')
                
                self.hover_label.setText(f"{date_str}\nValue: ${val_y:,.2f}")
                self.hover_label.setPos(val_x, val_y)
                
                # --- SMART ANCHORING LOGIC ---
                # 1. X-Axis (Left/Right flip)
                halfway_x = (self.chart_x_data[-1] + self.chart_x_data[0]) / 2
                anchor_x = 1.1 if val_x > halfway_x else -0.1
                
                # 2. Y-Axis (Top/Bottom flip)
                max_y = max(self.chart_y_data)
                min_y = min(self.chart_y_data)
                y_range = max_y - min_y if max_y != min_y else max_y * 0.1
                
                # If we are in the top 20% of the graph, push the text BELOW the dot
                if val_y > max_y - (y_range * 0.2):
                    anchor_y = -0.1 # Draws downwards
                else:
                    anchor_y = 1.1  # Draws upwards
                
                self.hover_label.setAnchor((anchor_x, anchor_y))
                # -----------------------------
                
                self.vLine.setPos(val_x)
                self.hLine.setPos(val_y)
                
                self.hover_label.show()
                self.vLine.show()
                self.hLine.show()
        else:
            if hasattr(self, 'hover_label'):
                self.hover_label.hide()
                self.vLine.hide()
                self.hLine.hide()
    

    def switch_tab(self, index):
        self.pages.setCurrentIndex(index)
        
        if index in [0, 1]: 
            self.balance_label.show()
            self.update_portfolio() 
        else:
            self.balance_label.hide()
            
        # Add this logic for the Community tab (index 2)
        if index == 2:
            self.sync_privacy_state()
            self.load_following_list() # Automatically load followers when opening the tab


    def get_quote(self):
        ticker = self.ticker_input.text().upper()
        if not ticker:
            QMessageBox.warning(self, "Error", "Please enter a ticker symbol.")
            return
            
        self.price_label.setText("Fetching...")
        
        try:
            # 1. Fetch Current Price[cite: 1]
            response = requests.get(f"{API_URL}/quote/{ticker}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                price = data.get("current_price")
                if price is not None:
                    self.price_label.setText(f"Current Price: ${price:,.2f}")
                else:
                    self.price_label.setText("Current Price: ---")
                    QMessageBox.warning(self, "Error", "Ticker not found.")
                    return # Exit early if ticker is bad
            else:
                self.price_label.setText("Current Price: ---")
                QMessageBox.warning(self, "Error", "Failed to fetch price.")
                return # Exit early if API fails

            # 2. Fetch Historical Data
            hist_response = requests.get(f"{API_URL}/history/{ticker}?timeframe={self.trade_timeframe}", timeout=5)
            
            if hist_response.status_code == 200:
                raw_hist_data = hist_response.json()
                self.trade_history_data = raw_hist_data
                
                formatted_data = []
                x_labels = {} # Map the index to the date string
                
                for i, candle in enumerate(raw_hist_data):
                    try:
                        o = float(candle.get("Open", candle.get("open", 0)))
                        c = float(candle.get("Close", candle.get("close", 0)))
                        l = float(candle.get("Low", candle.get("low", 0)))
                        h = float(candle.get("High", candle.get("high", 0)))
                        
                        formatted_data.append((i, o, c, l, h))
                        
                        # Save the date string for the X-Axis
                        # Depending on the backend format, we might want to split it to look cleaner
                        date_str = candle.get("Date", candle.get("Datetime", ""))
                        x_labels[i] = date_str
                        
                    except (ValueError, TypeError):
                        continue
                
                # --- UPDATE THE CHART ---
                self.trade_chart.clear() # This wipes the candles AND the crosshairs
                
                # 1. Give the custom axis the new dates
                self.trade_time_axis.x_labels = x_labels
                
                if formatted_data:
                    # 2. Add the candles
                    candle_item = CandlestickItem(formatted_data)
                    self.trade_chart.addItem(candle_item)
                    
                    # 3. Re-add the crosshairs and labels so they aren't deleted permanently!
                    self.trade_chart.addItem(self.trade_vLine, ignoreBounds=True)
                    self.trade_chart.addItem(self.trade_hLine, ignoreBounds=True)
                    self.trade_chart.addItem(self.trade_hover_label)
                    
                    self.trade_vLine.hide()
                    self.trade_hLine.hide()
                    self.trade_hover_label.hide()
                    
                    self.trade_chart.autoRange()
                else:
                    print(f"Warning: No valid historical data parsed for {ticker}")

            else:
                print(f"Failed to fetch history. Status code: {hist_response.status_code}")
                # We don't throw a popup here so it doesn't interrupt the user, 
                # but we print to console for debugging.

        except Exception as e:
            self.price_label.setText("Current Price: ---")
            QMessageBox.critical(self, "Error", f"Connection failed: {e}")

    def buy_stock(self):
        ticker = self.ticker_input.text().upper()
        qty_str = self.qty_input.text()
        user_id = self.main_window.current_user_id

        # 1. Basic Validation (Did they leave a box blank?)
        if not ticker or not qty_str:
            QMessageBox.warning(self, "Error", "Please enter a ticker and a quantity.")
            return

        # 2. Number Validation (Did they type 'five' instead of '5'?)
        try:
            quantity = float(qty_str)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Error", "Quantity must be a valid positive number.")
            return

        # 3. Send the Buy Request to FastAPI
        try:
            payload = {
                "user_id": user_id,
                "ticker": ticker,
                "quantity": quantity
            }
            
            response = requests.post(f"{API_URL}/buy", json=payload, timeout=5) # Fails safely after 5 seconds
            
            if response.status_code == 200:
                # Success! Let the user know.
                QMessageBox.information(self, "Trade Executed", f"Successfully bought {quantity} shares of {ticker}!")
                
                # Clear the quantity box for the next trade
                self.qty_input.clear() 
                
                # --- THE MAGIC LINE ---
                # This instantly updates the cash label at the top of the screen!
                self.update_portfolio()
                
            else:
                # Backend caught an error (e.g., Insufficient Funds, Market Closed)
                error_msg = response.json().get("detail", "Transaction failed.")
                QMessageBox.warning(self, "Trade Failed", error_msg)
                
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Connection Error", "Could not connect to the backend server.")


    def sell_stock(self):
        ticker = self.ticker_input.text().upper()
        qty_str = self.qty_input.text()
        user_id = self.main_window.current_user_id

        # 1. Basic Validation
        if not ticker or not qty_str:
            QMessageBox.warning(self, "Error", "Please enter a ticker and a quantity.")
            return

        # 2. Number Validation
        try:
            quantity = float(qty_str)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Error", "Quantity must be a valid positive number.")
            return

        # 3. Send the Sell Request to FastAPI
        try:
            payload = {
                "user_id": user_id,
                "ticker": ticker,
                "quantity": quantity
            }
            
            # Added a 5-second timeout just in case the server hangs again!
            response = requests.post(f"{API_URL}/sell", json=payload, timeout=5)
            
            if response.status_code == 200:
                QMessageBox.information(self, "Trade Executed", f"Successfully sold {quantity} shares of {ticker}!")
                
                # Clear the quantity box
                self.qty_input.clear() 
                
                # Instantly update the cash label (it should go up this time!)
                self.update_portfolio()
                
            else:
                # Backend caught an error (e.g., You don't own enough shares)
                error_msg = response.json().get("detail", "Transaction failed.")
                QMessageBox.warning(self, "Trade Failed", error_msg)
                
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Connection Error", "Could not connect to the backend server.")
        except requests.exceptions.Timeout:
            QMessageBox.critical(self, "Timeout Error", "The server took too long to respond. Try again.")


        try:
            response = requests.get(f"{API_URL}/portfolio/{user_id}", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                # 1. Update the BIG Header (Total Account Value)
                total_val = data.get("total_account_value", 100000.0)
                self.total_value_label.setText(f"${total_val:,.2f}")
                
                # 2. Update the Sidebar Cash Balance (Syncing them up!)
                cash = data.get("cash_balance", 0.0)
                self.balance_label.setText(f"Cash Balance: ${cash:,.2f}")
                
                # 3. Calculate % Change from $100k starting point
                # (You can eventually replace 100000 with a 'starting_balance' variable)
                diff = total_val - 100000.0
                perc = (diff / 100000.0) * 100
                
                self.percent_change_label.setText(f"{diff:+,.2f} ({perc:+.2f}%)")
                # Set color: Green if profit, Red if loss
                color = "#10b981" if diff >= 0 else "#ef4444"
                self.percent_change_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")

                # 4. Fill the Holdings Table
                positions = data.get("positions", [])
                self.holdings_table.setRowCount(0)
                
                for i, stock in enumerate(positions):
                    self.holdings_table.insertRow(i)
                    
                    # Mapping your JSON fields to the table
                    ticker = stock.get("ticker", "???")
                    qty = stock.get("quantity", 0)
                    avg = stock.get("average_price", 0.0)
                    curr = stock.get("current_price", 0.0)
                    val = stock.get("current_value", 0.0)
                    pnl_p = stock.get("pnl_percentage", 0.0)

                    # Create Items
                    self.holdings_table.setItem(i, 0, QTableWidgetItem(ticker))
                    self.holdings_table.setItem(i, 1, QTableWidgetItem(str(qty)))
                    self.holdings_table.setItem(i, 2, QTableWidgetItem(f"${avg:,.2f}"))
                    self.holdings_table.setItem(i, 3, QTableWidgetItem(f"${curr:,.2f}"))
                    self.holdings_table.setItem(i, 4, QTableWidgetItem(f"${val:,.2f}"))
                    
                    # PnL Percent Column with Color
                    pnl_item = QTableWidgetItem(f"{pnl_p:+.2f}%")
                    pnl_item.setForeground(Qt.GlobalColor.green if pnl_p >= 0 else Qt.GlobalColor.red)
                    self.holdings_table.setItem(i, 5, pnl_item)

                # Make the table look clean
                self.holdings_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
                
            else:
                print(f"Backend Error: {response.status_code}")
        except Exception as e:
            print(f"Error updating portfolio: {e}")

    
    def toggle_privacy(self):
        user_id = self.main_window.current_user_id
        if not user_id:
            return

        # .isChecked() returns True if the button is pressed (Public)
        is_public = self.privacy_btn.isChecked()
        
        try:
            # Send the PUT request to our new endpoint
            payload = {"is_public": is_public}
            response = requests.put(f"{API_URL}/user/{user_id}/privacy", json=payload, timeout=5)
            
            if response.status_code == 200:
                # Success! Update the UI text
                if is_public:
                    self.privacy_btn.setText("Portfolio: PUBLIC")
                    print("DEBUG: Set portfolio to Public in database")
                else:
                    self.privacy_btn.setText("Portfolio: PRIVATE")
                    print("DEBUG: Set portfolio to Private in database")
            else:
                # If the backend failed, un-toggle the button so the UI matches reality
                QMessageBox.warning(self, "Error", "Failed to update privacy settings.")
                self.privacy_btn.setChecked(not is_public) 
                
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Connection Error", "Could not connect to the server.")
            self.privacy_btn.setChecked(not is_public) # Revert the button state

    def sync_privacy_state(self):
        user_id = self.main_window.current_user_id
        if not user_id:
            return

        try:
            response = requests.get(f"{API_URL}/user/{user_id}/privacy", timeout=5)
            if response.status_code == 200:
                is_public = response.json().get("is_public", False)
                
                # CRITICAL: We block the button's signals temporarily!
                # If we don't do this, calling .setChecked() will count as a "click" 
                # and accidentally trigger your PUT request again.
                self.privacy_btn.blockSignals(True)
                
                self.privacy_btn.setChecked(is_public)
                if is_public:
                    self.privacy_btn.setText("Portfolio: PUBLIC")
                else:
                    self.privacy_btn.setText("Portfolio: PRIVATE")
                    
                self.privacy_btn.blockSignals(False) # Unblock it so the user can click it again
                
        except Exception as e:
            print(f"Failed to sync privacy state: {e}")

    def search_users(self):
        query = self.user_search_input.text().strip()
        user_id = self.main_window.current_user_id
        self.community_list.clear()
        
        if not query:
            self.load_following_list()
            return 

        # --- UI UPDATES FOR SEARCH MODE ---
        self.list_title_label.setText("Search Results")
        self.clear_search_btn.show()

        try:
            response = requests.get(f"{API_URL}/users/search?query={query}&current_user_id={user_id}", timeout=5)
            
            if response.status_code == 200:
                users = response.json()
                
                if not users:
                    item = QListWidgetItem("No public users found.")
                    item.setFlags(Qt.ItemFlag.NoItemFlags) # Make it unclickable
                    self.community_list.addItem(item)
                    return

                # Add each user to the list
                for u in users:
                    item = QListWidgetItem(f"👤 {u['username']}")
                    # MAGIC TRICK: Store the user_id invisibly inside the item!
                    item.setData(Qt.ItemDataRole.UserRole, u['user_id']) 
                    self.community_list.addItem(item)
            else:
                QMessageBox.warning(self, "Error", "Failed to fetch search results.")
                
        except requests.exceptions.ConnectionError:
             QMessageBox.critical(self, "Error", "Could not connect to server.")

    def load_following_list(self):
        # Reset the UI back to "Following" mode
        self.user_search_input.clear()
        self.clear_search_btn.hide()
        self.list_title_label.setText("Following")
        self.community_list.clear()
        
        self.spy_username_label.setText("Select a user to view their portfolio")
        self.spy_chart.clear()
        self.spy_table.setRowCount(0)
        self.follow_btn.hide()

        user_id = self.main_window.current_user_id
        if not user_id:
            return

        try:
            response = requests.get(f"{API_URL}/user/{user_id}/following", timeout=5)
            if response.status_code == 200:
                following = response.json()
                
                if not following:
                    item = QListWidgetItem("You aren't following anyone yet.")
                    item.setFlags(Qt.ItemFlag.NoItemFlags) # Unclickable
                    self.community_list.addItem(item)
                    return
                
                # Populate the list with the people you follow!
                for u in following:
                    item = QListWidgetItem(f"⭐ {u['username']}")
                    item.setData(Qt.ItemDataRole.UserRole, u['user_id']) 
                    self.community_list.addItem(item)
            else:
                print(f"Failed to load following list: {response.status_code}")
                
        except Exception as e:
            print(f"Error loading following list: {e}")


    def load_spy_portfolio(self, item):
        # 1. Get the hidden user_id from the clicked item
        target_user_id = item.data(Qt.ItemDataRole.UserRole)
        follower_id = self.main_window.current_user_id
        
        if not target_user_id or not follower_id:
            return

        self.current_spy_id = target_user_id
        
        username = item.text().replace("👤 ", "").replace("⭐ ", "")
        self.spy_username_label.setText(f"{username}'s Portfolio")
        
        try:
            check_res = requests.get(f"{API_URL}/user/{follower_id}/follows/{target_user_id}", timeout=5)
            if check_res.status_code == 200:
                is_following = check_res.json().get("is_following", False)
                
                if is_following:
                    self.follow_btn.setText("Unfollow")
                    self.follow_btn.setStyleSheet("background-color: #ef4444; color: white; font-weight: bold;")
                else:
                    self.follow_btn.setText("Follow User")
                    self.follow_btn.setStyleSheet("background-color: #10b981; color: white; font-weight: bold;")
                    
        except Exception as e:
            print(f"Error checking follow status: {e}")
        
        self.follow_btn.show()

        try:
            # 2. Fetch their Holdings (Reusing your existing endpoint!)
            response = requests.get(f"{API_URL}/portfolio/{target_user_id}", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                positions = data.get("positions", [])
                
                self.spy_table.setRowCount(0)
                for i, stock in enumerate(positions):
                    self.spy_table.insertRow(i)
                    self.spy_table.setItem(i, 0, QTableWidgetItem(stock.get("ticker", "")))
                    self.spy_table.setItem(i, 1, QTableWidgetItem(str(stock.get("quantity", 0))))
                    self.spy_table.setItem(i, 2, QTableWidgetItem(f"${stock.get('average_price', 0):,.2f}"))
                    self.spy_table.setItem(i, 3, QTableWidgetItem(f"${stock.get('current_price', 0):,.2f}"))
                    self.spy_table.setItem(i, 4, QTableWidgetItem(f"${stock.get('current_value', 0):,.2f}"))
                    
                    pnl_p = stock.get("pnl_percentage", 0.0)
                    pnl_item = QTableWidgetItem(f"{pnl_p:+.2f}%")
                    pnl_item.setForeground(Qt.GlobalColor.green if pnl_p >= 0 else Qt.GlobalColor.red)
                    self.spy_table.setItem(i, 5, pnl_item)
            else:
                self.spy_table.setRowCount(0)
                print(f"Failed to load spy portfolio. Status: {response.status_code}")
        
            # 3. Fetch their Portfolio Chart History (Defaulting to 1W view)
            hist_res = requests.get(f"{API_URL}/portfolio/history/{target_user_id}?timeframe=ALL", timeout=5)
            
            if hist_res.status_code == 200:
                hist_data = hist_res.json()
                self.spy_chart.clear()
                # Draw a dashed gray line at exactly $100,000
                breakeven_line = pg.InfiniteLine(
                    pos=100000, 
                    angle=0, 
                    pen=pg.mkPen(color='#64748b', style=Qt.PenStyle.DashLine, width=2)
                )
                self.spy_chart.addItem(breakeven_line)
                if len(hist_data) > 0:
                    from datetime import datetime
                    
                    formatted_x = []
                    y_data = []
                    
                    # We create a list of tuples: [(0, 'Mar 25'), (1, 'Mar 26'), ...]
                    x_ticks = [] 

                    for i, point in enumerate(hist_data):
                        date_str = datetime.fromtimestamp(point['x']).strftime('%b %d')
                        formatted_x.append(i) 
                        y_data.append(point['y'])
                        x_ticks.append((i, date_str))

                    # 1. Force the bottom axis to use our exact string labels
                    bottom_axis = self.spy_chart.getAxis('bottom')
                    bottom_axis.setTicks([x_ticks])
                    
                    # 2. Add symbol='o' to draw visible dots on the line
                    pen = pg.mkPen(color='#38bdf8', width=3) 
                    self.spy_chart.plot(
                        formatted_x, 
                        y_data, 
                        pen=pen, 
                        symbol='o',           # Draws a circle at every data point
                        symbolSize=6,         # Size of the circle
                        symbolBrush='#38bdf8',# Color of the circle
                        antialias=True
                    )
                else:
                    print("No chart history found for this user.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load user data: {e}")


    def toggle_follow_user(self):
        follower_id = self.main_window.current_user_id
        leader_id = self.current_spy_id # The person we clicked on
        
        if not follower_id or not leader_id:
            return

        # Check the current text of the button to determine the action
        action = self.follow_btn.text()
        
        try:
            if action == "Follow User":
                # Send Subscribe request
                payload = {"follower_id": follower_id, "leader_id": leader_id}
                res = requests.post(f"{API_URL}/subscribe", json=payload, timeout=5)
                
                if res.status_code == 200:
                    self.follow_btn.setText("Unfollow")
                    self.follow_btn.setStyleSheet("background-color: #ef4444; color: white; font-weight: bold;")
                    
                    # Refresh the following list if we aren't currently searching
                    if self.list_title_label.text() == "Following":
                        self.load_following_list()
            else:
                # Send Unsubscribe request
                res = requests.delete(f"{API_URL}/subscribe?follower_id={follower_id}&leader_id={leader_id}", timeout=5)
                
                if res.status_code == 200:
                    self.follow_btn.setText("Follow User")
                    self.follow_btn.setStyleSheet("background-color: #10b981; color: white; font-weight: bold;")
                    
                    # Refresh the list
                    if self.list_title_label.text() == "Following":
                        self.load_following_list()
                        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to update subscription: {e}")
    
    def load_leaderboard(self, timeframe="1W"):
        user_id = self.main_window.current_user_id
        if not user_id:
            return
            
        self.leaderboard_list.clear()

        try:
            # Call your new endpoint
            res = requests.get(f"{API_URL}/leaderboard?timeframe={timeframe}&user_id={user_id}", timeout=5)
            
            if res.status_code == 200:
                data = res.json()
                top_10 = data.get("top_10", [])
                my_stats = data.get("my_stats", {})

                # 1. Populate the Top 10 List
                for user in top_10:
                    rank = user['rank']
                    username = user['username']
                    pct = user['pct_change']

                    # Format text: "1. 👤 TraderJoe (+4.50%)"
                    sign = "+" if pct >= 0 else ""
                    display_text = f"{rank}. 👤 {username} ({sign}{pct:.2f}%)"

                    item = QListWidgetItem(display_text)
                    
                    # Store the user_id so load_spy_portfolio knows who to spy on!
                    item.setData(Qt.ItemDataRole.UserRole, user['user_id'])

                    # Color the text green if profitable, red if losing
                    if pct >= 0:
                        item.setForeground(Qt.GlobalColor.green)
                    else:
                        item.setForeground(Qt.GlobalColor.red)

                    self.leaderboard_list.addItem(item)

                # 2. Update your Pinned Rank at the bottom
                if my_stats:
                    my_rank = my_stats['rank']
                    my_pct = my_stats['pct_change']
                    my_sign = "+" if my_pct >= 0 else ""
                    
                    self.my_rank_label.setText(
                        f"Your Rank: {my_rank} | Return: {my_sign}{my_pct:.2f}%"
                    )
            else:
                print(f"Failed to load leaderboard. Status: {res.status_code}")
        except Exception as e:
            print(f"Error loading leaderboard: {e}")

    def logout(self):
        self.main_window.current_user_id = None
        self.ticker_input.clear()
        self.qty_input.clear()
        self.price_label.setText("Current Price: ---")
        self.main_window.switch_screen(0) 

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trading Simulator")
        
        # --- Screen Resizing Logic ---
        screen = QApplication.primaryScreen().availableGeometry()
        width = int(screen.width() * 0.75)
        height = int(screen.height() * 0.75)
        self.resize(width, height)
        
        # Center the window on the screen
        self.move((screen.width() - width) // 2, (screen.height() - height) // 2)

        # --- Global Dark Modern Theme (QSS) ---
        self.setStyleSheet("""
            QMainWindow {
                background-color: #110e14; /* background color */
            }
            QWidget {
                background-color: #110e14;
                color: #f8fafc;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit {
                background-color: #1c1426;
                color: #f8fafc;
                border: 1px solid #1c1426;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #53298a; /* Light blue highlight when typing */
            }
            QPushButton {
                background-color: #3b82f6; /* Primary Blue */
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb; /* Darker blue on hover */
            }
            QPushButton[flat="true"] {
                background-color: transparent;
                color: #94a3b8;
                font-weight: normal;
            }
            QPushButton[flat="true"]:hover {
                color: #cbd5e1;
                text-decoration: underline;
            }
            QPushButton#AuthBtn {
                background-color: #53298a; /* Your Custom Purple */
            }
            QPushButton#AuthBtn:hover {
                background-color: #3f1f69; /* Slightly darker purple on hover */
            }
            QMessageBox {
                background-color: #1e293b;
            }
            QMessageBox QLabel {
                color: #f8fafc;
            }
            QMessageBox QPushButton {
                min-width: 80px;
            }
                           /* --- Sidebar Navigation Styles --- */
            QFrame#Sidebar {
                background-color: #161720; /* Slightly darker than main background */
                border-right: 2px solid #2C2F3F;
            }
            QPushButton#NavBtn {
                background-color: transparent;
                color: #94a3b8;
                text-align: left;
                padding: 12px 20px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton#NavBtn:hover {
                background-color: #2C2F3F;
                color: #f8fafc;
            }
            QPushButton#NavBtn:checked {
                background-color: #53298a; /* Your purple color */
                color: white;
            }
        """)

        self.current_user_id = None 

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.login_screen = LoginScreen(self)
        self.signup_screen = SignupScreen(self)
        self.home_screen = HomeScreen(self)
        
        self.stacked_widget.addWidget(self.login_screen)
        self.stacked_widget.addWidget(self.signup_screen)
        self.stacked_widget.addWidget(self.home_screen)

    def switch_screen(self, index):
        self.stacked_widget.setCurrentIndex(index)
        if index == 2:
            self.home_screen.update_portfolio()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())