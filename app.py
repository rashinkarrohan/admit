from flask import Flask, render_template, request, redirect, url_for, jsonify
import csv
import os
from threading import Lock
from pathlib import Path
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File lock to prevent race conditions
lock = Lock()

# CSV file path, configurable via environment variable
CSV_FILE = os.getenv("CSV_FILE", str(Path(__file__).resolve().parent / 'database.csv'))
logger.info(f"Using CSV file at: {CSV_FILE}")

# In-memory cache for CSV data
cached_data = None

def load_data():
    """Load the CSV file data with caching and in a thread-safe manner."""
    global cached_data
    if cached_data is not None:
        return cached_data
    
    with lock:
        try:
            logger.info("Loading data from CSV")
            with open(CSV_FILE, mode='r') as file:
                reader = csv.DictReader(file)
                cached_data = list(reader)
                return cached_data
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            return []

def save_data(data):
    """Save the data back to the CSV file in a thread-safe manner and update cache."""
    global cached_data
    with lock:
        try:
            logger.info("Saving data to CSV")
            with open(CSV_FILE, mode='w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            cached_data = data  # Update cache
        except Exception as e:
            logger.error(f"Error saving CSV file: {e}")

@app.route('/')
def index():
    """Displays the courses and related data."""
    data = load_data()
    if not data:
        return "No data available", 404

    courses = {entry['course'] for entry in data}
    if not courses:
        return "No courses found", 404

    default_course = next(iter(courses))
    return render_template('index.html', courses=courses, default_course=default_course)

@app.route('/get_universities/<course>', methods=['GET'])
def get_universities(course):
    """Return university data for a selected course."""
    data = load_data()
    normalized_course = course.strip().lower()
    filtered_data = [entry for entry in data if entry['course'].strip().lower() == normalized_course]

    if not filtered_data:
        return jsonify({"error": f"No data found for the selected course: {course}"}), 404

    return jsonify(filtered_data)

@app.route('/get_courses/<university>', methods=['GET'])
def get_courses(university):
    """Return courses for the selected university."""
    data = load_data()
    courses = {entry['course'] for entry in data if entry['university'] == university}
    return jsonify(list(courses))

@app.route('/update', methods=['GET', 'POST'])
def update():
    """Handles updating the university course data."""
    if request.method == 'POST':
        try:
            university = request.form['university']
            course = request.form['course']
            gmat_score = request.form.get('gmat', type=float) or None
            gre_score = request.form.get('gre', type=float) or None
            experience_years = float(request.form['experience'])
            gpa = float(request.form['gpa'])
            toefl_score = request.form.get('toefl', type=float) or None
            ielts_score = request.form.get('ielts', type=float) or None

            data = load_data()
            logger.info(f"Form submitted with data: {request.form}")

            for entry in data:
                if entry['university'] == university and entry['course'] == course:
                    update_entry(entry, gmat_score, gre_score, experience_years, gpa, toefl_score, ielts_score)
                    break

            save_data(data)
            logger.info(f"Updated data successfully for {university} - {course}")
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Error updating data: {e}")
            return "Error updating data", 500

    data = load_data()
    universities = {entry['university'] for entry in data}
    return render_template('update.html', universities=list(universities))

def update_entry(entry, gmat_score, gre_score, experience_years, gpa, toefl_score, ielts_score):
    """Helper function to update entry data and averages."""
    gmat_count, gre_count, exp_count, gpa_count, toefl_count, ielts_count = (
        int(entry.get('gmat_count', 0)),
        int(entry.get('gre_count', 0)),
        int(entry.get('experience_count', 0)),
        int(entry.get('gpa_count', 0)),
        int(entry.get('toefl_count', 0)),
        int(entry.get('ielts_count', 0)),
    )

    if gmat_score is not None:
        entry['gmat_average'] = (float(entry.get('gmat_average', 0)) * gmat_count + gmat_score) / (gmat_count + 1)
        entry['gmat_count'] = gmat_count + 1

    if gre_score is not None:
        entry['gre_average'] = (float(entry.get('gre_average', 0)) * gre_count + gre_score) / (gre_count + 1)
        entry['gre_count'] = gre_count + 1

    entry['experience_average'] = (float(entry.get('experience_average', 0)) * exp_count + experience_years) / (exp_count + 1)
    entry['experience_count'] = exp_count + 1

    entry['gpa_average'] = (float(entry.get('gpa_average', 0)) * gpa_count + gpa) / (gpa_count + 1)
    entry['gpa_count'] = gpa_count + 1

    if toefl_score is not None:
        entry['toefl_average'] = (float(entry.get('toefl_average', 0)) * toefl_count + toefl_score) / (toefl_count + 1)
        entry['toefl_count'] = toefl_count + 1

    if ielts_score is not None:
        entry['ielts_average'] = (float(entry.get('ielts_average', 0)) * ielts_count + ielts_score) / (ielts_count + 1)
        entry['ielts_count'] = ielts_count + 1

if __name__ == '__main__':
    app.run(debug=os.getenv("DEBUG", "False") == "True")
