import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import EvaluadorPrincipal from './App.jsx'
import { VisorLogs } from './verLogs.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<EvaluadorPrincipal />} />
        <Route path="/logs" element={<VisorLogs />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)