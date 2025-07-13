from flask import Flask, render_template, request, redirect, flash, session, url_for
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from db import users_collection
import secrets
from bson.objectid import ObjectId
from pymongo import DESCENDING
from datetime import datetime, date
import os
from flask_mail import Mail, Message
from bson import ObjectId
from functools import wraps
import random


def convert_objectid_to_str(data):
    """Recursively converts all ObjectId instances in the data to string."""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)  # Convert ObjectId to string
            elif isinstance(value, (dict, list)):
                convert_objectid_to_str(value)
    elif isinstance(data, list):
        for item in data:
            convert_objectid_to_str(item)
    return data


app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = '16d71a4d4d85faf90aa4a54a53881fbb'  
app.config['MONGO_URI'] = 'mongodb://localhost:27017/jobconnect'

# Initialize MongoDB
mongo = PyMongo(app)

users_collection = mongo.db.users
jobs_collection = mongo.db.jobs
applications_collection = mongo.db.applications
saved_jobs_collection = mongo.db.saved_jobs



# Configure Flask-Mail
# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'tvdevika24@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'glii qvop ezsx pajv'  # Replace with your email password
app.config['MAIL_DEFAULT_SENDER'] = 'tvdevika24@gmail.com'  # Replace with your email

mail = Mail(app)


# File upload configuration
UPLOAD_FOLDER = 'static/resumes'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def send_email(subject, recipient, body):
    message = Message(subject, recipients=[recipient])
    message.body = body
    try:
        mail.send(message)
    except Exception as e:
        print(f"Error sending email: {e}")


# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phonenumber = request.form['phonenumber']
        usertype = request.form['usertype']

        # Check if user already exists
        existing_user = users_collection.find_one({'username': username})
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('register'))


        if usertype == 'recruiter':
            company_name = request.form.get('company_name')
            company_details = request.form.get('company_details')
            status = 'pending'  # Recruiters need admin approval
            flash('Registration successful! Wait for admin approval.', 'info')
        else:
            company_name = None
            company_details = None
            status = 'approved'  # Job seekers are approved immediately


        # Insert new user into the database
        new_user = {'username': username, 'password': password, 'email': email, 'phonenumber' : phonenumber, 'usertype': usertype, 'company_name': company_name, 'company_details': company_details, 'status': status}
        users_collection.insert_one(new_user)
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Verify user credentials
        user = users_collection.find_one({'username': username, 'password': password})
        if user:
            if user['usertype'] == 'recruiter' and user['status'] != 'approved':
                flash('Your account is pending approval by the admin.', 'error')
                return redirect(url_for('login'))
            session['username'] = username
            session['usertype'] = user['usertype']

            # Redirect to the appropriate dashboard based on user type
            if user['usertype'] == 'jobseeker':
                return redirect(url_for('seeker_dashboard'))
            elif user['usertype'] == 'recruiter':
                return redirect(url_for('recruiter_dashboard'))
            elif user['usertype'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('home'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


# Generic Dashboard Route
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# Job Seeker Dashboard
@app.route('/seeker_dashboard')
@login_required
def seeker_dashboard():
    return render_template('seeker_dashboard.html')

# Recruiter Dashboard
@app.route('/recruiter_dashboard')
@login_required
def recruiter_dashboard():
    # Fetch jobs posted by the recruiter
    posted_jobs = jobs_collection.find({'recruiter_username': session['username']})
    return render_template('recruiter_dashboard.html', posted_jobs=posted_jobs)

@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if request.method == 'POST':
        job_id = request.form.get('job_id')
        user_id = request.form.get('user_id')
        action = request.form.get('action')
        result = None

        # Handle recruiter actions
        if user_id:
            if action == 'approve':
                users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'status': 'approved'}})
                flash('Recruiter approved successfully!', 'success')
                return redirect(url_for('recruiter_management'))
    
            elif action == 'reject':
                # Fetch the recruiter's username before deletion
                recruiter = users_collection.find_one({'_id': ObjectId(user_id)})
                if recruiter:
                    recruiter_username = recruiter['username']

                    # Delete jobs associated with the recruiter
                    jobs_collection.delete_many({'recruiter_username': recruiter_username})

                    # Delete the recruiter from the database
                    result = users_collection.delete_one({'_id': ObjectId(user_id)})

                    if result.deleted_count > 0:
                        flash('Recruiter rejected and deleted successfully!', 'success')
                    else:
                        flash('Recruiter not found or deletion failed!', 'error')
                else:
                    flash('Recruiter not found!', 'error')

                return redirect(url_for('recruiter_management'))

    
            elif action == 'delete':
                # Fetch the recruiter's username before deletion
                recruiter = users_collection.find_one({'_id': ObjectId(user_id)})
                if recruiter:
                    recruiter_username = recruiter['username']

                    # Delete jobs associated with the recruiter
                    jobs_collection.delete_many({'recruiter_username': recruiter_username})

                    # Delete the recruiter
                    result = users_collection.delete_one({'_id': ObjectId(user_id)})

                    if result.deleted_count > 0:
                        flash('Recruiter and their associated jobs deleted successfully!', 'success')
                    else:
                        flash('Recruiter not found or deletion failed!', 'error')
                else:
                    flash('Recruiter not found!', 'error')

            return redirect(url_for('recruiter_management'))


        # Handle job actions
        elif job_id:
            if action == 'approve':
                jobs_collection.update_one({'_id': ObjectId(job_id)}, {'$set': {'status': 'approved'}})
                flash('Job approved successfully!', 'success')
                return redirect(url_for('job_management'))
            elif action == 'reject':
                jobs_collection.update_one({'_id': ObjectId(job_id)}, {'$set': {'status': 'rejected'}})
                flash('Job rejected successfully!', 'success')
                return redirect(url_for('job_management'))
            elif action == 'delete':
                result = jobs_collection.update_one({'_id': ObjectId(job_id)}, {'$set': {'status': 'deleted'}})
                if result.modified_count > 0:
                    flash('Job deleted successfully!', 'success')
                else:
                    flash('Job not found or deletion failed!', 'error')
                return redirect(url_for('job_management'))

            return redirect(url_for('admin_dashboard'))

    # Fetch All Recruiters
    all_recruiters = users_collection.find({'usertype': 'recruiter'}).sort([('_id', DESCENDING)])
    all_jobs = jobs_collection.find().sort([('_id', DESCENDING)])
    return render_template('admin_dashboard.html', recruiters=all_recruiters, jobs=all_jobs)



# Job Posting Route
@app.route('/post_job', methods=['GET', 'POST'])
@login_required
def post_job():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        salary = request.form['salary']
        application_deadline = request.form['application_deadline']
        company = request.form['company']
        phone_number = request.form['phone_number']
        mail_id = request.form['mail_id']
        location = request.form['location']
        job_type = request.form['job_type']
        skills = request.form['skills']
        today_date = datetime.today().strftime('%Y-%m-%d')
        # Ensure salary is in correct format
        try:
            salary = float(salary)
        except ValueError:
            flash('Please enter a valid salary amount.', 'error')
            return redirect(url_for('post_job'))

        # Ensure application deadline is not in the past
        today = datetime.today().date()  # Convert `datetime.datetime` to `date`
        deadline = datetime.strptime(application_deadline, '%Y-%m-%d').date()
        if deadline < today:
            flash('The application deadline cannot be in the past.', 'error')
            return redirect(url_for('post_job'))

        # Insert job post into the database
        job_post = {
            'title': title,
            'description': description,
            'company': company,  # Add the company field
            'phone_number': phone_number,  # Add the phone number field
            'mail_id': mail_id,  # Add the mail ID field
            'location': location,  # Add the location field
            'salary': salary,
            'job_type' : job_type,
            'skills' : skills,
            'application_deadline': application_deadline,
            'recruiter_username': session['username'],  # Make sure the session contains a username
            'status': 'pending'
        }
        jobs_collection = mongo.db.jobs  # Replace with your actual MongoDB collection
        jobs_collection.insert_one(job_post)
        flash('Job posted successfully!', 'success')
        return redirect(url_for('recruiter_dashboard'))

    return render_template('post_job.html')

