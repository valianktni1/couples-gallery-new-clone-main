import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'sonner'
import GalleryPage from './pages/GalleryPage'

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-center" />
      <Routes>
        <Route path="/gallery/:token" element={<GalleryPage />} />
        <Route path="/" element={
          <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center">
            <h1 className="text-2xl font-serif text-gray-900">Gallery V2</h1>
          </div>
        } />
      </Routes>
    </BrowserRouter>
  )
}

export default App
