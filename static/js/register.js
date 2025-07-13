document.addEventListener('DOMContentLoaded', function() {
    const userTypeSelect = document.getElementById('usertype');
    const recruiterFields = document.getElementById('recruiterFields');

    userTypeSelect.addEventListener('change', function() {
        if (userTypeSelect.value === 'recruiter') {
            recruiterFields.style.display = 'block';
        } else {
            recruiterFields.style.display = 'none';
        }
    });
});