@app.route('/recruiter_management')
@login_required
def recruiter_management():
    recruiters = users_collection.find({
        'usertype': 'recruiter',
        'status': {'$in': ['pending', 'approved']}})

    # Convert the cursor to a list
    recruiters = list(recruiters)

    # Convert ObjectId to string for each recruiter
    for recruiter in recruiters:
        recruiter['_id'] = str(recruiter['_id'])

    return render_template('recruiter_management.html', recruiters=recruiters)



@app.route('/job_management')
@login_required
def job_management():
    # You can retrieve jobs from the database and pass them to the template
    jobs = jobs_collection.find({}, {'title': 1, 'company': 1, 'status': 1}).sort([('_id', DESCENDING)])
    return render_template('job_management.html', jobs=jobs)


# Display Approved Jobs with Search and Filter Functionality
@app.route('/search_jobs', methods=['GET'])
@login_required
def search_jobs():
    query = request.args.get('query', '')
    salary_range = request.args.get('salary_range', '')
    job_type = request.args.get('job_type', '')

    filters = {"status": "approved"}  # Base filter to show only approved jobs

    # Search Functionality (if search query is provided)
    if query:
        filters["$or"] = [
            {"title": {"$regex": query, "$options": "i"}},
            {"company": {"$regex": query, "$options": "i"}},
            {"location": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]
    
    # Apply Salary Range Filter (if selected)
    if salary_range:
        if salary_range == '200000+':
            filters["salary"] = {"$gte": 200000}
        else:
            min_salary, max_salary = map(int, salary_range.split('-'))
            filters["salary"] = {"$gte": min_salary, "$lte": max_salary}
    
    # Apply Job Type Filter (if selected)
    if job_type:
        filters["job_type"] = job_type
    
    # Fetch jobs based on combined filters
    approved_jobs = jobs_collection.find(filters).sort([('_id', DESCENDING)])
    
    return render_template('search_jobs.html', jobs=approved_jobs)




# Display Job Details Page
@app.route('/job_details/<job_id>')
@login_required
def job_details(job_id):
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    if job:
        job['_id'] = str(job['_id'])  # Convert ObjectId to string
        return render_template('job_details.html', job=job)
    else:
        return "Job not found", 404



@app.route('/apply_job/<job_id>', methods=['POST'])
@login_required
def apply_for_job(job_id):
    # Ensure that job_id is now passed to this function
    if 'username' not in session:
        flash('You need to log in to apply for a job.', 'error')
        return redirect(url_for('login'))

    applicant_username = session['username']

    # Form data
    name = request.form.get('name')
    age = request.form.get('age')
    skills = request.form.get('skills')
    experience = request.form.get('experience')
    phone_number = request.form.get('phone_number')
    mail_id = request.form.get('mail_id')
    details = request.form.get('details')
    resume = request.files['resume']

    # Save resume file
    resume_filename = None
    if resume and allowed_file(resume.filename):
        resume_filename = f"{applicant_username}_{resume.filename}"
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_filename)
        resume.save(resume_path)
    else:
        flash('Invalid file type. Only PDF, DOC, and DOCX allowed.', 'error')
        return redirect(url_for('job_details', job_id=job_id))

    # Insert into the database
    new_application = {
        'job_id': job_id,
        'applicant_username': applicant_username,
        'name': name,
        'age': age,
        'skills': skills,
        'experience': experience,
        'phone_number': phone_number,
        'mail_id': mail_id,
        'details': details,
        'resume_path': resume_filename,
        'status': 'Applied',
        'application_date': datetime.now()
    }

    try:
        applications_collection.insert_one(new_application)
        flash('Application submitted successfully!', 'success')
    except Exception as e:
        flash('There was an error submitting your application. Please try again.', 'error')

    return redirect(url_for('job_details', job_id=job_id))  # Make sure you are redirecting to the correct page


