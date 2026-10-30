import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import { AppProvider } from './context/AppContext.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  // No StrictMode: in dev it runs every effect twice, which doubles AI calls on the free tier.
  <BrowserRouter>
    <AppProvider>
      <App />
    </AppProvider>
  </BrowserRouter>,
)
