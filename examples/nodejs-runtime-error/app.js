#!/usr/bin/env node

/**
 * User Data Processor
 * Fetches user data and generates a summary report
 */

const users = [
    { id: 1, name: 'Alice', email: 'alice@example.com', status: 'active' },
    { id: 2, name: 'Bob', email: 'bob@example.com', status: 'active' },
    { id: 3, name: 'Charlie', email: 'charlie@example.com', status: 'inactive' },
    { id: 4, name: 'Diana', email: 'diana@example.com', status: 'active' }
];

function getUserStats(users) {
    const stats = {
        total: users.length,
        active: users.filter(u => u.status === 'active').length,
        inactive: users.filter(u => u.status === 'inactive').length
    };
    return stats;
}

function generateReport(users) {
    console.log('Generating user report...\n');

    const stats = getUserStats(users);

    console.log('=== User Statistics ===');
    console.log(`Total Users: ${stats.total}`);
    console.log(`Active Users: ${stats.active}`);
    console.log(`Inactive Users: ${stats.inactive}`);
    console.log('');

    // Bug: Trying to access property on undefined
    // The getUserById function doesn't exist, but we're calling it
    console.log('=== Featured User ===');
    const featuredUser = getUserById(1);  // This function is not defined!
    console.log(`Name: ${featuredUser.name}`);
    console.log(`Email: ${featuredUser.email}`);
    console.log(`Status: ${featuredUser.status}`);
}

function main() {
    console.log('User Data Processor v1.0\n');
    generateReport(users);
    console.log('\nReport generated successfully!');
}

main();
