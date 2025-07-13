// manage_applications.js

const applications = JSON.parse(document.getElementById('applicationsData').textContent);
const jobDetails = JSON.parse(document.getElementById('jobDetailsData').textContent);

function showApplicants(jobId) {
    const applicantsSection = document.getElementById('applicantsSection');
    const jobTitleElement = document.getElementById('jobTitle');
    const applicantsList = document.getElementById('applicantsList');

    jobTitleElement.textContent = jobDetails[jobId];
    applicantsList.innerHTML = '';

    const filteredApplications = applications.filter(app => app.job_id === jobId);

    if (filteredApplications.length > 0) {
        filteredApplications.forEach(app => {
            applicantsList.innerHTML += `
                <div class="bg-white p-4 rounded-lg shadow-md mb-4">
                    <p><strong>Name:</strong> ${app.name}</p>
                    <p><strong>Email:</strong> ${app.email}</p>
                    <p><strong>Resume:</strong> <a href="${app.resume_url}" target="_blank" class="text-blue-500">View Resume</a></p>
                    <p><strong>Status:</strong> ${app.status}</p>
                    <form method="POST" action="/update_application_status">
                        <input type="hidden" name="application_id" value="${app._id}">
                        <select name="status" class="border p-2 rounded-md">
                            <option value="Pending" ${app.status === 'Pending' ? 'selected' : ''}>Pending</option>
                            <option value="Shortlisted" ${app.status === 'Shortlisted' ? 'selected' : ''}>Shortlisted</option>
                            <option value="Rejected" ${app.status === 'Rejected' ? 'selected' : ''}>Rejected</option>
                        </select>
                        <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded-md ml-2">Update Status</button>
                    </form>
                </div>
            `;
        });
    } else {
        applicantsList.innerHTML = '<p>No applicants for this job.</p>';
    }

    applicantsSection.classList.remove('hidden');
}
