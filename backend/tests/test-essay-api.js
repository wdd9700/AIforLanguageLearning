
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
            console.log('Registration failed, trying login...');
            // In case user exists (unlikely with timestamp)
        }

        if (!token) {
            console.error('Failed to get token');
            return;
        }

        // 2. Test Text Correction
        console.log('Testing Text Correction...');
        const textRes = await axios.post(`${API_URL}/essay/correct`, {
            text: "I go to school yesterday. It is very fun.",
            language: "english"
        }, {
            headers: { Authorization: `Bearer ${token}` }
        });
        console.log('Text Correction Result:', JSON.stringify(textRes.data, null, 2));

        // 3. Test Image Correction (Mocking OCR if possible, or just sending invalid image to see error handling)
        console.log('Testing Image Correction (Expect Error or Mock Result)...');
        try {
            await axios.post(`${API_URL}/essay/correct`, {
                image: "invalid_base64",
                language: "english"
            }, {
                headers: { Authorization: `Bearer ${token}` }
            });
        } catch (e) {
            console.log('Image Correction failed as expected (invalid image):', e.response?.data || e.message);
        }

    } catch (e) {
        console.error('Test failed:', e.response?.data || e.message);
    }
}

test();
