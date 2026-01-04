import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export default function NotFound() {
    const navigate = useNavigate()

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100">
            <div className="text-center">
                <h1 className="text-6xl font-bold text-gray-800 mb-4">404</h1>
                <p className="text-xl text-gray-600 mb-8">Página não encontrada</p>
                <Button onClick={() => navigate('/')}>
                    Voltar para Home
                </Button>
            </div>
        </div>
    )
}
