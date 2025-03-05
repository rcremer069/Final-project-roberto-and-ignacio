from flask import Flask, render_template, request, redirect, url_for, flash, session
import pandas as pd
from deep_translator import GoogleTranslator
import detectlanguage
import os

# Initialize Flask
app = Flask(__name__)
app.secret_key = 'SOME_RANDOM_SECRET_KEY'  # for session & flash messages

# Configure detectlanguage API key
# mail: mokeso9617@jomspar.com
# pass: 85j2GnsB@JrkfFF
detectlanguage.configuration.api_key = "63ae83d2da2401010ce086fe081af0a0"

# CSV file path (update as needed)
CSV_FILE = 'words.csv'
LANGUAGES_LIST = ['en', 'de']

# Ensure CSV exists
if not os.path.exists(CSV_FILE):
    # Create a blank CSV with 'en' and 'de' columns if not present
    pd.DataFrame(columns=['en', 'de']).to_csv(CSV_FILE, index=False)

# ----------
# HELPERS
# ----------
def read_words_csv():
    """Read the CSV and return a Pandas DataFrame."""
    return pd.read_csv(CSV_FILE)

def write_words_csv(df):
    """Write the given DataFrame to the CSV file."""
    df.to_csv(CSV_FILE, index=False)

def translate_word(source_language, target_language, text):
    """Helper to use deep_translator."""
    return GoogleTranslator(source=source_language, target=target_language).translate(text)

def detect_lang(text):
    """Wrapper to detect language."""
    return detectlanguage.simple_detect(text)

# ----------
# CORE FUNCTIONS
# ----------
def delete_word_by_id(row_id):
    """
    Delete a word from the CSV by row index.
    """
    df = read_words_csv()
    if 0 <= row_id < len(df):
        df.drop(labels=row_id, inplace=True)
        df.reset_index(drop=True, inplace=True)
        write_words_csv(df)
        return True, 'Word deleted successfully.'
    else:
        return False, 'Invalid row index.'
    
def add_new_word(raw_word):
    """
    Add a new word to the CSV after translating it.
    """
    if not raw_word:
        return False, "Please enter a word."
    source_language = detect_lang(raw_word)
    if source_language not in LANGUAGES_LIST:
        return False, "Use English or German only."
    target_language = 'en' if source_language == 'de' else 'de'
    translated = translate_word(source_language, target_language, raw_word)
    if translated.lower() == raw_word.lower():
        return False, "The word cannot be translated (it came back identical)."
    df = read_words_csv()
    if target_language == 'en':
        en_word = translated.lower()
        de_word = raw_word.lower()
    else:
        en_word = raw_word.lower()
        de_word = translated.lower()
    already_exists = (
        (df['en'].str.lower() == en_word) & (df['de'].str.lower() == de_word)
    ).any()
    if already_exists:
        return False, 'That pair already exists in the dictionary.'
    new_row = pd.DataFrame({'en': [en_word], 'de': [de_word]})
    df = pd.concat([df, new_row], ignore_index=True)
    write_words_csv(df)
    return True, f'The word "{raw_word}" ({source_language.upper()}) was added successfully!'

def generate_quiz(selected_lang):
    """
    Generate a quiz question and correct answers.
    """
    df = read_words_csv()
    if df.empty:
        return False, "No words in the dictionary to quiz on!", None, None
    valid_rows = df[(df['en'].str.len() <= 28) & (df['de'].str.len() <= 28)]
    if valid_rows.empty:
        valid_rows = df
    random_row = valid_rows.sample().iloc[0]
    if selected_lang == 'EN':
        question_word = random_row['en']
        correct_answers = [random_row['de'].lower()]
    else:
        question_word = random_row['de']
        correct_answers = [random_row['en'].lower()]
    return True, None, question_word, correct_answers

# ----------
# ROUTES
# ----------
@app.route('/')
def home():
    """
    Redirect to dictionary page by default or render a custom home page.
    """
    return redirect(url_for('dictionary_view'))

@app.route('/dictionary', methods=['GET', 'POST'])
def dictionary_view():
    """
    Show all words, allow searching by either English or German.
    Also let the user delete words if they wish.
    """
    df = read_words_csv()

    # If user submitted a search form (via POST), or used GET param
    if request.method == 'POST':
        search_term = request.form.get('search', '').strip().lower()
        return redirect(url_for('dictionary_view', q=search_term))

    # Check if there's a search query in the URL
    q = request.args.get('q', '').strip().lower()
    if q:
        # Filter rows where 'q' appears in the English or German columns
        filtered = df[
            df['en'].str.contains(q, case=False, na=False)
            | df['de'].str.contains(q, case=False, na=False)
        ]
    else:
        filtered = df

    # Convert to list of dictionaries for easy iteration
    words_list = filtered.to_dict('records')
    return render_template('dictionary.html', words=words_list, query=q)

@app.route('/delete/<int:row_id>')
def delete_word(row_id):
    success, message = delete_word_by_id(row_id)
    flash(message, 'info' if success else 'error')
    return redirect(url_for('dictionary_view'))

@app.route('/add', methods=['GET', 'POST'])
def add_word():
    if request.method == 'POST':
        raw_word = request.form.get('word', '').strip()
        success, message = add_new_word(raw_word)
        flash(message, 'success' if success else 'error')
        return redirect(url_for('add_word'))
    return render_template('form.html')

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        guess = request.form.get('guess', '').strip().lower()
        correct_answers = session.get('quiz_answers', [])
        if guess in correct_answers:
            flash("Correct!", "success")
        else:
            flash(f"Incorrect. Correct answer(s): {', '.join(correct_answers)}", "error")
        return redirect(url_for('quiz'))
    selected_lang = request.args.get('lang', 'EN').upper()
    if selected_lang not in ['EN', 'DE']:
        selected_lang = 'EN'
    success, message, question_word, correct_answers = generate_quiz(selected_lang)
    if not success:
        flash(message, 'error')
        return redirect(url_for('dictionary_view'))
    session['quiz_answers'] = correct_answers
    return render_template('quiz.html', question_word=question_word, selected_lang=selected_lang)

# ----------
# RUN
# ----------
if __name__ == '__main__':
    app.run(debug=True)
