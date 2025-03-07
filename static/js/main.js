// API Base URL
const API_BASE_URL = 'http://localhost:5432/api';

// Show/Hide Sections
function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(section => {
        section.classList.add('hidden');
    });
    document.getElementById(sectionId).classList.remove('hidden');
    if (sectionId === 'users') {
        loadUsers();
    } else if (sectionId === 'books') {
        loadBooks();
    } else if (sectionId === 'dashboard') {
        loadDashboardStats();
    }
}

// User Management Functions
async function loadUsers() {
    try {
        console.log('Fetching users...');
        const response = await fetch(`${API_BASE_URL}/users`);
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        const users = await response.json();
        console.log('Received users:', users);
        
        const tbody = document.getElementById('usersTableBody');
        tbody.innerHTML = '';
        
        users.forEach(user => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">${user.userId || ''}</td>
                <td class="px-6 py-4 whitespace-nowrap">${user.name}</td>
                <td class="px-6 py-4 whitespace-nowrap">${user.email}</td>
                <td class="px-6 py-4 whitespace-nowrap">${user.role}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <button onclick="showUserForm('${user._id}')" class="text-blue-600 hover:text-blue-900 mr-3">Edit</button>
                    <button onclick="deleteUser('${user._id}')" class="text-red-600 hover:text-red-900">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading users:', error);
        alert('Error loading users: ' + error.message);
    }
}

function showUserForm(userId = null) {
    const modal = document.getElementById('userFormModal');
    const formTitle = document.getElementById('userFormTitle');
    const form = document.getElementById('userForm');
    
    formTitle.textContent = userId ? 'Edit User' : 'Add New User';
    form.reset();
    
    if (userId) {
        document.getElementById('userId').value = userId;
        // Load user data and populate form
        fetch(`${API_BASE_URL}/users/${userId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(user => {
                document.getElementById('userUserId').value = user.userId || '';
                document.getElementById('userName').value = user.name;
                document.getElementById('userEmail').value = user.email;
                document.getElementById('userRole').value = user.role;
            })
            .catch(error => {
                console.error('Error loading user data:', error);
                alert('Error loading user data: ' + error.message);
            });
    } else {
        document.getElementById('userId').value = '';
    }
    
    modal.classList.remove('hidden');
}

function closeUserForm() {
    document.getElementById('userFormModal').classList.add('hidden');
}

async function handleUserSubmit(event) {
    event.preventDefault();
    
    // Get form values
    const userId = document.getElementById('userId').value;
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
    
    console.log('Submitting user data:', userData);
    
    try {
        const url = userId ? `${API_BASE_URL}/users/${userId}` : `${API_BASE_URL}/users`;
        const method = userId ? 'PUT' : 'POST';
        
        console.log(`Making ${method} request to ${url}`);
        
        const response = await fetch(url, {
            method: method,
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(userData)
        });

        console.log('Response status:', response.status);
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || `HTTP error! status: ${response.status}`);
        }

        console.log('Success:', result);
        
        closeUserForm();
        loadUsers();
        alert(userId ? 'User updated successfully!' : 'User added successfully!');
    } catch (error) {
        console.error('Error saving user:', error);
        alert('Error saving user: ' + error.message);
    }
}

async function deleteUser(userId) {
    if (confirm('Are you sure you want to delete this user?')) {
        try {
            const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            loadUsers();
            alert('User deleted successfully!');
        } catch (error) {
            console.error('Error deleting user:', error);
            alert('Error deleting user: ' + error.message);
        }
    }
}

// Book Management Functions
async function loadBooks() {
    try {
        const response = await fetch(`${API_BASE_URL}/books`);
        const books = await response.json();
        const tbody = document.getElementById('booksTableBody');
        tbody.innerHTML = '';
        
        books.forEach(book => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">${book.title}</td>
                <td class="px-6 py-4 whitespace-nowrap">${book.author}</td>
                <td class="px-6 py-4 whitespace-nowrap">${book.isbn}</td>
                <td class="px-6 py-4 whitespace-nowrap">${book.status}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <button onclick="editBook('${book._id}')" class="text-blue-600 hover:text-blue-900 mr-3">Edit</button>
                    <button onclick="deleteBook('${book._id}')" class="text-red-600 hover:text-red-900">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading books:', error);
        alert('Error loading books');
    }
}

function showBookForm(bookId = null) {
    const modal = document.getElementById('bookFormModal');
    const formTitle = document.getElementById('bookFormTitle');
    const form = document.getElementById('bookForm');
    
    formTitle.textContent = bookId ? 'Edit Book' : 'Add New Book';
    form.reset();
    
    if (bookId) {
        document.getElementById('bookId').value = bookId;
        // Load book data and populate form
        fetch(`${API_BASE_URL}/books/${bookId}`)
            .then(response => response.json())
            .then(book => {
                document.getElementById('bookTitle').value = book.title;
                document.getElementById('bookAuthor').value = book.author;
                document.getElementById('bookIsbn').value = book.isbn;
                document.getElementById('bookStatus').value = book.status;
            });
    } else {
        document.getElementById('bookId').value = '';
    }
    
    modal.classList.remove('hidden');
}

function closeBookForm() {
    document.getElementById('bookFormModal').classList.add('hidden');
}

async function handleBookSubmit(event) {
    event.preventDefault();
    const bookId = document.getElementById('bookId').value;
    const bookData = {
        title: document.getElementById('bookTitle').value,
        author: document.getElementById('bookAuthor').value,
        isbn: document.getElementById('bookIsbn').value,
        status: document.getElementById('bookStatus').value
    };
    
    try {
        if (bookId) {
            await fetch(`${API_BASE_URL}/books/${bookId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bookData)
            });
        } else {
            await fetch(`${API_BASE_URL}/books`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bookData)
            });
        }
        closeBookForm();
        loadBooks();
        loadDashboardStats();
    } catch (error) {
        console.error('Error saving book:', error);
        alert('Error saving book');
    }
}

async function deleteBook(bookId) {
    if (confirm('Are you sure you want to delete this book?')) {
        try {
            await fetch(`${API_BASE_URL}/books/${bookId}`, {
                method: 'DELETE'
            });
            loadBooks();
            loadDashboardStats();
        } catch (error) {
            console.error('Error deleting book:', error);
            alert('Error deleting book');
        }
    }
}

// Dashboard Functions
async function loadDashboardStats() {
    try {
        const [usersResponse, booksResponse] = await Promise.all([
            fetch(`${API_BASE_URL}/users`),
            fetch(`${API_BASE_URL}/books`)
        ]);
        
        const users = await usersResponse.json();
        const books = await booksResponse.json();
        
        document.getElementById('totalUsers').textContent = users.length;
        document.getElementById('totalBooks').textContent = books.length;
        document.getElementById('availableBooks').textContent = books.filter(book => book.status === 'available').length;
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    showSection('dashboard');
    
    // Form submission handlers
    document.getElementById('userForm').addEventListener('submit', handleUserSubmit);
    document.getElementById('bookForm').addEventListener('submit', handleBookSubmit);
}); 