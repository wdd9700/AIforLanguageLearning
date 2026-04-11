/**
 * 安全认证前端 JavaScript 模块
 * 
 * 包含功能：
 * - 用户登录
 * - 用户注册
 * - Token 管理
 * - 用户信息获取
 * - 退出登录
 * 
 * 对应后端：auth_routes.py, auth_core.py
 */

const API_BASE_URL = '';

// In-memory token storage (not localStorage) for better security
let _accessToken = null;
let _tokenExpiry = null;

function setAccessToken(token, expiresInSeconds) {
    _accessToken = token;
    _tokenExpiry = Date.now() + (expiresInSeconds * 1000);
}

function getAccessToken() {
    // Check if token is expired
    if (_tokenExpiry && Date.now() > _tokenExpiry) {
        _accessToken = null;
        _tokenExpiry = null;
    }
    return _accessToken;
}

function clearAccessToken() {
    _accessToken = null;
    _tokenExpiry = null;
}

// ==================== 工具函数 ====================

/**
 * 显示消息提示
 * @param {string} message - 消息内容
 * @param {string} type - 消息类型: success/error
 */
function showMessage(message, type = 'success') {
    const msgDiv = document.getElementById('message');
    msgDiv.textContent = message;
    msgDiv.className = `message ${type}`;
    msgDiv.style.display = 'block';
    
    setTimeout(() => {
        msgDiv.style.display = 'none';
    }, 3000);
}

/**
 * 切换密码可见性
 * @param {string} inputId - 密码输入框 ID
 */
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    input.type = input.type === 'password' ? 'text' : 'password';
}

// Read cookie helper
function getCookie(name) {
    const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
}

// ==================== API 调用函数 ====================

/**
 * 用户登录
 * @param {string} username - 用户名
 * @param {string} password - 密码
 * @returns {Promise<Object>} 登录结果
 */
async function login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.code === 200) {
            // Store access token in memory (not localStorage)
            setAccessToken(data.data.access_token, data.data.expires_in);
            return {
                success: true,
                data: data.data,
                message: data.message
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
 * 用户注册
 * @param {string} username - 用户名
 * @param {string} email - 邮箱
 * @param {string} password - 密码
 * @returns {Promise<Object>} 注册结果
 */
async function register(username, email, password) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username,
                email,
                password
            })
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
 * 获取当前用户信息
 * @returns {Promise<Object>} 用户信息
 */
async function getCurrentUser() {
    const token = getAccessToken();
    
    if (!token) {
        // Try to refresh if no valid token in memory
        const refreshResult = await refreshToken();
        if (!refreshResult.success) {
            return { success: false, message: 'Not logged in' };
        }
        token = getAccessToken();
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
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
 * 刷新 Access Token
 * @returns {Promise<Object>} 刷新结果
 */
async function refreshToken() {
    // Use cookie-based refresh (cookie `refresh_token`) with CSRF double-submit
    const csrf = getCookie('csrf_token');
    try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrf
            },
            body: JSON.stringify({})
        });
        
        const data = await response.json();
        
        if (response.ok && data.code === 200) {
            // Store new access token in memory
            setAccessToken(data.data.access_token, data.data.expires_in);
            return {
                success: true,
                data: data.data
            };
        } else {
            return {
                success: false,
                    message: data.message || 'Refresh failed'
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
 * 退出登录
 * @param {string} token - Access Token
 * @returns {Promise<Object>} 退出结果
 */
async function apiLogout(token) {
    try {
        let opts = { method: 'POST' };
        if (token) {
            opts.headers = { 'Authorization': `Bearer ${token}` };
        } else {
            // cookie-based logout requires CSRF header
            const csrf = getCookie('csrf_token');
            opts = { method: 'POST', credentials: 'include', headers: { 'X-CSRF-Token': csrf } };
        }

        const response = await fetch(`${API_BASE_URL}/auth/logout`, opts);
        const data = await response.json();

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

// ==================== 自动刷新 Token ====================

/**
 * 设置 Token 自动刷新
 * 在 Token 过期前自动刷新
 */
function setupTokenRefresh() {
    // Check every 10 minutes (access token expires in 15 minutes)
    setInterval(async () => {
        const token = getAccessToken();
        
        if (token) {
            // Try to refresh token before it expires
            const result = await refreshToken();
            if (!result.success) {
                 console.log('Token refresh failed, may need to re-login');
            }
        }
    }, 10 * 60 * 1000); // 10 minutes
}

// 页面加载时设置自动刷新
document.addEventListener('DOMContentLoaded', setupTokenRefresh);

// ==================== 导出（供其他脚本使用） ====================

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        login,
        register,
        getCurrentUser,
        refreshToken,
        apiLogout,
        showMessage,
        togglePassword
    };
}
