from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager
from pydantic import BaseModel
from passlib.context import CryptContext
import mysql.connector
from db import get_db_connection, DB_USER, DB_PASSWORD, DB_NAME
import yfinance as yf
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
#from sshtunnel import SSHTunnelForwarder //no longer needed since Turing

# --- Global Variables ---
db_conn = None
ssh_tunnel = None
# Initialize the scheduler and force it to use Eastern Time (Market Hours)
scheduler = BackgroundScheduler(timezone="America/New_York") 

# --- global login sesh for /gets ---
def get_active_db():
    global db_conn
    return db_conn

# --- Security Setup ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 1. The Global Cache Dictionary
price_cache = {}

# How many seconds a price stays valid before we ask yfinance again
CACHE_TTL_SECONDS = 60 

def get_cached_price(ticker: str):
    ticker = ticker.upper()
    now = datetime.now()

    # 2. Check the cache FIRST
    if ticker in price_cache:
        cached_data = price_cache[ticker]
        
        # Calculate how old the data is
        time_diff = (now - cached_data["last_updated"]).total_seconds()
        
        if time_diff < CACHE_TTL_SECONDS:
            print(f"⚡ CACHE HIT: Returning saved price for {ticker}")
            return cached_data["price"]

    # 3. If not in cache, or if it's too old, fetch from yfinance
    print(f"🌐 CACHE MISS: Fetching fresh price for {ticker} from yfinance...")
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d") 
        
        if hist.empty:
            return None # Ticker doesn't exist or no data
            
        current_price = float(hist["Close"].iloc[-1])
        
        # 4. Save the new price and current time to the cache
        price_cache[ticker] = {
            "price": current_price,
            "last_updated": now
        }
        
        return current_price
        
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

# --- APScheduler Background Task ---
def record_portfolio_history():
    """Calculates total net worth for all users and saves it to the history table."""
    print(f"[{datetime.now()}] 🔔 Market Closed! Taking daily portfolio snapshots...")
    
    fresh_db = None
    cursor = None
    
    try:
        fresh_db = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = fresh_db.cursor(dictionary=True)
        
    except Exception as e:
        print(f"❌ Scheduler Error: Could not connect to Database - {e}")
        return
        
    try:
        # 1. Get all users and their cash balances
        cursor.execute("SELECT user_id, cash_balance FROM users")
        users = cursor.fetchall()

        for user in users:
            user_id = user['user_id']
            cash = float(user['cash_balance'])
            total_stock_value = 0.0

            # 2. Get this user's active holdings
            cursor.execute("SELECT ticker, quantity FROM holdings WHERE user_id = %s", (user_id,))
            holdings = cursor.fetchall()

            # 3. Calculate live value utilizing the CACHE function
            for holding in holdings:
                ticker = holding['ticker']
                qty = float(holding['quantity'])
                
                # Use your custom cache function to avoid spamming yfinance!
                current_price = get_cached_price(ticker)
                
                if current_price is not None:
                    total_stock_value += (current_price * qty)

            # 4. Calculate Total Net Worth
            total_account_value = cash + total_stock_value

            # 5. Insert the snapshot
            cursor.execute("""
                INSERT INTO portfolio_history (user_id, total_account_value, timestamp)
                VALUES (%s, %s, NOW())
            """, (user_id, total_account_value))
        
        fresh_db.commit()
        print("✅ Daily portfolio snapshots saved successfully!")

    except Exception as e:
        fresh_db.rollback()
        print(f"❌ Failed to record daily history: {e}")
        
    finally:
        cursor.close()
        if fresh_db.is_connected():
            fresh_db.close()

# --- Lifespan Manager (Keeps the DB/SSH connection alive) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_conn
    print("Starting API on Turing...")
    db_conn = get_db_connection()
    
    if not db_conn or not db_conn.is_connected():
        print("CRITICAL ERROR: Could not connect to the database.")
    else:
        print("Database connection active!")
        
        # --- Start the Scheduler ---
        # Runs Monday-Friday at 4:00 PM EST
        scheduler.add_job(record_portfolio_history, 'cron', day_of_week='mon-fri', hour=16, minute=0)
        scheduler.start()
        print("⏰ Background scheduler started (Running Mon-Fri @ 4:00 PM EST)")
        
    yield 
    
    print("Shutting down API. Closing connections...")
    
    # --- Safely shut down the Scheduler ---
    scheduler.shutdown(wait=False)
    
    if db_conn and db_conn.is_connected():
        db_conn.close()
    print("Cleanup complete. Goodbye!")

