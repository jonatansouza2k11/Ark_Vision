/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'dark-bg': '#0a0a0a',
                'dark-card': '#1a1a1a',
                'dark-border': '#2a2a2a',
                'accent-cyan': '#00D9FF',
                'accent-blue': '#3B82F6',
                'accent-purple': '#8B5CF6',
            },
            animation: {
                'slide-in': 'slideIn 0.3s ease-out',
                'slide-out': 'slideOut 0.3s ease-out',
            },
            keyframes: {
                slideIn: {
                    '0%': { transform: 'translateX(400px)', opacity: '0' },
                    '100%': { transform: 'translateX(0)', opacity: '1' },
                },
                slideOut: {
                    '0%': { transform: 'translateX(0)', opacity: '1' },
                    '100%': { transform: 'translateX(400px)', opacity: '0' },
                },
            },
        },
    },
    plugins: [],
}
