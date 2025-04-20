// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // File input validation
    const answerSheetInput = document.getElementById('answer_sheet');
    const answerKeyInput = document.getElementById('answer_key');
    
    if (answerSheetInput) {
        answerSheetInput.addEventListener('change', function() {
            validateFileInput(this, ['jpg', 'jpeg', 'png', 'pdf']);
        });
    }
    
    if (answerKeyInput) {
        answerKeyInput.addEventListener('change', function() {
            validateFileInput(this, ['jpg', 'jpeg', 'png', 'pdf', 'txt']);
        });
    }
    
    // Auto-close alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000);
    });
});

// Function to validate file input
function validateFileInput(input, allowedExtensions) {
    const file = input.files[0];
    if (!file) return;
    
    const fileName = file.name;
    const fileExtension = fileName.split('.').pop().toLowerCase();
    
    if (!allowedExtensions.includes(fileExtension)) {
        alert(`Invalid file type. Allowed types: ${allowedExtensions.join(', ')}`);
        input.value = '';
    }
    
    // Check file size (max 16MB)
    const maxSize = 16 * 1024 * 1024; // 16MB in bytes
    if (file.size > maxSize) {
        alert('File size exceeds the maximum limit of 16MB.');
        input.value = '';
    }
}
