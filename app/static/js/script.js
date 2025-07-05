// Custom JavaScript for Learning Management System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Add Dashboard link to dropdowns that only have My Profile and Logout
    const dropdownMenus = document.querySelectorAll('.dropdown-menu');
    dropdownMenus.forEach(function(menu) {
        const items = menu.querySelectorAll('.dropdown-item');
        
        // Check if this dropdown only has My Profile and Logout
        if (items.length === 2) {
            let hasMyProfile = false;
            let hasLogout = false;
            
            items.forEach(function(item) {
                const text = item.textContent.trim();
                if (text.includes('My Profile')) hasMyProfile = true;
                if (text.includes('Logout')) hasLogout = true;
            });
            
            // If this is the dropdown we're looking for
            if (hasMyProfile && hasLogout) {
                // Get dashboard URLs from data attributes in the body
                const dashboardUrls = {
                    admin: document.body.dataset.adminDashboardUrl || '/admin/dashboard',
                    instructor: document.body.dataset.instructorDashboardUrl || '/instructor/dashboard',
                    student: document.body.dataset.studentDashboardUrl || '/student/dashboard',
                    parent: document.body.dataset.parentDashboardUrl || '/parent/dashboard',
                    guest: document.body.dataset.guestDashboardUrl || '/guest/dashboard'
                };
                
                // Get user role to determine dashboard URL
                const userRole = document.body.dataset.userRole || 'student'; // Default to student if not set
                
                // Create Dashboard link
                const dashboardItem = document.createElement('li');
                const dashboardLink = document.createElement('a');
                
                // Use the URL from data attributes if available
                if (document.body.dataset[userRole + 'DashboardUrl']) {
                    dashboardLink.href = document.body.dataset[userRole + 'DashboardUrl'];
                } else {
                    // Fallback to constructed URL
                    dashboardLink.href = '/' + userRole + '/dashboard';
                }
                
                dashboardLink.className = 'dropdown-item';
                dashboardLink.innerHTML = '<i class="fas fa-tachometer-alt me-2"></i> Dashboard';
                
                dashboardItem.appendChild(dashboardLink);
                
                // Add it at the beginning of the dropdown
                menu.insertBefore(dashboardItem, menu.firstChild);
            }
        }
    });

    // Password confirmation validation
    const passwordField = document.getElementById('password');
    const confirmPasswordField = document.getElementById('confirm_password');
    
    if (passwordField && confirmPasswordField) {
        confirmPasswordField.addEventListener('input', function() {
            if (passwordField.value !== confirmPasswordField.value) {
                confirmPasswordField.setCustomValidity("Passwords do not match");
            } else {
                confirmPasswordField.setCustomValidity("");
            }
        });
    }

    // Sidebar toggle functionality (for mobile)
    const sidebarToggle = document.getElementById('sidebarToggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.body.classList.toggle('sidebar-toggled');
            document.querySelector('.sidebar').classList.toggle('toggled');
        });
    }

    // Close alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Add active class to current navigation item
    const currentLocation = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav a.nav-link');
    
    navLinks.forEach(function(link) {
        if (link.getAttribute('href') === currentLocation) {
            link.classList.add('active');
        }
    });

    // Course search functionality
    const searchInput = document.getElementById('courseSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const courseCards = document.querySelectorAll('.course-card');
            
            courseCards.forEach(function(card) {
                const title = card.querySelector('.card-title').textContent.toLowerCase();
                const description = card.querySelector('.card-text').textContent.toLowerCase();
                
                if (title.includes(searchTerm) || description.includes(searchTerm)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }
}); 