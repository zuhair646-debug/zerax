import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowRight, Home } from 'lucide-react';

/**
 * Universal back button — appears top-right (RTL) on every internal page.
 * • If browser history exists → goes back one step.
 * • Otherwise → falls back to homepage `/`.
 * • Always shows a tiny home icon to "escape" to landing in one click.
 */
export const BackButton = ({ to = null, label = 'رجوع', className = '' }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleBack = () => {
    if (to) {
      navigate(to);
    } else if (window.history.length > 1 && location.key !== 'default') {
      navigate(-1);
    } else {
      navigate('/');
    }
  };

  return (
    <div className={`flex items-center gap-2 ${className}`} data-testid="back-button-wrapper">
      <button
        onClick={handleBack}
        data-testid="back-button"
        className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/70 hover:bg-slate-700 text-gray-300 hover:text-white border border-slate-600 hover:border-slate-500 transition-all text-sm"
      >
        <ArrowRight className="w-4 h-4" />
        <span>{label}</span>
      </button>
      <button
        onClick={() => navigate('/')}
        data-testid="home-button"
        className="inline-flex items-center justify-center w-9 h-9 rounded-lg bg-slate-800/70 hover:bg-slate-700 text-gray-300 hover:text-white border border-slate-600 hover:border-slate-500 transition-all"
        title="الصفحة الرئيسية"
      >
        <Home className="w-4 h-4" />
      </button>
    </div>
  );
};

export default BackButton;
