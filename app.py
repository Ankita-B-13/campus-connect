import json, os, uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY','campus_connect_secret_key_2026')

# Load/Save JSON - MODIFIED FOR ROBUSTNESS
def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, 'r') as f:
                # Read content first to check if file is empty
                content = f.read().strip() # .strip() to handle potential whitespace
                if not content: # If file is empty or only whitespace
                    return []
                # If not empty, seek back to beginning and load JSON
                f.seek(0)
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: JSONDecodeError in {file}. File might be empty or malformed. Returning empty list.")
            return []
    return []

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

DATA_DIR = 'data'
# Ensure DATA_DIR exists before trying to load files
os.makedirs(DATA_DIR, exist_ok=True) 

USERS = load_json(f'{DATA_DIR}/users.json') or []
POSTS = load_json(f'{DATA_DIR}/posts.json') or []
REQUESTS = load_json(f'{DATA_DIR}/requests.json') or []

# ... (rest of your app.py code remains the same) ...

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = next((u for u in USERS if u['email'] == email and u['password'] == password), None)
        if user:
            session['user'] = user
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    global USERS # Added global keyword to modify the global USERS list
    if request.method == 'POST':
        user = {
            'id': str(uuid.uuid4()),
            'name': request.form['name'],
            'email': request.form['email'],
            'password': request.form['password'],
            'skills': [s.strip() for s in request.form['skills'].split(',')],
            'interests': [i.strip() for i in request.form['interests'].split(',')],
            'bio': request.form.get('bio', ''),
            'avatar': f"https://api.dicebear.com/7.x/avataaars/svg?seed={request.form['email']}"
        }
        USERS.append(user)
        save_json(f'{DATA_DIR}/users.json', USERS)
        session['user'] = user
        return redirect(url_for('dashboard'))
    return render_template('login.html', signup=True)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    user = session['user']
    
    # Calculate match scores
    recommendations = []
    for u in USERS:
        if u['id'] != user['id']:
            # Make sure 'skills' key exists for comparison
            user_skills = set(user.get('skills', []))
            u_skills = set(u.get('skills', []))

            common = len(user_skills.intersection(u_skills))
            score = min(95, common * 25 + 20) # Simple scoring, max 95%
            recommendations.append({**u, 'match_score': score})
    
    recommendations.sort(key=lambda x: x['match_score'], reverse=True)
    
    return render_template('dashboard.html', user=user, recommendations=recommendations[:6])

@app.route('/browse')
def browse():
    if 'user' not in session: return redirect(url_for('login'))
    query = request.args.get('q', '').lower()
    filtered = USERS
    if query:
        filtered = [u for u in USERS if query in u['name'].lower() or 
                   any(query in s.lower() for s in u.get('skills', []))]
    return render_template('browse.html', users=filtered, current_user=session['user'])

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    global USERS # Added global keyword
    if 'user' not in session: return redirect(url_for('login'))
    
    current_user_id = session['user']['id'] # Get the ID from the session
    
    if request.method == 'POST':
        # Update user data in the session
        session['user']['skills'] = [s.strip() for s in request.form['skills'].split(',')]
        session['user']['interests'] = [i.strip() for i in request.form['interests'].split(',')]
        session['user']['bio'] = request.form.get('bio', '')
        
        # Update user data in the global USERS list and save to file
        for i, u in enumerate(USERS):
            if u['id'] == current_user_id:
                USERS[i] = session['user'] # Update the user in the list
                break
        save_json(f'{DATA_DIR}/users.json', USERS)
        
        # Redirect to avoid form resubmission on refresh
        return redirect(url_for('profile')) 
        
    # For GET request, display the current user's profile
    return render_template('profile.html', user=session['user'])


@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    global POSTS # Added global keyword
    if 'user' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        post = {
            'id': str(uuid.uuid4()),
            'user_id': session['user']['id'],
            'user_name': session['user']['name'],
            'type': request.form['type'],  # "looking_for_team" or "looking_to_join"
            'title': request.form['title'],
            'description': request.form['description'],
            'skills_needed': [s.strip() for s in request.form['skills_needed'].split(',')],
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        POSTS.append(post)
        save_json(f'{DATA_DIR}/posts.json', POSTS)
        return redirect(url_for('dashboard'))
    return render_template('post_form.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    # os.makedirs(DATA_DIR, exist_ok=True) # This is now done earlier for consistency
    app.run(debug=True)