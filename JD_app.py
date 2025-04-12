
# Step 1: Initialize SQLite DB and Tables 
import sqlite3
import os
import pandas as pd
import re
import spacy
from pdfminer.high_level import extract_text

nlp = spacy.load("en_core_web_sm")

def init_db():
    conn = sqlite3.connect("job_match_system.db")
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS job_descriptions (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT,
            raw_description TEXT,
            extracted_skills TEXT,
            education TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            education TEXT,
            experience_years INTEGER,
            skills TEXT,
            certifications TEXT,
            tech_stack TEXT,
            raw_text TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS match_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            candidate_id INTEGER,
            match_score REAL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS shortlisted (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            candidate_id INTEGER,
            match_score REAL
        )
    ''')

    conn.commit()
    conn.close()


# =================== 📄 Step 2: Job Description Parser ===================
def extract_from_jd(text):
    doc = nlp(text)
    skills = []
    education = []
    for sent in doc.sents:
        if "skill" in sent.text.lower():
            skills.append(sent.text)
        if any(deg in sent.text.lower() for deg in ["bachelor", "master", "phd", "degree"]):
            education.append(sent.text)

    cleaned_skills = ", ".join(set(re.findall(r'[A-Za-z\+\#\.]+', ' '.join(skills))))
    cleaned_edu = ", ".join(set(re.findall(r'(Bachelor|Master|PhD|Diploma)[^.,\n]+', ' '.join(education), re.I)))

    return {
        "skills": cleaned_skills,
        "education": cleaned_edu
    }

def process_job_descriptions(file_path):
    df = pd.read_csv(file_path, encoding='ISO-8859-1')  # Fix for UnicodeDecodeError
    conn = sqlite3.connect("job_match_system.db")
    c = conn.cursor()

    for _, row in df.iterrows():
        parsed = extract_from_jd(row['Job Description'])
        c.execute('''
            INSERT INTO job_descriptions (job_title, raw_description, extracted_skills, education)
            VALUES (?, ?, ?, ?)
        ''', (row['Job Title'], row['Job Description'], parsed['skills'], parsed['education']))

    conn.commit()
    conn.close()

# =================== 📄 Step 3: CV Parser ===================
def extract_from_cv(text):
    doc = nlp(text)
    name = ""
    email = ""
    skills = []
    education = []
    certifications = []
    experience_years = 0
    tech_stack = []

    for ent in doc.ents:
        if ent.label_ == "PERSON" and not name:
            name = ent.text
        if ent.label_ == "ORG" and "certified" in ent.sent.text.lower():
            certifications.append(ent.sent.text)

    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    email = email_match.group() if email_match else ""

    edu_matches = re.findall(r"(Bachelor|Master|Diploma|PhD)[^.,\n]+", text, re.I)
    education = list(set(edu_matches))

    experience_matches = re.findall(r'(\d+)[+]?\s+years', text)
    if experience_matches:
        experience_years = max([int(y) for y in experience_matches])

    tech_keywords = re.findall(r'\b(Java|Python|SQL|MySQL|Kafka|Spring Boot|Azure DevOps|AWS|C\+\+|Power BI|TensorFlow|React|Node|Docker)\b', text, re.I)
    tech_stack = list(set(tech_keywords))

    skills_section = re.findall(r'Skills[\s\S]{0,200}', text, re.I)
    skill_words = re.findall(r'[A-Za-z\+\#\.]{2,}', ' '.join(skills_section))
    skills = list(set(skill_words))

    return {
        "name": name,
        "email": email,
        "education": ", ".join(education),
        "experience": experience_years,
        "skills": ", ".join(skills),
        "certifications": ", ".join(certifications),
        "tech_stack": ", ".join(tech_stack)
    }

def process_cv_folder(folder_path):
    conn = sqlite3.connect("job_match_system.db")
    c = conn.cursor()

    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            text = extract_text(os.path.join(folder_path, filename))
            parsed = extract_from_cv(text)
            c.execute('''
                INSERT INTO candidates (name, email, education, experience_years, skills, certifications, tech_stack, raw_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (parsed['name'], parsed['email'], parsed['education'], parsed['experience'], parsed['skills'], parsed['certifications'], parsed['tech_stack'], text))

    conn.commit()
    conn.close()

   # =================== 🧠 Step 4: Matching Engine ===================
def compute_match_score(jd_skills, cv_skills, jd_edu, cv_edu, cv_tech):
    jd_skills_set = set(jd_skills.lower().split(", "))
    cv_skills_set = set(cv_skills.lower().split(", "))
    tech_stack_set = set(cv_tech.lower().split(", "))

    skill_score = len(jd_skills_set & (cv_skills_set | tech_stack_set)) / len(jd_skills_set) if jd_skills_set else 0
    edu_score = 1 if jd_edu.lower() in cv_edu.lower() else 0.5

    return round(0.7 * skill_score + 0.3 * edu_score, 2) * 100

def run_matching():
    conn = sqlite3.connect("job_match_system.db")
    c = conn.cursor()
    c2 = conn.cursor()

    c.execute("SELECT * FROM job_descriptions")
    jobs = c.fetchall()

    for job in jobs:
        job_id, _, _, jd_skills, jd_edu = job
        c2.execute("SELECT * FROM candidates")
        candidates = c2.fetchall()

        for cand in candidates:
            cand_id, _, _, cv_edu, _, cv_skills, _, cv_tech, _ = cand
            score = compute_match_score(jd_skills, cv_skills, jd_edu, cv_edu, cv_tech)
            c2.execute('''
                INSERT INTO match_scores (job_id, candidate_id, match_score)
                VALUES (?, ?, ?)
            ''', (job_id, cand_id, score))

    conn.commit()
    conn.close()

 # =================== ✅ Step 5: Shortlisting ===================
def shortlist(threshold=80):
    conn = sqlite3.connect("job_match_system.db")
    c = conn.cursor()

    c.execute("SELECT * FROM match_scores WHERE match_score >= ?", (threshold,))
    for row in c.fetchall():
        _, job_id, cand_id, score = row
        c.execute("INSERT INTO shortlisted (job_id, candidate_id, match_score) VALUES (?, ?, ?)", (job_id, cand_id, score))

    conn.commit()
    conn.close()

    # =================== 📧 Step 6: Generate Emails ===================
def generate_emails():
    conn = sqlite3.connect("job_match_system.db")
    c = conn.cursor()

    c.execute('''
        SELECT s.job_id, s.candidate_id, j.job_title, c.name, c.email
        FROM shortlisted s
        JOIN job_descriptions j ON s.job_id = j.job_id
        JOIN candidates c ON s.candidate_id = c.candidate_id
    ''')

    for job_id, cand_id, job_title, name, email in c.fetchall():
        message = f"""
        Subject: Interview Invitation – {job_title} Role

        Dear {name},

        You’ve been shortlisted for the {job_title} position. Please confirm your availability for an interview on:

        • April 11, 10:00 AM
        • April 12, 2:30 PM

        Regards,
        HR Team
        """
        print(f"Sending email to: {email}\n{message}\n")

    conn.close()

# =================== 🚀 Main Execution ===================
if __name__ == "__main__":
    from google.colab import files
    import zipfile
    import os

    # Step 1: Upload job_description.csv and ZIP folder of CVs
    print("📁 Please upload job_description.csv and 200_cv_pdfs.zip")
    uploaded = files.upload()  # Upload both files when prompted

    # Step 2: Extract the ZIP file
    zip_path = "CVs1.zip"
    extract_path = "/content/200_cv_pdfs"
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

    # Step 3: Set correct paths
    job_desc_csv_path = "/content/job_description.csv"
    cv_folder_path = extract_path

    # Step 4: Run the full pipeline
    init_db()
    process_job_descriptions(job_desc_csv_path)
    process_cv_folder(cv_folder_path)
    run_matching()
    shortlist(threshold=0.80)
    generate_emails()


import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(layout="wide")

st.sidebar.title("🔍 Resume Matcher System")
uploaded_jd = st.sidebar.file_uploader("Upload Job Descriptions CSV", type="csv")
uploaded_cv_zip = st.sidebar.file_uploader("Upload ZIP of Candidate CVs", type="zip")
run_pipeline = st.sidebar.button("Run Matching Pipeline 🚀")

if run_pipeline:
    # Save and extract files, then run pipeline functions
    with st.spinner("Running pipeline..."):
        init_db()
        process_job_descriptions(uploaded_jd.name)
        with open("uploaded_cv.zip", "wb") as f: f.write(uploaded_cv_zip.read())
        extract_path = "unzipped_cvs"
        with zipfile.ZipFile("uploaded_cv.zip", 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        process_cv_folder(extract_path)
        run_matching()
        shortlist()

    st.success("✅ Pipeline Completed")

# Tabs to visualize steps
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📄 JDs Summary", "👩‍💻 Candidates", "🤝 Match Scores", "✅ Shortlist", "📧 Emails"])

with tab1:
    st.header("📄 Job Description Summary")
    df = pd.read_sql_query("SELECT * FROM job_descriptions", sqlite3.connect("job_match_system.db"))
    st.dataframe(df)

with tab2:
    st.header("👩‍💻 Parsed Candidate Info")
    df = pd.read_sql_query("SELECT * FROM candidates", sqlite3.connect("job_match_system.db"))
    st.dataframe(df)

with tab3:
    st.header("🤝 Matching Scores")
    df = pd.read_sql_query("SELECT * FROM match_scores", sqlite3.connect("job_match_system.db"))
    st.dataframe(df)

with tab4:
    st.header("✅ Shortlisted Candidates")
    df = pd.read_sql_query('''
        SELECT s.match_score, j.job_title, c.name, c.email
        FROM shortlisted s
        JOIN job_descriptions j ON s.job_id = j.job_id
        JOIN candidates c ON s.candidate_id = c.candidate_id
    ''', sqlite3.connect("job_match_system.db"))
    st.dataframe(df)

with tab5:
    st.header("📧 Generated Emails")
    df = pd.read_sql_query('''
        SELECT j.job_title, c.name, c.email
        FROM shortlisted s
        JOIN job_descriptions j ON s.job_id = j.job_id
        JOIN candidates c ON s.candidate_id = c.candidate_id
    ''', sqlite3.connect("job_match_system.db"))

    for index, row in df.iterrows():
        email_msg = f"""
        **To:** {row['email']}
        **Subject:** Interview Invitation – {row['job_title']} Role

        Dear {row['name']},

        You’ve been shortlisted for the **{row['job_title']}** position. Please confirm your availability for an interview on:

        - April 11, 10:00 AM  
        - April 12, 2:30 PM  

        Regards,  
        HR Team
        """
        st.markdown(email_msg)