# --- App Initialization ---
app = FastAPI(title="Virtual Trading API", lifespan=lifespan)

# --- Pydantic Models ---
class UserCreate(BaseModel):
    username: str
    password: str

class TradeRequest(BaseModel):
    user_id: int
    ticker: str
    quantity: float

class PrivacyToggleRequest(BaseModel):
    is_public: bool

class SubscribeRequest(BaseModel):
    follower_id: int
    leader_id: int
# --- API Routes ---

@app.get("/")
def read_root():
    return {"message": "Trading API is online and securely tunneled!"}

@app.post("/signup")
def create_user(user: UserCreate):
    """Creates a new user with a hashed password and $100,000 starting balance."""
    if not db_conn or not db_conn.is_connected():
        raise HTTPException(status_code=500, detail="Database disconnected")
    
    # 1. Hash the plain-text password
    hashed_password = pwd_context.hash(user.password)
    
    cursor = db_conn.cursor()
    try:
        # 2. Insert into the database
        query = "INSERT INTO users (username, password_hash) VALUES (%s, %s)"
        cursor.execute(query, (user.username, hashed_password))
        db_conn.commit() # Save the changes!
        
        # 3. Get the ID of the user we just created
        new_user_id = cursor.lastrowid
        
        return {
            "status": "Success",
            "message": f"User '{user.username}' created with $100,000!",
            "user_id": new_user_id
        }
        
    except mysql.connector.IntegrityError:
        db_conn.rollback()
        raise HTTPException(status_code=400, detail="Username already exists")
    except Exception as e:
        db_conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.get("/quote/{ticker}")
