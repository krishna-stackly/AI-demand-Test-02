import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from './admin/components/Toast';

// User-facing site
import Home from './user/pages/Home';

// Admin panel
import Login from './admin/pages/Authentication/Login';
import ForgotPassword from './admin/pages/Authentication/ForgotPassword';
import OTP from './admin/pages/Authentication/Otp';
import ResetPassword from './admin/pages/Authentication/ResetPassword';

function App() {
  return (
    <>
      <Router>
        <Routes>
          {/* User-facing site: / */}
          <Route path="/" element={<Home />} />

          {/* Admin panel: /admin/* — matches the redirects axiosConfig.js
              already issues (window.location.href = "/admin/login"), so no
              basename or vite `base` config is needed. */}
          <Route path="/admin" element={<Navigate to="/admin/login" replace />} />
          <Route path="/admin/login" element={<Login />} />
          <Route path="/admin/forgot-password" element={<ForgotPassword />} />
          <Route path="/admin/otp" element={<OTP />} />
          <Route path="/admin/reset-password" element={<ResetPassword />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
      <ToastContainer />
    </>
  );
}

export default App;
