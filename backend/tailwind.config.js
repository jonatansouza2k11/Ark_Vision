/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./templates/**/*.html",
        "./static/**/*.js",
    ],
    theme: {
        extend: {
            colors: {
                'dark': {
                    'bg': '#0f172a',
                    'card': '#1e293b',
                    'border': '#334155',
                },
                'accent': {
                    'blue': '#3b82f6',
                    'cyan': '#06b6d4',
                }
            },
            boxShadow: {
                'glow-blue': '0 0 25px rgba(59, 130, 246, 0.4)',
            }
        },
    },
    plugins: [],
}
