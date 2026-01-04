// Main JavaScript for Campus Complaint Portal

// Utility function for API calls
async function apiCall(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// UPVOTE FUNCTION
async function upvote(complaintId) {
    try {
        console.log('Upvoting complaint:', complaintId);
        
        // Get the button that was clicked
        const button = event.target.closest("button");
        
        if (!button) {
            console.error('Button not found');
            return;
        }
        
        // Disable the button immediately
        const originalContent = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<span>Upvoting...</span>';

        const response = await fetch(`/complaint/${complaintId}/upvote`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        console.log('Upvote response:', data);

        if (data.success) {
            showNotification("Upvoted successfully!", "success");

            // Update button with new count
            button.innerHTML = `<span>👍 Upvoted (${data.upvotes})</span>`;
            button.classList.add("text-green-600", "font-semibold");
            button.classList.remove("text-blue-600");
            
            // Keep button disabled so user can't upvote again
            // button.disabled = true; // Already disabled
            
            console.log('Upvote successful, new count:', data.upvotes);
        } else {
            console.error('Upvote failed:', data.error);
            showNotification("Error: " + (data.error || "Failed to upvote"), "error");
            
            // Re-enable button on error
            button.disabled = false;
            button.innerHTML = originalContent;
        }
    } catch (error) {
        console.error("Upvote error:", error);
        showNotification("Failed to upvote. Please try again.", "error");
        
        // Re-enable button on error
        const button = event.target.closest("button");
        if (button) {
            button.disabled = false;
            button.innerHTML = button.innerHTML.replace('Upvoting...', 'Upvote');
        }
    }
}

// Make upvote function globally available
window.upvote = upvote;

async function apiCall(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}



// Show loading indicator
function showLoading(element) {
    element.disabled = true;
    element.classList.add('opacity-50', 'cursor-not-allowed');
}

// Hide loading indicator
function hideLoading(element) {
    element.disabled = false;
    element.classList.remove('opacity-50', 'cursor-not-allowed');
}

// Show notification
function showNotification(message, type = 'info') {
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        warning: 'bg-yellow-500',
        info: 'bg-blue-500'
    };
    
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 ${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg z-50 fade-in`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Format date for display
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (days < 7) return `${days} day${days > 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

// Copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showNotification('Failed to copy', 'error');
    });
}

// Initialize tooltips
function initTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    
    tooltips.forEach(element => {
        element.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'absolute bg-gray-800 text-white text-xs rounded py-1 px-2 z-50';
            tooltip.textContent = this.getAttribute('data-tooltip');
            tooltip.style.top = `${this.offsetTop - 30}px`;
            tooltip.style.left = `${this.offsetLeft}px`;
            
            this.appendChild(tooltip);
        });
        
        element.addEventListener('mouseleave', function() {
            const tooltip = this.querySelector('.absolute');
            if (tooltip) tooltip.remove();
        });
    });
}

// Auto-save form data
function autoSaveForm(formId, storageKey) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    // Load saved data
    const savedData = localStorage.getItem(storageKey);
    if (savedData) {
        const data = JSON.parse(savedData);
        Object.keys(data).forEach(key => {
            const input = form.querySelector(`[name="${key}"]`);
            if (input) input.value = data[key];
        });
    }
    
    // Save on input
    form.addEventListener('input', function() {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        localStorage.setItem(storageKey, JSON.stringify(data));
    });
    
    // Clear on submit
    form.addEventListener('submit', function() {
        localStorage.removeItem(storageKey);
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add fade-in animation to main content
    const main = document.querySelector('main');
    if (main) {
        main.classList.add('fade-in');
    }
    
    // Initialize tooltips
    initTooltips();
    
    // Auto-save complaint form
    autoSaveForm('complaintForm', 'draft_complaint');
    
    // Add smooth scroll behavior
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
    
    // Confirm before leaving page with unsaved changes
    let formChanged = false;
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('change', () => formChanged = true);
        form.addEventListener('submit', () => formChanged = false);
    });
    
    window.addEventListener('beforeunload', function(e) {
        if (formChanged) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
});

// Export functions for use in other scripts
window.complaintPortal = {
    apiCall,
    showLoading,
    hideLoading,
    showNotification,
    formatDate,
    copyToClipboard
};