import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import './index.css';
import { ClerkProvider } from '@clerk/react';

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
const app = <BrowserRouter><App /></BrowserRouter>;

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {publishableKey?.startsWith('pk_') ? <ClerkProvider publishableKey={publishableKey} afterSignOutUrl="/" appearance={{ variables: { colorPrimary: '#65e0b4', colorBackground: '#14212a', colorText: '#e9eef1', colorTextSecondary: '#9cabb4', colorInputBackground: '#0c171f', colorInputText: '#e9eef1', borderRadius: '8px' } }}>{app}</ClerkProvider> : app}
  </React.StrictMode>,
);
