/**
 * Cameras.tsx - Cameras Page
 * Main page for camera management
 */

import MainLayout from '../components/layout/MainLayout';
import { CamerasManager } from '../components/cameras/CamerasManager';

export function Cameras() {
    return (
        <MainLayout>
            <CamerasManager />
        </MainLayout>
    );
}

export default Cameras;
