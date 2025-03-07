// API Base URL
const API_BASE_URL = 'http://localhost:5432/api';

document.addEventListener('DOMContentLoaded', () => {
    const userForm = document.getElementById('userForm');
    
    userForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        // Get form values
        const userUserId = document.getElementById('userUserId').value.trim();
        const userName = document.getElementById('userName').value.trim();
        const userEmail = document.getElementById('userEmail').value.trim();
        const userRole = document.getElementById('userRole').value;
        
        // Validate form data
        if (!userUserId) {
            alert('Please enter a User ID');
            return;
        }
        if (!userName) {
            alert('Please enter a Name');
            return;
        }
        if (!userEmail) {
            alert('Please enter an Email');
            return;
        }
        if (!userRole) {
            alert('Please select a Role');
            return;
        }
        
        // Validate email format
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(userEmail)) {
            alert('Please enter a valid email address');
            return;
        }
        
        const userData = {
            userId: userUserId,
            name: userName,
            email: userEmail,
            role: userRole
        };
        
        try {
            const response = await fetch(`${API_BASE_URL}/users`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(userData)
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || `HTTP error! status: ${response.status}`);
            }
            
            alert('User added successfully!');
            window.location.href = '/users';
        } catch (error) {
            console.error('Error adding user:', error);
            alert('Error adding user: ' + error.message);
        }
    });
}); 