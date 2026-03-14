$(document).ready(function() {
    
    // Page load animations
    $('.room-card').hide().fadeIn(800);
    $('.success-card').slideDown(800);

    // Form Validation logic
    $('#bookingForm').on('submit', function(e) {
        
        // Clear previous error styles
        $('.is-invalid').removeClass('is-invalid');
        
        let isValid = true;
        let checkInVal = $('#check_in_date').val();
        let checkOutVal = $('#check_out_date').val();
        
        if (!checkInVal) {
            $('#check_in_date').addClass('is-invalid');
            isValid = false;
        }
        
        if (!checkOutVal) {
            $('#check_out_date').addClass('is-invalid');
            isValid = false;
        }

        if (checkInVal && checkOutVal) {
            let checkInDate = new Date(checkInVal);
            let checkOutDate = new Date(checkOutVal);
            
            // Validate dates
            if (checkOutDate <= checkInDate) {
                alert('Error: Check-out date must be after the check-in date.');
                $('#check_out_date').addClass('is-invalid');
                isValid = false;
            }
            
            // Validate Check-in is not in the past
            let today = new Date();
            today.setHours(0,0,0,0);
            if (checkInDate < today) {
                alert('Error: Check-in date cannot be in the past.');
                $('#check_in_date').addClass('is-invalid');
                isValid = false;
            }
        }
        
        if (!isValid) {
            e.preventDefault(); // Prevent form submission
        } else {
            // Confirm dialog before submitting sumbit
            if (!confirm('Are you sure you want to confirm this booking?')) {
                e.preventDefault();
            } else {
                $('#submitBtn').text('Processing...').prop('disabled', true);
            }
        }
    });

    // Set minimum date to today for date inputs
    // Format YYYY-MM-DD
    let today = new Date().toISOString().split('T')[0];
    $('#check_in_date').attr('min', today);
    $('#check_out_date').attr('min', today);
});
