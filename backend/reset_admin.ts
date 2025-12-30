
import { Database } from './src/database/db';
import { UserModel } from './src/models/user';
import { config } from './src/config/env';
import path from 'path';

async function resetAdmin() {
    console.log('Initializing DB connection...');
    const db = new Database();
    await db.initialize();

    const userModel = new UserModel(db);
    const adminUser = config.admin.user;
    const adminPass = config.admin.password;

    console.log(`Checking for admin user: ${adminUser}`);
    const existing = await userModel.findByUsername(adminUser);

    if (existing) {
        console.log('Admin user exists. Resetting password...');
        // Since we don't have a direct updatePassword method exposed in the snippet I read,
        // I'll delete and recreate, or use raw SQL if needed. 
        // But wait, UserModel usually has update or I can just delete it.
        // Let's try to delete and recreate to be safe and ensure clean state.
        await db.run('DELETE FROM users WHERE username = ?', [adminUser]);
        console.log('Old admin user deleted.');
    }

    console.log(`Creating admin user: ${adminUser} / ${adminPass}`);
    try {
        await userModel.create({
            username: adminUser,
            email: 'admin@example.com',
            password: adminPass
        });
        console.log('Admin user created successfully!');
    } catch (e) {
        console.error('Failed to create admin user:', e);
    }

    await db.close();
}

resetAdmin().catch(console.error);
