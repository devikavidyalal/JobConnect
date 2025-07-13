// Set the min attribute for the application deadline to today's date
document.addEventListener('DOMContentLoaded', function () {
    const today = new Date().toISOString().split('T')[0]; // Format today's date as YYYY-MM-DD
    const applicationDeadlineInput = document.getElementById('application_deadline');
    applicationDeadlineInput.setAttribute('min', today);
});

// Salary Field Validation (Client-side)
const salaryInput = document.getElementById('salary');
salaryInput.addEventListener('input', function () {
    const salaryValue = salaryInput.value;
    if (isNaN(salaryValue) || salaryValue <= 0) {
        salaryInput.setCustomValidity("Please enter a valid salary number.");
    } else {
        salaryInput.setCustomValidity("");
    }
});
