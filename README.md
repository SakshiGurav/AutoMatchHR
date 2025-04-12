# AutoMatchHR


#  Resume Matcher System

A smart, end-to-end pipeline that parses **Job Descriptions** and **Candidate CVs**, matches them using NLP and rule-based logic, computes match scores, shortlists top candidates, and auto-generates interview invitation emails. The project also comes with a **Streamlit dashboard** for easy interaction and visualization.


##  Features

- Parse Job Descriptions (JDs) and extract key skills & education
- Parse CVs (PDFs) to extract candidate profiles
- Compute match scores based on skill, education & tech stack overlap
- Shortlist candidates above a given threshold
- Auto-generate interview emails
- Streamlit UI to explore the data and results



##  Technologies Used

- Python 
- Streamlit
- spaCy (NLP)
- pdfminer (PDF extraction)
- SQLite (Database)
- pandas



##  Installation

1. **Clone this repository:**


git clone https://github.com/yourusername/resume-matcher.git
cd resume-matcher


2. **Install required packages:**


pip install -r requirements.txt


3. **Install NLP model (if not installed):**


python -m spacy download en_core_web_sm



##  How to Use

### Step 1: Prepare Files

- A CSV file containing job descriptions (`job_description.csv`) with columns: `Job Title`, `Job Description`
- A ZIP file of CV PDFs (e.g., `200_cv_pdfs.zip`)

### Step 2: Run Streamlit App


streamlit run JD_app.py


### Step 3: Upload Files

- Upload your `job_description.csv` and `ZIP of CVs` in the sidebar
- Click on `Run Matching Pipeline `

### Step 4: View Results

Explore the five tabs:
-  JDs Summary
-  Candidates
-  Match Scores
-  Shortlist
-  Emails



##  Match Score Logic

Match Score =  
**70% Skill Overlap** +  
**30% Education Match**

> Candidates above 80% score are shortlisted by default.



##  Auto Email Sample


To: candidate@example.com  
Subject: Interview Invitation – Data Scientist Role

Dear John Doe,

You’ve been shortlisted for the Data Scientist position. Please confirm your availability for an interview on:

- April 11, 10:00 AM
- April 12, 2:30 PM

Regards,  
HR Team



##  Project Structure


JD_app.py                # Main Streamlit app with backend pipeline
job_match_system.db      # Auto-created SQLite database
job_description.csv      # Input file (uploaded via UI)
200_cv_pdfs.zip          # Input file (uploaded via UI)
unzipped_cvs/            # Extracted CV PDFs (temp folder)