@app.route('/manage_applications', methods=['GET'])
@login_required
def manage_applications():
    recruiter_username = session.get('username')
    if not recruiter_username:
        flash('Please log in to manage applications.', 'error')
        return redirect(url_for('login'))
    
    query = request.args.get('query', '')  # Get the search query from the request

    # Fetch jobs posted by the recruiter with optional search filter
    search_filter = {'recruiter_username': recruiter_username}
    
    if query:
        search_filter['title'] = {'$regex': query, '$options': 'i'}  # Case-insensitive search
    
    posted_jobs = list(jobs_collection.find(search_filter))
    
    # Fetch applications related to those jobs
    job_ids = [job['_id'] for job in posted_jobs]
    applications = list(applications_collection.find({'job_id': {'$in': job_ids}}))
    
    # Convert ObjectIds to strings for easier rendering
    applications = convert_objectid_to_str(applications)
    job_details = {str(job['_id']): job['title'] for job in posted_jobs}
    
    return render_template('manage_applications.html', applications=applications, job_details=job_details)



@app.route('/manage_applications_status')
@login_required
def manage_applications_status():
    job_id = request.args.get('job_id')
    job_title = request.args.get('job_title')
    
    # Fetch applications for the specific job
    applications = list(applications_collection.find({'job_id': job_id}))
    
    return render_template('manage_applications_status.html', 
                           applications=applications, 
                           job_title=job_title)
    

@app.route('/update_application_status', methods=['POST'])
@login_required
def update_application_status():
    application_id = request.form['application_id']
    status = request.form['status']
    
    application = applications_collection.find_one({'_id': ObjectId(application_id)})
    job_id = application['job_id']
    seeker_username = application['applicant_username']
    seeker = users_collection.find_one({'username': seeker_username})
    seeker_email = seeker['email']
    
    # Get job details for email content
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    job_title = job['title']
    company_name = job['company']

    if status == 'rejected':
        # Remove the application if rejected
        applications_collection.delete_one({'_id': ObjectId(application_id)})
        flash('Application has been rejected and removed from the list.', 'danger')

        # Prepare email body
        subject = f"Job Application Rejected for {job_title}"
        body = f"Dear {seeker_username},\n\n" \
               f"Your application for the job '{job_title}' at {company_name} has been rejected.\n\n" \
               "Thank you for your interest.\n\nBest regards,\nJobConnect"
        send_email(subject, seeker_email, body)

    elif status == 'shortlisted' or status == 'selected':
        # Update the application status
        applications_collection.update_one(
            {'_id': ObjectId(application_id)},
            {'$set': {'status': status}}
        )
        flash(f'Application status updated to {status} successfully.', 'success')

        # Prepare email body
        subject = f"Job Application {status.capitalize()} for {job_title}"
        body = f"Dear {seeker_username},\n\n" \
               f"Congratulations! Your application for the job '{job_title}' at {company_name} has been {status}.\n\n" \
               "We will contact you soon with further information.\n\nBest regards,\nJobConnect"
        send_email(subject, seeker_email, body)

    return redirect(request.referrer)


@app.route('/view_applications')
@login_required
def view_applications():
    username = session['username']  # Assuming user is logged in
    applications = list(applications_collection.find({'applicant_username': username}))
    job_details = {str(job['_id']): job['title'] for job in jobs_collection.find()}
    return render_template('view_applications.html', applications=applications, job_details=job_details)



