
const axios = require('axios');

const API_URL = 'http://localhost:3006/api';

async function test() {
    try {
        // 1. Register/Login
        const email = `test${Date.now()}@example.com`;
        const password = 'Password123!';
        const username = `user${Date.now()}`;

        console.log('Registering user:', email);
        let token;
        try {
            const regRes = await axios.post(`${API_URL}/auth/register`, {
                username,
                email,
                password
            });
            console.log('Registration response:', regRes.data);
            token = regRes.data.data?.accessToken || regRes.data.accessToken || regRes.data.token;
            console.log('Registered successfully');
        } catch (e) {
            console.log('Registration failed:', e.message);
            return;
        }

        if (!token) {
            console.error('Failed to get token');
            return;
        }

        // 2. Test Vocabulary Query
        console.log('Testing Vocabulary Query...');
        const words = ['serendipity', '人工智能'];
        
        for (const word of words) {
            console.log(`Querying: ${word}`);
            try {
                const queryRes = await axios.post(`${API_URL}/query/vocabulary`, {
                    word: word
                }, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                console.log('Query Result:', JSON.stringify(queryRes.data, null, 2));
            } catch (e) {
                console.error(`Query failed for ${word}:`, e.response?.data || e.message);
            }
        }

    } catch (e) {
        console.error('Test failed:', e.response?.data || e.message);
    }
}

test();
