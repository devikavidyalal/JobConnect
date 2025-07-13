from pymongo import MongoClient

# Establish a connection to MongoDB
client = MongoClient('mongodb://localhost:27017/')

# Database name: jobconnect
db = client['jobconnect']

# Collection names
users_collection = db['users']
jobs_collection = db['jobs']
applications_collection = db['applications']

# Example data insertion (Optional)
sample_data = [
    {"username": "TestUser", "password": "password123", "usertype": "job_seeker"},
    {"username": "TestRecruiter", "password": "password123", "usertype": "recruiter"}
]

admin_user = {
    "username": "admin",
    "password": "admin123",  # Plaintext for now, but ideally hashed in production
    "email": "admin@jobconnect.com",
    "usertype": "admin"
}
users_collection.insert_one(admin_user)
print("Admin user created successfully!")
# Insert sample data if needed
if users_collection.count_documents({}) == 0:
    users_collection.insert_many(sample_data)
    print("Sample data inserted into 'users' collection.")


