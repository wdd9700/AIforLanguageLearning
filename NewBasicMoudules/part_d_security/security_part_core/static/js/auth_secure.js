/**
 * Secure Authentication JavaScript Module
 * 
 * Security features:
 * - No token storage in localStorage/memory (all HttpOnly cookies)
 * - CSRF token handling for state-changing operations
 * - Automatic token refresh before expiry
 * 
 * Tokens are stored in HttpOnly cookies by the backend.
 * Frontend only handles CSRF token for POST/PUT/DELETE requests.
 */

const API_BASE_URL = '';

// CSRF token storage (not sensitive, can be in memory)
let _csrfToken = null;

// ==================== Utility Functions ====================

function showMessage(message, type = 'success') {
    const msgDiv = document.getElementById('message');
    if (!msgDiv) return;
    msgDiv.textContent = message;
    msgDiv.className = `message ${type}`;
    msgDiv.style.display = 'block';
    
    setTimeout(() => {
        msgDiv.style.display = 'none';
    }, 3000);
}

function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    if (input) {
        input.type = input.type === 'password' ? 'text' : 'password';
    }
}

// Read cookie by name
function getCookie(name) {
    const match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return match ? match.pop() : '';
}

// Get CSRF token from cookie
function getCsrfToken() {
    if (!_csrfToken) {
        _csrfToken = getCookie('csrf_token');
    }
    return _csrfToken;
}

// ==================== API Functions ====================

/**
 * User Login
 * Backend sets HttpOnly cookies for access_token and refresh_token
 */
async function login(username, password) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            credentials: 'include',  // Important: send/receive cookies
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok && data.code === 200) {
            // Store CSRF token for future requests
            if (data.data && data.data.csrf_token) {
                _csrfToken = data.data.csrf_token;
            }
            return {
                success: true,
                data: data.data,
                message: data.message
            };
        } else if (response.status === 429) {
            return {
                success: false,
                message: 'Too many login attempts. Please try again after 5 minutes.'
            };
        } else {
            return {
                success: false,
                message: data.message || 'Login failed'
            };
        }
    } catch (error) {
        console.error('Login error:', error);
        return {
            success: false,
            message: 'Network error, please try again later'
        };
    }
}

/**
 * User Registration
 */
async function register(username, email, password) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, email, password })
        });
        
        const data = await response.json();
        
        if (response.ok && data.code === 201) {
            return {
                success: true,
                data: data.data,
                message: data.message
            };
        } else {
            return {
                success: false,
                message: data.message || 'Registration failed'
            };
        }
    } catch (error) {
        console.error('Register error:', error);
        return {
            success: false,
            message: 'Network error, please try again later'
        };
    }
}

/**
 * Get Current User Info
 * Backend reads access_token from HttpOnly cookie
 */
async function getCurrentUser() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            method: 'GET',
            credentials: 'include'  // Send cookies
        });
        
        const data = await response.json();
        
        if (response.ok && data.code === 200) {
            return {
                success: true,
                data: data.data
            };
        } else if (response.status === 401) {
            // Token expired, try to refresh
            const refreshed = await refreshToken();
            if (refreshed.success) {
                // Retry the request
                return getCurrentUser();
            }
            return {
                success: false,
                message: 'Session expired, please login again'
            };
        } else {
            return {
                success: false,
                message: data.message || 'Failed to get user info'
            };
        }
    } catch (error) {
        console.error('Get user error:', error);
        return {
            success: false,
            message: 'Network error'
        };
    }
}

/**
 * Refresh Access Token
 * Backend reads refresh_token from HttpOnly cookie
 */
async function refreshToken() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            credentials: 'include'  // Send cookies
        });
        
        const data = await response.json();
        
        if (response.ok && data.code === 200) {
            return {
                success: true,
                data: data.data
            };
        } else {
            return {
                success: false,
                message: data.message || 'Session expired, please login again'
            };
        }
    } catch (error) {
        console.error('Refresh token error:', error);
        return {
            success: false,
            message: 'Network error'
        };
    }
}

/**
 * User Logout
 * Clears HttpOnly cookies on backend
 */
async function apiLogout() {
    try {
        const csrf = getCsrfToken();
        const headers = {};
        if (csrf) {
            headers['X-CSRF-Token'] = csrf;
        }
        
        const response = await fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            credentials: 'include',
            headers: headers
        });
        
        const data = await response.json();
        
        // Clear CSRF token
        _csrfToken = null;
        
        return {
            success: response.ok && data.code === 200,
            message: data.message
        };
    } catch (error) {
        console.error('Logout error:', error);
        return {
            success: false,
            message: 'Network error'
        };
    }
}

// ==================== Auto Refresh ====================

/**
 * Setup automatic token refresh
 * Refreshes access token every 10 minutes (token expires in 15 minutes)
 */
function setupTokenRefresh() {
    // Refresh every 10 minutes
    setInterval(async () => {
        const result = await refreshToken();
        if (!result.success) {
            console.log('Token refresh failed, user may need to re-login');
        }
    }, 10 * 60 * 1000); // 10 minutes
}

// Setup on page load
document.addEventListener('DOMContentLoaded', setupTokenRefresh);

// ==================== Exports ====================

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        login,
        register,
        getCurrentUser,
        refreshToken,
        apiLogout,
        showMessage,
        togglePassword,
        getCsrfToken
    };
}