@app.route('/view_application_details/<application_id>')
@login_required
def view_application_details(application_id):
    try:
        application = applications_collection.find_one({'_id': ObjectId(application_id)})
        
        if application:
            job = jobs_collection.find_one({'_id': ObjectId(application['job_id'])})
            
            if job:
                job['_id'] = str(job['_id'])  # Convert ObjectId to string
                application['_id'] = str(application['_id'])  # Convert ObjectId to string
                return render_template('application_details.html', job=job, application=application)
            else:
                flash('Job not found!', 'error')
                return redirect(url_for('view_applications'))
        else:
            flash('Application not found!', 'error')
            return redirect(url_for('view_applications'))
    except Exception as e:
        flash(f'Error occurred: {str(e)}', 'error')
        return redirect(url_for('view_applications'))




@app.route('/apply_job', methods=['POST'])
@login_required
def apply_job():
    # Get form data
    job_id = request.form.get('job_id')
    name = request.form.get('name')
    age = request.form.get('age')
    skills = request.form.get('skills')
    experience = request.form.get('experience')
    resume = request.files.get('resume')
    details = request.form.get('details')
    
    # Handle file upload (e.g., save resume file)
    if resume and allowed_file(resume.filename):
        filename = f"{session['username']}_{resume.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print("Saving file to:", filepath)  # Debugging output
        resume.save(filepath)

    
    # Example: Save the application details to the database (implement as needed)
    # db.save_application({...})
    
    flash('Application submitted successfully!', 'success')
    return redirect(url_for('job_details', job_id=job_id))


# Example route for job details (make sure this route exists too)
@app.route('/job/<job_id>')
@login_required
def view_job_details(job_id):
    # Fetch job details from the database (implement as needed)
    job = {}  # Replace with actual job data
    return render_template('job_details.html', job=job)


@app.route('/save_job/<job_id>')
@login_required
def save_job(job_id):
    if 'username' not in session:
        flash('You need to log in to save jobs.', 'error')
        return redirect(url_for('login'))

    user_id = session['username']  # Get the logged-in user's username (you can also use an actual user ID if needed)
    saved_job = saved_jobs_collection.find_one({'user_id': user_id, 'job_id': job_id})
    
    if saved_job:
        flash('You have already saved this job.', 'info')
    else:
        saved_jobs_collection.insert_one({'user_id': user_id, 'job_id': job_id})
        flash('Job saved for later!', 'success')

    return redirect(url_for('job_details', job_id=job_id))



@app.route('/saved_jobs', methods=['GET'])
@login_required
def saved_jobs():
    if 'username' not in session:
        flash('Please log in to view saved jobs.', 'error')
        return redirect(url_for('login'))
    
    user_id = session['username']
    
    # Get search and filter parameters from the request
    query = request.args.get('query', '')
    salary_range = request.args.get('salary_range', '')
    job_type = request.args.get('job_type', '')
    
    # Get all saved job IDs for the user
    saved_jobs = saved_jobs_collection.find({'user_id': user_id})
    saved_job_ids = [ObjectId(saved_job['job_id']) for saved_job in saved_jobs]
    
    # Build the filter query for jobs
    filters = {'_id': {'$in': saved_job_ids}}
    
    # Search functionality
    if query:
        filters["$or"] = [
            {"title": {"$regex": query, "$options": "i"}},
            {"company": {"$regex": query, "$options": "i"}},
            {"location": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]
    
    # Salary range filter
    if salary_range:
        if salary_range == "200000+":
            filters["salary"] = {"$gt": 200000}
        else:
            min_salary, max_salary = map(int, salary_range.split('-'))
            filters["salary"] = {"$gte": min_salary, "$lte": max_salary}
    
    # Job type filter
    if job_type:
        filters["job_type"] = job_type
    
    # Fetch jobs from the jobs collection based on filters
    saved_jobs_list = []
    jobs = jobs_collection.find(filters).sort([('_id', -1)])
    for job in jobs:
        job['_id'] = str(job['_id'])  # Convert ObjectId to string
        saved_jobs_list.append(job)
    
    return render_template('saved_jobs.html', saved_jobs=saved_jobs_list)

@app.route('/edit_job', methods=['GET', 'POST'])
@login_required
def edit_job():
    job_id = request.args.get('job_id')
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})

    if request.method == 'POST':
        # Get the updated data from the form
        new_title = request.form['title']
        new_description = request.form['description']
        new_job_type = request.form['job_type']
        new_skills = request.form['skills']
        new_company = request.form['company']
        new_location = request.form['location']
        new_phone_number = request.form['phone_number']
        new_mail_id = request.form['mail_id']
        new_salary = request.form['salary']
        new_application_deadline = request.form['application_deadline']

        # Prepare the data to update
        updated_data = {
            'title': new_title,
            'description': new_description,
            'job_type': new_job_type,
            'skills': new_skills,
            'company': new_company,
            'location': new_location,
            'phone_number': new_phone_number,
            'mail_id': new_mail_id,
            'salary': new_salary,
            'application_deadline': new_application_deadline
        }

        # Update the job in the database
        result = jobs_collection.update_one(
            {'_id': ObjectId(job_id)},
            {'$set': updated_data}
        )

        # Flash success or failure message
        if result.modified_count > 0:
            flash('Job post updated successfully!', 'success')
        else:
            flash('No changes made to the job post.', 'warning')

        return redirect(url_for('manage_applications'))

    return render_template('edit_job.html', job=job)




