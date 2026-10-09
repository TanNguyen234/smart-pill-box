import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import DongHo from './DongHo.tsx'

const isDongHoRoute = window.location.pathname === '/dongho';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {isDongHoRoute ? <DongHo /> : <App />}
  </StrictMode>,
)
