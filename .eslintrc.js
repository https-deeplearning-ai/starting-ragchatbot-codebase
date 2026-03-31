module.exports = {
    env: {
        browser: true,
        es2021: true,
    },
    extends: ['eslint:recommended'],
    parserOptions: {
        ecmaVersion: 2021,
    },
    globals: {
        marked: 'readonly',
    },
    rules: {
        'no-unused-vars': 'warn',
        'no-console': 'warn',
    },
};