@app.route('/delete_job/<job_id>', methods=['GET'])
@login_required
def delete_job(job_id):
    # Convert job_id from string to ObjectId
    try:
        job_id = ObjectId(job_id)
    except Exception as e:
        flash('Invalid job ID', 'danger')
        return redirect(url_for('manage_applications'))

    # Delete the job from the jobs collection
    job = jobs_collection.find_one({'_id': job_id})
    if job:
        # Delete the job post
        jobs_collection.delete_one({'_id': job_id})
        
        # Delete all corresponding applications
        applications_collection.delete_many({'job_id': job_id})
        
        # Flash success message with number of applications deleted
        #flash(f'Job post and {applications_collection.deleted_count} applications deleted successfully!', 'success')
    else:
        flash('Job post not found.', 'danger')

    return redirect(url_for('manage_applications'))



# Set cache control headers to prevent cached pages after logout
@app.after_request
def add_cache_control_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# Forgot Password Route
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        user = users_collection.find_one({'username': username})
        if user and user['email'] == email:
            otp = random.randint(100000, 999999)
            session['otp'] = otp
            session['reset_username'] = username
            msg = Message('Your OTP for Password Reset',
                          sender='your_email@example.com',
                          recipients=[email])
            msg.body = f'Your OTP is {otp}. Please enter this to reset your password.'
            mail.send(msg)
            flash('OTP sent to your registered email.', 'success')
            return redirect(url_for('validate_otp'))
        else:
            flash('Invalid username or email.', 'error')
    return render_template('forgot_password.html')

# Validate OTP Route
@app.route('/validate_otp', methods=['GET', 'POST'])
def validate_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        if 'otp' in session and str(session['otp']) == entered_otp:
            flash('OTP validated. Please reset your password.', 'success')
            return redirect(url_for('reset_password'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
    return render_template('validate_otp.html')

# Reset Password Route
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form['password']
        username = session.get('reset_username')
        if username and new_password:
            users_collection.update_one(
                {'username': username},
                {'$set': {'password': new_password}}
            )
            flash('Password has been reset successfully!', 'success')
            session.pop('otp', None)
            session.pop('reset_username', None)
            return redirect(url_for('login'))
        else:
            flash('An error occurred. Please try again.', 'error')
    return render_template('reset_password.html')


# Home Page
@app.route('/')
def home():
    return render_template('home.html')


# Logout Route to Clear Session and Prevent Caching
@app.route('/logout')
def logout():
    session.clear()  # Clear session data on logout
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(debug=True)
