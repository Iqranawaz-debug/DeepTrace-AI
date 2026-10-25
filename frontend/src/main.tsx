import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider, createBrowserRouter } from 'react-router-dom'
import { App } from './app/App'
import './styles/fonts.css'
import './styles/tokens.css'
import './styles/app.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode><RouterProvider router={createBrowserRouter([{ path: "*", element: <App /> }])} /></StrictMode>,
)
