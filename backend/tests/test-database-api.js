
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
            token = regRes.data.data?.accessToken || regRes.data.accessToken || regRes.data.token;
            console.log('Registered successfully');
        } catch (e) {
            console.log('Registration failed:', e.message);
            return;
        }

        const headers = { Authorization: `Bearer ${token}` };

        // 2. Test Student Profile
        console.log('Testing Student Profile...');
        await axios.post(`${API_URL}/learning/profile`, {
            level: 'intermediate',
            goals: ['pass_exam', 'travel'],
            interests: ['technology', 'music']
        }, { headers });
        const profileRes = await axios.get(`${API_URL}/learning/profile`, { headers });
        console.log('Profile:', JSON.stringify(profileRes.data.data, null, 2));

        // 3. Test Vocabulary Due
        console.log('Testing Vocabulary Due...');
        // Add a word via query first (which adds to vocab table now)
        await axios.post(`${API_URL}/query/vocabulary`, { word: 'epiphany' }, { headers });
        
        const dueRes = await axios.get(`${API_URL}/learning/vocabulary/due`, { headers });
        console.log('Due Words:', JSON.stringify(dueRes.data.data, null, 2));

        // 4. Test Essay History
        console.log('Testing Essay History...');
        // Add an essay via correct first
        await axios.post(`${API_URL}/essay/correct`, { text: 'I like apple.', language: 'english' }, { headers });
        
        const essaysRes = await axios.get(`${API_URL}/learning/essays`, { headers });
        console.log('Essays:', JSON.stringify(essaysRes.data.data, null, 2));

        // 5. Test Analysis
        console.log('Testing Learning Analysis...');
        const analysisRes = await axios.post(`${API_URL}/learning/analyze`, { dimension: 'overall' }, { headers });
        console.log('Analysis Report:', analysisRes.data.data.report.substring(0, 100) + '...');

    } catch (e) {
        console.error('Test failed:', e.response?.data || e.message);
    }
}

test();
