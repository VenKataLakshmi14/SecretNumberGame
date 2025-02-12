from flask import Flask, request, render_template, session, redirect, url_for, jsonify, flash
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import secrets
import random

# Initialize Flask app
app = Flask(__name__)
# Set a strong secret key for session management 
app.secret_key = secrets.token_hex(16)  

# MySQL Database Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  # The MySQL user you created
app.config['MYSQL_PASSWORD'] = 'Root@123'  # MySQL password
app.config['MYSQL_DB'] = 'guessinggame'  # Database name
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'  # To fetch rows as dictionaries

# Initialize MySQL, Bcrypt, and LoginManager
mysql = MySQL(app)  
bcrypt = Bcrypt(app)  
login_manager = LoginManager(app)  
login_manager.login_view = 'login'  # Set default login page

# Define User class that works with Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# Load the user based on user ID from the session
@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return User(user['id'], user['username'])  # Return User object
    return None


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':  # Handle form submission
        username = request.form['username']
        password = request.form['password']
        # Hash the password before saving it to the database
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        cursor = mysql.connection.cursor()
        # Insert new user into the 'users' table
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        mysql.connection.commit()  # Commit transaction
        cursor.close()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('login'))  
    
    return render_template('register.html')  # Show the registration form if GET request


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':  # Handle form submission
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        # Check if the username exists in the 'users' table
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.check_password_hash(user['password'], password):  # Validate password
            login_user(User(user['id'], user['username']))  # Log the user in
            flash("Login successful!", "success")
            return redirect(url_for('index'))  # Redirect to main page after successful login
        else:
            flash("Invalid username or password.", "danger")  # Show error message for failed login

    return render_template('login.html')  # Show the login form if GET request

# Route for logging out the user
@app.route('/logout')
def logout():
    if current_user.is_authenticated:  # Check if the user is logged in
        logout_user()  # Log the user out
        flash("Logged out successfully.", "info")
    return redirect(url_for('login'))  # Redirect to login page after logout

# Main game route (only for authenticated users)
@app.route('/')
@login_required
def index():
    session['secret_number'] = random.randint(1, 10)  # Generate a random secret number
    session['guess_count'] = 0  # Initialize guess count
    session['guess_limit'] = 3  # Set the maximum number of guesses
    return render_template('index.html')  # Render the game page

# Route to handle user's guess in the game
@app.route('/guess', methods=['POST'])
@login_required
def guess():
    guess = int(request.form['guess'])  # Retrieve the user's guess from the form
    session['guess_count'] += 1  # Increment the guess count

    if guess == session['secret_number']:  
        session.pop('secret_number', None)  
        session.pop('guess_count', None)  
        return render_template('win.html')  

    elif session['guess_count'] >= session['guess_limit']:  # Check if the guess limit is reached
        old_secret_number = session.pop('secret_number', None) 
        session.pop('guess_count', None)  
        return render_template('lose.html', old_secret_number=old_secret_number) 

    else:
        remaining = session['guess_limit'] - session['guess_count']  # Calculate remaining guesses
        return render_template('guess.html', remaining=remaining)  #

# API endpoint for guessing (only for authenticated users)
@app.route('/api/guess', methods=['POST'])
@login_required
def api_guess():
    data = request.get_json()  # Get JSON data from the request

    if not data or 'guess' not in data:  # Check if the guess is provided
        return jsonify({"error": "Invalid request. Please provide a 'guess' in the payload."}), 400

    guess = data['guess']

    if not isinstance(guess, int) or guess < 1 or guess > 10:  # Validate the guess (must be an integer between 1 and 10)
        return jsonify({"error": "Guess must be an integer between 1 and 10."}), 400

    if 'secret_number' not in session:  
        session['secret_number'] = random.randint(1, 10)  
        session['guess_count'] = 0  
        session['guess_limit'] = 3 

    session['guess_count'] += 1  

    if guess == session['secret_number']:  
        session.pop('secret_number', None)  
        session.pop('guess_count', None)  
        return jsonify({"result": "win", "message": "Congratulations! You guessed the correct number."})

    if session['guess_count'] >= session['guess_limit']:  
        secret_number = session.pop('secret_number', None)  
        session.pop('guess_count', None)  
        return jsonify({"result": "lose", "message": f"Sorry, you've lost. The correct number was {secret_number}."})

    remaining_guesses = session['guess_limit'] - session['guess_count']  # Calculate remaining guesses
    return jsonify({"result": "incorrect", "remaining_guesses": remaining_guesses})  # Respond with incorrect guess and remaining guesses

# Start the Flask app in debug mode
if __name__ == '__main__':
    app.run(debug=True)