def get_stock_quote(ticker: str):
    """Fetches the current live market price (cached) for a given ticker."""
    try:
        # 1. Ask our new cache helper for the price instead of yfinance directly!
        current_price = get_cached_price(ticker)
        
        # 2. Check if the ticker is fake or delisted (our helper returns None if so)
        if current_price is None:
            raise HTTPException(status_code=404, detail=f"No data found for ticker: {ticker}")
        
        # 3. Return your original success format
        return {
            "status": "Success",
            "ticker": ticker.upper(),
            "current_price": round(current_price, 2)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/buy")
def buy_stock(trade: TradeRequest, db=Depends(get_active_db)):
    """Executes a buy order, deducts cash, and updates the user's portfolio."""
    ticker_upper = trade.ticker.upper()
    
    try:
        # 1. Get the live price using our CACHE helper! (No more direct yfinance calls here)
        current_price = get_cached_price(ticker_upper)
        
        if current_price is None:
            raise HTTPException(status_code=404, detail=f"Invalid ticker or no data: {ticker_upper}")
            
        total_cost = current_price * trade.quantity
        
        # 2. Start the Database Transaction
        cursor = db.cursor(dictionary=True)
        
        # 3. Check User Balance
        cursor.execute("SELECT cash_balance FROM users WHERE user_id = %s", (trade.user_id,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if float(user['cash_balance']) < total_cost:
            raise HTTPException(status_code=400, detail="Insufficient funds")
            
        # 4. Deduct the money
        new_balance = float(user['cash_balance']) - total_cost
        cursor.execute("UPDATE users SET cash_balance = %s WHERE user_id = %s", (new_balance, trade.user_id))
        
        # 5. Update the Portfolio (Check if they already own this stock)
        cursor.execute("SELECT quantity, average_price FROM holdings WHERE user_id = %s AND ticker = %s", 
                       (trade.user_id, ticker_upper))
        position = cursor.fetchone()
        
        if position:
            # If they already own it, calculate the new combined average price
            old_qty = float(position['quantity'])
            old_avg_price = float(position['average_price'])
            
            new_qty = old_qty + trade.quantity
            new_avg_price = ((old_qty * old_avg_price) + total_cost) / new_qty
            
            cursor.execute("""
                UPDATE holdings 
                SET quantity = %s, average_price = %s 
                WHERE user_id = %s AND ticker = %s
            """, (new_qty, new_avg_price, trade.user_id, ticker_upper))
        else:
            # They don't own it yet, insert a brand new row
            cursor.execute("""
                INSERT INTO holdings (user_id, ticker, quantity, average_price) 
                VALUES (%s, %s, %s, %s)
            """, (trade.user_id, ticker_upper, trade.quantity, current_price))
            
        # 6. Log the receipt in the transactions table
        cursor.execute("""
            INSERT INTO transactions (user_id, ticker, action, quantity, execution_price)
            VALUES (%s, %s, 'BUY', %s, %s)
        """, (trade.user_id, ticker_upper, trade.quantity, current_price))
        
        # 7. COMMIT
        db.commit()
        
        return {
            "status": "Success",
            "message": f"Successfully bought {trade.quantity} shares of {ticker_upper}",
            "execution_price": round(current_price, 2),
            "total_cost": round(total_cost, 2),
            "remaining_balance": round(new_balance, 2)
        }
        
    except HTTPException:
        db.rollback() # Cancel everything if there was an API error
        raise
    except Exception as e:
        db.rollback() # Cancel everything if the database crashed
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'cursor' in locals():
            cursor.close()


@app.get("/portfolio/{user_id}")
def get_portfolio(user_id: int):
    """Fetches user cash balance, active positions, and calculates live PnL."""
    if not db_conn or not db_conn.is_connected():
        raise HTTPException(status_code=500, detail="Database disconnected")
        
    cursor = db_conn.cursor(dictionary=True)
    try:
        # 1. Get the user's cash balance
        cursor.execute("SELECT cash_balance FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        cash_balance = float(user['cash_balance'])
        
        # 2. Get the user's active stock positions
        cursor.execute("SELECT ticker, quantity, average_price FROM holdings WHERE user_id = %s", (user_id,))
        positions = cursor.fetchall()
        
        # 3. Calculate live PnL for each position
        portfolio_data = []
        total_stock_value = 0.0
        
        for pos in positions:
            ticker = pos['ticker']
            qty = float(pos['quantity'])
            avg_price = float(pos['average_price'])
            
            # Fetch the live price right now
            stock = yf.Ticker(ticker)
            todays_data = stock.history(period='1d')
            
            # If yfinance fails for a second, fallback to avg_price to prevent a crash
            current_price = float(todays_data['Close'].iloc[-1]) if not todays_data.empty else avg_price
            
            # The Magic Math
            current_value = current_price * qty
            total_cost = avg_price * qty
            unrealized_pnl = current_value - total_cost
            pnl_percentage = (unrealized_pnl / total_cost) * 100 if total_cost > 0 else 0
            
            total_stock_value += current_value
            
            portfolio_data.append({
                "ticker": ticker,
                "quantity": qty,
                "average_price": round(avg_price, 2),
                "current_price": round(current_price, 2),
                "current_value": round(current_value, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "pnl_percentage": round(pnl_percentage, 2)
            })
            
        # 4. Calculate total net worth
        total_account_value = cash_balance + total_stock_value
        
        return {
            "status": "Success",
            "user_id": user_id,
            "cash_balance": round(cash_balance, 2),
            "total_stock_value": round(total_stock_value, 2),
            "total_account_value": round(total_account_value, 2),
            "positions": portfolio_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.post("/sell")
def sell_stock(trade: TradeRequest, db=Depends(get_active_db)):
    """Executes a sell order, adds cash, and updates the user's portfolio."""
    ticker_upper = trade.ticker.upper()
    
    try:
        # 1. Get the live price using our CACHE helper!
        current_price = get_cached_price(ticker_upper)
        
        if current_price is None:
            raise HTTPException(status_code=404, detail=f"Invalid ticker or no data: {ticker_upper}")
            
        total_sale_value = current_price * trade.quantity
        
        # 2. Start the Database Transaction
        cursor = db.cursor(dictionary=True)
        
        # 3. Check the Portfolio (Do they actually own enough to sell?)
        cursor.execute("SELECT quantity FROM holdings WHERE user_id = %s AND ticker = %s", 
                       (trade.user_id, ticker_upper))
        position = cursor.fetchone()
        
        if not position:
            raise HTTPException(status_code=400, detail=f"You do not own any shares of {ticker_upper}")
            
        current_qty = float(position['quantity'])
        
        if current_qty < trade.quantity:
            raise HTTPException(status_code=400, detail=f"Not enough shares. You only have {current_qty} shares of {ticker_upper}")
            
        # 4. Update the Portfolio Table
        if current_qty == trade.quantity:
            # They are selling everything! Delete the row entirely.
            cursor.execute("DELETE FROM holdings WHERE user_id = %s AND ticker = %s", 
                           (trade.user_id, ticker_upper))
        else:
            # They are selling a portion. Reduce the quantity.
            new_qty = current_qty - trade.quantity
            cursor.execute("UPDATE holdings SET quantity = %s WHERE user_id = %s AND ticker = %s", 
                           (new_qty, trade.user_id, ticker_upper))
                           
        # 5. Add the cash back to the user's balance
        cursor.execute("UPDATE users SET cash_balance = cash_balance + %s WHERE user_id = %s", 
                       (total_sale_value, trade.user_id))
                       
        # 6. Log the receipt in the transactions table
        cursor.execute("""
            INSERT INTO transactions (user_id, ticker, action, quantity, execution_price)
            VALUES (%s, %s, 'SELL', %s, %s)
        """, (trade.user_id, ticker_upper, trade.quantity, current_price))
        
        # 7. COMMIT THE TRANSACTION
        db.commit()
        
        # Fetch the updated cash balance to show the user
        cursor.execute("SELECT cash_balance FROM users WHERE user_id = %s", (trade.user_id,))
        new_balance = float(cursor.fetchone()['cash_balance'])
        
        return {
            "status": "Success",
            "message": f"Successfully sold {trade.quantity} shares of {ticker_upper}",
            "execution_price": round(current_price, 2),
            "total_sale_value": round(total_sale_value, 2),
            "new_balance": round(new_balance, 2)
        }
        
    except HTTPException:
        db.rollback() # Cancel everything on an API error
        raise
    except Exception as e:
        db.rollback() # Cancel everything if the database crashes
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'cursor' in locals():
            cursor.close()

#login part
class LoginRequest(BaseModel):
    username: str
    password: str
@app.post("/login")
def login(request: LoginRequest, db=Depends(get_active_db)): 
    cursor = db.cursor(dictionary=True) 
    
    try:
        sql = "SELECT user_id, password_hash FROM users WHERE username = %s"
        cursor.execute(sql, (request.username,))
        user = cursor.fetchone()

        if not user or not pwd_context.verify(request.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        return {
            "message": "Login successful",
            "user_id": user["user_id"]
        }
        
    finally:
        cursor.close()


@app.get("/transactions/{user_id}")
def get_transactions(user_id: int, db=Depends(get_active_db)):
    cursor = db.cursor(dictionary=True)
    
    try:
        # We updated the SELECT and ORDER BY clauses to match your exact columns
        sql = """
            SELECT transaction_id, ticker, action, quantity, execution_price, timestamp 
            FROM transactions 
            WHERE user_id = %s 
            ORDER BY timestamp DESC
        """
        cursor.execute(sql, (user_id,))
        transactions = cursor.fetchall()
        
        return {"transactions": transactions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
    finally:
        cursor.close()

@app.get("/balance/{user_id}")
def get_balance(user_id: int):
    if not db_conn or not db_conn.is_connected():
        raise HTTPException(status_code=500, detail="Database not connected")
        
    cursor = db_conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT cash_balance FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        return {"cash_balance": float(user["cash_balance"])}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.get("/portfolio/history/{user_id}")
def get_portfolio_history(user_id: int, timeframe: str = "1M"): # Defaults to 1 Month
    db_conn.commit() # Ensure we have the latest data before fetching history
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Map the frontend button text to MySQL time intervals
        intervals = {
            "1D": "1 DAY",
            "1W": "7 DAY",
            "1M": "1 MONTH",
            "1Y": "1 YEAR"
        }
        # If they send weird text, default to 1 MONTH
        sql_interval = intervals.get(timeframe, "1 MONTH") 

        # Use NOW() - INTERVAL to only grab recent data
        query = f"""
            SELECT total_account_value, timestamp 
            FROM portfolio_history 
            WHERE user_id = %s 
            AND timestamp >= NOW() - INTERVAL {sql_interval}
            ORDER BY timestamp ASC
        """
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()

        history = [{"x": row['timestamp'].timestamp(), "y": float(row['total_account_value'])} for row in rows]
        return history
    finally:
        cursor.close()


@app.get("/debug-db")
def debug_db():
    cursor = db_conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM portfolio_history")
        return cursor.fetchall()
    finally:
        cursor.close()

@app.get("/history/{ticker}")
def get_ticker_history(ticker: str, timeframe: str = "1M"):
    try:
        stock = yf.Ticker(ticker)
        
        # Configure yfinance based on the requested timeframe
        if timeframe == "1D":
            hist = stock.history(period="1d", interval="5m")
        elif timeframe == "1W":
            hist = stock.history(period="5d", interval="15m")
        else: # "1M"
            hist = stock.history(period="1mo", interval="1d")
            
        if hist.empty:
            raise HTTPException(status_code=404, detail="No historical data found.")
            
        hist = hist.reset_index()
        
        date_col = 'Datetime' if 'Datetime' in hist.columns else 'Date'
        
        # Remove the timezone info and convert to a clean string
        hist[date_col] = hist[date_col].dt.strftime('%Y-%m-%d %H:%M') if timeframe != "1M" else hist[date_col].dt.strftime('%Y-%m-%d')
        
        if date_col == 'Datetime':
            hist.rename(columns={'Datetime': 'Date'}, inplace=True)
            
        data = hist.to_dict(orient="records")
        return data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/user/{user_id}/privacy")
def get_user_privacy(user_id: int, db=Depends(get_active_db)):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT is_public FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Convert the MySQL integer (1 or 0) back to a Python boolean (True or False)
        is_public = bool(user["is_public"])
        
        return {"is_public": is_public}
        
    finally:
        cursor.close()

@app.put("/user/{user_id}/privacy")

def update_user_privacy(user_id: int, request: PrivacyToggleRequest, db=Depends(get_active_db)):

    cursor = db.cursor() 
    
    try:
        # Convert the Python boolean (True/False) to a MySQL integer (1/0)
        public_status = 1 if request.is_public else 0
        
        # The SQL query to update the specific user
        sql = "UPDATE users SET is_public = %s WHERE user_id = %s"
        
        # Execute the query with our variables safely passed in
        cursor.execute(sql, (public_status, user_id))
        
        # Commit
        db.commit() 

        return {"message": "Privacy updated successfully", "is_public": request.is_public}
        
    except Exception as e:
        db.rollback() # If something crashes, undo any partial database changes
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
    finally:
        cursor.close()
        
@app.get("/users/search")
def search_users(query: str, current_user_id: int, db=Depends(get_active_db)):
    cursor = db.cursor(dictionary=True)
    try:
        # Search for public users matching the query, excluding the current user
        sql = """
            SELECT user_id, username 
            FROM users 
            WHERE username LIKE %s 
            AND is_public = 1 
            AND user_id != %s
            LIMIT 20
        """
        # Add the % wildcards so it searches for partial matches (e.g., 'jo' finds 'john')
        search_term = f"%{query}%"
        cursor.execute(sql, (search_term, current_user_id))
        users = cursor.fetchall()
        
        return users
    finally:
        cursor.close()

@app.post("/subscribe")


def follow_user(request: SubscribeRequest, db=Depends(get_active_db)):
    cursor = db.cursor()
    try:
        sql = "INSERT IGNORE INTO subscriptions (follower_id, leader_id) VALUES (%s, %s)"
        cursor.execute(sql, (request.follower_id, request.leader_id))
        db.commit()
        return {"message": "Successfully followed user"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.delete("/subscribe")
def unfollow_user(follower_id: int, leader_id: int, db=Depends(get_active_db)):
    cursor = db.cursor()
    try:
        sql = "DELETE FROM subscriptions WHERE follower_id = %s AND leader_id = %s"
        cursor.execute(sql, (follower_id, leader_id))
        db.commit()
        return {"message": "Successfully unfollowed user"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.get("/user/{user_id}/following")
def get_following_list(user_id: int, db=Depends(get_active_db)):
    cursor = db.cursor(dictionary=True)
    try:
        # Join the users table so we can get their actual usernames, not just IDs
        sql = """
            SELECT u.user_id, u.username 
            FROM subscriptions s
            JOIN users u ON s.leader_id = u.user_id
            WHERE s.follower_id = %s
        """
        cursor.execute(sql, (user_id,))
        following = cursor.fetchall()
        return following
    finally:
        cursor.close()

@app.get("/user/{follower_id}/follows/{leader_id}")
def check_if_following(follower_id: int, leader_id: int, db=Depends(get_active_db)):
    cursor = db.cursor()
    try:
        sql = "SELECT 1 FROM subscriptions WHERE follower_id = %s AND leader_id = %s"
        cursor.execute(sql, (follower_id, leader_id))
        
        # If fetchone() returns data, the row exists (True). Otherwise, it's False.
        is_following = cursor.fetchone() is not None
        
        return {"is_following": is_following}
    finally:
        cursor.close()

@app.post("/admin/force-snapshot")
def force_snapshot():
    try:
        # Call your APScheduler function manually
        record_portfolio_history() 
        return {"message": "Snapshot forced successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/leaderboard")
def get_leaderboard(timeframe: str, user_id: int, db=Depends(get_active_db)):
    # 1. Force the database connection to refresh its snapshot!
    db.commit() 
    
    # 2. Use buffered=True to prevent cursor loop skipping
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        # Grab every user's privacy status and username
        cursor.execute("SELECT user_id, username, is_public FROM users")
        users = {u['user_id']: u for u in cursor.fetchall()}

        # Determine our "Start Date" for the math
        now = datetime.now()
        if timeframe == "1W":
            start_date = now - timedelta(days=7)
        elif timeframe == "1M":
            start_date = now - timedelta(days=30)
        else: # "ALL"
            start_date = None

        rankings = []

        print(f"\n--- STARTING LEADERBOARD LOOP (Found {len(users)} users in DB) ---")

        # 3. Calculate the % return for every user
        for uid, user_data in users.items():
            print(f"Checking User ID: {uid} ({user_data['username']})...")
            
            # --- Get their most recent account value ---
            cursor.execute("""
                SELECT total_account_value FROM portfolio_history 
                WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1
            """, (uid,))
            latest_row = cursor.fetchone()
            
            if not latest_row:
                print(f"   [!] SKIPPED: Database returned NO history for User {uid}.")
                continue 
            
            current_val = float(latest_row['total_account_value'])
            print(f"   [SUCCESS] Found latest value for User {uid}: {current_val}")

            # --- Get their starting value ---
            if timeframe == "ALL" or not start_date:
                start_val = 100000.0
            else:
                cursor.execute("""
                    SELECT total_account_value FROM portfolio_history 
                    WHERE user_id = %s AND timestamp <= %s 
                    ORDER BY timestamp DESC LIMIT 1
                """, (uid, start_date))
                start_row = cursor.fetchone()
                start_val = float(start_row['total_account_value']) if start_row else 100000.0

            # --- Calculate Percentage Change ---
            pct_change = ((current_val - start_val) / start_val) * 100
            
            rankings.append({
                "user_id": uid,
                "username": user_data["username"],
                "is_public": user_data["is_public"],
                "pct_change": pct_change,
                "current_val": current_val
            })

        # 4. Sort the list from highest % to lowest %
        rankings.sort(key=lambda x: x['pct_change'], reverse=True)

        # 5 & 6. Build Top 10 and find the requesting user's "Public" rank
        top_10 = []
        my_stats = None
        current_public_rank = 1

        for r in rankings:
            if r['user_id'] == user_id:
                my_stats = r.copy()
                my_stats['rank'] = current_public_rank 

            if r['is_public']:
                r['rank'] = current_public_rank
                if len(top_10) < 10:
                    top_10.append(r)
                current_public_rank += 1

            if len(top_10) == 10 and my_stats is not None:
                break

        # 7. Fallback Block (If the user actually has no trades yet)
        if my_stats is None:
            fallback_user = users.get(user_id, {})
            my_stats = {
                "user_id": user_id,
                "username": fallback_user.get("username", "You"),
                "is_public": fallback_user.get("is_public", False),
                "pct_change": 0.0,
                "current_val": 100000.0, 
                "rank": "Unranked" 
            }

        return {
            "top_10": top_10,
            "my_stats": my_stats
        }

    except Exception as e:
        print(f"CRITICAL API ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()